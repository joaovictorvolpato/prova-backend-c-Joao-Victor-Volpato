"""Configurações da aplicação, carregadas de variáveis de ambiente."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Drone Missions API"
    log_level: str = "INFO"
    database_url: str = "sqlite:///data/missions.db"
    database_connect_attempts: int = 30
    database_connect_delay_seconds: float = 1.0

    # Cache distribuído; vazio faz a API rodar sem Redis
    redis_url: str | None = None
    idempotency_ttl_seconds: int = 300

    # Modelos de IA e origem das imagens processadas
    models_manifest: str = "models/manifest.json"
    images_root: str = "data/images"

    # O token é emitido por outro microsserviço; aqui só validamos a assinatura.
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    # Quando preenchidos, iss e aud também passam a ser exigidos do token.
    jwt_issuer: str | None = None
    jwt_audience: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cache das settings: o arquivo .env é lido uma única vez por processo."""
    return Settings()
