"""Providers de injeção de dependência.

Monta a cadeia driver -> repository -> service e a entrega pronta aos
endpoints, sempre tipada pelas interfaces. Trocar a implementação (outro banco,
outra regra) é uma mudança só neste arquivo.
"""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status

from src.api.schemas.auth import AuthenticatedUser
from src.config import Settings, get_settings
from src.domain.repositories import IMissionRepository
from src.repository.database import Database
from src.repository.mission_repository import MissionRepository
from src.service.interfaces import IMissionService, ITokenService
from src.service.mission_service import MissionService
from src.service.token_service import TokenService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_database(settings: SettingsDep) -> Database:
    """Devolve o singleton já conectado pelo lifespan."""
    return Database(settings.database_url)


DatabaseDep = Annotated[Database, Depends(get_database)]


def get_mission_repository(database: DatabaseDep) -> IMissionRepository:
    return MissionRepository(database)


def get_mission_service(
    repository: Annotated[IMissionRepository, Depends(get_mission_repository)],
) -> IMissionService:
    return MissionService(repository)


def get_token_service(settings: SettingsDep) -> ITokenService:
    return TokenService(settings)


MissionServiceDep = Annotated[IMissionService, Depends(get_mission_service)]
TokenServiceDep = Annotated[ITokenService, Depends(get_token_service)]


def get_current_user(request: Request) -> AuthenticatedUser:
    """Lê a identidade que o middleware JWT colocou no request."""
    user: dict[str, Any] | None = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Requisição não autenticada",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthenticatedUser(id=user["id"], username=user["username"])


CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]
