from collections.abc import AsyncIterable
from typing import Any, Dict, Literal
import os

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
import matplotlib.pyplot as plt
import pandas as pd
import json
import os
from datetime import datetime


memory = MemorySaver()


@tool
def generate_report_text(insights_json: str, answer_markdown: str) -> str:
    """Generate a professional report text from insights and answers with context window management.
    
    Args:
        insights_json: JSON string containing insights data
        answer_markdown: Markdown formatted answer text
        
    Returns:
        A professional report with title, executive summary, key findings, recommendations, and references
    """
    from openai import OpenAI
    import tiktoken
    
    MODEL = "gpt-4o-mini"
    client = OpenAI()
    
    # GPT-4o-mini has 128K context window, leave room for response (~4K tokens)
    MAX_CONTEXT_TOKENS = 120000
    
    SYSTEM_REPORT = """You are a Report Generator Agent.
                        Produce a professional report with:
                        - Title
                        - Executive Summary
                        - Key Findings (with inline [#] citations if provided)
                        - Recommendations
                        - References

                        If the input data is truncated due to length, note this in your report and work with the available information."""
    
    def count_tokens(text: str) -> int:
        """Count tokens in text using tiktoken."""
        try:
            encoding = tiktoken.encoding_for_model(MODEL)
            return len(encoding.encode(text))
        except Exception:
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4
    
    def truncate_text(text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        try:
            encoding = tiktoken.encoding_for_model(MODEL)
            tokens = encoding.encode(text)
            if len(tokens) <= max_tokens:
                return text
            # Truncate and add indication
            truncated_tokens = tokens[:max_tokens]
            truncated_text = encoding.decode(truncated_tokens)
            return truncated_text + "\n\n[NOTE: Content truncated due to length limits]"
        except Exception:
            # Fallback: character-based truncation
            char_limit = max_tokens * 4  # rough estimation
            if len(text) <= char_limit:
                return text
            return text[:char_limit] + "\n\n[NOTE: Content truncated due to length limits]"
    
    # Count tokens for system prompt
    system_tokens = count_tokens(SYSTEM_REPORT)
    
    # Calculate available space for user content
    available_tokens = MAX_CONTEXT_TOKENS - system_tokens - 100  # buffer
    
    # Prepare user content
    user_content = f"Insights JSON:\n{insights_json}\n\nAnswer (Markdown):\n{answer_markdown}"
    user_tokens = count_tokens(user_content)
    
    # Truncate if necessary
    if user_tokens > available_tokens:
        # Try to preserve both insights and answer proportionally
        insights_ratio = len(insights_json) / (len(insights_json) + len(answer_markdown))
        insights_tokens = int(available_tokens * insights_ratio * 0.9)  # 90% of proportion
        answer_tokens = available_tokens - insights_tokens - 50  # buffer for formatting
        
        truncated_insights = truncate_text(insights_json, insights_tokens)
        truncated_answer = truncate_text(answer_markdown, answer_tokens)
        
        user_content = f"Insights JSON:\n{truncated_insights}\n\nAnswer (Markdown):\n{truncated_answer}"
    
    msgs = [
        {"role": "system", "content": SYSTEM_REPORT},
        {"role": "user", "content": user_content}
    ]
    
    try:
        resp = client.chat.completions.create(
            model=MODEL, 
            messages=msgs,
            max_tokens=4000,  # Limit response length
            temperature=0.1   # More consistent outputs
        )
        return resp.choices[0].message.content
    except Exception as e:
        if "context_length_exceeded" in str(e).lower():
            # Further reduce content and retry
            reduced_content = truncate_text(user_content, available_tokens // 2)
            msgs[1]["content"] = reduced_content
            try:
                resp = client.chat.completions.create(
                    model=MODEL, 
                    messages=msgs,
                    max_tokens=4000,
                    temperature=0.1
                )
                return resp.choices[0].message.content
            except Exception as retry_e:
                return f"Error generating report: {str(retry_e)}. Please try with smaller input data."
        else:
            return f"Error generating report: {str(e)}"


@tool
def generate_chart(data_json: str, chart_type: str = "bar", title: str = "Data Analysis Chart", x_label: str = "Categories", y_label: str = "Values") -> str:
    """Generate charts and graphs for data visualization.
    
    Args:
        data_json: JSON string containing the data to visualize
        chart_type: Type of chart (bar, line, pie, scatter, histogram)
        title: Title for the chart
        x_label: Label for x-axis
        y_label: Label for y-axis
        
    Returns:
        The path to the saved chart image
    """
    try:
        # Parse the data
        data = json.loads(data_json)
        
        # Create a unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_path = f"chart_{chart_type}_{timestamp}.png"
        
        # Set up the plot style
        plt.style.use('default')
        plt.figure(figsize=(10, 6))
        
        if chart_type.lower() == "bar":
            if isinstance(data, dict):
                plt.bar(data.keys(), data.values())
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                # Handle list of dictionaries
                df = pd.DataFrame(data)
                if len(df.columns) >= 2:
                    plt.bar(df.iloc[:, 0], df.iloc[:, 1])
                    
        elif chart_type.lower() == "line":
            if isinstance(data, dict):
                plt.plot(list(data.keys()), list(data.values()), marker='o')
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                df = pd.DataFrame(data)
                if len(df.columns) >= 2:
                    plt.plot(df.iloc[:, 0], df.iloc[:, 1], marker='o')
                    
        elif chart_type.lower() == "pie":
            if isinstance(data, dict):
                plt.pie(data.values(), labels=data.keys(), autopct='%1.1f%%')
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                df = pd.DataFrame(data)
                if len(df.columns) >= 2:
                    plt.pie(df.iloc[:, 1], labels=df.iloc[:, 0], autopct='%1.1f%%')
                    
        elif chart_type.lower() == "scatter":
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                df = pd.DataFrame(data)
                if len(df.columns) >= 2:
                    plt.scatter(df.iloc[:, 0], df.iloc[:, 1])
                    
        elif chart_type.lower() == "histogram":
            if isinstance(data, list):
                plt.hist(data, bins=20, alpha=0.7)
            elif isinstance(data, dict):
                plt.hist(list(data.values()), bins=20, alpha=0.7)
        
        # Set labels and title
        plt.title(title, fontsize=14, fontweight='bold')
        if chart_type.lower() != "pie":
            plt.xlabel(x_label)
            plt.ylabel(y_label)
        
        # Improve layout and save
        plt.tight_layout()
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_path
        
    except Exception as e:
        return f"Error generating chart: {str(e)}"


@tool
def save_pdf(text: str, path: str = "rag_report.pdf", chart_paths: str = "") -> str:
    """Save report text as a PDF file with optional chart images.
    
    Args:
        text: The report text to save
        path: Output path for the PDF file
        chart_paths: Comma-separated paths to chart images to include
        
    Returns:
        The path to the saved PDF file
    """
    doc = SimpleDocTemplate(path, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = []
    
    # Add text content
    for line in text.split("\n"):
        if not line.strip():
            story.append(Spacer(1, 10))
        else:
            story.append(Paragraph(line, styles["Normal"]))
    
    # Add charts if provided
    if chart_paths and chart_paths.strip():
        story.append(Spacer(1, 20))
        story.append(Paragraph("Data Visualizations", styles["Heading2"]))
        story.append(Spacer(1, 10))
        
        for chart_path in chart_paths.split(","):
            chart_path = chart_path.strip()
            if chart_path and os.path.exists(chart_path):
                try:
                    # Add chart image to PDF
                    img = Image(chart_path, width=400, height=240)
                    story.append(img)
                    story.append(Spacer(1, 10))
                except Exception as e:
                    story.append(Paragraph(f"Error loading chart: {chart_path}", styles["Normal"]))
    
    doc.build(story)
    return path


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class ReportAgent:
    """ReportAgent - a specialized assistant for generating professional reports from data."""

    SYSTEM_INSTRUCTION = (
        'You are a specialized assistant for generating professional reports with data visualization capabilities. '
        "Your purpose is to use the 'generate_report_text', 'generate_chart', and 'save_pdf' tools to create comprehensive reports from provided data. "
        'You can process insights in JSON format and answers in markdown format to create structured reports. '
        'You can also create charts and graphs (bar, line, pie, scatter, histogram) from data to enhance visual analysis. '
        'Charts will be automatically included in PDF reports when generated. '
        'If the user asks about anything other than report generation or data visualization, '
        'politely state that you cannot help with that topic and can only assist with report generation and data analysis. '
        'Set response status to input_required if the user needs to provide more information (insights_json and answer_markdown). '
        'Set response status to error if there is an error while processing the request. '
        'Set response status to completed if the report is successfully generated.'
    )

    def __init__(self):
        model_source = os.getenv("model_source", "google")
        if model_source == "google":
            self.model = ChatGoogleGenerativeAI(model='gemini-2.0-flash')
        else:
            self.model = ChatOpenAI(
                 model=os.getenv("TOOL_LLM_NAME"),
                 openai_api_key=os.getenv("API_KEY", "EMPTY"),
                 openai_api_base=os.getenv("TOOL_LLM_URL"),
                 temperature=0
             )
        self.tools = [generate_report_text, generate_chart, save_pdf]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat,
        )

    def invoke(self, query, context_id) -> str:
        config = {'configurable': {'thread_id': context_id}}
        self.graph.invoke({'messages': [('user', query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        for item in self.graph.stream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                tool_name = message.tool_calls[0].get('name', 'unknown')
                if 'chart' in tool_name:
                    content = 'Generating charts and visualizations...'
                elif 'report' in tool_name:
                    content = 'Generating report text...'
                elif 'pdf' in tool_name:
                    content = 'Creating PDF document...'
                else:
                    content = 'Processing data...'
                    
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': content,
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing report data and visualizations...',
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
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