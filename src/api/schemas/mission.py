"""Schemas de entrada e saída das rotas de missão.

Os schemas existem só na borda: validam o payload HTTP e formatam a resposta.
O restante da aplicação trabalha com a entidade Mission.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.domain.mission import Mission, MissionStatus


class MissionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Talhão 12 - Fazenda São João"])
    drone_model: str = Field(min_length=1, max_length=60, examples=["DJI Mavic 3M"])
    status: MissionStatus = MissionStatus.PLANNED
    image_count: int = Field(default=0, ge=0)
    area_hectares: float = Field(default=0.0, ge=0)


class MissionUpdateRequest(BaseModel):
    """Atualização parcial: só os campos enviados são alterados."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    drone_model: str | None = Field(default=None, min_length=1, max_length=60)
    status: MissionStatus | None = None
    image_count: int | None = Field(default=None, ge=0)
    area_hectares: float | None = Field(default=None, ge=0)

    def to_changes(self) -> dict[str, object]:
        return self.model_dump(exclude_unset=True, exclude_none=True)


class MissionResponse(BaseModel):
    id: str
    name: str
    status: MissionStatus
    created_at: datetime
    drone_model: str
    image_count: int
    area_hectares: float

    @classmethod
    def from_domain(cls, mission: Mission) -> "MissionResponse":
        return cls(
            id=mission.id,
            name=mission.name,
            status=mission.status,
            created_at=mission.created_at,
            drone_model=mission.drone_model,
            image_count=mission.image_count,
            area_hectares=mission.area_hectares,
        )

