import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

limiter = Limiter(key_func=get_remote_address)

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token, get_password_hash
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.schemas.membership import UserTenantResponse
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.services.auth_service import AuthService
from app.services.user_service import UserService

from app.core.dependencies import get_current_membership, get_current_tenant
from app.models.membership import Membership
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


def _send_reset_email(to_email: str, reset_url: str) -> None:
    """Send password reset email. Configure RESEND_API_KEY in environment to enable."""
    if not settings.RESEND_API_KEY:
        logger.info(f"[DEV] Password reset link for {to_email}: {reset_url}")
        return
    try:
        import resend  # type: ignore
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": to_email,
            "subject": "Recupera tu contraseña - Control Admin",
            "html": (
                f"<p>Hola,</p>"
                f"<p>Haz clic en el enlace para restablecer tu contraseña. Expira en 1 hora.</p>"
                f'<p><a href="{reset_url}" style="background:#000;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block;">Restablecer contraseña</a></p>'
                f"<p>Si no lo solicitaste, ignora este email.</p>"
            ),
        })
    except Exception as e:
        logger.error(f"Error sending reset email to {to_email}: {e}")


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        _, token, refresh_token = AuthService.register(
            db=db,
            company_name=payload.company_name,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password
        )
        return TokenResponse(access_token=token, refresh_token=refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        token, refresh_token = AuthService.login(
            db=db,
            email=form_data.username,
            password=form_data.password
        )
        return TokenResponse(access_token=token, refresh_token=refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    user_id = decode_refresh_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    new_access = create_access_token(str(user.id))
    new_refresh = create_refresh_token(str(user.id))
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/tenants", response_model=list[UserTenantResponse])
def get_my_tenants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memberships = UserService.get_user_tenants(db, current_user.id)

    return [
        UserTenantResponse(
            tenant_id=membership.tenant.id,
            tenant_name=membership.tenant.name,
            tenant_slug=membership.tenant.slug,
            role=membership.role,
            status=membership.status
        )
        for membership in memberships
    ]

@router.get("/me/context")
def get_context(
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(get_current_membership),
    tenant: Tenant = Depends(get_current_tenant),
):
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "role": membership.role
    }


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    email: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Generates a password reset token and sends email. Always returns 200 to avoid enumeration."""
    user = db.query(User).filter(User.email == email.strip().lower(), User.is_active == True).first()
    if user:
        # Invalidate previous unused tokens
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,
        ).update({"used": True})

        token = PasswordResetToken(
            user_id=user.id,
            token=str(uuid.uuid4()),
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(token)
        db.commit()

        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token.token}"
        _send_reset_email(user.email, reset_url)

    return {"message": "Si el email está registrado, recibirás un enlace en breve."}


@router.post("/reset-password")
def reset_password(
    token: str = Body(...),
    new_password: str = Body(...),
    db: Session = Depends(get_db),
):
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres.")

    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token
    ).first()

    if not reset or not reset.is_valid:
        raise HTTPException(status_code=400, detail="El enlace es inválido o ha expirado. Solicita uno nuevo.")

    user = db.query(User).filter(User.id == reset.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado.")

    user.password_hash = get_password_hash(new_password)
    reset.used = True
    db.commit()
    return {"message": "Contraseña actualizada correctamente."}