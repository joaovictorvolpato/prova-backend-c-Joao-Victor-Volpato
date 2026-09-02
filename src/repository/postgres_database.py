"""
Implementação do driver sobre PostgreSQL, com pool de conexões.
"""

import asyncio
import re
from typing import Any

import asyncpg

from src.repository.database import Database, Row

_SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    drone_model   TEXT NOT NULL,
    image_count   INTEGER NOT NULL DEFAULT 0,
    area_hectares DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_missions_status ON missions (status);

CREATE TABLE IF NOT EXISTS predictions (
    id            TEXT PRIMARY KEY,
    request_id    TEXT UNIQUE,
    mission_id    TEXT,
    image_key     TEXT NOT NULL,
    model_version TEXT NOT NULL,
    status        TEXT NOT NULL,
    detections    TEXT NOT NULL DEFAULT '[]',
    inference_ms  DOUBLE PRECISION,
    total_ms      DOUBLE PRECISION,
    error         TEXT,
    created_at    TEXT NOT NULL,
    created_by    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_predictions_mission ON predictions (mission_id);
"""

_PLACEHOLDER = re.compile(r"\?")


class PostgresDatabase(Database):
    """Diferente do SQLite, aqui o paralelismo é real: o pool abre várias
    conexões de rede independentes, então leituras concorrentes não ficam em
    fila atrás de uma única thread.
    """

    _lock = asyncio.Lock()

    def __init__(self, dsn: str, *, min_size: int = 2, max_size: int = 10) -> None:
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Banco não conectado: chame connect() no lifespan")
        return self._pool

    async def connect(self) -> None:
        async with self._lock:
            if self._pool is not None:
                return
            self._pool = await asyncpg.create_pool(
                self._dsn, min_size=self._min_size, max_size=self._max_size
            )
            async with self._pool.acquire() as connection:
                await connection.execute(_SCHEMA)

    async def disconnect(self) -> None:
        async with self._lock:
            if self._pool is None:
                return
            await self._pool.close()
            self._pool = None

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        status = await self.pool.execute(self._translate(query), *params)
        # asyncpg devolve algo como "UPDATE 1"; o último campo é a contagem.
        _, _, affected = status.rpartition(" ")
        return int(affected) if affected.isdigit() else 0

    async def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> Row | None:
        return await self.pool.fetchrow(self._translate(query), *params)

    async def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[Row]:
        return list(await self.pool.fetch(self._translate(query), *params))

    @staticmethod
    def _translate(query: str) -> str:
        """Converte os placeholders `?` dos repositories para o `$n` do asyncpg.

        Mantém o SQL dos repositories em um dialeto só; a diferença de sintaxe
        fica contida no driver.
        """
        counter = iter(range(1, query.count("?") + 1))
        return _PLACEHOLDER.sub(lambda _: f"${next(counter)}", query)
