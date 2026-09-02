"""Entidade Mission e suas regras próprias."""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from src.domain.exceptions import InvalidMissionError


class MissionStatus(str, Enum):
    """Estados possíveis de uma missão, do planejamento à conclusão."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


# Transições permitidas. Uma missão encerrada não volta a rodar.
_ALLOWED_TRANSITIONS: dict[MissionStatus, set[MissionStatus]] = {
    MissionStatus.PLANNED: {MissionStatus.IN_PROGRESS, MissionStatus.CANCELED},
    MissionStatus.IN_PROGRESS: {MissionStatus.COMPLETED, MissionStatus.FAILED},
    MissionStatus.COMPLETED: set(),
    MissionStatus.FAILED: set(),
    MissionStatus.CANCELED: set(),
}


@dataclass(frozen=True, slots=True)
class Mission:
    """Missão de voo. Imutável: alterações produzem uma nova instância."""

    id: str
    name: str
    status: MissionStatus
    created_at: datetime
    drone_model: str
    image_count: int
    area_hectares: float

    @classmethod
    def create(
        cls,
        *,
        name: str,
        drone_model: str,
        status: MissionStatus = MissionStatus.PLANNED,
        image_count: int = 0,
        area_hectares: float = 0.0,
    ) -> "Mission":
        """Cria uma missão nova, com id e created_at gerados pelo domínio."""
        mission = cls(
            id=str(uuid4()),
            name=name.strip(),
            status=status,
            created_at=datetime.now(timezone.utc),
            drone_model=drone_model.strip(),
            image_count=image_count,
            area_hectares=area_hectares,
        )
        mission.validate()
        return mission

    def validate(self) -> None:
        if not self.name:
            raise InvalidMissionError("O nome da missão não pode ser vazio")
        if not self.drone_model:
            raise InvalidMissionError("O modelo do drone é obrigatório")
        if self.image_count < 0:
            raise InvalidMissionError("image_count não pode ser negativo")
        if self.area_hectares < 0:
            raise InvalidMissionError("area_hectares não pode ser negativo")

    def with_changes(self, **changes: object) -> "Mission":
        """Aplica alterações validando a entidade resultante.

        Mudança de status passa pela máquina de estados; os demais campos são
        substituídos diretamente.
        """
        raw_status = changes.get("status")
        if raw_status is not None:
            # Converte antes de comparar: o status pode chegar como string,
            # e assim a entidade guarda sempre o enum.
            new_status = MissionStatus(raw_status)
            changes = {**changes, "status": new_status}
            if new_status != self.status:
                self._assert_transition_allowed(new_status)

        updated = replace(self, **changes)  # type: ignore[arg-type]
        updated.validate()
        return updated

    def _assert_transition_allowed(self, new_status: MissionStatus) -> None:
        if new_status not in _ALLOWED_TRANSITIONS[self.status]:
            raise InvalidMissionError(
                f"Transição de status inválida: {self.status.value} -> {new_status.value}"
            )
