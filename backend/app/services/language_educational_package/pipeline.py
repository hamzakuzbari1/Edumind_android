"""Shared generation pipeline: normalize → validate → repair → validate → freeze."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4

from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.freeze import freeze_package
from app.services.language_educational_package.lifecycle import PackageLifecycleStatus
from app.services.language_educational_package.material_kinds import BodyBlockKind, InputMaterialKind
from app.services.language_educational_package.normalize import NormalizationResult, normalize_author_response
from app.services.language_educational_package.repair import RepairResult, repair_package
from app.services.language_educational_package.types import (
    ELP_AUTHOR_VERSION,
    ELP_SCHEMA_VERSION,
    AuthoredTeachingBlock,
    BodyBlock,
    DiscussionFlow,
    EducationalPackage,
    InputMaterial,
    MiniPractice,
    ReflectionSection,
    StorySpine,
    VocabularyInContext,
)
from app.services.language_educational_package.validation import (
    ValidationResult,
    validate_package_draft,
    validation_to_dict,
)


class GenerationOutcome(StrEnum):
    success = "success"
    soft_failure = "soft_failure"  # repaired then passed
    hard_failure = "hard_failure"


@dataclass(slots=True)
class PackageGenerationResult:
    success: bool
    outcome: GenerationOutcome
    package: EducationalPackage | None
    constraints: PackageConstraints
    normalization: NormalizationResult
    validation: ValidationResult | None
    repair: RepairResult | None
    audit: dict[str, Any]


def _draft_to_package(draft: dict[str, Any], constraints: PackageConstraints) -> EducationalPackage:
    material_raw = draft.get("input_material") if isinstance(draft.get("input_material"), dict) else {}
    try:
        kind = InputMaterialKind(str(material_raw.get("kind") or constraints.input_material_kind.value))
    except ValueError:
        kind = constraints.input_material_kind
    blocks_raw = material_raw.get("body_blocks") or []
    blocks: list[BodyBlock] = []
    for i, b in enumerate(blocks_raw):
        if not isinstance(b, dict):
            continue
        try:
            bkind = BodyBlockKind(str(b.get("kind") or "paragraph"))
        except ValueError:
            bkind = BodyBlockKind.other
        blocks.append(
            BodyBlock(
                kind=bkind,
                text=str(b.get("text") or ""),
                block_ref=str(b.get("block_ref") or f"b{i}"),
                speaker=str(b.get("speaker") or ""),
            )
        )
    teaching_raw = draft.get("teaching_blocks_authored") or []
    teaching = [
        AuthoredTeachingBlock.from_dict(b) for b in teaching_raw if isinstance(b, dict)
    ]
    spine_raw = draft.get("story_spine")
    if not isinstance(spine_raw, dict):
        spine_raw = draft.get("educational_case") if isinstance(draft.get("educational_case"), dict) else None
    return EducationalPackage(
        package_id=str(draft.get("package_id") or ""),
        schema_version=ELP_SCHEMA_VERSION,
        author_version=ELP_AUTHOR_VERSION,
        author_provider=str(draft.get("author_provider") or "pending"),
        constraints_fingerprint="",
        content_fingerprint="",
        blueprint_hash=constraints.blueprint_hash,
        mission_id=constraints.mission_id,
        status=PackageLifecycleStatus.draft,
        input_material=InputMaterial(
            kind=kind,
            title=str(material_raw.get("title") or ""),
            body_blocks=blocks,
            media_refs=[str(m) for m in (material_raw.get("media_refs") or [])]
            if isinstance(material_raw.get("media_refs"), list)
            else [],
            cefr_check_echo=str(material_raw.get("cefr_check_echo") or ""),
        ),
        story_spine=StorySpine.from_dict(spine_raw),
        vocabulary_in_context=VocabularyInContext.from_dict(
            draft.get("vocabulary_in_context")  # type: ignore[arg-type]
        ),
        teaching_blocks_authored=teaching,
        discussion=DiscussionFlow.from_dict(
            draft.get("discussion") if isinstance(draft.get("discussion"), dict) else None
        ),
        mini_practice=MiniPractice.from_dict(
            draft.get("mini_practice") if isinstance(draft.get("mini_practice"), dict) else None
        ),
        reflection=ReflectionSection.from_dict(
            draft.get("reflection") if isinstance(draft.get("reflection"), dict) else None
        ),
        teacher_notes=dict(draft.get("teacher_notes") or {})
        if isinstance(draft.get("teacher_notes"), dict)
        else {},
        metadata=dict(draft.get("metadata") or {}) if isinstance(draft.get("metadata"), dict) else {},
        progression_metadata={},
    )


def process_package_generation(
    constraints: PackageConstraints,
    raw_author_response: str,
    *,
    author_provider: str,
    attempt_repair: bool = True,
    generation_duration_ms: int = 0,
) -> PackageGenerationResult:
    """Run E1 pipeline on author output. No LLM call here."""
    normalization = normalize_author_response(raw_author_response)
    if not normalization.success or normalization.draft is None:
        audit = {
            "outcome": GenerationOutcome.hard_failure.value,
            "author_provider": author_provider,
            "normalization_errors": list(normalization.errors),
            "generation_duration_ms": generation_duration_ms,
            "package_id": None,
        }
        return PackageGenerationResult(
            success=False,
            outcome=GenerationOutcome.hard_failure,
            package=None,
            constraints=constraints,
            normalization=normalization,
            validation=None,
            repair=None,
            audit=audit,
        )

    package = _draft_to_package(normalization.draft, constraints)
    validation = validate_package_draft(package, constraints)
    repair: RepairResult | None = None

    if attempt_repair and (not validation.passed or validation.warning_count > 0):
        package, repair = repair_package(package, constraints, validation)
        validation = validate_package_draft(package, constraints)

    if not validation.passed:
        package.status = PackageLifecycleStatus.rejected
        audit = {
            "outcome": GenerationOutcome.hard_failure.value,
            "author_provider": author_provider,
            "validation": validation_to_dict(validation),
            "repair_actions": list(repair.actions) if repair else [],
            "generation_duration_ms": generation_duration_ms,
            "package_id": None,
        }
        return PackageGenerationResult(
            success=False,
            outcome=GenerationOutcome.hard_failure,
            package=package,
            constraints=constraints,
            normalization=normalization,
            validation=validation,
            repair=repair,
            audit=audit,
        )

    frozen = freeze_package(
        package,
        constraints,
        author_provider=author_provider,
        package_id=package.package_id or f"elp_{uuid4().hex}",
    )
    outcome = (
        GenerationOutcome.soft_failure
        if repair and repair.repaired
        else GenerationOutcome.success
    )
    audit = {
        "outcome": outcome.value,
        "author_provider": author_provider,
        "validation": validation_to_dict(validation),
        "repair_actions": list(repair.actions) if repair else [],
        "generation_duration_ms": generation_duration_ms,
        "package_id": frozen.package_id,
        "constraints_fingerprint": frozen.constraints_fingerprint,
        "content_fingerprint": frozen.content_fingerprint,
        "schema_version": frozen.schema_version,
        "author_version": frozen.author_version,
    }
    return PackageGenerationResult(
        success=True,
        outcome=outcome,
        package=frozen,
        constraints=constraints,
        normalization=normalization,
        validation=validation,
        repair=repair,
        audit=audit,
    )
