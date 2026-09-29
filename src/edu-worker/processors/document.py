"""Processor for document processing tasks."""

import asyncio
from datetime import datetime
from uuid import uuid4

from content_understanding import AzureContentUnderstandingClient
from edu_ai.llm import create_chat_model, create_embeddings, is_llm_configured
from edu_core.schemas.documents import DocumentStatus
from edu_core.storage import StorageService, document_contents_path, document_path
from edu_db.models import Document, DocumentSegment
from edu_queue.schemas import DocumentProcessingData
from local_extraction import extract_document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from rich.console import Console

from processors.base import BaseProcessor

console = Console(force_terminal=True)


class DocumentProcessor(BaseProcessor[DocumentProcessingData]):
    """Processor that extracts, splits and embeds uploaded documents."""

    def __init__(
        self,
        storage: StorageService,
        azure_cu_endpoint: str,
        azure_cu_key: str,
        azure_cu_analyzer_id: str,
        azure_openai_embedding_deployment: str,
        azure_openai_endpoint: str,
        azure_openai_api_version: str,
    ):
        """Initialize the processor.

        Args:
            storage: Storage client for document files
            azure_cu_endpoint: Azure Content Understanding endpoint (optional)
            azure_cu_key: Azure Content Understanding subscription key (optional)
            azure_cu_analyzer_id: Azure Content Understanding analyzer ID
            azure_openai_embedding_deployment: Azure OpenAI embedding deployment
            azure_openai_endpoint: Azure OpenAI endpoint
            azure_openai_api_version: Azure OpenAI API version
        """
        self.storage = storage

        # Without Content Understanding, documents are extracted locally
        self.cu_client = None
        if azure_cu_endpoint and azure_cu_key:
            self.cu_client = AzureContentUnderstandingClient(
                endpoint=azure_cu_endpoint,
                subscription_key=azure_cu_key,
            )

        self.embeddings = create_embeddings(
            azure_deployment=azure_openai_embedding_deployment,
            azure_endpoint=azure_openai_endpoint,
            azure_api_version=azure_openai_api_version,
        )
        self.summary_llm = (
            create_chat_model(
                azure_endpoint=azure_openai_endpoint,
                azure_api_version=azure_openai_api_version,
            )
            if is_llm_configured(azure_endpoint=azure_openai_endpoint)
            else None
        )
        self.analyzer_id = azure_cu_analyzer_id

    async def process(self, payload: DocumentProcessingData) -> None:
        """Process document asynchronously: analyze, index, and create embeddings.

        Safe to retry: segments from an earlier failed attempt are replaced.

        Args:
            payload: Document processing data

        Raises:
            Exception: If processing fails
        """
        document_id = payload["document_id"]
        project_id = payload["project_id"]

        with self._get_db_session() as db:
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if not document:
                    raise ValueError(f"Document {document_id} not found")

                path = document.original_blob_name or document_path(
                    project_id, document_id, document.file_type
                )
                file_content = await asyncio.to_thread(self.storage.download, path)

                # Step 1: Extract text (Content Understanding or locally)
                analyzed_result = await asyncio.to_thread(
                    self._analyze_document,
                    file_content=file_content,
                    file_type=document.file_type,
                )
                analyzed_content = analyzed_result["content"]
                analyzed_summary = analyzed_result["summary"]

                # Step 2: Save the extracted text next to the original
                contents_path = document_contents_path(project_id, document_id)
                await asyncio.to_thread(
                    self.storage.upload,
                    contents_path,
                    analyzed_content.encode("utf-8"),
                    "text/plain; charset=utf-8",
                )
                document.processed_text_blob_name = contents_path
                db.commit()

                # Step 3: Update document status to processed
                self._update_document_processed_status(
                    db=db,
                    document_id=document_id,
                    summary=analyzed_summary,
                )

                # Step 4: Create segments and embeddings (replacing any from a failed attempt)
                db.query(DocumentSegment).filter(
                    DocumentSegment.document_id == document_id
                ).delete()
                db.commit()
                await self._create_segments_and_embeddings(
                    db=db, document_id=document_id, content=analyzed_content
                )

                # Step 5: Mark document as indexed
                self._mark_document_indexed(db=db, document_id=document_id)

                console.log(f"Processed document {document_id}")
            except Exception:
                self._mark_document_failed(db=db, document_id=document_id)
                raise

    def _analyze_document(self, file_content: bytes, file_type: str) -> dict:
        """Analyze document using Azure Content Understanding, or locally if not configured.

        Args:
            file_content: The file content as bytes
            file_type: The file extension

        Returns:
            Dictionary containing content and summary
        """
        if self.cu_client is None:
            return extract_document(file_content, file_type, self.summary_llm)

        response = self.cu_client.begin_analyze_data(
            analyzer_id=self.analyzer_id, data=file_content
        )
        result = self.cu_client.poll_result(response=response)

        contents_item = result["result"]["contents"][0]

        content = contents_item["markdown"]
        summary = contents_item["fields"]["Summary"]["valueString"]

        return {
            "content": content,
            "summary": summary,
        }

    async def _create_segments_and_embeddings(
        self, db, document_id: str, content: str
    ) -> None:
        """Create document segments and generate embeddings.

        Args:
            db: Database session
            document_id: The document ID
            content: The document content
        """
        # Split text into chunks
        chunks = self.split_markdown_with_headers(text=content)

        # Create segments in database
        self._create_document_segments(document_id=document_id, chunks=chunks, db=db)

        # Generate embeddings for all segments
        await self._generate_embeddings_for_segments(document_id=document_id, db=db)

    async def _generate_embeddings_for_segments(self, db, document_id: str) -> None:
        """Generate embeddings for document segments with rate limiting.

        Args:
            db: Database session
            document_id: The document ID
        """
        segments = (
            db.query(DocumentSegment)
            .filter(
                DocumentSegment.document_id == document_id,
                DocumentSegment.embedding_vector.is_(None),
            )
            .all()
        )

        if not segments:
            return

        texts = [str(segment.content) for segment in segments]

        embeddings_list = await self.embeddings.aembed_documents(texts)

        batch_num = len(embeddings_list) // 20 + 1
        for i in range(batch_num):
            start_index = i * 20
            end_index = min((i + 1) * 20, len(embeddings_list))
            batch_segments = segments[start_index:end_index]
            batch_embeddings = embeddings_list[start_index:end_index]

            for segment, embedding in zip(
                batch_segments, batch_embeddings, strict=False
            ):
                segment.embedding_vector = embedding

            db.commit()

            if i < batch_num - 1:
                await asyncio.sleep(1)

        db.commit()

    @staticmethod
    def split_markdown_with_headers(
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        length_function=len,
        delimiter: str = "<!-- PageBreak -->",
    ) -> list[str]:
        """Split markdown text into chunks using headers and page breaks.

        Args:
            text: The text to split
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            length_function: Function to calculate length
            delimiter: Page break delimiter

        Returns:
            List of text chunks
        """
        pages = [p.strip() for p in text.split(delimiter) if p.strip()]

        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
        )
        chunker = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
        )

        chunks: list[str] = []
        for page in pages:
            sections = header_splitter.split_text(page)
            try:
                chunks.extend(
                    [d.page_content for d in chunker.split_documents(sections)]
                )
            except AttributeError:
                for sec in sections:
                    chunks.extend(chunker.split_text(sec.page_content))
        return chunks

    @staticmethod
    def _update_document_processed_status(db, document_id: str, summary: str) -> None:
        """Update document status to processed.

        Args:
            db: Database session
            document_id: The document ID
            summary: Document summary
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.PROCESSED.value
            document.processed_at = datetime.now()
            document.summary = summary
            db.commit()

    @staticmethod
    def _mark_document_indexed(db, document_id: str) -> None:
        """Mark document as indexed.

        Args:
            db: Database session
            document_id: The document ID
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.INDEXED.value
            db.commit()

    @staticmethod
    def _mark_document_failed(db, document_id: str) -> None:
        """Mark document as failed.

        Args:
            db: Database session
            document_id: The document ID
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.FAILED.value
            db.commit()

    @staticmethod
    def _create_document_segments(
        db,
        document_id: str,
        chunks: list[str],
    ) -> None:
        """Create document segments in database.

        Args:
            db: Database session
            document_id: The document ID
            chunks: List of text chunks
        """
        segments = [
            DocumentSegment(
                id=str(uuid4()),
                document_id=document_id,
                content=chunk,
                content_type="text",
            )
            for chunk in chunks
        ]
        db.add_all(segments)
        db.commit()
