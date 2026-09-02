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
