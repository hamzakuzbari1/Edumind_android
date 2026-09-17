"""Writing runtime types (W6)."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.language.content import LanguageContentItem
from app.services.language_writing_generation.audit_types import GenerationOutcome, WritingGenerationAuditRecord
from app.services.language_writing_generation.canonical_lesson_types import WritingCanonicalGeneratedLesson
from app.services.language_writing_generation.generation_pipeline import GenerationPipelineResult
from app.services.language_writing_lesson_planner.types import WritingLessonBlueprint
from app.services.language_writing_runtime.errors import WritingRuntimeError
from app.services.language_writing_runtime.provider_types import WritingModelProviderInfo

RUNTIME_SCHEMA_VERSION = "6.0.0"


@dataclass(frozen=True, slots=True)
class WritingRuntimeGenerateResult:
    """Full runtime outcome — lesson, audit, errors."""

    success: bool
    outcome: GenerationOutcome | None
    blueprint: WritingLessonBlueprint | None
    pipeline: GenerationPipelineResult | None
    canonical_lesson: WritingCanonicalGeneratedLesson | None
    audit: WritingGenerationAuditRecord | None
    content_item: LanguageContentItem | None
    provider: WritingModelProviderInfo | None
    error: WritingRuntimeError | None = None
    runtime_version: str = RUNTIME_SCHEMA_VERSION
    attempts: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "outcome": self.outcome.value if self.outcome else None,
            "runtime_version": self.runtime_version,
            "attempts": self.attempts,
            "error": self.error.to_dict() if self.error else None,
            "blueprint_hash": self.blueprint.blueprint_hash if self.blueprint else None,
            "generation_hash": self.canonical_lesson.generation_hash if self.canonical_lesson else None,
            "content_item_id": self.content_item.id if self.content_item else None,
            "provider": {
                "provider_name": self.provider.provider_name,
                "model_name": self.provider.model_name,
            }
            if self.provider
            else None,
        }
