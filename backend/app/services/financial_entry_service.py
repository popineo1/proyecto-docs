from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.extraction_run import ExtractionRun
from app.models.financial_entry import FinancialEntry
from app.models.tenant import Tenant
from app.services.document_classifier import DocumentClassifier
from app.services.financial_movement_writer import FinancialMovementWriter


_DATE_FORMATS = [
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d.%m.%y",
]


def _parse_date(raw: str) -> date | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


class FinancialEntryService:
    @staticmethod
    def create_from_extraction(
        db: Session,
        extraction: ExtractionRun
    ) -> FinancialEntry:
        data = extraction.normalized_output_json or {}
        raw_data = extraction.raw_output_json or {}

        tenant = db.query(Tenant).filter(Tenant.id == extraction.tenant_id).first()
        tenant_name = tenant.name if tenant else None

        entry_kind = DocumentClassifier.classify(
            normalized_data=data,
            raw_data=raw_data,
            tenant_name=tenant_name,
        )

        if entry_kind == "income":
            # tercero = quien me paga → receptor/cliente de la factura
            supplier_or_customer = (
                data.get("receiver_name")
                or data.get("customer_name")
                or data.get("client_name")
            )
        else:
            # tercero = quien me cobra → emisor/proveedor de la factura
            supplier_or_customer = (
                data.get("supplier_name")
                or raw_data.get("issuer")
                or data.get("customer_name")
            )


        issue_date_raw = data.get("issue_date")
        total_amount_raw = data.get("total_amount")
        vat_rate_raw = data.get("vat_rate")
        document_type = data.get("document_type")

        issue_date_value = None
        if issue_date_raw:
            issue_date_value = _parse_date(issue_date_raw)

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
            kind=entry_kind,
            issue_date=issue_date_value,
            supplier_or_customer=supplier_or_customer,
            tax_base=tax_base,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency="EUR",
            category=document_type,
            status_review="pending",
            notes=f"Entrada creada automáticamente desde extraction_run ({entry_kind})"
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)

        FinancialMovementWriter.sync_from_financial_entry(db, entry)

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

        if payload.kind is not None:
            entry.kind = payload.kind

        db.commit()
        db.refresh(entry)

        FinancialMovementWriter.sync_from_financial_entry(db, entry)

        return entry