"""Fixtures dos testes: cada teste roda contra um banco SQLite próprio."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.main import create_app
from src.repository.database import Database


@pytest.fixture
def images_root(tmp_path):
    root = tmp_path / "images"
    root.mkdir()
    return root


@pytest.fixture
def settings(tmp_path, images_root) -> Settings:
    return Settings(
        database_url=str(tmp_path / "test.db"),
        jwt_secret="test-secret",
        images_root=str(images_root),
        # Manifesto real: o registry é memorizado, então o modelo carrega uma
        # única vez para toda a suíte.
        models_manifest="models/manifest.json",
    )


@pytest.fixture
def image_key(images_root) -> str:
    """Grava uma imagem pequena e devolve a chave dela no storage."""
    from PIL import Image

    key = "missao-12/frame-0001.png"
    path = images_root / key
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), color=(120, 140, 90)).save(path)
    return key


@pytest.fixture
def client(settings: Settings):
    # O singleton é reiniciado para não vazar conexão entre testes.
    Database.reset()
    with TestClient(create_app(settings)) as test_client:
        yield test_client
    Database.reset()


@pytest.fixture
def make_token(settings: Settings):
    """Emite um token como faria o serviço de autenticação."""

    def _make(
        *,
        subject: str = "user-123",
        username: str = "tester",
        expires_in: timedelta = timedelta(minutes=30),
        secret: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {"sub": subject, "username": username, "iat": now, "exp": now + expires_in},
            secret or settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

    return _make


@pytest.fixture
def auth_headers(make_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token()}"}


@pytest.fixture
def mission_payload() -> dict[str, object]:
    return {
        "name": "Talhão 12",
        "drone_model": "DJI Mavic 3M",
        "image_count": 120,
        "area_hectares": 34.5,
    }
