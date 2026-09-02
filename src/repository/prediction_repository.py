"""Repository do histórico de predições."""

import json
from datetime import datetime
from typing import Any, Sequence

import aiosqlite

from src.domain.prediction import (
    BoundingBox,
    Detection,
    Prediction,
    PredictionStatus,
)
from src.domain.repositories import IPredictionRepository
from src.repository.base import AbstractRepository


class PredictionRepository(AbstractRepository[Prediction], IPredictionRepository):
    """As detecções são serializadas em JSON numa coluna.

    Elas só são lidas junto da predição que as originou, então normalizar em
    outra tabela custaria um join a cada leitura sem nenhum ganho de consulta.
    """

    @property
    def table(self) -> str:
        return "predictions"

    @property
    def columns(self) -> Sequence[str]:
        return (
            "id",
            "request_id",
            "mission_id",
            "image_key",
            "model_version",
            "status",
            "detections",
            "inference_ms",
            "total_ms",
            "error",
            "created_at",
            "created_by",
        )

    def to_row(self, entity: Prediction) -> dict[str, Any]:
        return {
            "id": entity.id,
            "request_id": entity.request_id,
            "mission_id": entity.mission_id,
            "image_key": entity.image_key,
            "model_version": entity.model_version,
            "status": entity.status.value,
            "detections": json.dumps(
                [
                    {
                        "label": detection.label,
                        "confidence": detection.confidence,
                        "box": [
                            detection.box.x_min,
                            detection.box.y_min,
                            detection.box.x_max,
                            detection.box.y_max,
                        ],
                    }
                    for detection in entity.detections
                ]
            ),
            "inference_ms": entity.inference_ms,
            "total_ms": entity.total_ms,
            "error": entity.error,
            "created_at": entity.created_at.isoformat(),
            "created_by": entity.created_by,
        }

    def to_domain(self, row: aiosqlite.Row) -> Prediction:
        detections = tuple(
            Detection(
                label=item["label"],
                confidence=item["confidence"],
                box=BoundingBox(*item["box"]),
            )
            for item in json.loads(row["detections"])
        )
        return Prediction(
            id=row["id"],
            request_id=row["request_id"],
            mission_id=row["mission_id"],
            image_key=row["image_key"],
            model_version=row["model_version"],
            status=PredictionStatus(row["status"]),
            detections=detections,
            inference_ms=row["inference_ms"],
            total_ms=row["total_ms"],
            error=row["error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            created_by=row["created_by"],
        )

    async def get_by_request_id(self, request_id: str) -> Prediction | None:
        query = f"SELECT {', '.join(self.columns)} FROM {self.table} WHERE request_id = ?"
        row = await self._db.fetch_one(query, (request_id,))
        return self.to_domain(row) if row else None

    async def list(
        self,
        *,
        mission_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Prediction]:
        query = f"SELECT {', '.join(self.columns)} FROM {self.table}"
        params: tuple[Any, ...] = ()
        if mission_id is not None:
            query += " WHERE mission_id = ?"
            params += (mission_id,)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += (limit, offset)

        rows = await self._db.fetch_all(query, params)
        return [self.to_domain(row) for row in rows]
