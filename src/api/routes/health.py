"""Healthcheck: usado pelo Docker na Parte 4 e por qualquer orquestrador."""

from typing import Annotated

from fastapi import Depends, Response, status

from fastapi import APIRouter

from src.api.dependencies import DatabaseDep, get_cache
from src.api.schemas.common import HealthResponse
from src.domain.cache import ICache

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Saúde da aplicação",
    responses={503: {"model": HealthResponse}},
)
async def health(
    response: Response,
    database: DatabaseDep,
    cache: Annotated[ICache, Depends(get_cache)],
) -> HealthResponse:
    try:
        await database.ping()
        database_status = "up"
    except Exception:
        database_status = "down"

    # O cache é opcional: sem ele a API degrada, mas continua servindo.
    cache_status = "up" if await cache.ping() else "disabled"

    if database_status != "up":
        # 503 para o orquestrador substituir a réplica; responder 200 com o
        # banco fora faria o container passar por saudável.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", database=database_status, cache=cache_status)

    return HealthResponse(status="ok", database=database_status, cache=cache_status)
