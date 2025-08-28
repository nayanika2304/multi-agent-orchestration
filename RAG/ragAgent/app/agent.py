# ragAgent/rag_agent.py
import sys
import os
from pathlib import Path

# Add the parent directory (RAG) to Python path to access shared modules
current_dir = Path(__file__).parent
rag_dir = current_dir.parent.parent
sys.path.insert(0, str(rag_dir))

from collections.abc import AsyncIterable
from typing import Dict, Any, List, Literal
import json

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from shared.context import ContextWindowTracker, Message
from shared.vectorstore import VectorStore

memory = MemorySaver()

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
        model_source = os.getenv("model_source", "google")
        if model_source == "google":
            self.model = ChatGoogleGenerativeAI(model='gemini-2.0-flash')
        else:
            self.model = ChatOpenAI(
                model=os.getenv("TOOL_LLM_NAME", "gpt-4o-mini"),
                openai_api_key=os.getenv("API_KEY", "EMPTY"),
                openai_api_base=os.getenv("TOOL_LLM_URL"),
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
        model_name = 'gemini-2.0-flash' if model_source == "google" else os.getenv("TOOL_LLM_NAME", "gpt-4o-mini")
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

    def _chat(self, messages: List[Dict[str, str]]) -> str:
        """Helper method to invoke the model directly for internal RAG processing"""
        formatted_messages = [(msg["role"], msg["content"]) for msg in messages]
        response = self.model.invoke(formatted_messages)
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

    def _perform_rag_search(self, user_query: str) -> Dict[str, Any]:
        """Internal method to perform the actual RAG search and answer generation"""
        try:
            # PLAN
            SYSTEM_PLANNER = "You are a planner. Break the user goal into 2-4 precise retrieval subtasks."
            self.tracker_plan.add("user", user_query)
            plan_msgs = self.tracker_plan.build_prompt(SYSTEM_PLANNER)
            plan = self._chat(plan_msgs)

            # RETRIEVE (selective)
            # naive subtask splitting: one query per line
            subtasks = [s.strip("- ").strip() for s in plan.splitlines() if s.strip()]
            retrieved = []
            for st in subtasks[:4]:
                docs = self.vs.search(st, k=4)
                retrieved.extend(docs)

            # ANALYZE
            docs_text = []
            citations = []
            for i, d in enumerate(retrieved, start=1):
                docs_text.append(f"[{i}] {d.page_content}")
                citations.append({"i": i, "meta": d.metadata})
            
            SYSTEM_ANALYZER = "You analyze retrieved chunks and extract key facts with citations. Output JSON."
            analyze_prompt = f"Documents:\n" + "\n\n".join(docs_text) + "\n\nTask: extract key facts with which doc id supports each fact. JSON array."
            self.tracker_an.add("user", analyze_prompt)
            an_msgs = self.tracker_an.build_prompt(SYSTEM_ANALYZER)
            insights_json = self._chat(an_msgs)

            # SUMMARIZE
            SYSTEM_SUMMARIZER = "You write a concise, well-structured answer grounded in provided insights. Include inline citations like [#]."
            self.tracker_sum.add("user", f"Insights JSON:\n{insights_json}")
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
        rag_result = self._perform_rag_search(query)
        
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
