from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AiJobOut(BaseModel):
    id: int
    job_type: str
    status: str
    lesson_id: int | None = None
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
