"""Adaptador de storage de imagens em disco local.

Substitui, no escopo da prova, o microsserviço que abstrai o S3 no diagrama da
Parte 1. A porta é a mesma, então trocar a implementação não toca no service.
"""

import asyncio
from pathlib import Path

from src.domain.exceptions import ImageNotFoundError
from src.domain.storage import IImageStorage


class LocalImageStorage(IImageStorage):
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _resolve(self, key: str) -> Path:
        # Impede que uma key como "../../etc/passwd" saia do diretório raiz.
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root.resolve()):
            raise ImageNotFoundError(key)
        return path

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._resolve(key).is_file)

    async def read(self, key: str) -> bytes:
        path = self._resolve(key)
        if not await asyncio.to_thread(path.is_file):
            raise ImageNotFoundError(key)
        # Leitura de arquivo é I/O bloqueante: sai do event loop.
        return await asyncio.to_thread(path.read_bytes)
