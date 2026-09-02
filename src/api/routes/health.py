"""Healthcheck: usado pelo Docker na Parte 4 e por qualquer orquestrador."""

from fastapi import APIRouter

from src.api.dependencies import DatabaseDep
from src.api.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Saúde da aplicação")
async def health(database: DatabaseDep) -> HealthResponse:
    try:
        await database.fetch_one("SELECT 1")
        database_status = "up"
    except Exception:
        database_status = "down"
    return HealthResponse(status="ok", database=database_status)
