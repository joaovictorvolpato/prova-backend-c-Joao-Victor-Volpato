"""Entidades do processamento de imagens por modelo de IA."""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class PredictionStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Caixa em coordenadas relativas (0..1), independente da resolução."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True, slots=True)
class Detection:
    label: str
    confidence: float
    box: BoundingBox


@dataclass(frozen=True, slots=True)
class InferenceParams:
    """Parâmetros que o cliente pode ajustar por requisição."""

    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    max_detections: int = 300
    classes: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class Prediction:
    """Uma execução de inferência, do pedido ao resultado.

    É o registro do histórico: nasce como `running`, antes da inferência, para
    que uma queda do processo no meio do caminho deixe rastro em vez de sumir.
    """

    id: str
    image_key: str
    model_version: str
    status: PredictionStatus
    created_at: datetime
    created_by: str
    request_id: str | None = None
    mission_id: str | None = None
    detections: tuple[Detection, ...] = field(default_factory=tuple)
    inference_ms: float | None = None
    total_ms: float | None = None
    error: str | None = None

    @classmethod
    def start(
        cls,
        *,
        image_key: str,
        model_version: str,
        created_by: str,
        request_id: str | None = None,
        mission_id: str | None = None,
    ) -> "Prediction":
        return cls(
            id=str(uuid4()),
            image_key=image_key,
            model_version=model_version,
            status=PredictionStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            request_id=request_id,
            mission_id=mission_id,
        )

    def succeeded(
        self, detections: tuple[Detection, ...], *, inference_ms: float, total_ms: float
    ) -> "Prediction":
        return replace(
            self,
            status=PredictionStatus.SUCCEEDED,
            detections=detections,
            inference_ms=inference_ms,
            total_ms=total_ms,
        )

    def failed(self, error: str, *, total_ms: float) -> "Prediction":
        return replace(
            self, status=PredictionStatus.FAILED, error=error, total_ms=total_ms
        )
