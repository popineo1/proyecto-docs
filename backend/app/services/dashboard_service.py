from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.financial_entry import FinancialEntry
from app.models.tenant import Tenant


class DashboardService:
    @staticmethod
    def get_summary(db: Session, tenant: Tenant):
        total_expenses = (
            db.query(func.coalesce(func.sum(FinancialEntry.total_amount), 0))
            .filter(
                FinancialEntry.tenant_id == tenant.id,
                FinancialEntry.kind == "expense"
            )
            .scalar()
        )

        total_income = (
            db.query(func.coalesce(func.sum(FinancialEntry.total_amount), 0))
            .filter(
                FinancialEntry.tenant_id == tenant.id,
                FinancialEntry.kind == "income"
            )
            .scalar()
        )

        total_vat = (
            db.query(func.coalesce(func.sum(FinancialEntry.tax_amount), 0))
            .filter(FinancialEntry.tenant_id == tenant.id)
            .scalar()
        )

        documents_processed = (
            db.query(func.count(Document.id))
            .filter(
                Document.tenant_id == tenant.id,
                Document.processing_status.in_(["processed", "pending", "review", "error"])
            )
            .scalar()
        )

        pending_reviews = (
            db.query(func.count(FinancialEntry.id))
            .filter(
                FinancialEntry.tenant_id == tenant.id,
                FinancialEntry.status_review == "pending"
            )
            .scalar()
        )

        return {
            "total_expenses": float(total_expenses or Decimal("0")),
            "total_income": float(total_income or Decimal("0")),
            "total_vat": float(total_vat or Decimal("0")),
            "documents_processed": int(documents_processed or 0),
            "pending_reviews": int(pending_reviews or 0),
        }
