# ragAgent/rag_agent.py
import sys
import os
import logging
from pathlib import Path

# Add the parent directory (RAG) to Python path to access shared modules
current_dir = Path(__file__).parent
rag_dir = current_dir.parent.parent
sys.path.insert(0, str(rag_dir))

from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

# LangSmith tracing
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_ENDPOINT", os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"))
os.environ.setdefault("LANGCHAIN_API_KEY", os.getenv("LANGSMITH_API_KEY", ""))
os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGSMITH_PROJECT", "03892bba-bf1e-4c69-82d9-1058208e56ae"))

from collections.abc import AsyncIterable
from typing import Dict, Any, List, Literal, Optional
import concurrent.futures
import json

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from shared.context import ContextWindowTracker, Message
from shared.vectorstore import VectorStore

memory = MemorySaver()
logger = logging.getLogger(__name__)

class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


# MCP Tools for external clients to access RAG functionality
@tool
def search_documents(query: str, max_results: int = 5) -> str:
    """Search through documents using semantic search.
    
    Args:
        query: Search query to find relevant documents
        max_results: Maximum number of results to return
        
    Returns:
        JSON string containing search results with content and metadata
    """
    try:
        # This will be used by the global RAG agent instance
        # Note: This requires the agent to be instantiated and available
        if hasattr(search_documents, '_agent_instance'):
            agent = search_documents._agent_instance
            docs = agent.vs.search(query, k=max_results)
            
            formatted_results = []
            for i, doc in enumerate(docs, 1):
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', 0.0),
                    "source": doc.metadata.get("source", "unknown"),
                    "id": i
                })
            
            return json.dumps({
                "query": query,
                "results": formatted_results,
                "total_results": len(formatted_results)
            })
        else:
            return json.dumps({
                "query": query,
                "results": [],
                "total_results": 0,
                "error": "RAG agent not initialized",
                "fallback": True
            })
            
    except Exception as e:
        return json.dumps({
            "query": query,
            "results": [],
            "total_results": 0,
            "error": f"Search failed: {str(e)}",
            "fallback": True
        })


@tool
def query_database(sql_query: str, database: str = "vector_db") -> str:
    """Execute database queries to retrieve structured data from the vector database.
    
    Args:
        sql_query: Query description (not actual SQL for security)
        database: Database name to query (vector_db, metadata, etc.)
        
    Returns:
        JSON string containing query results
    """
    try:
        # For vector database, convert natural language to vector search
        if hasattr(query_database, '_agent_instance'):
            agent = query_database._agent_instance
            
            # Convert the "SQL-like" query to a semantic search
            search_terms = sql_query.lower().replace('select', '').replace('from', '').replace('where', '')
            docs = agent.vs.search(search_terms, k=10)
            
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "unknown")
                })
            
            return json.dumps({
                "query": sql_query,
                "database": database,
                "results": results,
                "row_count": len(results),
                "note": "Converted natural language query to vector search"
            })
        else:
            return json.dumps({
                "query": sql_query,
                "database": database,
                "results": [],
                "row_count": 0,
                "error": "RAG agent not initialized"
            })
            
    except Exception as e:
        return json.dumps({
            "error": f"Database query failed: {str(e)}",
            "query": sql_query,
            "database": database
        })


@tool
def retrieve_context(topic: str, document_types: str = "all") -> str:
    """Retrieve relevant context and background information for a topic.
    
    Args:
        topic: Topic or subject to retrieve context for
        document_types: Types of documents to search (all, docs, papers, reports)
        
    Returns:
        JSON string containing contextual information
    """
    try:
        if hasattr(retrieve_context, '_agent_instance'):
            agent = retrieve_context._agent_instance
            
            # Search for context about the topic
            context_query = f"context background information about {topic}"
            docs = agent.vs.search(context_query, k=5)
            
            context_data = {
                "topic": topic,
                "document_types": document_types,
                "context": [],
                "related_topics": [],
                "sources": []
            }
            
            for doc in docs:
                context_data["context"].append({
                    "type": "background",
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "metadata": doc.metadata
                })
                
                source = doc.metadata.get("source", "unknown")
                if source not in context_data["sources"]:
                    context_data["sources"].append(source)
            
            return json.dumps(context_data)
        else:
            return json.dumps({
                "topic": topic,
                "error": "RAG agent not initialized",
                "context": []
            })
            
    except Exception as e:
        return json.dumps({
            "topic": topic,
            "error": f"Context retrieval failed: {str(e)}",
            "context": []
        })


