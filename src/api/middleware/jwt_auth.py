"""Middleware de autenticação JWT.

Roda antes de qualquer rota: valida o Bearer token e coloca a identidade em
request.state.user, de onde a dependência get_current_user a lê. Ficar no
middleware garante que uma rota nova já nasça protegida — só as rotas
explicitamente listadas como públicas ficam de fora.
"""

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

import jwt
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

TokenDecoder = Callable[[str], dict[str, Any]]


class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        *,
        token_decoder: TokenDecoder,
        public_paths: Iterable[str] = (),
    ) -> None:
        super().__init__(app)
        # Recebe apenas a função de decodificar: o middleware não conhece o
        # serviço concreto que valida o token.
        self._decode = token_decoder
        self._public_paths = tuple(public_paths)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if self._is_public(request):
            return await call_next(request)

        token = self._extract_token(request)
        if token is None:
            return self._unauthorized("Token de autenticação ausente")

        try:
            claims = self._decode(token)
        except jwt.ExpiredSignatureError:
            return self._unauthorized("Token expirado")
        except jwt.InvalidTokenError:
            return self._unauthorized("Token inválido")

        request.state.user = {"id": claims.get("sub"), "username": claims.get("username")}
        return await call_next(request)

    def _is_public(self, request: Request) -> bool:
        # OPTIONS precisa passar para o preflight de CORS não quebrar.
        if request.method == "OPTIONS":
            return True
        path = request.url.path.rstrip("/") or "/"
        return any(path == public or path.startswith(f"{public}/") for public in self._public_paths)

    @staticmethod
    def _extract_token(request: Request) -> str | None:
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return None
        return token.strip()

    @staticmethod
    def _unauthorized(detail: str) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": detail},
            headers={"WWW-Authenticate": "Bearer"},
        )
