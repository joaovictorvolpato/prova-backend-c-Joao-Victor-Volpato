"""Fixtures dos testes: cada teste roda contra um banco SQLite próprio."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.main import create_app
from src.repository.database import Database


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(database_url=str(tmp_path / "test.db"), jwt_secret="test-secret")


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
