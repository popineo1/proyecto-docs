import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.financial_movement import FinancialMovement
from app.schemas.financial_movement import FinancialMovementCreate, FinancialMovementUpdate


class FinancialMovementService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        tenant_id: uuid.UUID,
        payload: FinancialMovementCreate,
    ) -> FinancialMovement:
        movement = FinancialMovement(
            tenant_id=tenant_id,
            **payload.model_dump(),
        )

        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        *,
        kind: str | None = None,
        status: str | None = None,
        source_type: str | None = None,
        category: str | None = None,
        third_party_name: str | None = None,
        business_area: str | None = None,
        needs_review: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[FinancialMovement]:
        stmt = select(FinancialMovement).where(FinancialMovement.tenant_id == tenant_id)

        if kind:
            stmt = stmt.where(func.lower(FinancialMovement.kind) == kind.strip().lower())

        if status:
            stmt = stmt.where(func.lower(FinancialMovement.status) == status.strip().lower())

        if source_type:
            stmt = stmt.where(func.lower(FinancialMovement.source_type) == source_type.strip().lower())

        if category:
            stmt = stmt.where(func.lower(FinancialMovement.category) == category.strip().lower())

        if third_party_name:
            stmt = stmt.where(
                func.lower(FinancialMovement.third_party_name).contains(third_party_name.strip().lower())
            )

        if business_area:
            stmt = stmt.where(func.lower(FinancialMovement.business_area) == business_area.strip().lower())

        if needs_review is not None:
            stmt = stmt.where(FinancialMovement.needs_review.is_(needs_review))

        if date_from:
            stmt = stmt.where(FinancialMovement.movement_date >= date_from)

        if date_to:
            stmt = stmt.where(FinancialMovement.movement_date <= date_to)

        stmt = stmt.order_by(
            FinancialMovement.movement_date.desc().nullslast(),
            FinancialMovement.created_at.desc(),
        ).offset(skip).limit(limit)

        return self.db.execute(stmt).scalars().all()

    def get_by_id(
        self,
        tenant_id: uuid.UUID,
        movement_id: uuid.UUID,
    ) -> FinancialMovement | None:
        stmt = select(FinancialMovement).where(
            FinancialMovement.id == movement_id,
            FinancialMovement.tenant_id == tenant_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update(
        self,
        tenant_id: uuid.UUID,
        movement_id: uuid.UUID,
        payload: FinancialMovementUpdate,
    ) -> FinancialMovement | None:
        movement = self.get_by_id(tenant_id, movement_id)
        if not movement:
            return None

        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(movement, field, value)

        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def delete(
        self,
        tenant_id: uuid.UUID,
        movement_id: uuid.UUID,
    ) -> bool:
        movement = self.get_by_id(tenant_id, movement_id)
        if not movement:
            return False

        self.db.delete(movement)
        self.db.commit()
        return True

    def list_for_review(
        self,
        tenant_id: uuid.UUID,
        confidence_level: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[FinancialMovement]:
        """Return movements that need review, ordered by lowest confidence first."""
        stmt = select(FinancialMovement).where(
            FinancialMovement.tenant_id == tenant_id,
            FinancialMovement.needs_review.is_(True),
        )
        if confidence_level:
            stmt = stmt.where(FinancialMovement.confidence_level == confidence_level)
        stmt = stmt.order_by(
            FinancialMovement.confidence_score.asc().nullsfirst(),
            FinancialMovement.movement_date.desc().nullslast(),
        ).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()