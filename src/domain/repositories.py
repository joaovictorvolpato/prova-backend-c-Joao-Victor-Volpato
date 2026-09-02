"""Portas de persistência.

As interfaces ficam no domínio, e não na camada de repository, justamente para
que a dependência aponte para dentro: o service depende desta abstração e a
implementação SQL (camada externa) é que depende do domínio.
"""

from abc import ABC, abstractmethod

from src.domain.mission import Mission


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
