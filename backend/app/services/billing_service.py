"""
billing_service.py — Stripe Billing integrado con tenants.

Flujo principal:
  1. checkout()     → crea Stripe Customer (si no existe) + Checkout Session → URL de pago
  2. portal()       → crea Customer Portal Session → URL de gestión (cancelar, cambiar tarjeta…)
  3. handle_webhook → procesa eventos Stripe y sincroniza subscription_status en BD

Webhooks que debes activar en el dashboard de Stripe:
  - customer.subscription.created
  - customer.subscription.updated
  - customer.subscription.deleted
  - invoice.payment_succeeded
  - invoice.payment_failed
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# Estados de Stripe que permiten acceso completo a la plataforma
ACTIVE_STATUSES = {"active", "trialing"}


def _get_stripe():
    """Importación lazy de stripe para no fallar si no está instalado."""
    try:
        import stripe as _stripe
        if not settings.STRIPE_SECRET_KEY:
            raise RuntimeError("STRIPE_SECRET_KEY no configurada")
        _stripe.api_key = settings.STRIPE_SECRET_KEY
        return _stripe
    except ImportError:
        raise RuntimeError("Instala stripe: pip install stripe>=11.0.0")


def get_or_create_customer(db: Session, tenant: Tenant) -> str:
    """Devuelve el stripe_customer_id del tenant, creándolo en Stripe si no existe."""
    if tenant.stripe_customer_id:
        return tenant.stripe_customer_id

    stripe = _get_stripe()
    customer = stripe.Customer.create(
        name=tenant.name,
        metadata={"tenant_id": str(tenant.id), "slug": tenant.slug},
    )
    tenant.stripe_customer_id = customer.id
    db.commit()
    logger.info("[BILLING] Customer creado: %s → %s", tenant.slug, customer.id)
    return customer.id


def create_checkout_session(
    db: Session,
    tenant: Tenant,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Crea una Stripe Checkout Session y devuelve la URL de pago.
    El usuario es redirigido a esa URL para completar el pago.
    """
    if not settings.STRIPE_PRICE_ID:
        raise RuntimeError("STRIPE_PRICE_ID no configurada")

    stripe = _get_stripe()
    customer_id = get_or_create_customer(db, tenant)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"tenant_id": str(tenant.id)},
        # Permitir al cliente introducir su correo si no lo tiene
        customer_update={"address": "auto"},
        allow_promotion_codes=True,
    )
    logger.info("[BILLING] Checkout session creada: %s", session.id)
    return session.url


def create_portal_session(
    db: Session,
    tenant: Tenant,
    return_url: str,
) -> str:
    """
    Crea una Stripe Customer Portal Session.
    Permite al tenant gestionar su suscripción (cancelar, cambiar tarjeta, ver facturas).
    """
    stripe = _get_stripe()
    customer_id = get_or_create_customer(db, tenant)

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    logger.info("[BILLING] Portal session creada para %s", tenant.slug)
    return session.url


def sync_subscription(db: Session, tenant: Tenant, subscription) -> None:
    """Sincroniza el estado de una suscripción Stripe con el tenant en BD."""
    tenant.stripe_subscription_id = subscription.id
    tenant.subscription_status = subscription.status
    tenant.subscription_plan = (
        subscription.items.data[0].price.id if subscription.items.data else None
    )
    period_end = getattr(subscription, "current_period_end", None)
    if period_end:
        tenant.subscription_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc).replace(tzinfo=None)

    db.commit()
    logger.info(
        "[BILLING] Tenant %s → status=%s sub=%s period_end=%s",
        tenant.slug, tenant.subscription_status, tenant.stripe_subscription_id, tenant.subscription_period_end,
    )


def handle_webhook(payload: bytes, sig_header: str, db: Session) -> dict:
    """
    Verifica la firma del webhook de Stripe y procesa el evento.
    Devuelve {"status": "ok"} o lanza ValueError si la firma es inválida.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET no configurada")

    stripe = _get_stripe()

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Firma Stripe inválida: {e}") from e

    event_type = event["type"]
    logger.info("[BILLING] Webhook recibido: %s", event_type)

    # ── Suscripción creada o actualizada ──────────────────────────────────────
    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
        if tenant:
            sync_subscription(db, tenant, sub)
        else:
            logger.warning("[BILLING] Tenant no encontrado para customer %s", customer_id)

    # ── Suscripción cancelada ─────────────────────────────────────────────────
    elif event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub["customer"]
        tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
        if tenant:
            tenant.subscription_status = "canceled"
            tenant.stripe_subscription_id = None
            db.commit()
            logger.info("[BILLING] Suscripción cancelada para %s", tenant.slug)

    # ── Pago exitoso ──────────────────────────────────────────────────────────
    elif event_type == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        customer_id = invoice["customer"]
        sub_id = invoice.get("subscription")
        if sub_id:
            tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
            if tenant:
                sub = stripe.Subscription.retrieve(sub_id)
                sync_subscription(db, tenant, sub)

    # ── Pago fallido ──────────────────────────────────────────────────────────
    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        customer_id = invoice["customer"]
        tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
        if tenant:
            tenant.subscription_status = "past_due"
            db.commit()
            logger.warning("[BILLING] Pago fallido para %s → past_due", tenant.slug)

    return {"status": "ok", "event": event_type}
