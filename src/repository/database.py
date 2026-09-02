"""
Driver de banco de dados: contrato comum e singleton por processo.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Mapping

Row = Mapping[str, Any]


class Database(ABC):
    """Contrato que os repositories enxergam.

    Só as implementações conhecem o driver concreto, então trocar SQLite por
    PostgreSQL não muda uma linha de repository, service ou domínio.
    """

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> int: ...

    @abstractmethod
    async def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> Row | None: ...

    @abstractmethod
    async def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[Row]: ...

    async def ping(self) -> None:
        """Levanta exceção se o banco não responder. Usado pelo healthcheck."""
        await self.fetch_one("SELECT 1")


_instance: Database | None = None
_lock = asyncio.Lock()


def get_database(database_url: str) -> Database:
    """Devolve o singleton, criando-o na primeira chamada.

    A URL define a implementação: `postgresql://...` usa asyncpg, qualquer
    outra coisa é tratada como caminho de arquivo SQLite.
    """
    global _instance
    if _instance is None:
        _instance = _build(database_url)
    return _instance


def reset_database() -> None:
    """Descarta a instância. Usado apenas pelos testes."""
    global _instance
    _instance = None


def _build(database_url: str) -> Database:
    if database_url.startswith(("postgresql://", "postgres://")):
        from src.repository.postgres_database import PostgresDatabase

        return PostgresDatabase(database_url)

    from src.repository.sqlite_database import SQLiteDatabase

    path = database_url.removeprefix("sqlite:///")
    return SQLiteDatabase(path)
