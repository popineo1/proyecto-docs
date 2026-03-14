from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.financial_entry import FinancialEntryResponse
from app.services.financial_entry_service import FinancialEntryService
from app.schemas.financial_entry_review import FinancialEntryReviewRequest

router = APIRouter(prefix="/financial-entries", tags=["Financial Entries"])


@router.get("", response_model=list[FinancialEntryResponse])
def list_financial_entries(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    return FinancialEntryService.list_by_tenant(db, current_tenant.id)


@router.get("/{entry_id}", response_model=FinancialEntryResponse)
def get_financial_entry(
    entry_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    entry = FinancialEntryService.get_by_id(
        db=db,
        tenant_id=current_tenant.id,
        entry_id=entry_id
    )

    if entry is None:
        raise HTTPException(status_code=404, detail="Entrada financiera no encontrada")

    return entry

@router.patch("/{entry_id}/review", response_model=FinancialEntryResponse)
def review_financial_entry(
    entry_id: UUID,
    payload: FinancialEntryReviewRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    entry = FinancialEntryService.get_by_id(
        db=db,
        tenant_id=current_tenant.id,
        entry_id=entry_id
    )

    if entry is None:
        raise HTTPException(status_code=404, detail="Entrada financiera no encontrada")

    return FinancialEntryService.review_entry(db, entry, payload)
