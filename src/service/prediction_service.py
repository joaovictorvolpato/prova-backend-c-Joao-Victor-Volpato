"""Regras de negócio do processamento de imagens.

Orquestra validação, inferência e histórico. É aqui que o tempo é medido e que
toda execução — inclusive a que falha — vira um registro.
"""

import asyncio
from time import perf_counter

from src.domain.cache import ICache
from src.domain.exceptions import (
    DomainError,
    ImageNotFoundError,
    PredictionInProgressError,
    PredictionNotFoundError,
)
from src.domain.inference import IModelRegistry
from src.domain.prediction import InferenceParams, Prediction
from src.domain.repositories import IPredictionRepository
from src.domain.storage import IImageStorage
from src.service.interfaces import IMissionService, IPredictionService


class PredictionService(IPredictionService):
    def __init__(
        self,
        repository: IPredictionRepository,
        registry: IModelRegistry,
        storage: IImageStorage,
        mission_service: IMissionService,
        cache: ICache,
        idempotency_ttl_seconds: int = 300,
    ) -> None:
        self._repository = repository
        self._registry = registry
        self._storage = storage
        self._mission_service = mission_service
        self._cache = cache
        self._idempotency_ttl = idempotency_ttl_seconds

    async def predict(
        self,
        *,
        image_key: str,
        created_by: str,
        params: InferenceParams,
        model_version: str | None = None,
        mission_id: str | None = None,
        request_id: str | None = None,
    ) -> Prediction:
        started = perf_counter()

        # Idempotência: o mesmo request_id não reprocessa a imagem. O registro
        # cobre o que já terminou; o lock no Redis cobre o que ainda está em
        # andamento, inclusive em outra réplica da API.
        lock_key = f"prediction:{request_id}" if request_id else None
        if request_id:
            existing = await self._repository.get_by_request_id(request_id)
            if existing is not None:
                return existing
            if not await self._cache.acquire(lock_key, self._idempotency_ttl):
                raise PredictionInProgressError(request_id)

        # Validações que dependem de estado, antes de gastar CPU com o modelo.
        if not await self._storage.exists(image_key):
            raise ImageNotFoundError(image_key)
        if mission_id is not None:
            await self._mission_service.get(mission_id)
        engine = self._registry.get(model_version)

        prediction = Prediction.start(
            image_key=image_key,
            model_version=engine.info.version,
            created_by=created_by,
            request_id=request_id,
            mission_id=mission_id,
        )
        # Grava antes de inferir: se o processo cair no meio, fica o rastro.
        await self._repository.create(prediction)

        try:
            image = await self._storage.read(image_key)
            inference_started = perf_counter()
            # Inferência é CPU-bound: fora do event loop, senão trava a API.
            detections = await asyncio.to_thread(engine.predict, image, params)
            inference_ms = (perf_counter() - inference_started) * 1000
        except DomainError as error:
            failed = prediction.failed(str(error), total_ms=self._elapsed(started))
            await self._repository.update(failed)
            raise
        finally:
            if lock_key:
                await self._cache.release(lock_key)

        succeeded = prediction.succeeded(
            detections, inference_ms=inference_ms, total_ms=self._elapsed(started)
        )
        return await self._repository.update(succeeded)

    async def get(self, prediction_id: str) -> Prediction:
        prediction = await self._repository.get_by_id(prediction_id)
        if prediction is None:
            raise PredictionNotFoundError(prediction_id)
        return prediction

    async def list(
        self,
        *,
        mission_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Prediction]:
        return await self._repository.list(mission_id=mission_id, limit=limit, offset=offset)

    def available_models(self) -> tuple[tuple[str, ...], str]:
        return self._registry.available_versions(), self._registry.active_version

    @staticmethod
    def _elapsed(started: float) -> float:
        return (perf_counter() - started) * 1000
