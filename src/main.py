"""Composição da aplicação: lifespan, middleware e rotas."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.api.errors import register_exception_handlers
from src.api.middleware.jwt_auth import JWTAuthMiddleware
from src.api.routes import auth, health, missions
from src.config import Settings, get_settings
from src.repository.database import Database
from src.service.token_service import TokenService

# Rotas que não exigem token: healthcheck e documentação.
PUBLIC_PATHS = ("/health", "/docs", "/redoc", "/openapi.json", "/")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Composition root da aplicação.

    Sem argumento, usa as Settings do ambiente. Receber uma instância explícita
    serve aos testes, que precisam de banco e chave próprios; nesse caso o
    override abaixo garante que endpoints, lifespan e middleware leiam a mesma
    configuração.
    """
    override = settings is not None
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Conexão aberta uma vez na subida e fechada no shutdown.
        database = Database(settings.database_url)
        await database.connect()
        try:
            yield
        finally:
            await database.disconnect()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "API de missões de voo — Parte 2 da prova prática. "
            "A emissão de tokens é responsabilidade do serviço de autenticação."
        ),
        lifespan=lifespan,
    )
    if override:
        app.dependency_overrides[get_settings] = lambda: settings

    # O middleware só precisa validar o token, então recebe apenas o decoder.
    token_service = TokenService(settings)
    app.add_middleware(
        JWTAuthMiddleware,
        token_decoder=token_service.decode,
        public_paths=PUBLIC_PATHS,
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(missions.router)

    return app


app = create_app()
