"""Contratos da camada de service.

Os endpoints dependem destas interfaces, nunca das implementações concretas, o
que permite trocar a regra de negócio (ou usar um dublê nos testes) sem tocar na
camada de API.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.mission import Mission, MissionStatus


class IMissionService(ABC):
    @abstractmethod
    async def create(
        self,
        *,
        name: str,
        drone_model: str,
        status: MissionStatus | None = None,
        image_count: int = 0,
        area_hectares: float = 0.0,
    ) -> Mission: ...

    @abstractmethod
    async def get(self, mission_id: str) -> Mission: ...

    @abstractmethod
    async def update(self, mission_id: str, changes: dict[str, object]) -> Mission: ...

    @abstractmethod
    async def delete(self, mission_id: str) -> None: ...


class ITokenService(ABC):
    @abstractmethod
    def decode(self, token: str) -> dict[str, Any]:
        """Valida assinatura, expiração e claims, devolvendo o conteúdo do token."""
