"""Providers de injeção de dependência.

Monta a cadeia driver -> repository -> service e a entrega pronta aos
endpoints, sempre tipada pelas interfaces. Trocar a implementação (outro banco,
outra regra) é uma mudança só neste arquivo.
"""

from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status

from src.api.schemas.auth import AuthenticatedUser
from src.config import Settings, get_settings
from src.domain.cache import ICache
from src.domain.inference import IModelRegistry
from src.domain.repositories import IMissionRepository, IPredictionRepository
from src.domain.storage import IImageStorage
from src.infra.onnx_engine import OnnxModelRegistry
from src.repository.database import Database, get_database as build_database
from src.repository.mission_repository import MissionRepository
from src.repository.prediction_repository import PredictionRepository
from src.repository.redis_cache import NullCache, RedisCache
from src.repository.storage import LocalImageStorage
from src.service.interfaces import IMissionService, IPredictionService, ITokenService
from src.service.mission_service import MissionService
from src.service.prediction_service import PredictionService
from src.service.token_service import TokenService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_database(settings: SettingsDep) -> Database:
    """Devolve o singleton já conectado pelo lifespan."""
    return build_database(settings.database_url)


DatabaseDep = Annotated[Database, Depends(get_database)]


def get_mission_repository(database: DatabaseDep) -> IMissionRepository:
    return MissionRepository(database)


@lru_cache
def get_model_registry_for(manifest_path: str) -> IModelRegistry:
    """Registry por manifesto, memorizado: o modelo carrega uma vez por processo."""
    return OnnxModelRegistry(manifest_path)


def get_model_registry(settings: SettingsDep) -> IModelRegistry:
    return get_model_registry_for(settings.models_manifest)


@lru_cache
def get_cache_for(redis_url: str | None) -> ICache:
    """Um cliente por processo; sem REDIS_URL a API roda sem Redis."""
    return RedisCache(redis_url) if redis_url else NullCache()


def get_cache(settings: SettingsDep) -> ICache:
    return get_cache_for(settings.redis_url)


def get_image_storage(settings: SettingsDep) -> IImageStorage:
    return LocalImageStorage(settings.images_root)


def get_prediction_repository(database: DatabaseDep) -> IPredictionRepository:
    return PredictionRepository(database)


def get_mission_service(
    repository: Annotated[IMissionRepository, Depends(get_mission_repository)],
) -> IMissionService:
    return MissionService(repository)


def get_token_service(settings: SettingsDep) -> ITokenService:
    return TokenService(settings)


MissionServiceDep = Annotated[IMissionService, Depends(get_mission_service)]


def get_prediction_service(
    repository: Annotated[IPredictionRepository, Depends(get_prediction_repository)],
    registry: Annotated[IModelRegistry, Depends(get_model_registry)],
    storage: Annotated[IImageStorage, Depends(get_image_storage)],
    mission_service: MissionServiceDep,
    cache: Annotated[ICache, Depends(get_cache)],
    settings: SettingsDep,
) -> IPredictionService:
    return PredictionService(
        repository,
        registry,
        storage,
        mission_service,
        cache,
        settings.idempotency_ttl_seconds,
    )


PredictionServiceDep = Annotated[IPredictionService, Depends(get_prediction_service)]
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
