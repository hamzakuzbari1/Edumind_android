"""Development-only email testing."""

from pydantic import BaseModel, EmailStr


class TestEmailRequest(BaseModel):
    to: EmailStr


class TestEmailResponse(BaseModel):
    ok: bool
    message_id: str | None = None
    detail: str | None = None
