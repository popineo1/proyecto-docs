import json
import logging
import re
import unicodedata

from app.schemas.ai_extraction import AIExtractionResult

logger = logging.getLogger(__name__)

_MAX_TEXT_CHARS = 6000

_INVALID_THIRD_PARTY_TERMS = {
    "factura", "factura ordinaria", "factura simplificada", "factura rectificativa",
    "adeudo por", "adeudo", "domiciliaciones sepa", "domiciliacion sepa", "sepa",
    "total factura", "importe total", "importe", "total",
    "datos cliente", "datos del cliente", "datos proveedor", "datos fiscales",
    "concepto", "descripcion", "observaciones", "notas",
    "invoice", "receipt", "ticket", "recibo", "albaran",
    "cargo", "abono", "pago", "cobro", "transferencia",
    "extracto", "resumen", "liquidacion", "presupuesto",
    "n/a", "ninguno", "desconocido", "unknown", "sin nombre",
}

_SYSTEM_PROMPT_TEMPLATE = """\
Eres un experto en contabilidad y documentos fiscales españoles. Analiza el documento \
y extrae su información en formato JSON.

## Identidad del usuario (NUNCA poner en third_party_name)
{tenant_block}

## Reglas de clasificación operation_kind
- income: el usuario es el EMISOR de la factura (él cobra al cliente)
- expense: el usuario es el RECEPTOR (él paga al proveedor)
- unknown: no se puede determinar con certeza

## Reglas CRÍTICAS para third_party_name
1. Debe ser la persona o empresa EXTERNA real que interviene en la operación.
2. Si operation_kind = income → third_party_name = el cliente/receptor (quien paga al usuario).
3. Si operation_kind = expense → third_party_name = el proveedor/emisor (a quien paga el usuario).
4. NUNCA puede ser el propio usuario ni ninguno de sus alias listados arriba.
5. NUNCA puede ser un título de documento ni término genérico como:
   FACTURA, ADEUDO POR, DOMICILIACIONES SEPA, TOTAL FACTURA, DATOS CLIENTE,
   CONCEPTO, RECIBO, TICKET, TRANSFERENCIA, EXTRACTO, CARGO, ABONO.
6. Si no puedes identificar un tercero externo real con certeza, pon null y marca needs_review = true.

## Reglas para category (categoría de NEGOCIO, no tipo de documento)
- category NO puede ser "invoice", "receipt", "ticket", "other" ni ningún tipo de documento.
- document_type y category son campos distintos: document_type describe el formato, category describe el negocio.
- Usa EXACTAMENTE uno de estos valores según operation_kind:

  Si operation_kind = income:
  - "Servicios administrativos"
  - "Digitalización"
  - "Desarrollo / tecnología"
  - "Formación / talleres"
  - "Consultoría"
  - "Otros ingresos"

  Si operation_kind = expense:
  - "Software y suscripciones"
  - "Seguros"
  - "Telecomunicaciones"
  - "Alquileres"
  - "Suministros"
  - "Material de oficina"
  - "Gestoría / asesoría"
  - "Transporte"
  - "Bancos y comisiones"
  - "Otros gastos"

- Si operation_kind = unknown o la categoría no encaja con ninguna de las anteriores:
  - Usa "Otros ingresos" si parece un ingreso, o "Otros gastos" si parece un gasto.

## Reglas para campos fiscales adicionales
- vat_pct: porcentaje IVA aplicado. España: general=21, reducido=10, superreducido=4.
- irpf_pct / irpf_amount: retención IRPF. El profesional cobra total = base + iva - irpf_retenido.
  Tipos habituales: 15% (profesional estándar), 7% (nuevos autónomos primeros 2 años), 19% (alquileres).
- inversion_sujeto_pasivo: true cuando la factura viene de empresa extranjera UE/EEUU sin IVA español.
  Ejemplos: Anthropic, OpenAI, Google LLC, Lovable, GitHub, AWS, Stripe, Adobe, Microsoft Ireland.
  En ese caso vat_amount=0, vat_pct=0, inversion_sujeto_pasivo=true.
- es_rectificativa: true si el documento contiene "ABONO", "RECTIFICATIVA", "Credit Note" o importes negativos.
  En ese caso rectifica_a = número de la factura original que anula.
- trimestre: Q1=enero-marzo, Q2=abril-junio, Q3=julio-septiembre, Q4=octubre-diciembre.
  Calcularlo siempre a partir de issue_date si está disponible.

## Formato de respuesta (JSON estricto)
{{
  "document_type": "invoice|ticket|receipt|other",
  "operation_kind": "income|expense|unknown",
  "issuer_name": "nombre del emisor o null",
  "issuer_tax_id": "NIF/CIF del emisor o null",
  "receiver_name": "nombre del receptor/cliente o null",
  "receiver_tax_id": "NIF/CIF del receptor o null",
  "third_party_name": "tercero externo real o null",
  "third_party_tax_id": "NIF/CIF del tercero o null",
  "invoice_number": "número de factura o null",
  "issue_date": "DD/MM/YYYY o null",
  "due_date": "DD/MM/YYYY o null",
  "tax_base": número o null,
  "vat_amount": número o null,
  "vat_pct": número (21/10/4/0) o null,
  "irpf_amount": número o null,
  "irpf_pct": número (15/7/19) o null,
  "total_amount": número o null,
  "currency": "EUR",
  "trimestre": "Q1"|"Q2"|"Q3"|"Q4" o null,
  "es_rectificativa": true|false,
  "rectifica_a": "número factura original o null",
  "inversion_sujeto_pasivo": true|false,
  "category": "una de las categorías de negocio listadas arriba",
  "confidence_score": número entre 0.0 y 1.0,
  "needs_review": true|false,
  "review_reason": "motivo si needs_review es true, si no null"
}}"""


