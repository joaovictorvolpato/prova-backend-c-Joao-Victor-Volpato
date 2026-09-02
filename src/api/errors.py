"""Tradução de erros de domínio para respostas HTTP.

Concentrar isso aqui mantém service e repository livres de qualquer noção de
status code.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    DuplicatedMissionError,
    InvalidMissionError,
    MissionNotFoundError,
)

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    MissionNotFoundError: status.HTTP_404_NOT_FOUND,
    DuplicatedMissionError: status.HTTP_409_CONFLICT,
    InvalidMissionError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def register_exception_handlers(app: FastAPI) -> None:
    for error_type, status_code in _STATUS_BY_ERROR.items():
        app.add_exception_handler(error_type, _make_handler(status_code))


def _make_handler(status_code: int):
    async def handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler
