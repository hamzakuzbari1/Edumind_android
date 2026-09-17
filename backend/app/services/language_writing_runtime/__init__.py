"""Writing Runtime (W6) — first implementation phase; orchestrates frozen W0–W5 architecture."""

from __future__ import annotations

from app.services.language_writing_runtime.generation_runtime import generate_writing_lesson
from app.services.language_writing_runtime.model_provider import get_writing_model_provider
from app.services.language_writing_runtime.types import WritingRuntimeGenerateResult

RUNTIME_VERSION = "6.0.0"
RESPONSIBILITY = "Writing generation runtime — Lesson Planner through Generation Audit with Claude provider"

__all__ = [
    "RESPONSIBILITY",
    "RUNTIME_VERSION",
    "WritingRuntimeGenerateResult",
    "generate_writing_lesson",
    "get_writing_model_provider",
]
