"""Repository de missões: SQL puro e mapeamento banco <-> domínio."""

from datetime import datetime
from typing import Any, Sequence

import aiosqlite

from src.domain.mission import Mission, MissionStatus
from src.domain.repositories import IMissionRepository
from src.repository.base import AbstractRepository


class MissionRepository(AbstractRepository[Mission], IMissionRepository):
    """Implementa a porta IMissionRepository sobre SQLite.

    Herda de AbstractRepository o CRUD genérico e acrescenta as consultas
    específica de missão (a busca por nome, usada na regra de unicidade).
    """

    @property
    def table(self) -> str:
        return "missions"

    @property
    def columns(self) -> Sequence[str]:
        return (
            "id",
            "name",
            "status",
            "created_at",
            "drone_model",
            "image_count",
            "area_hectares",
        )

    def to_row(self, entity: Mission) -> dict[str, Any]:
        return {
            "id": entity.id,
            "name": entity.name,
            "status": entity.status.value,
            # ISO 8601 mantém a ordenação lexicográfica igual à cronológica.
            "created_at": entity.created_at.isoformat(),
            "drone_model": entity.drone_model,
            "image_count": entity.image_count,
            "area_hectares": entity.area_hectares,
        }

    def to_domain(self, row: aiosqlite.Row) -> Mission:
        return Mission(
            id=row["id"],
            name=row["name"],
            status=MissionStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            drone_model=row["drone_model"],
            image_count=row["image_count"],
            area_hectares=row["area_hectares"],
        )

    async def get_by_name(self, name: str) -> Mission | None:
        query = f"SELECT {', '.join(self.columns)} FROM {self.table} WHERE name = ?"
        row = await self._db.fetch_one(query, (name,))
        return self.to_domain(row) if row else None

