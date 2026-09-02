"""Portas de inferência.

O domínio define o que um modelo precisa saber fazer; qual biblioteca executa
isso (ONNX Runtime, PyTorch, um serviço remoto) é detalhe da camada externa.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.prediction import Detection, InferenceParams


@dataclass(frozen=True, slots=True)
class ModelInfo:
    version: str
    task: str
    description: str = ""


class IInferenceEngine(ABC):
    """Um modelo carregado e pronto para inferir."""

    @property
    @abstractmethod
    def info(self) -> ModelInfo: ...

    @abstractmethod
    def predict(self, image: bytes, params: InferenceParams) -> tuple[Detection, ...]:
        """Executa a inferência. Síncrono de propósito: quem chama decide a thread."""


class IModelRegistry(ABC):
    """Guarda os modelos disponíveis, carregados uma única vez por versão."""

    @property
    @abstractmethod
    def active_version(self) -> str: ...

    @abstractmethod
    def get(self, version: str | None = None) -> IInferenceEngine:
        """Devolve o engine da versão pedida (ou da ativa), reaproveitando o cache."""

    @abstractmethod
    def available_versions(self) -> tuple[str, ...]: ...
