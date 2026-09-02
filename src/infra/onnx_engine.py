"""Execução dos modelos com ONNX Runtime.

Única parte do projeto que conhece a biblioteca de inferência. O registry
carrega cada versão uma vez e mantém a sessão em memória; o engine converte
entre a imagem crua e o formato que o modelo espera.
"""

import io
import json
import threading
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from PIL import Image, UnidentifiedImageError

from src.domain.exceptions import (
    InferenceError,
    InvalidImageError,
    ModelVersionNotFoundError,
)
from src.domain.inference import IInferenceEngine, IModelRegistry, ModelInfo
from src.domain.prediction import BoundingBox, Detection, InferenceParams


class OnnxDetectionEngine(IInferenceEngine):
    """Detector de objetos sobre uma sessão ONNX já carregada.

    A sessão do ONNX Runtime é thread-safe, então a mesma instância atende
    requisições concorrentes sem lock.
    """

    def __init__(
        self,
        session: ort.InferenceSession,
        *,
        info: ModelInfo,
        input_name: str,
        labels: dict[int, str],
    ) -> None:
        self._session = session
        self._info = info
        self._input_name = input_name
        self._labels = labels

    @property
    def info(self) -> ModelInfo:
        return self._info

    def predict(self, image: bytes, params: InferenceParams) -> tuple[Detection, ...]:
        tensor = self._preprocess(image)
        try:
            boxes, classes, scores, _ = self._session.run(None, {self._input_name: tensor})
        except Exception as error:  # falha dentro do runtime
            raise InferenceError(f"Falha ao executar o modelo: {error}") from error
        return self._postprocess(boxes[0], classes[0], scores[0], params)

    def _preprocess(self, image: bytes) -> np.ndarray:
        try:
            with Image.open(io.BytesIO(image)) as handle:
                rgb = handle.convert("RGB")
                array = np.asarray(rgb, dtype=np.uint8)
        except (UnidentifiedImageError, OSError) as error:
            raise InvalidImageError("Arquivo não é uma imagem válida") from error
        # O modelo aceita resolução dinâmica no formato NHWC uint8.
        return array[np.newaxis, ...]

    def _postprocess(
        self,
        boxes: np.ndarray,
        classes: np.ndarray,
        scores: np.ndarray,
        params: InferenceParams,
    ) -> tuple[Detection, ...]:
        detections: list[Detection] = []
        for box, class_id, score in zip(boxes, classes, scores):
            confidence = float(score)
            if confidence < params.confidence_threshold:
                # As saídas vêm ordenadas por score: abaixo do corte, acabou.
                break
            label = self._labels.get(int(class_id), f"class_{int(class_id)}")
            if params.classes and label not in params.classes:
                continue
            y_min, x_min, y_max, x_max = (float(value) for value in box)
            detections.append(
                Detection(
                    label=label,
                    confidence=confidence,
                    box=BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max),
                )
            )
            if len(detections) >= params.max_detections:
                break
        return tuple(detections)


class OnnxModelRegistry(IModelRegistry):
    """Carrega os modelos declarados no manifesto, uma vez cada.

    O cache é por versão: a primeira chamada paga o carregamento, as seguintes
    reaproveitam a mesma sessão. Assim é possível servir mais de uma versão sem
    reiniciar o processo, o que sustenta rollback e comparação entre versões.
    """

    def __init__(self, manifest_path: str) -> None:
        self._manifest_path = Path(manifest_path)
        self._manifest = self._load_manifest()
        self._engines: dict[str, IInferenceEngine] = {}
        # Protege o cache: duas requisições simultâneas pedindo a mesma versão
        # nova não podem carregar o modelo duas vezes.
        self._lock = threading.Lock()

    @property
    def active_version(self) -> str:
        version: str = self._manifest["active_version"]
        return version

    def available_versions(self) -> tuple[str, ...]:
        return tuple(model["version"] for model in self._manifest["models"])

    def get(self, version: str | None = None) -> IInferenceEngine:
        version = version or self.active_version
        engine = self._engines.get(version)
        if engine is not None:
            return engine

        with self._lock:
            # Outra thread pode ter carregado enquanto esperávamos o lock.
            if version in self._engines:
                return self._engines[version]
            engine = self._build(version)
            self._engines[version] = engine
            return engine

    def loaded_versions(self) -> tuple[str, ...]:
        return tuple(self._engines)

    def _load_manifest(self) -> dict[str, Any]:
        if not self._manifest_path.is_file():
            raise FileNotFoundError(
                f"Manifesto de modelos não encontrado em {self._manifest_path}"
            )
        with self._manifest_path.open(encoding="utf-8") as handle:
            manifest: dict[str, Any] = json.load(handle)
        return manifest

    def _build(self, version: str) -> IInferenceEngine:
        entry = next(
            (model for model in self._manifest["models"] if model["version"] == version),
            None,
        )
        if entry is None:
            raise ModelVersionNotFoundError(version, self.available_versions())

        model_path = self._manifest_path.parent / entry["file"]
        if not model_path.is_file():
            raise InferenceError(f"Arquivo do modelo ausente: {model_path}")

        session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        return OnnxDetectionEngine(
            session,
            info=ModelInfo(
                version=entry["version"],
                task=entry["task"],
                description=entry.get("description", ""),
            ),
            input_name=entry["input_name"],
            labels={int(key): value for key, value in entry["labels"].items()},
        )
