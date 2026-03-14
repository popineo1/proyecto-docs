from fastapi import APIRouter
from app.api.v1.endpoints import auth, documents, jobs, financial_entries, dashboard

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(jobs.router)
api_router.include_router(financial_entries.router)
api_router.include_router(dashboard.router)
