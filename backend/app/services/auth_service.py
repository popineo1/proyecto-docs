import re
import unicodedata

from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.models.user import User
from app.models.membership import Membership
from app.repositories.user_repository import UserRepository
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token


class AuthService:
    @staticmethod
    def _slugify(value: str) -> str:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        value = re.sub(r"-{2,}", "-", value).strip("-")
        return value or "empresa"

    @staticmethod
    def _generate_unique_tenant_slug(db: Session, company_name: str) -> str:
        base_slug = AuthService._slugify(company_name)
        slug = base_slug
        counter = 2

        while db.query(Tenant).filter(Tenant.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    @staticmethod
    def register(
        db: Session,
        company_name: str,
        full_name: str,
        email: str,
        password: str
    ):
        existing = UserRepository.get_by_email(db, email)
        if existing:
            raise ValueError("El email ya está registrado")

        company_name = company_name.strip()
        full_name = full_name.strip()
        email = email.strip().lower()

        slug = AuthService._generate_unique_tenant_slug(db, company_name)

        tenant = Tenant(
            name=company_name,
            slug=slug,
            vertical=None
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
        refresh_token = create_refresh_token(str(user.id))
        return user, token, refresh_token

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
        refresh_token = create_refresh_token(str(user.id))
        return token, refresh_token