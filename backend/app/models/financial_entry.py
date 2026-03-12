import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import String, DateTime, Date, ForeignKey, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FinancialEntry(Base):
    __tablename__ = "financial_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    extraction_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # income / expense

    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    supplier_or_customer: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    tax_base: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="EUR")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    status_review: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    tenant = relationship("Tenant", back_populates="financial_entries")
    document = relationship("Document", back_populates="financial_entries")
    extraction_run = relationship("ExtractionRun", back_populates="financial_entries")