"""Rotas de processamento de imagens por modelo de IA."""

from fastapi import APIRouter, Query, status

from src.api.dependencies import CurrentUserDep, PredictionServiceDep
from src.api.schemas.common import ErrorResponse
from src.api.schemas.prediction import (
    ModelsResponse,
    PredictionListResponse,
    PredictionRequest,
    PredictionResponse,
)

router = APIRouter(tags=["predictions"], responses={401: {"model": ErrorResponse}})


@router.post(
    "/predictions",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Processa uma imagem com o modelo",
    responses={
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def create_prediction(
    payload: PredictionRequest,
    service: PredictionServiceDep,
    current_user: CurrentUserDep,
) -> PredictionResponse:
    prediction = await service.predict(
        image_key=payload.image_key,
        created_by=current_user.id,
        params=payload.to_params(),
        model_version=payload.model_version,
        mission_id=payload.mission_id,
        request_id=payload.request_id,
    )
    return PredictionResponse.from_domain(prediction)


@router.get(
    "/predictions",
    response_model=PredictionListResponse,
    summary="Histórico de predições",
)
async def list_predictions(
    service: PredictionServiceDep,
    _: CurrentUserDep,
    mission_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PredictionListResponse:
    predictions = await service.list(mission_id=mission_id, limit=limit, offset=offset)
    return PredictionListResponse(
        items=[PredictionResponse.from_domain(prediction) for prediction in predictions],
        limit=limit,
        offset=offset,
    )


@router.get(
    "/predictions/{prediction_id}",
    response_model=PredictionResponse,
    summary="Busca uma predição pelo id",
    responses={404: {"model": ErrorResponse}},
)
async def get_prediction(
    prediction_id: str,
    service: PredictionServiceDep,
    _: CurrentUserDep,
) -> PredictionResponse:
    prediction = await service.get(prediction_id)
    return PredictionResponse.from_domain(prediction)


@router.get("/models", response_model=ModelsResponse, summary="Modelos disponíveis")
async def list_models(service: PredictionServiceDep, _: CurrentUserDep) -> ModelsResponse:
    versions, active = service.available_models()
    return ModelsResponse(active_version=active, available_versions=list(versions))
