import app.db.base
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.api import api_router


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.APP_DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost:4201",
        "http://localhost:3000",
        "https://www.tuadministrativo.com",
        "https://tuadministrativo.com",
        "https://controladmin.tuadministrativo.com",
        "https://control-admin.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {"message": "API funcionando correctamente"}