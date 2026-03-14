from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.extraction_run import ExtractionRun
from app.models.financial_entry import FinancialEntry


class FinancialEntryService:
    @staticmethod
    def create_from_extraction(
        db: Session,
        extraction: ExtractionRun
    ) -> FinancialEntry:
        data = extraction.normalized_output_json or {}

        supplier_name = data.get("supplier_name")
        issue_date_raw = data.get("issue_date")
        total_amount_raw = data.get("total_amount")
        vat_rate_raw = data.get("vat_rate")
        document_type = data.get("document_type")

        issue_date_value = None
        if issue_date_raw:
            issue_date_value = date.fromisoformat(issue_date_raw)

        total_amount = None
        if total_amount_raw is not None:
            total_amount = Decimal(str(total_amount_raw)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

        vat_rate = Decimal("0")
        if vat_rate_raw is not None:
            vat_rate = Decimal(str(vat_rate_raw))

        tax_amount = None
        tax_base = None

        if total_amount is not None and vat_rate > 0:
            divisor = Decimal("1") + (vat_rate / Decimal("100"))
            tax_base = (total_amount / divisor).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )
            tax_amount = (total_amount - tax_base).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )
        elif total_amount is not None:
            tax_base = total_amount
            tax_amount = Decimal("0.00")

        entry = FinancialEntry(
            tenant_id=extraction.tenant_id,
            document_id=extraction.document_id,
            extraction_run_id=extraction.id,
            kind="expense",
            issue_date=issue_date_value,
            supplier_or_customer=supplier_name,
            tax_base=tax_base,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency="EUR",
            category=document_type,
            status_review="pending",
            notes="Entrada creada automáticamente desde extraction_run mock"
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)

        return entry

    @staticmethod
    def list_by_tenant(db: Session, tenant_id: UUID):
        return (
            db.query(FinancialEntry)
            .filter(FinancialEntry.tenant_id == tenant_id)
            .order_by(FinancialEntry.created_at.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, tenant_id: UUID, entry_id: UUID) -> FinancialEntry | None:
        return (
            db.query(FinancialEntry)
            .filter(
                FinancialEntry.id == entry_id,
                FinancialEntry.tenant_id == tenant_id
            )
            .first()
        )
    
    @staticmethod
    def review_entry(
        db: Session,
        entry: FinancialEntry,
        payload
    ) -> FinancialEntry:

        entry.status_review = payload.status_review

        if payload.supplier_or_customer is not None:
            entry.supplier_or_customer = payload.supplier_or_customer

        if payload.issue_date is not None:
            entry.issue_date = payload.issue_date

        if payload.tax_base is not None:
            entry.tax_base = payload.tax_base

        if payload.tax_amount is not None:
            entry.tax_amount = payload.tax_amount

        if payload.total_amount is not None:
            entry.total_amount = payload.total_amount

        if payload.category is not None:
            entry.category = payload.category

        db.commit()
        db.refresh(entry)

        return entry

