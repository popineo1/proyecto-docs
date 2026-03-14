from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.membership import Membership


class UserService:
    @staticmethod
    def get_user_tenants(db: Session, user_id: UUID):
        memberships = (
            db.query(Membership)
            .options(joinedload(Membership.tenant))
            .filter(Membership.user_id == user_id)
            .all()
        )
        return memberships