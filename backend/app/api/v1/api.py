from fastapi import APIRouter
from app.api.v1.endpoints import auth, documents, jobs, financial_entries, financial_movements, dashboard, purchases, analytics, manual_movements, admin, invitations, billing

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(billing.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(financial_entries.router)
api_router.include_router(financial_movements.router)
api_router.include_router(dashboard.router)
api_router.include_router(purchases.router)
api_router.include_router(analytics.router)
api_router.include_router(manual_movements.router)
api_router.include_router(invitations.router)