@tool
def semantic_search(query: str, index_name: str = "default", filters: str = "{}") -> str:
    """Perform semantic search across indexed content.
    
    Args:
        query: Natural language search query
        index_name: Name of the search index to use
        filters: JSON string of filters to apply
        
    Returns:
        JSON string containing semantic search results
    """
    try:
        if hasattr(semantic_search, '_agent_instance'):
            agent = semantic_search._agent_instance
            
            filters_dict = json.loads(filters) if filters != "{}" else {}
            
            # Use the RAG agent's vector store for semantic search
            docs = agent.vs.search(query, k=10)
            
            search_results = {
                "query": query,
                "index": index_name,
                "filters": filters_dict,
                "results": [],
                "total_matches": len(docs)
            }
            
            for doc in docs:
                # Apply filters if any
                include_doc = True
                for filter_key, filter_value in filters_dict.items():
                    if filter_key in doc.metadata:
                        if doc.metadata[filter_key] != filter_value:
                            include_doc = False
                            break
                
                if include_doc:
                    search_results["results"].append({
                        "content": doc.page_content,
                        "similarity_score": getattr(doc, 'score', 0.0),
                        "metadata": doc.metadata
                    })
            
            return json.dumps(search_results)
        else:
            return json.dumps({
                "query": query,
                "index": index_name,
                "error": "RAG agent not initialized",
                "results": []
            })
            
    except Exception as e:
        return json.dumps({
            "query": query,
            "index": index_name,
            "error": f"Semantic search failed: {str(e)}",
            "results": []
        })


@tool
def perform_rag_query(question: str, include_citations: bool = True) -> str:
    """Perform a complete RAG query with planning, retrieval, analysis, and synthesis.
    
    Args:
        question: The question to answer using RAG
        include_citations: Whether to include citations in the response
        
    Returns:
        JSON string containing the complete RAG response with answer, plan, and citations
    """
    try:
        if hasattr(perform_rag_query, '_agent_instance'):
            agent = perform_rag_query._agent_instance
            rag_result = agent._perform_rag_search(question)
            
            if rag_result["status"] == "completed":
                return json.dumps({
                    "question": question,
                    "answer": rag_result["answer_markdown"],
                    "plan": rag_result["plan"],
                    "insights": rag_result["insights_json"],
                    "citations": rag_result["citations"] if include_citations else [],
                    "metrics": rag_result["metrics"],
                    "status": "completed"
                })
            else:
                return json.dumps({
                    "question": question,
                    "error": rag_result.get("message", "RAG query failed"),
                    "status": "error"
                })
        else:
            return json.dumps({
                "question": question,
                "error": "RAG agent not initialized",
                "status": "error"
            })
            
    except Exception as e:
        return json.dumps({
            "question": question,
            "error": f"RAG query failed: {str(e)}",
            "status": "error"
        })

