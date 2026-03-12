from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User
from app.models.membership import Membership
from app.repositories.user_repository import UserRepository
from app.core.security import get_password_hash, verify_password, create_access_token


class AuthService:
    @staticmethod
    def register(db: Session, company_name: str, company_slug: str, vertical: str | None,
                 full_name: str, email: str, password: str):
        existing = UserRepository.get_by_email(db, email)
        if existing:
            raise ValueError("El email ya está registrado")

        tenant = Tenant(
            name=company_name,
            slug=company_slug,
            vertical=vertical
        )

        user = User(
            email=email,
            full_name=full_name,
            password_hash=get_password_hash(password),
            is_active=True,
            is_superuser=False
        )

        db.add(tenant)
        db.add(user)
        db.flush()

        membership = Membership(
            tenant_id=tenant.id,
            user_id=user.id,
            role="owner"
        )

        db.add(membership)
        db.commit()
        db.refresh(user)

        token = create_access_token(str(user.id))
        return user, token

    @staticmethod
    def login(db: Session, email: str, password: str):
        user = UserRepository.get_by_email(db, email)
        if not user:
            raise ValueError("Credenciales inválidas")

        if not verify_password(password, user.password_hash):
            raise ValueError("Credenciales inválidas")

        if not user.is_active:
            raise ValueError("Usuario inactivo")

        token = create_access_token(str(user.id))
        return token