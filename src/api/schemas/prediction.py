"""Schemas das rotas de predição."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.prediction import InferenceParams, Prediction, PredictionStatus


class PredictionRequest(BaseModel):
    """Solicitação de processamento.

    A imagem é referenciada por chave, não enviada no corpo: arquivos grandes
    vão direto para o storage e a API recebe só o ponteiro.
    """

    image_key: str = Field(min_length=1, examples=["missao-12/frame-0001.jpg"])
    mission_id: str | None = None
    model_version: str | None = Field(
        default=None, description="Versão do modelo; vazio usa a ativa"
    )
    confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    max_detections: int = Field(default=300, ge=1, le=1000)
    classes: list[str] | None = Field(
        default=None, description="Filtra o resultado para estas classes"
    )
    request_id: str | None = Field(
        default=None, description="Chave de idempotência: repetir não reprocessa"
    )

    def to_params(self) -> InferenceParams:
        return InferenceParams(
            confidence_threshold=self.confidence_threshold,
            iou_threshold=self.iou_threshold,
            max_detections=self.max_detections,
            classes=tuple(self.classes) if self.classes else None,
        )


class BoundingBoxResponse(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DetectionResponse(BaseModel):
    label: str
    confidence: float
    box: BoundingBoxResponse


class PredictionResponse(BaseModel):
    id: str
    status: PredictionStatus
    image_key: str
    model_version: str
    mission_id: str | None
    request_id: str | None
    detections: list[DetectionResponse]
    inference_ms: float | None
    total_ms: float | None
    error: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, prediction: Prediction) -> "PredictionResponse":
        return cls(
            id=prediction.id,
            status=prediction.status,
            image_key=prediction.image_key,
            model_version=prediction.model_version,
            mission_id=prediction.mission_id,
            request_id=prediction.request_id,
            detections=[
                DetectionResponse(
                    label=detection.label,
                    confidence=detection.confidence,
                    box=BoundingBoxResponse(
                        x_min=detection.box.x_min,
                        y_min=detection.box.y_min,
                        x_max=detection.box.x_max,
                        y_max=detection.box.y_max,
                    ),
                )
                for detection in prediction.detections
            ],
            inference_ms=prediction.inference_ms,
            total_ms=prediction.total_ms,
            error=prediction.error,
            created_at=prediction.created_at,
        )


class PredictionListResponse(BaseModel):
    items: list[PredictionResponse]
    limit: int
    offset: int


class ModelsResponse(BaseModel):
    active_version: str
    available_versions: list[str]
