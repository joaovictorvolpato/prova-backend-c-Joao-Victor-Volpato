"""Porta de acesso às imagens.

Hoje o adaptador lê do disco; em produção seria o microsserviço de storage que
abstrai o S3, sem que service e domínio percebam a troca.
"""

from abc import ABC, abstractmethod


class IImageStorage(ABC):
    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def read(self, key: str) -> bytes: ...
