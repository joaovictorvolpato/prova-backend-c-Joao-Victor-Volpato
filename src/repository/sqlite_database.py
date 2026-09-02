"""
Implementação do driver sobre SQLite.
"""

import asyncio
from pathlib import Path
from typing import Any

import aiosqlite

from src.repository.database import Database, Row

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

CREATE TABLE IF NOT EXISTS predictions (
    id            TEXT PRIMARY KEY,
    request_id    TEXT UNIQUE,
    mission_id    TEXT,
    image_key     TEXT NOT NULL,
    model_version TEXT NOT NULL,
    status        TEXT NOT NULL,
    detections    TEXT NOT NULL DEFAULT '[]',
    inference_ms  REAL,
    total_ms      REAL,
    error         TEXT,
    created_at    TEXT NOT NULL,
    created_by    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_predictions_mission ON predictions (mission_id);
"""


class SQLiteDatabase(Database):
    _lock = asyncio.Lock()

    def __init__(self, path: str) -> None:
        self._path = path
        self._connection: aiosqlite.Connection | None = None

    @property
    def connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            raise RuntimeError("Banco não conectado: chame connect() no lifespan")
        return self._connection

    async def connect(self) -> None:
        async with self._lock:
            if self._connection is not None:
                return
            if self._path != ":memory:":
                Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            self._connection = await aiosqlite.connect(self._path)
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

    async def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> Row | None:
        async with self.connection.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[Row]:
        async with self.connection.execute(query, params) as cursor:
            return list(await cursor.fetchall())