def _normalize_str(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _is_invalid_third_party(value: str | None, tenant_aliases_norm: set[str]) -> bool:
    if not value or not value.strip():
        return True
    norm = _normalize_str(value)
    if norm in _INVALID_THIRD_PARTY_TERMS:
        return True
    # Coincidencia parcial con términos genéricos (por si lleva puntuación)
    for term in _INVALID_THIRD_PARTY_TERMS:
        if norm == term or norm.startswith(term + " ") or norm.endswith(" " + term):
            return True
    # Coincidencia con el tenant
    if norm in tenant_aliases_norm:
        return True
    for alias in tenant_aliases_norm:
        if alias and (alias in norm or norm in alias):
            return True
    return False


def _sanitize_result(
    result: AIExtractionResult,
    tenant_aliases_norm: set[str],
) -> AIExtractionResult:
    kind = result.operation_kind
    third = result.third_party_name
    third_tax_id = result.third_party_tax_id

    # ── Paso 1: corregir operation_kind=unknown usando aliases del tenant ──────
    if kind == "unknown" and tenant_aliases_norm:
        receiver_norm = _normalize_str(result.receiver_name)
        issuer_norm = _normalize_str(result.issuer_name)
        receiver_is_tenant = any(
            a and (a in receiver_norm or receiver_norm in a)
            for a in tenant_aliases_norm if a
        )
        issuer_is_tenant = any(
            a and (a in issuer_norm or issuer_norm in a)
            for a in tenant_aliases_norm if a
        )
        if receiver_is_tenant and not issuer_is_tenant and result.issuer_name:
            # Regla 1: receiver = tenant → expense, tercero = issuer
            kind = "expense"
            third = result.issuer_name
            third_tax_id = result.issuer_tax_id
        elif issuer_is_tenant and not receiver_is_tenant and result.receiver_name:
            # Regla 2: issuer = tenant → income, tercero = receiver
            kind = "income"
            third = result.receiver_name
            third_tax_id = result.receiver_tax_id

    # ── Paso 2: corrección estructural si kind sigue siendo unknown ───────────
    if kind == "unknown":
        issuer = result.issuer_name
        receiver = result.receiver_name
        current_third_norm = _normalize_str(third)
        receiver_norm = _normalize_str(receiver)
        issuer_norm = _normalize_str(issuer)

        if (third and receiver and issuer
                and current_third_norm == receiver_norm
                and issuer_norm != receiver_norm):
            # Regla 3: third == receiver pero hay issuer distinto → expense estructural
            kind = "expense"
            third = issuer
            third_tax_id = result.issuer_tax_id
        elif (third and receiver and issuer
                and current_third_norm == issuer_norm
                and receiver_norm != issuer_norm):
            # Regla 4: third == issuer pero hay receiver distinto → income estructural
            kind = "income"
            third = receiver
            third_tax_id = result.receiver_tax_id

    # ── Paso 3: validar y limpiar third_party_name ────────────────────────────
    if _is_invalid_third_party(third, tenant_aliases_norm):
        third = None
        third_tax_id = None

    # Derivar tercero desde issuer/receiver si aún es None
    if third is None:
        if kind == "income":
            candidate = result.receiver_name
            candidate_tax_id = result.receiver_tax_id
        elif kind == "expense":
            candidate = result.issuer_name
            candidate_tax_id = result.issuer_tax_id
        else:
            candidate = result.issuer_name or result.receiver_name
            candidate_tax_id = (
                result.issuer_tax_id if candidate == result.issuer_name
                else result.receiver_tax_id
            )
        if candidate and not _is_invalid_third_party(candidate, tenant_aliases_norm):
            third = candidate
            third_tax_id = candidate_tax_id

    # ── Paso 4: aplicar cambios al resultado ──────────────────────────────────
    needs_review = result.needs_review
    review_reason = result.review_reason

    if third is None:
        needs_review = True
        review_reason = review_reason or "No se pudo identificar un tercero externo real"
        third_tax_id = None

    # Si la corrección de kind fue automática, limpiar needs_review si hay datos suficientes
    if kind != result.operation_kind and third is not None:
        needs_review = False
        review_reason = None

    result = result.model_copy(update={
        "operation_kind": kind,
        "third_party_name": third,
        "third_party_tax_id": third_tax_id,
        "needs_review": needs_review,
        "review_reason": review_reason,
    })

    return result


def _try_salvage_truncated_json(raw: str) -> dict | None:
    """Rescata los campos completos de un JSON truncado cerrando en el último campo válido."""
    text = raw.strip()
    if not text.startswith('{'):
        return None

    in_string = False
    escape_next = False
    last_safe_comma = -1

    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
        if ch == ',' and not in_string:
            last_safe_comma = i

    if last_safe_comma < 1:
        return None

    candidate = text[:last_safe_comma] + '\n}'
    # Limpiar trailing commas residuales
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    try:
        data = json.loads(candidate)
        logger.warning("JSON parcial rescatado: %d campos recuperados", len(data))
        data.setdefault("needs_review", True)
        data.setdefault("review_reason", "Respuesta IA incompleta, datos parciales")
        return data
    except json.JSONDecodeError:
        return None


def _sanitize_doc_text(text: str) -> str:
    """Elimina caracteres que hacen que Gemini genere JSON con strings sin cerrar."""
    # Comillas dobles → simples (evita que Gemini las incluya sin escapar en JSON)
    text = text.replace('"', "'").replace('“', "'").replace('”', "'")
    # Barras invertidas → slash (evita secuencias de escape inválidas)
    text = text.replace('\\', '/')
    # Colapsar líneas en blanco múltiples
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def _clean_json_response(text: str) -> str:
    """Extrae y repara JSON de una respuesta que puede venir con formato incorrecto."""
    text = text.strip()

    # Extraer bloque ```json ... ``` si existe
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    else:
        # Intentar extraer el objeto JSON más externo
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            text = match.group(0)

    # Eliminar comentarios // (fuera de strings, heurística simple)
    text = re.sub(r"//[^\n\"]*\n", "\n", text)

    # Eliminar trailing commas antes de } o ]
    text = re.sub(r",\s*([}\]])", r"\1", text)

    return text


_RETRY_SYSTEM_PROMPT = """\
Analiza el documento y devuelve SOLO un JSON en UNA ÚNICA LÍNEA, sin saltos de línea, \
sin sangría, sin comentarios, empezando por { y terminando por }.

Campos obligatorios en este orden exacto:
- operation_kind: "income" si el usuario cobra, "expense" si paga, "unknown" si no está claro
- third_party_name: nombre real de la empresa o persona externa (quien cobra o quien paga)
- total_amount: importe total numérico (sin símbolo €)
- issuer_name: nombre del emisor del documento
- receiver_name: nombre del receptor o titular
- document_type: "invoice", "receipt" u "other"
- issue_date: fecha en formato DD/MM/YYYY o null
- category: categoría del gasto/ingreso o null

Para adeudos SEPA, domiciliaciones y recibos:
- operation_kind siempre es "expense"
- third_party_name es el nombre de la empresa que cobra (campo NOMBRE EMISOR)
- total_amount es el campo TOTAL ADEUDADO o IMPORTE
- receiver_name es el TITULAR de la cuenta

Ejemplo de formato (una sola línea):
{"operation_kind":"expense","third_party_name":"NOMBRE EMPRESA","total_amount":99.99,\
"issuer_name":"NOMBRE EMPRESA","receiver_name":"NOMBRE TITULAR","document_type":"receipt",\
"issue_date":null,"category":null,"confidence_score":0.8,"needs_review":false,\
"review_reason":null,"issuer_tax_id":null,"receiver_tax_id":null,"third_party_tax_id":null,\
"invoice_number":null,"due_date":null,"tax_base":null,"vat_amount":null,\
"irpf_amount":null,"currency":"EUR"}"""


def _validate_cuadre(result: AIExtractionResult) -> AIExtractionResult:
    """Valida que total ≈ base + iva - irpf. Marca needs_review si no cuadra."""
    total = result.total_amount
    base = result.tax_base
    if total is None or base is None:
        return result
    iva = result.vat_amount or 0.0
    irpf = result.irpf_amount or 0.0
    expected = base + iva - irpf
    if abs(total - expected) > 0.02:
        note = f"Cuadre fallido: {base:.2f} + {iva:.2f} - {irpf:.2f} = {expected:.2f} ≠ {total:.2f}"
        logger.warning("[CUADRE] %s", note)
        return result.model_copy(update={
            "needs_review": True,
            "review_reason": result.review_reason or note,
        })
    return result


def _retry_extraction(client, model: str, text: str) -> dict | None:
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _RETRY_SYSTEM_PROMPT},
                {"role": "user", "content": text[:3000]},
            ],
            temperature=0,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content
        if not raw:
            return None
        logger.debug("RETRY RAW: %r", raw[:2000])
        cleaned = _clean_json_response(raw)
        return json.loads(cleaned)
    except Exception as e:
        logger.warning("Reintento IA también falló: %s", e)
        return None


