"""Listening lesson acquisition contract — explicit session state for the frontend."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.language_listening_bundles import LessonExperienceBundleOut

AcquisitionStatus = Literal[
    "ready",
    "reserved",
    "generating",
    "waiting",
    "retrying",
    "temporary_failure",
    "no_content",
]

ListeningNextOutcome = Literal["lesson_ready", "acquisition_pending"]


class ListeningAcquisitionStatusOut(BaseModel):
    """Explicit acquisition state — frontend must not infer from HTTP status."""

    model_config = ConfigDict(extra="forbid")

    status: AcquisitionStatus
    lesson_ready: bool = False
    waiting: bool = False
    generation_in_progress: bool = False
    temporary_failure: bool = False
    retry_after: int | None = None
    queue_position: int | None = None
    poll_after: int = 3
    reservation_id: str | None = None
    message_key: str
    attempt: int = 1
    acquisition_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ListeningNextResponseOut(BaseModel):
    """Union wrapper for GET /listening/next — always HTTP 200 when authenticated."""

    model_config = ConfigDict(extra="forbid")

    outcome: ListeningNextOutcome
    bundle: LessonExperienceBundleOut | None = None
    acquisition: ListeningAcquisitionStatusOut | None = None

    @model_validator(mode="after")
    def _validate_outcome(self) -> ListeningNextResponseOut:
        if self.outcome == "lesson_ready":
            if self.bundle is None:
                raise ValueError("bundle required when outcome is lesson_ready")
        elif self.outcome == "acquisition_pending":
            if self.acquisition is None:
                raise ValueError("acquisition required when outcome is acquisition_pending")
        return self
