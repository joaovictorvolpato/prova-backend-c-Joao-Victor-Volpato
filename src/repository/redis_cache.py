"""
Adaptadores de cache: Redis e a implementação nula usada quando não há Redis.
"""

from redis.asyncio import Redis

from src.domain.cache import ICache


class RedisCache(ICache):
    """O `SET NX EX` do Redis é atômico entre processos.

    É o que permite que várias réplicas da API coordenem entre si — algo que
    um cache em memória de cada processo não resolve.
    """

    def __init__(self, url: str) -> None:
        self._client = Redis.from_url(url, decode_responses=True)

    async def acquire(self, key: str, ttl_seconds: int) -> bool:
        return bool(await self._client.set(key, "1", nx=True, ex=ttl_seconds))

    async def release(self, key: str) -> None:
        await self._client.delete(key)

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


class NullCache(ICache):
    """Usada quando REDIS_URL não está configurada: a API roda sem Redis."""

    async def acquire(self, key: str, ttl_seconds: int) -> bool:
        return True

    async def release(self, key: str) -> None:
        return None

    async def ping(self) -> bool:
        return False
