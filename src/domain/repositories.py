"""Portas de persistência.

As interfaces ficam no domínio, e não na camada de repository, justamente para
que a dependência aponte para dentro: o service depende desta abstração e a
implementação SQL (camada externa) é que depende do domínio.
"""

from abc import ABC, abstractmethod

from src.domain.mission import Mission
from src.domain.prediction import Prediction


class IMissionRepository(ABC):
    """Contrato de persistência de missões."""

    @abstractmethod
    async def create(self, mission: Mission) -> Mission: ...

    @abstractmethod
    async def get_by_id(self, mission_id: str) -> Mission | None: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Mission | None: ...

    @abstractmethod
    async def update(self, mission: Mission) -> Mission: ...

    @abstractmethod
    async def delete(self, mission_id: str) -> bool: ...


class IPredictionRepository(ABC):
    """Contrato de persistência do histórico de predições."""

    @abstractmethod
    async def create(self, prediction: Prediction) -> Prediction: ...

    @abstractmethod
    async def update(self, prediction: Prediction) -> Prediction: ...

    @abstractmethod
    async def get_by_id(self, prediction_id: str) -> Prediction | None: ...

    @abstractmethod
    async def get_by_request_id(self, request_id: str) -> Prediction | None: ...

    @abstractmethod
    async def list(
        self,
        *,
        mission_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Prediction]: ...
