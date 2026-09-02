"""Schemas de autenticação."""

from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """Identidade extraída do JWT pelo middleware."""

    id: str
    username: str | None = None
