from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

VALID_ROLES = {"member", "admin", "owner"}

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.core.security import get_password_hash
from app.models.invitation import Invitation
from app.models.membership import Membership
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/invitations", tags=["Invitations"])

INVITATION_EXPIRES_DAYS = 7


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "member"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Rol no válido. Debe ser uno de: {', '.join(sorted(VALID_ROLES))}")
        return v


class InvitationResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str
    token: str
    expires_at: str
    created_at: str
    invited_by_name: str | None = None

    model_config = {"from_attributes": True}


class AcceptInvitationRequest(BaseModel):
    full_name: str
    password: str


@router.post("", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check if there's already a pending invitation for this email in this tenant
    existing = db.query(Invitation).filter(
        Invitation.tenant_id == tenant.id,
        Invitation.email == payload.email.lower(),
        Invitation.status == "pending",
        Invitation.expires_at > datetime.utcnow(),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una invitación pendiente para ese email.")

    # Check if user is already a member
    existing_user = UserRepository.get_by_email(db, payload.email)
    if existing_user:
        already_member = db.query(Membership).filter(
            Membership.tenant_id == tenant.id,
            Membership.user_id == existing_user.id,
        ).first()
        if already_member:
            raise HTTPException(status_code=400, detail="Ese usuario ya es miembro de la empresa.")

    invitation = Invitation(
        tenant_id=tenant.id,
        invited_by_user_id=current_user.id,
        email=payload.email.lower(),
        role=payload.role,
        expires_at=datetime.utcnow() + timedelta(days=INVITATION_EXPIRES_DAYS),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return InvitationResponse(
        id=str(invitation.id),
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        token=invitation.token,
        expires_at=invitation.expires_at.isoformat(),
        created_at=invitation.created_at.isoformat(),
        invited_by_name=current_user.full_name,
    )


@router.get("", response_model=list[InvitationResponse])
def list_invitations(
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invitations = db.query(Invitation).filter(
        Invitation.tenant_id == tenant.id,
    ).order_by(Invitation.created_at.desc()).all()

    return [
        InvitationResponse(
            id=str(i.id),
            email=i.email,
            role=i.role,
            status=i.status,
            token=i.token,
            expires_at=i.expires_at.isoformat(),
            created_at=i.created_at.isoformat(),
            invited_by_name=i.invited_by.full_name if i.invited_by else None,
        )
        for i in invitations
    ]


@router.get("/{token}/info")
def get_invitation_info(token: str, db: Session = Depends(get_db)):
    """Endpoint público para ver los datos de una invitación antes de aceptarla."""
    inv = db.query(Invitation).filter(Invitation.token == token).first()
    if not inv or inv.status != "pending" or inv.expires_at < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Invitación no válida o expirada.")

    return {
        "email": inv.email,
        "role": inv.role,
        "tenant_name": inv.tenant.name,
        "expires_at": inv.expires_at.isoformat(),
    }


@router.post("/{token}/accept", status_code=status.HTTP_201_CREATED)
def accept_invitation(
    token: str,
    payload: AcceptInvitationRequest,
    db: Session = Depends(get_db),
):
    inv = db.query(Invitation).filter(Invitation.token == token).first()
    if not inv or inv.status != "pending" or inv.expires_at < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Invitación no válida o expirada.")

    existing_user = UserRepository.get_by_email(db, inv.email)

    if existing_user:
        user = existing_user
    else:
        user = User(
            email=inv.email,
            full_name=payload.full_name.strip(),
            password_hash=get_password_hash(payload.password),
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        db.flush()

    already_member = db.query(Membership).filter(
        Membership.tenant_id == inv.tenant_id,
        Membership.user_id == user.id,
    ).first()

    if not already_member:
        membership = Membership(
            tenant_id=inv.tenant_id,
            user_id=user.id,
            role=inv.role,
        )
        db.add(membership)

    inv.status = "accepted"
    db.commit()

    return {"message": "Invitación aceptada correctamente. Ya puedes iniciar sesión."}


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_invitation(
    invitation_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inv = db.query(Invitation).filter(
        Invitation.id == invitation_id,
        Invitation.tenant_id == tenant.id,
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitación no encontrada.")

    inv.status = "cancelled"
    db.commit()
    return None
