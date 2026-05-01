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

        content = await file.read()
        if not content:
            raise ValueError("El archivo está vacío")

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
    def list_documents_by_tenant(db: Session, tenant_id: str):
        from app.models.financial_movement import FinancialMovement
        documents = (
            db.query(Document)
            .filter(Document.tenant_id == tenant_id)
            .order_by(Document.created_at.desc())
            .all()
        )
        
        # Attach counts (adhoc for now, could be optimized with a join)
        for doc in documents:
            doc.movements_count = db.query(FinancialMovement).filter(FinancialMovement.source_document_id == doc.id).count()
            
        return documents

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