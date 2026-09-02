"""Rota de identidade.

O login fica em outro microsserviço: esta API apenas valida o token recebido.
Este endpoint devolve a identidade extraída dele, útil para conferir se um token
é aceito aqui.
"""

from fastapi import APIRouter

from src.api.dependencies import CurrentUserDep
from src.api.schemas.auth import AuthenticatedUser
from src.api.schemas.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"], responses={401: {"model": ErrorResponse}})


@router.get("/me", response_model=AuthenticatedUser, summary="Usuário do token atual")
async def me(current_user: CurrentUserDep) -> AuthenticatedUser:
    return current_user
