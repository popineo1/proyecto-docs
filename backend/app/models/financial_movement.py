import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FinancialMovement(Base):
    __tablename__ = "financial_movements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    movement_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    kind: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # income | expense | tax | payroll | social_security | transfer | financing

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="proposed",
        index=True,
    )  # draft | proposed | confirmed | reconciled | archived

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # document | excel_import | bank_import | manual

    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source_financial_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("financial_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source_purchase_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    third_party_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    third_party_tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    concept: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    business_area: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    net_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    withholding_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="EUR")

    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    needs_review: Mapped[bool] = mapped_column(nullable=False, default=True, index=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_data: Mapped[dict | None] = mapped_column(Text, nullable=True) # Storing as text or JSON if possible
    
    # Confidence & Traceability
    confidence_level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)  # high | medium | low
    confidence_flags: Mapped[list | None] = mapped_column(Text, nullable=True) # JSON or Comma-separated
    source_raw_data: Mapped[str | None] = mapped_column(Text, nullable=True) # JSON of the original row
    inference_log: Mapped[str | None] = mapped_column(Text, nullable=True) # JSON log of changes

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="financial_movements")
    source_document = relationship("Document")
    source_financial_entry = relationship("FinancialEntry")
    source_purchase_entry = relationship("PurchaseEntry")