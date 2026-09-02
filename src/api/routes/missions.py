"""Rotas CRUD de missões."""

from fastapi import APIRouter, status

from src.api.dependencies import CurrentUserDep, MissionServiceDep
from src.api.schemas.common import ErrorResponse
from src.api.schemas.mission import (
    MissionCreateRequest,
    MissionResponse,
    MissionUpdateRequest,
)

router = APIRouter(
    prefix="/missions",
    tags=["missions"],
    responses={401: {"model": ErrorResponse}},
)


@router.post(
    "",
    response_model=MissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma missão",
    responses={409: {"model": ErrorResponse}},
)
async def create_mission(
    payload: MissionCreateRequest,
    service: MissionServiceDep,
    _: CurrentUserDep,
) -> MissionResponse:
    mission = await service.create(
        name=payload.name,
        drone_model=payload.drone_model,
        status=payload.status,
        image_count=payload.image_count,
        area_hectares=payload.area_hectares,
    )
    return MissionResponse.from_domain(mission)


@router.get(
    "/{mission_id}",
    response_model=MissionResponse,
    summary="Busca uma missão pelo id",
    responses={404: {"model": ErrorResponse}},
)
async def get_mission(
    mission_id: str,
    service: MissionServiceDep,
    _: CurrentUserDep,
) -> MissionResponse:
    mission = await service.get(mission_id)
    return MissionResponse.from_domain(mission)


@router.patch(
    "/{mission_id}",
    response_model=MissionResponse,
    summary="Atualiza parcialmente uma missão",
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def update_mission(
    mission_id: str,
    payload: MissionUpdateRequest,
    service: MissionServiceDep,
    _: CurrentUserDep,
) -> MissionResponse:
    mission = await service.update(mission_id, payload.to_changes())
    return MissionResponse.from_domain(mission)


@router.delete(
    "/{mission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove uma missão",
    responses={404: {"model": ErrorResponse}},
)
async def delete_mission(
    mission_id: str,
    service: MissionServiceDep,
    _: CurrentUserDep,
) -> None:
    await service.delete(mission_id)
