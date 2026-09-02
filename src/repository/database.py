"""
Driver de banco de dados (SQLite) exposto como singleton.
"""

import asyncio
from pathlib import Path
from typing import Any, Self

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    drone_model   TEXT NOT NULL,
    image_count   INTEGER NOT NULL DEFAULT 0,
    area_hectares REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_missions_status ON missions (status);

"""


class Database:
    """Singleton que encapsula a conexão com o SQLite.

    Só esta classe conhece o driver concreto: os repositories falam com ela por
    execute/fetch_one/fetch_all, de modo que trocar o banco (o PostgreSQL da
    Parte 4, por exemplo) não vaza para as demais camadas.
    """

    _instance: Self | None = None
    _lock = asyncio.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, database_url: str = "") -> None:
        if getattr(self, "_initialized", False):
            return
        self._database_url = database_url
        self._connection: aiosqlite.Connection | None = None
        self._initialized = True

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Banco não conectado: chame connect() no lifespan")
        return self._connection

    async def connect(self) -> None:
        async with self._lock:
            if self._connection is not None:
                return
            if self._database_url != ":memory:":
                Path(self._database_url).parent.mkdir(parents=True, exist_ok=True)
            self._connection = await aiosqlite.connect(self._database_url)
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA foreign_keys = ON")
            await self._connection.execute("PRAGMA journal_mode = WAL")
            await self._connection.executescript(_SCHEMA)
            await self._connection.commit()

    async def disconnect(self) -> None:
        async with self._lock:
            if self._connection is None:
                return
            await self._connection.close()
            self._connection = None

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        cursor = await self.connection.execute(query, params)
        await self.connection.commit()
        return cursor.rowcount

    async def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        async with self.connection.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        async with self.connection.execute(query, params) as cursor:
            return list(await cursor.fetchall())

    @classmethod
    def reset(cls) -> None:
        """Descarta a instância. Usado apenas pelos testes."""
        cls._instance = None
