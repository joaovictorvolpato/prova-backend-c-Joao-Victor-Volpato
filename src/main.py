"""Composição da aplicação: lifespan, middleware e rotas."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from src.api.dependencies import get_model_registry_for
from src.api.errors import register_exception_handlers
from src.api.middleware.jwt_auth import JWTAuthMiddleware
from src.api.routes import auth, health, missions, predictions
from src.config import Settings, get_settings
from src.repository.database import Database
from src.repository.database import get_database
from src.service.token_service import TokenService

logger = logging.getLogger(__name__)


async def connect_with_retry(database: Database, settings: Settings) -> None:
    """Espera o banco ficar disponível antes de a aplicação subir.

    O compose já segura a API até o healthcheck do Postgres passar, mas o banco
    também pode reiniciar depois disso — a retentativa aqui cobre esse caso e
    permite subir a stack sem depender do orquestrador.
    """
    for attempt in range(1, settings.database_connect_attempts + 1):
        try:
            await database.connect()
            return
        except Exception as error:
            if attempt == settings.database_connect_attempts:
                raise
            logger.warning(
                "Banco indisponível (tentativa %s/%s): %s",
                attempt,
                settings.database_connect_attempts,
                error,
            )
            await asyncio.sleep(settings.database_connect_delay_seconds)


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
    # O uvicorn configura só os loggers dele; sem isto, o log da aplicação não
    # chega à saída do container.
    logging.basicConfig(level=settings.log_level, format="%(levelname)s:     %(message)s")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Conexão aberta uma vez na subida e fechada no shutdown.
        database = get_database(settings.database_url)
        await connect_with_retry(database, settings)
        # Carrega a versão ativa do modelo já na subida: a primeira requisição
        # não paga o carregamento, e pesos ausentes derrubam o deploy aqui, e
        # não na cara do usuário.
        get_model_registry_for(settings.models_manifest).get()
        logger.info(
            "Aplicação pronta (event loop: %s)",
            type(asyncio.get_running_loop()).__module__,
        )
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
    app.include_router(predictions.router)

    return app


app = create_app()
