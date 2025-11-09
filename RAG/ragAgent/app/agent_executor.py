import logging
import sys
from pathlib import Path

# Add the parent directory (RAG) to Python path to access shared modules
current_dir = Path(__file__).parent
rag_dir = current_dir.parent.parent
sys.path.insert(0, str(rag_dir))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    InvalidParamsError,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)
from a2a.utils.errors import ServerError

from app.agent import RAGAgent
from shared.vectorstore import VectorStore


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGAgentExecutor(AgentExecutor):
    """RAG AgentExecutor Example."""

    def __init__(self):
        # Initialize vector store - path should be relative to RAG directory, not ragAgent
        # Get the RAG directory (parent of ragAgent)
        rag_dir = current_dir.parent.parent
        chroma_path = rag_dir / ".chroma"
        
        vector_store = VectorStore(path=str(chroma_path), collection="rag_docs")
        # Load existing vector store if it exists
        try:
            vector_store.load()
            # Verify vector store is actually loaded and has data
            if vector_store.vs is None:
                raise Exception("Vector store object is None after load")
            
            # Test search to verify it's working
            test_results = vector_store.search("test", k=1)
            logger.info(f"Vector store loaded successfully from {chroma_path}")
            logger.info(f"Vector store contains data (test search returned {len(test_results)} results)")
        except Exception as e:
            logger.error(f"Could not load existing vector store from {chroma_path}: {e}")
            logger.error("Vector store is required for RAG agent to function.")
            logger.error("Please run: cd RAG/shared && uv run python import_weather_sample.py")
            # Still create the agent, but it will fail on queries
            # This allows the agent to start but queries will fail gracefully
        
        self.agent = RAGAgent(vector_store)

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        try:
            async for item in self.agent.stream(query, task.context_id):
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']

                if not is_task_complete and not require_user_input:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item['content'],
                            task.context_id,
                            task.id,
                        ),
                    )
                elif require_user_input:
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item['content'],
                            task.context_id,
                            task.id,
                        ),
                        final=True,
                    )
                    break
                
                else:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='rag_result',
                    )
                    await updater.complete()
                    break
                
        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())