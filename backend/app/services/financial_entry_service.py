from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.extraction_run import ExtractionRun
from app.models.financial_entry import FinancialEntry
from app.models.tenant import Tenant
from app.services.document_classifier import DocumentClassifier
from app.services.financial_movement_writer import FinancialMovementWriter


# Traducciones de categorías en inglés (o variantes) a español normalizado
_CATEGORY_EN_TO_ES: dict[str, str] = {
    "insurance": "Seguros",
    "health insurance": "Seguros",
    "health_insurance": "Seguros",
    "medical insurance": "Seguros",
    "medical_insurance": "Seguros",
    "utilities": "Suministros",
    "supplies": "Suministros",
    "software": "Software y suscripciones",
    "software & subscriptions": "Software y suscripciones",
    "software and subscriptions": "Software y suscripciones",
    "subscriptions": "Software y suscripciones",
    "saas": "Software y suscripciones",
    "rent": "Alquileres",
    "rental": "Alquileres",
    "salaries": "Nóminas",
    "payroll": "Nóminas",
    "wages": "Nóminas",
    "tax": "Impuestos",
    "taxes": "Impuestos",
    "bank fees": "Bancos y comisiones",
    "bank_fees": "Bancos y comisiones",
    "banking fees": "Bancos y comisiones",
    "banking": "Bancos y comisiones",
    "commissions": "Bancos y comisiones",
    "office supplies": "Material de oficina",
    "office_supplies": "Material de oficina",
    "stationery": "Material de oficina",
    "transport": "Transporte",
    "transportation": "Transporte",
    "travel": "Transporte",
    "consulting": "Consultoría",
    "consultancy": "Consultoría",
    "professional services": "Gestoría / asesoría",
    "professional_services": "Gestoría / asesoría",
    "accounting": "Gestoría / asesoría",
    "legal": "Gestoría / asesoría",
    "telecommunications": "Telecomunicaciones",
    "telecom": "Telecomunicaciones",
    "phone": "Telecomunicaciones",
    "internet": "Telecomunicaciones",
    "marketing": "Marketing",
    "advertising": "Marketing",
    "training": "Formación / talleres",
    "education": "Formación / talleres",
    "administrative services": "Servicios administrativos",
    "digitalization": "Digitalización",
    "digitization": "Digitalización",
    "technology": "Desarrollo / tecnología",
    "development": "Desarrollo / tecnología",
    "other": "Otros gastos",
    "others": "Otros gastos",
    "other expenses": "Otros gastos",
    "other income": "Otros ingresos",
    "miscellaneous": "Otros gastos",
}

_INVALID_CATEGORIES = {"invoice", "receipt", "ticket", "other", "factura", "recibo", "albaran"}

# Mapa de palabras clave en nombre de proveedor → categoría de negocio.
# Se aplica como override cuando la IA no clasifica correctamente.
# Formato: (subcadena_en_minúsculas, categoría_destino)
_VENDOR_CATEGORY_MAP: list[tuple[str, str]] = [
    ("neting", "Software y suscripciones"),
    ("adeslas", "Seguros"),
    ("segurcaixa", "Seguros"),
    ("mapfre", "Seguros"),
    ("movistar", "Telecomunicaciones"),
    ("vodafone", "Telecomunicaciones"),
    ("orange", "Telecomunicaciones"),
    ("jazztel", "Telecomunicaciones"),
    ("endesa", "Suministros"),
    ("iberdrola", "Suministros"),
    ("naturgy", "Suministros"),
]


def _category_from_vendor(supplier: str | None) -> str | None:
    if not supplier:
        return None
    lower = supplier.strip().lower()
    for keyword, category in _VENDOR_CATEGORY_MAP:
        if keyword in lower:
            return category
    return None


