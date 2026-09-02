"""
Porta de cache distribuído.
"""

from abc import ABC, abstractmethod


class ICache(ABC):
    @abstractmethod
    async def acquire(self, key: str, ttl_seconds: int) -> bool:
        """Marca a chave se ela não existir. False significa que outro processo já a tem."""

    @abstractmethod
    async def release(self, key: str) -> None: ...

    @abstractmethod
    async def ping(self) -> bool: ...
