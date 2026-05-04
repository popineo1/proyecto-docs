import hashlib
import os
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.tenant import Tenant
from app.models.user import User
from app.models.job import Job


_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

_ALLOWED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif",
    ".xlsx", ".xls", ".csv",
}

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv", "application/csv",
    "application/octet-stream",  # fallback genérico que algunos clientes envían
}


class DocumentService:
    UPLOAD_ROOT = Path("storage/uploads")
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _ensure_tenant_folder(tenant_id: str) -> Path:
        tenant_folder = DocumentService.UPLOAD_ROOT / tenant_id
        tenant_folder.mkdir(parents=True, exist_ok=True)
        return tenant_folder

    @staticmethod
    async def save_uploaded_document(
        db: Session,
        file: UploadFile,
        current_user: User,
        current_tenant: Tenant
    ) -> Document:
        from app.core.supabase import get_supabase
        if not file.filename:
            raise ValueError("El archivo no tiene nombre")

        # Validate extension before reading to fail fast
        extension = Path(file.filename).suffix.lower()
        if extension not in _ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Tipo de archivo no permitido: '{extension}'. "
                f"Formatos aceptados: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
            )

        content = await file.read()
        if not content:
            raise ValueError("El archivo está vacío")

        # Validate size
        if len(content) > _MAX_FILE_SIZE:
            raise ValueError(
                f"El archivo supera el tamaño máximo permitido (20 MB). "
                f"Tamaño recibido: {len(content) / 1024 / 1024:.1f} MB"
            )

        # Validate MIME type (if provided by the client)
        if file.content_type and file.content_type not in _ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Tipo MIME no permitido: '{file.content_type}'. "
                "Usa PDF, imagen (JPG/PNG/WEBP) o Excel/CSV."
            )

        supabase = get_supabase()
        if not supabase:
            # Fallback a local si no hay Supabase configurado (para desarrollo)
            tenant_folder = DocumentService._ensure_tenant_folder(str(current_tenant.id))
            extension = Path(file.filename).suffix
            internal_filename = f"{uuid.uuid4()}{extension}"
            file_path = tenant_folder / internal_filename
            with open(file_path, "wb") as f:
                f.write(content)
            storage_key = str(file_path).replace("\\", "/")
        else:
            # Subida a Supabase Storage
            bucket_name = "documents"
            extension = Path(file.filename).suffix
            storage_key = f"{current_tenant.id}/{uuid.uuid4()}{extension}"
            
            # Nota: Supone que el bucket 'documents' ya existe
            try:
                supabase.storage.from_(bucket_name).upload(
                    path=storage_key,
                    file=content,
                    file_options={"content-type": file.content_type}
                )
            except Exception as e:
                # Si falla Suapbase, intentamos logear o manejar el error
                raise ValueError(f"Error subiendo a Supabase: {str(e)}")

        checksum = hashlib.sha256(content).hexdigest()

        # Deduplication: reject if this exact file was already uploaded by this tenant
        duplicate = db.query(Document).filter(
            Document.tenant_id == current_tenant.id,
            Document.checksum == checksum,
        ).first()
        if duplicate:
            raise ValueError(
                f"Este documento ya fue subido anteriormente "
                f"('{duplicate.filename_original}')."
            )

        document = Document(
            tenant_id=current_tenant.id,
            uploaded_by_user_id=current_user.id,
            storage_key=storage_key,
            filename_original=file.filename,
            mime_type=file.content_type or "application/octet-stream",
            file_size=len(content),
            checksum=checksum,
            upload_status="uploaded",
            processing_status="pending"
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return document

    @staticmethod
    def list_documents_by_tenant(db: Session, tenant_id: str, skip: int = 0, limit: int = 50):
        from sqlalchemy import func
        from app.models.financial_movement import FinancialMovement

        # Single query: count movements per document via subquery to avoid N+1
        movements_count_sub = (
            db.query(
                FinancialMovement.source_document_id,
                func.count(FinancialMovement.id).label("movements_count"),
            )
            .group_by(FinancialMovement.source_document_id)
            .subquery()
        )

        rows = (
            db.query(Document, func.coalesce(movements_count_sub.c.movements_count, 0))
            .outerjoin(movements_count_sub, Document.id == movements_count_sub.c.source_document_id)
            .filter(Document.tenant_id == tenant_id)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        result = []
        for doc, count in rows:
            doc.movements_count = count
            result.append(doc)

        return result

    @staticmethod
    def get_document_by_id(db: Session, tenant_id: str, document_id: str) -> Document | None:
        from app.models.financial_movement import FinancialMovement
        doc = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                Document.tenant_id == tenant_id
            )
            .first()
        )
        
        if doc:
            doc.movements_count = db.query(FinancialMovement).filter(FinancialMovement.source_document_id == doc.id).count()
            
        return doc

    @staticmethod
    def analyze_excel(document: Document) -> dict:
        from app.services.excel_processing_service import ExcelProcessingService
        if not document.storage_key:
            return {"error": "No storage key for document"}
        
        return ExcelProcessingService.preview_document(document.storage_key)

    @staticmethod
    def delete_document(db: Session, document: Document) -> None:
        # Borrar archivo físico si existe
        if document.storage_key:
            # storage_key might be relative or absolute.
            # We already use storage/uploads/... in save_uploaded_document
            file_path = Path(document.storage_key)
            if file_path.exists() and file_path.is_file():
                try:
                    # In some environments, we might need to close all handles first.
                    # My recent changes to ExcelProcessingService use context managers which should help.
                    file_path.unlink()
                except OSError as e:
                    # Log but don't crash if delete record is the priority
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Could not delete physical file {file_path}: {str(e)}")
                    # We still raise if the user explicitly needs to know why it failed in the UI
                    # But if we want to allow database cleanup, we could just proceed.
                    # The user specifically complained about 400 error, so let's make it robust.
                    pass 

        # Borrar en orden para respetar FKs:
        # 1. Movimientos financieros (referencian FinancialEntry y Document)
        from app.models.financial_movement import FinancialMovement
        db.query(FinancialMovement).filter(FinancialMovement.source_document_id == document.id).delete(synchronize_session=False)

        # 2. Entradas financieras (referencian Document)
        from app.models.financial_entry import FinancialEntry
        db.query(FinancialEntry).filter(FinancialEntry.document_id == document.id).delete(synchronize_session=False)

        # 3. Jobs
        db.query(Job).filter(Job.document_id == document.id).delete(synchronize_session=False)

        # 4. Documento
        db.delete(document)
        db.commit()