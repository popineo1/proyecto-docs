from decimal import Decimal

from sqlalchemy import Date, func
from sqlalchemy.orm import Session

from app.models.financial_movement import FinancialMovement


class AnalyticsService:
    @staticmethod
    def _safe_decimal(value) -> Decimal:
        if value is None:
            return Decimal("0.00")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def get_overview(db: Session, tenant_id):
        # Base filters for consolidated movements
        base_filter = [
            FinancialMovement.tenant_id == tenant_id,
            FinancialMovement.status.in_(["proposed", "confirmed", "reconciled"]),
        ]

        # Total Income
        income_total = (
            db.query(func.sum(FinancialMovement.total_amount))
            .filter(*base_filter, FinancialMovement.kind == "income")
            .scalar()
        )

        # Total Expenses (all non-income categories)
        expense_kinds = ["expense", "tax", "payroll", "social_security", "financing"]
        expense_total = (
            db.query(func.sum(FinancialMovement.total_amount))
            .filter(*base_filter, FinancialMovement.kind.in_(expense_kinds))
            .scalar()
        )

        # VAT metrics
        vat_charged = (
            db.query(func.sum(FinancialMovement.tax_amount))
            .filter(*base_filter, FinancialMovement.kind == "income")
            .scalar()
        )
        vat_supported = (
            db.query(func.sum(FinancialMovement.tax_amount))
            .filter(*base_filter, FinancialMovement.kind.in_(expense_kinds))
            .scalar()
        )

        # Retentions
        retention_sales = (
            db.query(func.sum(FinancialMovement.withholding_amount))
            .filter(*base_filter, FinancialMovement.kind == "income")
            .scalar()
        )
        # Assuming retenciones de alquiler are expenses with a specific category or document type
        retention_rent = (
            db.query(func.sum(FinancialMovement.withholding_amount))
            .filter(
                *base_filter,
                FinancialMovement.kind == "expense",
                FinancialMovement.category.ilike("%alquiler%")
            )
            .scalar()
        )

        income_total = AnalyticsService._safe_decimal(income_total)
        expense_total = AnalyticsService._safe_decimal(expense_total)
        vat_charged = AnalyticsService._safe_decimal(vat_charged)
        vat_supported = AnalyticsService._safe_decimal(vat_supported)
        retention_sales = AnalyticsService._safe_decimal(retention_sales)
        retention_rent = AnalyticsService._safe_decimal(retention_rent)

        avg_ticket = (
            db.query(func.avg(FinancialMovement.total_amount))
            .filter(*base_filter, FinancialMovement.kind == "income")
            .scalar()
        )

        documents_processed = (
            db.query(func.count(FinancialMovement.id))
            .filter(FinancialMovement.tenant_id == tenant_id)
            .scalar()
        )

        pending_reviews = (
            db.query(func.count(FinancialMovement.id))
            .filter(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.needs_review.is_(True),
            )
            .scalar()
        )

        # Burn Rate Calculation
        fixed_categories = ["Alquiler", "Personal / Seguros Sociales", "Nóminas", "Estructura"]
        variable_categories = ["Suscripciones / Software", "Marketing", "Suministros", "Otros"]

        fixed_burn = (
            db.query(func.sum(FinancialMovement.total_amount))
            .filter(
                *base_filter,
                FinancialMovement.kind.in_(expense_kinds),
                FinancialMovement.category.in_(fixed_categories)
            ).scalar()
        )
        variable_burn = (
            db.query(func.sum(FinancialMovement.total_amount))
            .filter(
                *base_filter,
                FinancialMovement.kind.in_(expense_kinds),
                FinancialMovement.category.in_(variable_categories)
            ).scalar()
        )

        return {
            "total_income": income_total,
            "total_expenses": expense_total,
            "net_profit": income_total - expense_total,
            "vat_charged": vat_charged,
            "vat_supported": vat_supported,
            "vat_balance": vat_supported - vat_charged,
            "retention_sales": retention_sales,
            "retention_rent": retention_rent,
            "average_ticket": AnalyticsService._safe_decimal(avg_ticket),
            "documents_processed": int(documents_processed or 0),
            "pending_reviews": int(pending_reviews or 0),
            "fixed_burn_rate": AnalyticsService._safe_decimal(fixed_burn),
            "variable_burn_rate": AnalyticsService._safe_decimal(variable_burn),
            "forecast_vat": vat_supported - vat_charged,
            "forecast_irpf": retention_sales + retention_rent,
        }

    @staticmethod
    def get_monthly_flow(db: Session, tenant_id):
        # We use movement_date or created_at as fallback
        date_col = func.coalesce(FinancialMovement.movement_date, func.cast(FinancialMovement.created_at, Date))
        month_expr = func.to_char(date_col, "YYYY-MM")

        expense_kinds = ["expense", "tax", "payroll", "social_security", "financing"]

        rows = (
            db.query(
                month_expr.label("month"),
                func.sum(FinancialMovement.total_amount).filter(FinancialMovement.kind == "income").label("income"),
                func.sum(FinancialMovement.total_amount).filter(FinancialMovement.kind.in_(expense_kinds)).label("expenses"),
            )
            .filter(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.status.in_(["proposed", "confirmed", "reconciled"]),
            )
            .group_by(month_expr)
            .order_by(month_expr)
            .all()
        )

        return [
            {
                "month": row.month,
                "income": AnalyticsService._safe_decimal(row.income),
                "expenses": AnalyticsService._safe_decimal(row.expenses),
                "profit": AnalyticsService._safe_decimal(row.income) - AnalyticsService._safe_decimal(row.expenses),
            }
            for row in rows
        ]

    @staticmethod
    def get_top_customers(db: Session, tenant_id, limit: int = 5):
        rows = (
            db.query(
                FinancialMovement.third_party_name.label("name"),
                func.sum(FinancialMovement.total_amount).label("amount"),
            )
            .filter(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.kind == "income",
                FinancialMovement.status.in_(["proposed", "confirmed", "reconciled"]),
                FinancialMovement.third_party_name.isnot(None),
            )
            .group_by(FinancialMovement.third_party_name)
            .order_by(func.sum(FinancialMovement.total_amount).desc())
            .limit(limit)
            .all()
        )
        return [{"name": r.name, "amount": AnalyticsService._safe_decimal(r.amount)} for r in rows]

    @staticmethod
    def get_top_suppliers(db: Session, tenant_id, limit: int = 5):
        expense_kinds = ["expense", "tax", "payroll", "social_security", "financing"]
        rows = (
            db.query(
                FinancialMovement.third_party_name.label("name"),
                func.sum(FinancialMovement.total_amount).label("amount"),
            )
            .filter(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.kind.in_(expense_kinds),
                FinancialMovement.status.in_(["proposed", "confirmed", "reconciled"]),
                FinancialMovement.third_party_name.isnot(None),
            )
            .group_by(FinancialMovement.third_party_name)
            .order_by(func.sum(FinancialMovement.total_amount).desc())
            .limit(limit)
            .all()
        )
        return [{"name": r.name, "amount": AnalyticsService._safe_decimal(r.amount)} for r in rows]

    @staticmethod
    def get_expenses_by_category(db: Session, tenant_id, limit: int = 6):
        expense_kinds = ["expense", "tax", "payroll", "social_security", "financing"]
        rows = (
            db.query(
                FinancialMovement.category.label("category_name"),
                func.sum(FinancialMovement.total_amount).label("total_amount"),
            )
            .filter(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.kind.in_(expense_kinds),
                FinancialMovement.status.in_(["proposed", "confirmed", "reconciled"]),
                FinancialMovement.category.isnot(None),
            )
            .group_by(FinancialMovement.category)
            .order_by(func.sum(FinancialMovement.total_amount).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "category_name": row.category_name or "Sin categoría",
                "total_amount": AnalyticsService._safe_decimal(row.total_amount).quantize(Decimal("0.01")),
            }
            for row in rows
        ]

    @staticmethod
    def get_income_by_category(db: Session, tenant_id, limit: int = 6):
        rows = (
            db.query(
                FinancialMovement.category.label("category_name"),
                func.sum(FinancialMovement.total_amount).label("total_amount"),
            )
            .filter(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.kind == "income",
                FinancialMovement.status.in_(["proposed", "confirmed", "reconciled"]),
                FinancialMovement.category.isnot(None),
            )
            .group_by(FinancialMovement.category)
            .order_by(func.sum(FinancialMovement.total_amount).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "category_name": row.category_name or "Sin categoría",
                "total_amount": AnalyticsService._safe_decimal(row.total_amount).quantize(Decimal("0.01")),
            }
            for row in rows
        ]

    @staticmethod
    def get_tax_monthly_flow(db: Session, tenant_id):
        date_col = func.coalesce(FinancialMovement.movement_date, func.cast(FinancialMovement.created_at, Date))
        month_expr = func.to_char(date_col, "YYYY-MM")
        expense_kinds = ["expense", "tax", "payroll", "social_security", "financing"]

        rows = (
            db.query(
                month_expr.label("month"),
                func.sum(FinancialMovement.tax_amount).filter(FinancialMovement.kind == "income").label("vat_charged"),
                func.sum(FinancialMovement.tax_amount).filter(FinancialMovement.kind.in_(expense_kinds)).label("vat_supported"),
                func.sum(FinancialMovement.withholding_amount).filter(FinancialMovement.kind == "income").label("retention_sales"),
                func.sum(FinancialMovement.withholding_amount).filter(
                    FinancialMovement.kind == "expense", 
                    FinancialMovement.category.ilike("%alquiler%")
                ).label("retention_rent"),
            )
            .filter(
                FinancialMovement.tenant_id == tenant_id,
                FinancialMovement.status.in_(["proposed", "confirmed", "reconciled"]),
            )
            .group_by(month_expr)
            .order_by(month_expr)
            .all()
        )

        return [
            {
                "month": row.month,
                "vat_charged": AnalyticsService._safe_decimal(row.vat_charged),
                "vat_supported": AnalyticsService._safe_decimal(row.vat_supported),
                "vat_balance": AnalyticsService._safe_decimal(row.vat_supported) - AnalyticsService._safe_decimal(row.vat_charged),
                "retention_sales": AnalyticsService._safe_decimal(row.retention_sales),
                "retention_rent": AnalyticsService._safe_decimal(row.retention_rent),
            }
            for row in rows
        ]