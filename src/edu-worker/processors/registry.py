"""Processor registry for mapping task types to processors."""

from edu_core.services.search import SearchService
from edu_core.storage import StorageService
from edu_queue.schemas import TaskType

from processors.base import BaseProcessor
from processors.chat_title import ChatTitleProcessor
from processors.document import DocumentProcessor
from processors.flashcard import FlashcardProcessor
from processors.mind_map import MindMapProcessor
from processors.note import NoteProcessor
from processors.quiz import QuizProcessor


class ProcessorRegistry:
    """Registry for task type to processor mapping."""

    def __init__(
        self,
        search_service: SearchService,
        storage: StorageService,
        azure_openai_chat_deployment: str,
        azure_openai_endpoint: str,
        azure_openai_api_version: str,
        azure_cu_endpoint: str,
        azure_cu_key: str,
        azure_cu_analyzer_id: str,
        azure_openai_embedding_deployment: str,
    ):
        """Initialize the registry with required services.

        Args:
            search_service: SearchService for RAG
            storage: Storage client for document files
            azure_openai_chat_deployment: Azure OpenAI chat deployment name
            azure_openai_endpoint: Azure OpenAI endpoint URL
            azure_openai_api_version: Azure OpenAI API version
            azure_cu_endpoint: Azure Content Understanding endpoint (optional)
            azure_cu_key: Azure Content Understanding subscription key (optional)
            azure_cu_analyzer_id: Azure Content Understanding analyzer ID
            azure_openai_embedding_deployment: Azure OpenAI embedding deployment
        """
        self.search_service = search_service
        self.storage = storage
        self.azure_openai_chat_deployment = azure_openai_chat_deployment
        self.azure_openai_endpoint = azure_openai_endpoint
        self.azure_openai_api_version = azure_openai_api_version
        self.azure_cu_endpoint = azure_cu_endpoint
        self.azure_cu_key = azure_cu_key
        self.azure_cu_analyzer_id = azure_cu_analyzer_id
        self.azure_openai_embedding_deployment = azure_openai_embedding_deployment

    def get_processor(self, task_type: TaskType) -> BaseProcessor:
        """Get processor for a task type.

        Args:
            task_type: The task type

        Returns:
            Processor instance for the task type

        Raises:
            ValueError: If task type is unknown
        """
        llm_args = (
            self.azure_openai_chat_deployment,
            self.azure_openai_endpoint,
            self.azure_openai_api_version,
        )
        processors = {
            TaskType.CHAT_TITLE_GENERATION: lambda: ChatTitleProcessor(*llm_args),
            TaskType.FLASHCARD_GENERATION: lambda: FlashcardProcessor(
                self.search_service, *llm_args, self.storage
            ),
            TaskType.QUIZ_GENERATION: lambda: QuizProcessor(
                self.search_service, *llm_args, self.storage
            ),
            TaskType.NOTE_GENERATION: lambda: NoteProcessor(
                self.search_service, *llm_args, self.storage
            ),
            TaskType.MIND_MAP_GENERATION: lambda: MindMapProcessor(
                self.search_service, *llm_args, self.storage
            ),
            TaskType.DOCUMENT_PROCESSING: lambda: DocumentProcessor(
                storage=self.storage,
                azure_cu_endpoint=self.azure_cu_endpoint,
                azure_cu_key=self.azure_cu_key,
                azure_cu_analyzer_id=self.azure_cu_analyzer_id,
                azure_openai_embedding_deployment=self.azure_openai_embedding_deployment,
                azure_openai_endpoint=self.azure_openai_endpoint,
                azure_openai_api_version=self.azure_openai_api_version,
            ),
        }

        factory = processors.get(task_type)
        if not factory:
            raise ValueError(f"Unknown task type: {task_type}")

        return factory()