class RAGAgent:
    """RAGAgent - a specialized assistant for RAG (Retrieval-Augmented Generation) queries."""

    SYSTEM_INSTRUCTION = (
        'You are a specialized RAG (Retrieval-Augmented Generation) assistant with MCP tool capabilities. '
        'Your purpose is to answer questions by retrieving relevant information from a knowledge base '
        'and providing well-structured, cited responses. '
        '\n\nYou have access to these MCP tools for external clients:'
        '\n- search_documents: Search through documents using semantic search'
        '\n- query_database: Execute database queries to retrieve structured data'
        '\n- retrieve_context: Get relevant context and background information'
        '\n- semantic_search: Perform semantic search across indexed content'
        '\n- perform_rag_query: Execute complete RAG query with planning, retrieval, and synthesis'
        '\n\nYou break down complex queries into subtasks, retrieve relevant documents, '
        'analyze the information, and synthesize comprehensive answers with proper citations. '
        'When external clients call your tools, provide accurate search and retrieval results. '
        'Set response status to input_required if the user needs to provide more information. '
        'Set response status to error if there is an error while processing the request. '
        'Set response status to completed if the request is complete.'
    )

    def __init__(self, vector_store: VectorStore):
        self.model = ChatOpenAI(
            model=os.getenv("TOOL_LLM_NAME", "gpt-4o-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY", os.getenv("API_KEY", "")),
            openai_api_base=os.getenv("TOOL_LLM_URL", None),
            temperature=0
        )
        
        self.vs = vector_store
        self.tools = [
            search_documents,
            query_database, 
            retrieve_context,
            semantic_search,
            perform_rag_query
        ]
        
        # Set agent instance reference on tools for MCP access
        search_documents._agent_instance = self
        query_database._agent_instance = self
        retrieve_context._agent_instance = self
        semantic_search._agent_instance = self
        perform_rag_query._agent_instance = self
        
        # Context trackers for different stages
        model_name = os.getenv("TOOL_LLM_NAME", "gpt-4o-mini")
        self.tracker_plan = ContextWindowTracker(model_name)
        self.tracker_an = ContextWindowTracker(model_name)
        self.tracker_sum = ContextWindowTracker(model_name)
        self.turns_since_summary = 0

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat,
        )

    def _chat(self, messages: List[Dict[str, str]], temperature: float = 0, max_tokens: Optional[int] = None) -> str:
        """Helper method to invoke the model directly for internal RAG processing"""
        formatted_messages = [(msg["role"], msg["content"]) for msg in messages]
        
        # Optimize LLM calls with reduced max_tokens for faster responses
        # Planning and analysis don't need long responses
        if max_tokens is None:
            # Determine appropriate max_tokens based on stage
            if "planner" in str(messages).lower() or "plan" in str(messages).lower():
                max_tokens = 200  # Planning needs short responses
            elif "analyze" in str(messages).lower() or "extract" in str(messages).lower():
                max_tokens = 1000  # Analysis needs moderate length
            else:
                max_tokens = 2000  # Summarization needs more tokens
        
        # Use streaming=False for faster synchronous calls
        response = self.model.invoke(
            formatted_messages,
            config={"temperature": temperature, "max_tokens": max_tokens}
        )
        return response.content

    def _simple_summarizer(self, messages: List[Message], prev_summary: str | None):
        content = "\n".join(f"{m.role}: {m.content}" for m in messages[-8:])  # last few msgs
        base = f"Previous summary:\n{prev_summary}\n\n" if prev_summary else ""
        msgs = [{"role": "system", "content": "Summarize conversation into a short bullet list memory."},
                {"role": "user", "content": base + content}]
        return self._chat(msgs)

    def _maybe_rollup(self):
        self.turns_since_summary += 1
        if self.turns_since_summary >= 4:
            self.tracker_plan.update_summary(self._simple_summarizer)
            self.tracker_an.update_summary(self._simple_summarizer)
            self.tracker_sum.update_summary(self._simple_summarizer)
            self.turns_since_summary = 0

    def _extract_location_entities(self, query: str) -> list:
        """Extract location names from the query using simple heuristics and LLM"""
        import re
        
        # Common US cities that might be in the data
        common_cities = [
            "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
            "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
            "San Francisco", "Indianapolis", "Columbus", "Fort Worth", "Charlotte",
            "Seattle", "Denver", "Washington", "Boston", "El Paso", "Detroit",
            "Nashville", "Portland", "Oklahoma City", "Las Vegas", "Memphis",
            "Louisville", "Baltimore", "Milwaukee", "Albuquerque", "Tucson",
            "Fresno", "Sacramento", "Kansas City", "Mesa", "Atlanta", "Omaha",
            "Colorado Springs", "Raleigh", "Virginia Beach", "Miami", "Oakland",
            "Minneapolis", "Tulsa", "Cleveland", "Wichita", "Arlington"
        ]
        
        # Check for exact city names (case-insensitive)
        found_locations = []
        query_lower = query.lower()
        for city in common_cities:
            if city.lower() in query_lower:
                found_locations.append(city)
        
        # Also try to extract using LLM for better entity recognition
        if not found_locations:
            try:
                extract_prompt = f"""Extract location names (cities, states, countries) from this query. 
Return only the location names, one per line. If no locations found, return "none".

Query: {query}

Locations:"""
                response = self._chat([{"role": "user", "content": extract_prompt}])
                locations = [l.strip() for l in response.splitlines() if l.strip() and l.strip().lower() != "none"]
                found_locations.extend(locations)
            except:
                pass
        
        return list(set(found_locations))  # Remove duplicates
    
    def _enhance_query_with_location(self, query: str, locations: list) -> str:
        """Enhance the query to emphasize location-specific information"""
        if not locations:
            return query
        
        location_str = ", ".join(locations)
        enhanced = f"{query} (specifically for {location_str})"
        return enhanced
    
    def _perform_rag_search_optimized(self, user_query: str) -> Dict[str, Any]:
        """Optimized RAG search for simple queries - skips planning stage"""
        try:
            # Check if vector store is available
            if self.vs is None or self.vs.vs is None:
                return {
                    "status": "error",
                    "message": "Vector store is not loaded. Please ensure the vector store is populated."
                }
            
            # Extract location entities
            locations = self._extract_location_entities(user_query)
            logger.info(f"Extracted locations from query: {locations}")
            
            # Skip planning - go straight to retrieval with the original query
            filter_dict = None
            if locations and len(locations) == 1:
                filter_dict = {"location": locations[0]}
                logger.info(f"Using location filter: {filter_dict}")
            
            # Single optimized search instead of multiple subtasks
            search_query = self._enhance_query_with_location(user_query, locations) if locations else user_query
            retrieved = self.vs.search(search_query, k=8, filter_dict=filter_dict)  # Get more docs in one search
            
            # Deduplicate
            seen_content = set()
            unique_retrieved = []
            for d in retrieved:
                content_hash = hash(d.page_content[:100])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_retrieved.append(d)
            
            retrieved = unique_retrieved[:8]  # Limit to 8 for faster processing
            
            if not retrieved:
                return {
                    "status": "error",
                    "message": "No documents found in vector store."
                }
            
            # Combine analysis and summarization into one step for simple queries
            docs_text = []
            citations = []
            for i, d in enumerate(retrieved, start=1):
                docs_text.append(f"[{i}] {d.page_content}")
                citations.append({"i": i, "meta": d.metadata})
            
            # Single LLM call for combined analysis + summarization
            location_focus = ""
            if locations:
                location_focus = f"\n\nIMPORTANT: Focus only on {', '.join(locations)}. Ignore other locations."
            
            SYSTEM_COMBINED = f"""You are analyzing retrieved documents and generating a concise answer.
Extract key facts and write a well-structured answer with inline citations like [#].
{location_focus}

Documents:
{chr(10).join(docs_text)}

Task: Extract key facts and provide a concise answer with citations."""
            
            self.tracker_sum.add("user", SYSTEM_COMBINED)
            combined_msgs = self.tracker_sum.build_prompt("")
            final_answer = self._chat(combined_msgs, max_tokens=1500)  # Combined response
            
            return {
                "status": "completed",
                "plan": "Optimized: Single-step processing",
                "insights_json": "{}",  # Skip separate insights for simple queries
                "answer_markdown": final_answer,
                "citations": citations,
                "metrics": {
                    "planner": {"tokens": 0, "calls": 0},
                    "analyzer": {"tokens": 0, "calls": 0},
                    "summarizer": self.tracker_sum.metrics()
                }
            }
        except Exception as e:
            logger.error(f"Error in optimized RAG search: {e}")
            return {
                "status": "error",
                "message": f"Error during RAG processing: {str(e)}"
            }

    def _perform_rag_search(self, user_query: str) -> Dict[str, Any]:
        """Internal method to perform the actual RAG search and answer generation"""
        try:
            # Check if vector store is available
            if self.vs is None or self.vs.vs is None:
                return {
                    "status": "error",
                    "message": "Vector store is not loaded. Please ensure the vector store is populated. Run: cd RAG/shared && uv run python import_weather_sample.py"
                }
            
            # Extract location entities from query
            locations = self._extract_location_entities(user_query)
            logger.info(f"Extracted locations from query: {locations}")
            
            # PLAN - Enhanced to focus on specific entities
            SYSTEM_PLANNER = """You are a planner. Break the user goal into 2-4 precise retrieval subtasks.
Focus on specific entities mentioned (like locations, dates, topics). 
If a specific location is mentioned, make sure subtasks emphasize that location.
Keep subtasks focused and specific."""
            
            # Enhance query for planning if locations found
            planning_query = self._enhance_query_with_location(user_query, locations) if locations else user_query
            self.tracker_plan.add("user", planning_query)
            plan_msgs = self.tracker_plan.build_prompt(SYSTEM_PLANNER)
            plan = self._chat(plan_msgs)

            # RETRIEVE (selective with location filtering) - PARALLELIZED
            subtasks = [s.strip("- ").strip() for s in plan.splitlines() if s.strip()]
            retrieved = []
            
            # If we found a specific location, use metadata filtering
            filter_dict = None
            if locations and len(locations) == 1:
                # Single location - use strict filtering
                filter_dict = {"location": locations[0]}
                logger.info(f"Using location filter: {filter_dict}")
            
            # Parallelize vector searches for better performance
            import asyncio
            import concurrent.futures
            
            def perform_search(subtask: str) -> list:
                """Perform a single search operation"""
                try:
                    # Enhance subtask with location if not already emphasized
                    search_query = subtask
                    if locations and not any(loc.lower() in subtask.lower() for loc in locations):
                        search_query = self._enhance_query_with_location(subtask, locations)
                    
                    docs = self.vs.search(search_query, k=4, filter_dict=filter_dict)
                    return docs
                except Exception as e:
                    logger.warning(f"Search failed for subtask '{subtask}': {e}")
                    return []
            
            # Execute searches in parallel using ThreadPoolExecutor
            # Vector store operations are I/O bound, so threading helps
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(subtasks[:4]))) as executor:
                search_futures = {
                    executor.submit(perform_search, st): st 
                    for st in subtasks[:4]
                }
                
                for future in concurrent.futures.as_completed(search_futures):
                    try:
                        docs = future.result()
                        retrieved.extend(docs)
                    except Exception as e:
                        subtask = search_futures[future]
                        logger.warning(f"Search future failed for subtask '{subtask}': {e}")
                        continue
            
            # If we have multiple locations or no strict filter, do post-retrieval filtering
            if locations and len(locations) == 1 and filter_dict:
                # Already filtered, but double-check
                filtered_retrieved = []
                for doc in retrieved:
                    doc_location = doc.metadata.get("location", "").lower()
                    query_location = locations[0].lower()
                    if query_location in doc_location or doc_location in query_location:
                        filtered_retrieved.append(doc)
                    elif not doc_location:  # Keep docs without location metadata
                        filtered_retrieved.append(doc)
                
                if filtered_retrieved:
                    retrieved = filtered_retrieved[:16]  # Limit to top results
                logger.info(f"Post-filtered to {len(retrieved)} documents matching location '{locations[0]}'")
            
            # Check if we retrieved any documents
            if not retrieved:
                return {
                    "status": "error",
                    "message": "No documents found in vector store. The vector store may be empty. Please populate it by running: cd RAG/shared && uv run python import_weather_sample.py"
                }

            # Deduplicate retrieved documents by content hash to avoid processing duplicates
            seen_content = set()
            unique_retrieved = []
            for d in retrieved:
                content_hash = hash(d.page_content[:100])  # Hash first 100 chars for dedup
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_retrieved.append(d)
            
            # Limit to top 12 documents to reduce processing time
            retrieved = unique_retrieved[:12]
            logger.info(f"Retrieved {len(retrieved)} unique documents (after deduplication)")
            
            # ANALYZE - with location focus
            docs_text = []
            citations = []
            for i, d in enumerate(retrieved, start=1):
                docs_text.append(f"[{i}] {d.page_content}")
                citations.append({"i": i, "meta": d.metadata})
            
            # Enhanced analyzer prompt to focus on requested location
            location_focus = ""
            if locations:
                location_focus = f"\n\nIMPORTANT: The user asked specifically about {', '.join(locations)}. Only extract facts related to these locations. Ignore information about other locations."
            
            SYSTEM_ANALYZER = f"You analyze retrieved chunks and extract key facts with citations. Output JSON.{location_focus}"
            analyze_prompt = f"Documents:\n" + "\n\n".join(docs_text) + f"\n\nTask: extract key facts with which doc id supports each fact. JSON array.{location_focus}"
            self.tracker_an.add("user", analyze_prompt)
            an_msgs = self.tracker_an.build_prompt(SYSTEM_ANALYZER)
            insights_json = self._chat(an_msgs)

            # SUMMARIZE - with strict location focus
            location_instruction = ""
            if locations:
                location_instruction = f"\n\nCRITICAL: The user asked about {', '.join(locations)}. Your answer must ONLY include information about {', '.join(locations)}. Do NOT mention other locations like Houston, Los Angeles, etc. If the retrieved documents contain information about other locations, ignore that information completely."
            
            SYSTEM_SUMMARIZER = f"You write a concise, well-structured answer grounded in provided insights. Include inline citations like [#].{location_instruction}"
            self.tracker_sum.add("user", f"Insights JSON:\n{insights_json}\n\nOriginal Query: {user_query}{location_instruction}")
            sum_msgs = self.tracker_sum.build_prompt(SYSTEM_SUMMARIZER)
            final_answer = self._chat(sum_msgs)

            self._maybe_rollup()

            return {
                "status": "completed",
                "plan": plan,
                "insights_json": insights_json,
                "answer_markdown": final_answer,
                "citations": citations,
                "metrics": {
                    "planner": self.tracker_plan.metrics(),
                    "analyzer": self.tracker_an.metrics(),
                    "summarizer": self.tracker_sum.metrics()
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during RAG processing: {str(e)}"
            }

    def invoke(self, query, context_id) -> str:
        # Perform RAG search directly since this is a specialized function
        import time
        start_time = time.time()
        logger.info(f"Starting RAG search for query: {query[:100]}...")
        
        # Early return optimization: If query is very simple, skip planning
        simple_query_patterns = ['weather', 'temperature', 'humidity']
        is_simple_query = any(pattern in query.lower() for pattern in simple_query_patterns) and len(query.split()) < 10
        
        if is_simple_query:
            logger.info("Detected simple query - using optimized path")
            # For simple queries, skip the planning stage and go straight to retrieval
            rag_result = self._perform_rag_search_optimized(query)
        else:
            rag_result = self._perform_rag_search(query)
        
        elapsed_time = time.time() - start_time
        logger.info(f"RAG search completed in {elapsed_time:.2f} seconds. Status: {rag_result.get('status')}")
        
        if rag_result["status"] == "completed":
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': rag_result["answer_markdown"],
                'metadata': {
                    'citations': rag_result["citations"],
                    'metrics': rag_result["metrics"]
                }
            }
        else:
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': rag_result.get("message", "Unable to process your request."),
            }

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        # Check if this is a tool call vs regular RAG query
        if any(tool_name in query.lower() for tool_name in ['search_documents', 'query_database', 'retrieve_context', 'semantic_search', 'perform_rag_query']):
            # Handle as tool usage through LangGraph
            for item in self.graph.stream(inputs, config, stream_mode='values'):
                message = item['messages'][-1]
                if (
                    isinstance(message, AIMessage)
                    and message.tool_calls
                    and len(message.tool_calls) > 0
                ):
                    tool_name = message.tool_calls[0].get('name', 'unknown')
                    if 'search' in tool_name:
                        content = 'Executing document search...'
                    elif 'database' in tool_name:
                        content = 'Querying database...'
                    elif 'context' in tool_name:
                        content = 'Retrieving context...'
                    elif 'rag' in tool_name:
                        content = 'Performing RAG query...'
                    else:
                        content = 'Processing tool request...'
                        
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': content,
                    }
                elif isinstance(message, ToolMessage):
                    yield {
                        'is_task_complete': False,
                        'require_user_input': False,
                        'content': 'Processing tool results...',
                    }

            yield self.get_agent_response(config)
        else:
            # Handle as regular RAG query
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Planning retrieval strategy...',
            }
            
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Searching knowledge base...',
            }
            
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Analyzing retrieved documents...',
            }
            
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': 'Synthesizing answer...',
            }
            
            # Perform the actual RAG search
            final_result = self.invoke(query, context_id)
            yield final_result

    def get_agent_response(self, config):
        # This method is kept for compatibility but may not be used in the same way
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == 'input_required':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'error':
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                'We are unable to process your request at the moment. '
                'Please try again.'
            ),
        }

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
