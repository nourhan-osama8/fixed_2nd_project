import os
import uuid
import shutil
import logging
import threading
from typing import List, Optional
from uuid import UUID
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.repositories.document_repository import DocumentRepository
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.core.config import settings
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.constants import DocumentStatus

logger = logging.getLogger("nileconnect")

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}


def _rebuild_rag_background() -> None:
    """Rebuild the RAG index in a background thread after a new upload."""
    try:
        from app.ai.rag.pipeline import rag
        rag.build()
        logger.info("RAG index rebuilt successfully after document upload.")
    except Exception as exc:
        logger.error("RAG rebuild failed: %s", exc)


class DocumentService:
    def __init__(self, db: Session):
        self.repo = DocumentRepository(db)

    def get_all(self, skip: int = 0, limit: int = 100, status: Optional[DocumentStatus] = None) -> List[DocumentResponse]:
        docs = self.repo.get_all(skip=skip, limit=limit, status=status)
        return [DocumentResponse.model_validate(d) for d in docs]

    def count(self, status: Optional[DocumentStatus] = None) -> int:
        return self.repo.count(status=status)

    def get_by_id(self, document_id: UUID) -> DocumentResponse:
        doc = self.repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(f"Document {document_id} not found")
        return DocumentResponse.model_validate(doc)

    async def upload(self, file: UploadFile, uploader_id: UUID) -> DocumentResponse:
        if file.content_type not in ALLOWED_TYPES:
            raise BadRequestError(f"File type '{file.content_type}' is not supported. Use PDF, DOCX, or TXT.")

        ext = ALLOWED_TYPES[file.content_type]
        safe_filename = f"{uuid.uuid4()}.{ext}"

        # ── Save to standard uploads dir ─────────────────────────────────────
        storage_path = os.path.join(settings.upload_dir_abs, safe_filename)
        os.makedirs(settings.upload_dir_abs, exist_ok=True)
        with open(storage_path, "wb") as dest:
            shutil.copyfileobj(file.file, dest)

        file_size = os.path.getsize(storage_path)

        # ── Copy to RAG docs dir (PDF, TXT, and DOCX are all indexable) ────────
        if ext in ("pdf", "txt", "docx"):
            rag_dir = Path(settings.rag_docs_dir_abs)
            rag_dir.mkdir(parents=True, exist_ok=True)
            rag_path = rag_dir / safe_filename
            shutil.copy2(storage_path, rag_path)
            logger.info("Copied %s to RAG docs dir: %s", safe_filename, rag_path)
            # Rebuild RAG index in a background thread so the HTTP response is not delayed
            threading.Thread(target=_rebuild_rag_background, daemon=True).start()

        doc = Document(
            filename=safe_filename,
            original_name=file.filename,
            file_type=ext,
            storage_path=storage_path,
            file_size=file_size,
            uploaded_by=uploader_id,
            status=DocumentStatus.READY,
        )
        created = self.repo.create(doc)
        return DocumentResponse.model_validate(created)

    def delete(self, document_id: UUID) -> None:
        doc = self.repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(f"Document {document_id} not found")

        # Remove physical file from uploads
        if os.path.exists(doc.storage_path):
            os.remove(doc.storage_path)

        # Remove from RAG docs dir if present
        rag_path = Path(settings.rag_docs_dir_abs) / doc.filename
        if rag_path.exists():
            rag_path.unlink()
            logger.info("Removed %s from RAG docs dir.", doc.filename)
            # Rebuild RAG after deletion
            threading.Thread(target=_rebuild_rag_background, daemon=True).start()

        self.repo.delete(doc)
