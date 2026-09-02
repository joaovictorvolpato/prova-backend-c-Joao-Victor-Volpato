"""Configurações da aplicação, carregadas de variáveis de ambiente."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Drone Missions API"
    database_url: str = "data/missions.db"

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
