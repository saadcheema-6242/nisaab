"""Service for uploading documents to storage."""

from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from edu_db.models import Document
from edu_db.session import get_session_factory

from edu_core.schemas.documents import DocumentStatus
from edu_core.storage import StorageService, document_path

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "md": "text/markdown",
    "html": "text/html",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "jpe": "image/jpeg",
    "webp": "image/webp",
    "heic": "image/heic",
    "heif": "image/heif",
}


class DocumentUploadService:
    """Service for uploading documents to storage."""

    def __init__(self, database_url: str, storage: StorageService) -> None:
        """Initialize the document upload service.

        Args:
            database_url: Database connection URL
            storage: Storage client for document files
        """
        self.database_url = database_url
        self.storage = storage

    def get_supported_types(self) -> list[str]:
        """Get list of supported document types.

        Returns:
            List of supported file extensions
        """
        return list(CONTENT_TYPES)

    def upload_document(
        self, file_content: bytes, filename: str, project_id: str, owner_id: str
    ) -> str:
        """Upload document to storage and create database record.

        Args:
            file_content: The file content as bytes
            filename: Name of the file
            project_id: The project ID
            owner_id: The owner's user ID

        Returns:
            ID of the created document

        Raises:
            Exception: If upload fails
        """
        with self._get_db_session() as db:
            document_id = self._create_document_record(
                db=db,
                file_content=file_content,
                filename=filename,
                project_id=project_id,
                owner_id=owner_id,
            )

            file_type = self._get_file_type(filename)
            path = document_path(project_id, document_id, file_type)
            self.storage.upload(
                path,
                file_content,
                content_type=CONTENT_TYPES.get(file_type, "application/octet-stream"),
            )

            self._update_document_storage_reference(
                db=db, document_id=document_id, path=path
            )
            return document_id

    def get_preview_url(
        self, project_id: str, document_id: str, filename: str, expires_in: int = 3600
    ) -> str:
        """Get a temporary URL for viewing a document in the browser.

        Args:
            project_id: The project ID
            document_id: The document ID
            filename: The original filename
            expires_in: URL validity in seconds

        Returns:
            Signed URL
        """
        path = document_path(project_id, document_id, self._get_file_type(filename))
        return self.storage.signed_url(path, expires_in=expires_in)

    def _create_document_record(
        self,
        db,
        file_content: bytes,
        filename: str,
        project_id: str,
        owner_id: str,
    ) -> str:
        """Create initial document record in database.

        Args:
            db: Database session
            file_content: The file content as bytes
            filename: Name of the file
            project_id: The project ID
            owner_id: The owner's user ID

        Returns:
            ID of the created document
        """
        document = Document(
            id=str(uuid4()),
            owner_id=owner_id,
            project_id=project_id,
            file_name=filename,
            file_type=self._get_file_type(filename),
            file_size=len(file_content),
            status=DocumentStatus.UPLOADED.value,
            uploaded_at=datetime.now(),
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        return document.id

    @staticmethod
    def _get_file_type(filename: str) -> str:
        """Extract file type from filename.

        Args:
            filename: Name of the file

        Returns:
            File extension or 'unknown'
        """
        return filename.split(".")[-1].lower() if "." in filename else "unknown"

    @staticmethod
    def _update_document_storage_reference(db, document_id: str, path: str) -> None:
        """Save the storage path and set status to processing.

        Args:
            db: Database session
            document_id: The document ID
            path: The object path in storage
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.original_blob_name = path
            document.status = DocumentStatus.PROCESSING.value
            db.commit()

    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions."""
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
