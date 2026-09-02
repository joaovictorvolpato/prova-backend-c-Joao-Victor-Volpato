"""Erros de domínio.

Ficam na camada mais interna para que service e repository sinalizem falhas sem
conhecer HTTP. A tradução para status code acontece na borda, em api/errors.py.
"""


class DomainError(Exception):
    """Erro base do domínio."""


class MissionNotFoundError(DomainError):
    def __init__(self, mission_id: str) -> None:
        super().__init__(f"Missão {mission_id} não encontrada")
        self.mission_id = mission_id


class DuplicatedMissionError(DomainError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Já existe uma missão com o nome '{name}'")
        self.name = name


class InvalidMissionError(DomainError):
    """Regra de negócio violada na criação ou atualização de uma missão."""


class ImageNotFoundError(DomainError):
    def __init__(self, image_key: str) -> None:
        super().__init__(f"Imagem '{image_key}' não encontrada no storage")
        self.image_key = image_key


class InvalidImageError(DomainError):
    """Arquivo existe mas não é uma imagem legível."""


class ModelVersionNotFoundError(DomainError):
    def __init__(self, version: str, available: tuple[str, ...] = ()) -> None:
        disponiveis = ", ".join(available) or "nenhuma"
        super().__init__(f"Versão de modelo '{version}' não existe. Disponíveis: {disponiveis}")
        self.version = version


class InferenceError(DomainError):
    """Falha durante a execução do modelo."""


class PredictionNotFoundError(DomainError):
    def __init__(self, prediction_id: str) -> None:
        super().__init__(f"Predição {prediction_id} não encontrada")
        self.prediction_id = prediction_id


class PredictionInProgressError(DomainError):
    def __init__(self, request_id: str) -> None:
        super().__init__(f"A requisição '{request_id}' já está sendo processada")
        self.request_id = request_id
