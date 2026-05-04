from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.membership import Membership
from app.models.tenant import Tenant
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se han podido validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id_raw = payload.get("sub")

        if user_id_raw is None:
            raise credentials_exception

        user_id = UUID(user_id_raw)

    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    return user


def get_current_membership(
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Membership:
    try:
        tenant_id = UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id no es un UUID válido"
        )

    membership = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.user_id == current_user.id,
            Membership.status == "active"
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este tenant"
        )

    return membership


def get_current_tenant(
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db)
) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == membership.tenant_id).first()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado"
        )

    if tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant inactivo"
        )

    return tenant


def require_active_subscription(
    tenant: Tenant = Depends(get_current_tenant),
) -> Tenant:
    """
    Dependencia que bloquea el acceso si el tenant no tiene suscripción activa en Stripe.
    Añádela a los routers o endpoints que deben estar detrás del muro de pago:

        @router.get("/data", dependencies=[Depends(require_active_subscription)])

    El frontend debe interceptar HTTP 402 y redirigir a la página de suscripción.
    Si STRIPE_SECRET_KEY no está configurada (entorno de desarrollo), se permite el acceso.
    """
    from app.core.config import settings
    from app.services.billing_service import ACTIVE_STATUSES

    # Sin Stripe configurado → modo desarrollo, acceso libre
    if not settings.STRIPE_SECRET_KEY:
        return tenant

    if tenant.subscription_status not in ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="subscription_required",
        )

    return tenant