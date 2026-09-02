"""Repository abstrato com as operações CRUD comuns.

Concentra o SQL genérico (o que muda entre entidades é só tabela, colunas e o
mapeamento de linha para objeto de domínio), evitando repetir os mesmos quatro
comandos em cada repository concreto.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Sequence, TypeVar

import aiosqlite

from src.repository.database import Database

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """Base CRUD sobre uma tabela com chave primária `id`."""

    def __init__(self, database: Database) -> None:
        self._db = database

    @property
    @abstractmethod
    def table(self) -> str:
        """Nome da tabela."""

    @property
    @abstractmethod
    def columns(self) -> Sequence[str]:
        """Colunas persistidas, na ordem usada pelo INSERT."""

    @abstractmethod
    def to_row(self, entity: T) -> dict[str, Any]:
        """Converte a entidade de domínio em colunas do banco."""

    @abstractmethod
    def to_domain(self, row: aiosqlite.Row) -> T:
        """Converte uma linha do banco na entidade de domínio."""

    async def create(self, entity: T) -> T:
        row = self.to_row(entity)
        placeholders = ", ".join("?" for _ in self.columns)
        query = (
            f"INSERT INTO {self.table} ({', '.join(self.columns)}) VALUES ({placeholders})"
        )
        await self._db.execute(query, tuple(row[column] for column in self.columns))
        return entity

    async def get_by_id(self, entity_id: str) -> T | None:
        query = f"SELECT {', '.join(self.columns)} FROM {self.table} WHERE id = ?"
        row = await self._db.fetch_one(query, (entity_id,))
        return self.to_domain(row) if row else None

    async def update(self, entity: T) -> T:
        row = self.to_row(entity)
        updatable = [column for column in self.columns if column != "id"]
        assignments = ", ".join(f"{column} = ?" for column in updatable)
        query = f"UPDATE {self.table} SET {assignments} WHERE id = ?"
        params = tuple(row[column] for column in updatable) + (row["id"],)
        await self._db.execute(query, params)
        return entity

    async def delete(self, entity_id: str) -> bool:
        query = f"DELETE FROM {self.table} WHERE id = ?"
        affected = await self._db.execute(query, (entity_id,))
        return affected > 0
