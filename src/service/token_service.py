"""Validação dos tokens emitidos pelo serviço de autenticação.

A emissão do token (login, senha, usuários) é responsabilidade de outro
microsserviço. Aqui só verificamos a assinatura, a expiração e, quando
configuradas, as claims de emissor e audiência.
"""

from typing import Any

import jwt

from src.config import Settings
from src.service.interfaces import ITokenService


class TokenService(ITokenService):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def decode(self, token: str) -> dict[str, Any]:
        options = {"require": ["exp", "sub"]}
        claims: dict[str, Any] = jwt.decode(
            token,
            self._settings.jwt_secret,
            algorithms=[self._settings.jwt_algorithm],
            issuer=self._settings.jwt_issuer,
            audience=self._settings.jwt_audience,
            options=options,
        )
        return claims
