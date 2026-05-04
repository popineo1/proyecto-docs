from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

limiter = Limiter(key_func=get_remote_address)

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.schemas.membership import UserTenantResponse
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.user_service import UserService

from app.core.dependencies import get_current_membership, get_current_tenant
from app.models.membership import Membership
from app.models.tenant import Tenant

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