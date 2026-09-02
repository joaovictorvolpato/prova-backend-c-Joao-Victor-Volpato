"""Regras de negócio das missões.

A camada faz a ponte entre a API e o repository: recebe dados já validados
sintaticamente pelos schemas, aplica as regras que dependem do estado
persistido (unicidade de nome, existência) e delega a persistência.
"""

from src.domain.exceptions import (
    DuplicatedMissionError,
    InvalidMissionError,
    MissionNotFoundError,
)
from src.domain.mission import Mission, MissionStatus
from src.domain.repositories import IMissionRepository
from src.service.interfaces import IMissionService


class MissionService(IMissionService):
    def __init__(self, repository: IMissionRepository) -> None:
        # Depende da porta, não da implementação SQL.
        self._repository = repository

    async def create(
        self,
        *,
        name: str,
        drone_model: str,
        status: MissionStatus | None = None,
        image_count: int = 0,
        area_hectares: float = 0.0,
    ) -> Mission:
        if await self._repository.get_by_name(name.strip()):
            raise DuplicatedMissionError(name)

        mission = Mission.create(
            name=name,
            drone_model=drone_model,
            status=status or MissionStatus.PLANNED,
            image_count=image_count,
            area_hectares=area_hectares,
        )
        return await self._repository.create(mission)

    async def get(self, mission_id: str) -> Mission:
        mission = await self._repository.get_by_id(mission_id)
        if mission is None:
            raise MissionNotFoundError(mission_id)
        return mission

    async def update(self, mission_id: str, changes: dict[str, object]) -> Mission:
        if not changes:
            raise InvalidMissionError("Nenhum campo informado para atualização")

        mission = await self.get(mission_id)

        new_name = changes.get("name")
        if isinstance(new_name, str) and new_name.strip() != mission.name:
            existing = await self._repository.get_by_name(new_name.strip())
            if existing and existing.id != mission_id:
                raise DuplicatedMissionError(new_name)
            changes["name"] = new_name.strip()

        # A entidade valida a si mesma, inclusive a transição de status.
        updated = mission.with_changes(**changes)
        return await self._repository.update(updated)

    async def delete(self, mission_id: str) -> None:
        deleted = await self._repository.delete(mission_id)
        if not deleted:
            raise MissionNotFoundError(mission_id)
