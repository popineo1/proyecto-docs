import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, BigInteger, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    upload_status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded", index=True)
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)

    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    tenant = relationship("Tenant", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="uploaded_documents")

    jobs = relationship("Job", back_populates="document", cascade="all, delete-orphan")
    extraction_runs = relationship("ExtractionRun", back_populates="document", cascade="all, delete-orphan")
    financial_entries = relationship("FinancialEntry", back_populates="document", cascade="all, delete-orphan")