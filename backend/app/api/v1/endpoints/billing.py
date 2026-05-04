"""
billing.py — Endpoints de Stripe Billing.

POST /billing/checkout  → URL de pago Stripe Checkout
POST /billing/portal    → URL del Customer Portal (gestión de suscripción)
POST /billing/webhook   → Receptor de webhooks Stripe (sin autenticación JWT)
GET  /billing/status    → Estado de suscripción del tenant actual
"""
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.services.billing_service import (
    ACTIVE_STATUSES,
    create_checkout_session,
    create_portal_session,
    handle_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("/checkout")
def checkout(
    success_url: str = Body(..., embed=True),
    cancel_url: str = Body(..., embed=True),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    Crea una sesión de pago en Stripe Checkout.
    Devuelve `checkout_url` al que el frontend debe redirigir al usuario.
    """
    try:
        url = create_checkout_session(db, tenant, success_url, cancel_url)
        return {"checkout_url": url}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/portal")
def portal(
    return_url: str = Body(..., embed=True),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """
    Crea una sesión del Customer Portal de Stripe.
    Permite al tenant gestionar su suscripción: cancelar, cambiar tarjeta, ver facturas.
    """
    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="Este tenant no tiene una suscripción activa en Stripe."
        )
    try:
        url = create_portal_session(db, tenant, return_url)
        return {"portal_url": url}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/status")
def subscription_status(
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
):
    """Estado de la suscripción del tenant. Útil para el frontend."""
    return {
        "subscription_status": tenant.subscription_status,
        "subscription_plan": tenant.subscription_plan,
        "subscription_period_end": tenant.subscription_period_end.isoformat() if tenant.subscription_period_end else None,
        "is_active": tenant.subscription_status in ACTIVE_STATUSES,
        "stripe_customer_id": tenant.stripe_customer_id,
    }


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receptor de webhooks de Stripe.
    ⚠️ NO usa autenticación JWT — la seguridad la proporciona la firma HMAC de Stripe.
    ⚠️ Lee el body RAW (bytes) antes de cualquier parsing — necesario para verificar firma.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Falta cabecera Stripe-Signature")

    try:
        result = handle_webhook(payload, sig_header, db)
        return result
    except ValueError as e:
        # Firma inválida → 400 (Stripe reintentará si devolvemos 5xx, no queremos eso)
        logger.warning("[BILLING] Webhook rechazado: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