def _normalize_category(value: str | None, entry_kind: str) -> str:
    fallback = "Otros ingresos" if entry_kind == "income" else "Otros gastos"
    if not value or not value.strip():
        return fallback
    cleaned = value.strip()
    translated = _CATEGORY_EN_TO_ES.get(cleaned.lower())
    if translated:
        return translated
    if cleaned.lower() in _INVALID_CATEGORIES:
        return fallback
    return cleaned


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

        # Si la IA ya determinó el kind, usarlo directamente; si no, clasificar
        ai_kind = data.get("operation_kind")
        if ai_kind in {"income", "expense"}:
            entry_kind = ai_kind
        else:
            entry_kind = DocumentClassifier.classify(
                normalized_data=data,
                raw_data=raw_data,
                tenant_name=tenant_name,
            )

        # third_party_name viene directo de la IA si está disponible
        ai_third_party = data.get("third_party_name")

        if ai_third_party:
            supplier_or_customer = ai_third_party
        elif entry_kind == "income":
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
        tax_base_raw = data.get("tax_base")
        tax_amount_raw = data.get("tax_amount")
        vat_rate_raw = data.get("vat_rate")
        document_type = data.get("document_type")

        # Categoría de negocio normalizada a español (nunca usar document_type)
        business_category = _normalize_category(data.get("category"), entry_kind)
        # Override por proveedor conocido (más fiable que la IA para nombres concretos)
        vendor_override = _category_from_vendor(supplier_or_customer)
        if vendor_override:
            business_category = vendor_override

        # IRPF / retención: siempre positivo (en facturas aparece restando)
        irpf_amount: Decimal | None = None
        irpf_raw = data.get("irpf_amount")
        if irpf_raw is not None:
            try:
                irpf_amount = Decimal(str(abs(float(irpf_raw)))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            except (ValueError, ArithmeticError):
                irpf_amount = None

        issue_date_value = None
        if issue_date_raw:
            issue_date_value = _parse_date(issue_date_raw)

        total_amount = None
        if total_amount_raw is not None:
            total_amount = Decimal(str(total_amount_raw)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

        # Usar tax_base y tax_amount directos si los proveyó la IA
        tax_base = None
        tax_amount = None

        if tax_base_raw is not None and tax_amount_raw is not None:
            tax_base = Decimal(str(tax_base_raw)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            tax_amount = Decimal(str(tax_amount_raw)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            vat_rate = Decimal("0")
            if vat_rate_raw is not None:
                vat_rate = Decimal(str(vat_rate_raw))

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

        needs_review: bool = bool(data.get("needs_review", False))

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
            category=business_category,
            status_review="pending",
            needs_review=needs_review,
            notes=f"Entrada creada automáticamente desde extraction_run ({entry_kind})"
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)

        import logging as _logging
        _log = _logging.getLogger(__name__)
        _log.warning(
            "[FINANCIAL_ENTRY] doc_id=%s | kind=%s | category=%s | supplier_or_customer=%s | "
            "tax_base=%s | tax_amount=%s | irpf=%s | total_amount=%s",
            extraction.document_id,
            entry.kind,
            entry.category,
            entry.supplier_or_customer,
            entry.tax_base,
            entry.tax_amount,
            irpf_amount,
            entry.total_amount,
        )

        FinancialMovementWriter.sync_from_financial_entry(db, entry, irpf_amount=irpf_amount)

        return entry

    @staticmethod
    def list_by_tenant(db: Session, tenant_id: UUID, skip: int = 0, limit: int = 50):
        return (
            db.query(FinancialEntry)
            .filter(FinancialEntry.tenant_id == tenant_id)
            .order_by(FinancialEntry.created_at.desc())
            .offset(skip)
            .limit(limit)
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
    def resync_from_extraction_runs(
        db: Session,
        tenant_id: UUID,
    ) -> dict:
        import logging as _logging
        _log = _logging.getLogger(__name__)

        runs = (
            db.query(ExtractionRun)
            .filter(
                ExtractionRun.tenant_id == tenant_id,
                ExtractionRun.status == "completed",
                ExtractionRun.normalized_output_json.isnot(None),
            )
            .all()
        )

        updated = 0
        skipped = 0
        errors: list[dict] = []

        for run in runs:
            try:
                entry = (
                    db.query(FinancialEntry)
                    .filter(FinancialEntry.extraction_run_id == run.id)
                    .first()
                )
                if not entry:
                    skipped += 1
                    continue

                data = run.normalized_output_json or {}

                # Re-aplicar normalización de categoría con la lógica corregida
                new_category = _normalize_category(data.get("category"), entry.kind)
                # Override por proveedor conocido
                vendor_override = _category_from_vendor(entry.supplier_or_customer)
                if vendor_override:
                    new_category = vendor_override

                # Re-extraer IRPF como valor positivo
                irpf_amount: Decimal | None = None
                irpf_raw = data.get("irpf_amount")
                if irpf_raw is not None:
                    try:
                        irpf_amount = Decimal(str(abs(float(irpf_raw)))).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    except (ValueError, ArithmeticError):
                        irpf_amount = None

                # Actualizar categoría siempre (fix de datos)
                entry.category = new_category

                # Actualizar needs_review solo si aún no ha sido revisado manualmente
                if entry.status_review == "pending":
                    entry.needs_review = bool(data.get("needs_review", False))

                db.add(entry)
                db.commit()
                db.refresh(entry)

                FinancialMovementWriter.sync_from_financial_entry(db, entry, irpf_amount=irpf_amount)

                _log.warning(
                    "[RESYNC] entry_id=%s | doc_id=%s | category=%s→%s | irpf=%s | needs_review=%s",
                    entry.id,
                    run.document_id,
                    data.get("category"),
                    new_category,
                    irpf_amount,
                    entry.needs_review,
                )
                updated += 1

            except Exception as exc:
                _log.error("[RESYNC] Error en run_id=%s: %s", run.id, exc)
                errors.append({"run_id": str(run.id), "error": str(exc)})
                db.rollback()

        return {
            "runs_found": len(runs),
            "entries_updated": updated,
            "entries_skipped": skipped,
            "errors": errors,
        }

    @staticmethod
    def review_entry(
        db: Session,
        entry: FinancialEntry,
        payload
    ) -> FinancialEntry:
        entry.status_review = payload.status_review
        if payload.status_review in {"revisado", "approved", "descartado", "rejected"}:
            entry.needs_review = False

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