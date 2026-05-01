import unicodedata


class DocumentClassifier:
    INCOME_TYPES = {
        "sales_invoice",
        "issued_invoice",
        "customer_invoice",
        "sale",
        "income",
        "receipt_sale",
        "venta",
        "factura_emitida",
        "factura_cliente",
        "ingreso",
    }

    EXPENSE_TYPES = {
        "supplier_invoice",
        "purchase_invoice",
        "expense",
        "ticket",
        "receipt",
        "gasto",
        "compra",
        "factura_proveedor",
        "factura_recibida",
    }

    INCOME_KEYWORDS = {
        "factura emitida",
        "factura cliente",
        "cliente",
        "customer",
        "sale",
        "venta",
        "ingreso",
        "invoice issued",
    }

    EXPENSE_KEYWORDS = {
        "factura proveedor",
        "factura recibida",
        "supplier",
        "proveedor",
        "expense",
        "gasto",
        "compra",
        "ticket",
        "receipt",
    }

    @staticmethod
    def _normalize(value: str | None) -> str:
        if not value:
            return ""
        text = str(value).strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return text

    @staticmethod
    def _matches_tenant(name: str | None, tenant_name: str | None) -> bool:
        if not name or not tenant_name:
            return False
        n = DocumentClassifier._normalize(name)
        t = DocumentClassifier._normalize(tenant_name)
        return t in n or n in t

    @classmethod
    def classify(cls, normalized_data: dict | None, raw_data: dict | None = None, tenant_name: str | None = None) -> str:
        normalized_data = normalized_data or {}
        raw_data = raw_data or {}

        explicit_kind = cls._normalize(normalized_data.get("kind"))
        if explicit_kind in {"income", "expense"}:
            return explicit_kind

        # Señal muy fuerte: pie de factura propia ("ELABORADO POR")
        if raw_data.get("has_elaborado_por"):
            return "income"

        # Comparación con el tenant actual: si sabemos quién emite y quién recibe
        if tenant_name:
            supplier_name_raw = normalized_data.get("supplier_name")
            receiver_name_raw = normalized_data.get("receiver_name")
            if supplier_name_raw or receiver_name_raw:
                if cls._matches_tenant(supplier_name_raw, tenant_name):
                    return "income"
                if cls._matches_tenant(receiver_name_raw, tenant_name):
                    return "expense"

        document_type = cls._normalize(normalized_data.get("document_type"))
        if document_type in cls.INCOME_TYPES:
            return "income"
        if document_type in cls.EXPENSE_TYPES:
            return "expense"

        # señales estructuradas
        customer_name = cls._normalize(
            normalized_data.get("customer_name") or normalized_data.get("client_name")
        )
        supplier_name = cls._normalize(normalized_data.get("supplier_name"))

        if customer_name and not supplier_name:
            return "income"
        if supplier_name and not customer_name:
            return "expense"

        # señales por texto libre
        searchable_parts = [
            normalized_data.get("document_type"),
            normalized_data.get("description"),
            normalized_data.get("title"),
            normalized_data.get("notes"),
            raw_data.get("supplier"),
            raw_data.get("customer"),
            raw_data.get("title"),
            raw_data.get("text"),
        ]
        searchable_text = " ".join(cls._normalize(v) for v in searchable_parts if v)

        if any(keyword in searchable_text for keyword in cls.INCOME_KEYWORDS):
            return "income"

        if any(keyword in searchable_text for keyword in cls.EXPENSE_KEYWORDS):
            return "expense"

        # fallback conservador
        return "expense"