class AIExtractionService:

    @staticmethod
    def extract(
        text: str,
        tenant_name: str | None = None,
        tenant_aliases: list[str] | None = None,
    ) -> AIExtractionResult | None:
        try:
            from openai import OpenAI
            from app.core.config import settings

            api_key: str | None = None
            base_url: str | None = None
            model: str = "gpt-4o-mini"

            if settings.OPENAI_API_KEY:
                api_key = settings.OPENAI_API_KEY
                logger.info("Usando proveedor: OpenAI · modelo: gpt-4o-mini")
            elif settings.GOOGLE_AI_KEY:
                api_key = settings.GOOGLE_AI_KEY
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                model = settings.GOOGLE_AI_MODEL
                logger.info("Usando proveedor: Google AI Studio · modelo: %s", model)
            else:
                logger.debug("Sin clave de IA configurada, saltando extracción")
                return None

            # Construir bloque de identidad del tenant para el prompt
            all_aliases: list[str] = []
            if tenant_name:
                all_aliases.append(tenant_name)
            if tenant_aliases:
                all_aliases.extend(a for a in tenant_aliases if a and a != tenant_name)

            if all_aliases:
                tenant_block = "El usuario se identifica con cualquiera de estos nombres/datos:\n" + "\n".join(
                    f"  - {a}" for a in all_aliases
                )
            else:
                tenant_block = "(identidad del usuario no disponible)"

            tenant_aliases_norm = {_normalize_str(a) for a in all_aliases if a}

            system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(tenant_block=tenant_block)

            client = OpenAI(api_key=api_key, base_url=base_url)
            truncated_text = _sanitize_doc_text(text[:_MAX_TEXT_CHARS])

            response = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": truncated_text},
                ],
                temperature=0,
                max_tokens=2000,
            )

            raw_json = response.choices[0].message.content
            if not raw_json:
                logger.warning("Gemini devolvió respuesta vacía")
                return None

            logger.debug("RAW GEMINI RESPONSE: %r", raw_json[:2000])
            cleaned = _clean_json_response(raw_json)

            engine = "gemini_first_try"
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as json_err:
                logger.warning("JSON incompleto en primer intento (%s), reintentando...", json_err)
                data = _retry_extraction(client, model, truncated_text)
                if data is not None:
                    engine = "gemini_retry"
                else:
                    logger.warning("Reintento falló, intentando rescate de campos parciales...")
                    data = _try_salvage_truncated_json(cleaned)
                    if data is not None:
                        engine = "gemini_salvage"
                if data is None:
                    raise

            result = AIExtractionResult.model_validate(data)
            result = _sanitize_result(result, tenant_aliases_norm)
            result = _validate_cuadre(result)

            logger.warning(
                "[EXTRACCION] motor=%s | kind=%s | third_party=%s | issuer=%s | "
                "receiver=%s | total=%s | confidence=%.2f | needs_review=%s | review_reason=%s",
                engine,
                result.operation_kind,
                result.third_party_name,
                result.issuer_name,
                result.receiver_name,
                result.total_amount,
                result.confidence_score,
                result.needs_review,
                result.review_reason,
            )

            return result

        except Exception as e:
            logger.warning("Extracción IA fallida, usando fallback regex: %s", e)
            return None

    @staticmethod
    def extract_multimodal(
        image_b64: str,
        tenant_name: str | None = None,
        tenant_aliases: list[str] | None = None,
    ) -> AIExtractionResult | None:
        """
        Extrae datos fiscales enviando la página del documento como imagen a Gemini.
        Requiere GOOGLE_AI_KEY. Mucho mejor que OCR+texto para PDFs escaneados o
        facturas con formatos visuales complejos.
        """
        try:
            from openai import OpenAI
            from app.core.config import settings

            if not settings.GOOGLE_AI_KEY:
                logger.debug("extract_multimodal requiere GOOGLE_AI_KEY")
                return None

            model = settings.GOOGLE_AI_MODEL
            client = OpenAI(
                api_key=settings.GOOGLE_AI_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )

            all_aliases: list[str] = []
            if tenant_name:
                all_aliases.append(tenant_name)
            if tenant_aliases:
                all_aliases.extend(a for a in tenant_aliases if a and a != tenant_name)

            if all_aliases:
                tenant_block = "El usuario se identifica con cualquiera de estos nombres/datos:\n" + "\n".join(
                    f"  - {a}" for a in all_aliases
                )
            else:
                tenant_block = "(identidad del usuario no disponible)"

            tenant_aliases_norm = {_normalize_str(a) for a in all_aliases if a}
            system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(tenant_block=tenant_block)
            # Para multimodal Gemini se instruye el formato en el propio prompt
            system_prompt += "\n\nResponde ÚNICAMENTE con el objeto JSON, sin texto adicional."

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                        {
                            "type": "text",
                            "text": "Extrae todos los datos fiscales de este documento según el esquema JSON indicado.",
                        },
                    ]},
                ],
                temperature=0,
                max_tokens=2000,
            )

            raw_json = response.choices[0].message.content
            if not raw_json:
                logger.warning("Gemini multimodal devolvió respuesta vacía")
                return None

            logger.debug("RAW GEMINI MULTIMODAL: %r", raw_json[:2000])
            cleaned = _clean_json_response(raw_json)

            engine = "gemini_multimodal"
            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as json_err:
                logger.warning("JSON incompleto en multimodal (%s), reintentando...", json_err)
                data = _retry_extraction(client, model, "Revisa la imagen del documento y extrae los campos.")
                if data is not None:
                    engine = "gemini_multimodal_retry"
                else:
                    data = _try_salvage_truncated_json(cleaned)
                    if data is not None:
                        engine = "gemini_multimodal_salvage"
                if data is None:
                    raise

            result = AIExtractionResult.model_validate(data)
            result = _sanitize_result(result, tenant_aliases_norm)
            result = _validate_cuadre(result)

            logger.warning(
                "[EXTRACCION] motor=%s | kind=%s | third_party=%s | total=%s | "
                "trimestre=%s | rectificativa=%s | isp=%s | confidence=%.2f | needs_review=%s",
                engine,
                result.operation_kind,
                result.third_party_name,
                result.total_amount,
                result.trimestre,
                result.es_rectificativa,
                result.inversion_sujeto_pasivo,
                result.confidence_score,
                result.needs_review,
            )

            return result

        except Exception as e:
            logger.warning("Extracción multimodal Gemini fallida: %s", e)
            return None
