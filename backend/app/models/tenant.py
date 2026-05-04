import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    vertical: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    fiscal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Stripe Billing
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    subscription_status: Mapped[str | None] = mapped_column(String(50), nullable=True)   # active, past_due, canceled…
    subscription_plan: Mapped[str | None] = mapped_column(String(100), nullable=True)    # price_id o alias legible
    subscription_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    memberships = relationship("Membership", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="tenant", cascade="all, delete-orphan")
    extraction_runs = relationship("ExtractionRun", back_populates="tenant", cascade="all, delete-orphan")
    financial_entries = relationship("FinancialEntry", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant")
    purchase_entries = relationship("PurchaseEntry", back_populates="tenant", cascade="all, delete-orphan")
    purchase_import_batches = relationship("PurchaseImportBatch", back_populates="tenant", cascade="all, delete-orphan")
    monthly_kpi_snapshots = relationship("MonthlyKpiSnapshot", back_populates="tenant", cascade="all, delete-orphan")
    provider_metric_snapshots = relationship("ProviderMetricSnapshot", back_populates="tenant", cascade="all, delete-orphan")
    category_metric_snapshots = relationship("CategoryMetricSnapshot", back_populates="tenant", cascade="all, delete-orphan")
    financial_movements = relationship("FinancialMovement", back_populates="tenant", cascade="all, delete-orphan")