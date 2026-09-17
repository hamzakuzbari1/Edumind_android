"""E1 author orchestration: cache -> Claude (or template) -> pipeline -> persist."""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.progression import LanguageProgression
from app.services.language_educational_package.fingerprint import compute_constraints_fingerprint
from app.services.language_educational_package.pipeline import (
    GenerationOutcome,
    process_package_generation,
)
from app.services.language_speaking_educational_package.claude_author import (
    AUTHOR_PROVIDER_CLAUDE,
    ClaudeAuthorResult,
    author_package_json_claude,
)
from app.services.language_speaking_educational_package.constraint_builder import (
    build_speaking_package_constraints,
)
from app.services.language_speaking_educational_package.persistence import (
    audit_from_item,
    constraints_from_item,
    find_cached_package_item,
    package_from_item,
    persist_frozen_package,
)
from app.services.language_speaking_educational_package.storage_index import record_package_in_index
from app.services.language_speaking_educational_package.template_author import (
    AUTHOR_PROVIDER_TEMPLATE,
    author_package_json_template,
)
from app.services.language_speaking_educational_package.types import (
    SPEAKING_ELP_TYPES_VERSION,
    SpeakingLearningPackageGenerateResult,
)

logger = logging.getLogger(__name__)

SPEAKING_ELP_VERSION = SPEAKING_ELP_TYPES_VERSION

AuthorMode = Literal["claude", "template", "auto"]


async def _lock_progression_row(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> LanguageProgression | None:
    result = await db.execute(
        select(LanguageProgression)
        .where(
            LanguageProgression.student_id == student_id,
            LanguageProgression.language_id == language_id,
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def _record_progression_after_generate(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    constraints: Any,
    locked_row: LanguageProgression | None = None,
) -> None:
    """Advance Curriculum Graph ledger after a package is generated."""
    try:
        from app.services.language_speaking_curriculum_engine.progression_catalog import (
            PROGRESSION_NODES,
        )
        from app.services.language_speaking_curriculum_engine.progression_memory import (
            merge_progression_ledger_into_payload,
            progression_ledger_from_payload,
            record_progression_exposure,
        )
        from app.services.language_speaking_curriculum_engine.progression_types import (
            ProgressionDecision,
        )

        prog = getattr(constraints, "curriculum_progression", None) or {}
        node_id = str(
            getattr(constraints, "progression_node_id", "")
            or prog.get("micro_skill_id")
            or ""
        )
        case_id = str(
            getattr(constraints, "progression_case_id", "")
            or prog.get("case_variant_id")
            or ""
        )
        if not node_id or node_id not in PROGRESSION_NODES:
            return
        node = PROGRESSION_NODES[node_id]
        variant = next((c for c in node.case_variants if c.case_id == case_id), None)
        if variant is None and node.case_variants:
            variant = node.case_variants[0]
        if variant is None:
            return
        decision = ProgressionDecision(
            action=str(getattr(constraints, "progression_action", "") or prog.get("action") or "enter"),
            node=node,
            case_variant=variant,
            previous_node_id=str(prog.get("previous_node_id") or ""),
            prerequisites_met=bool(prog.get("prerequisites_met", True)),
            estimated_mastery=float(prog.get("estimated_mastery") or 0.0),
            path_index=int(prog.get("path_index") or 0),
            path_length=int(prog.get("path_length") or 0),
            reason=str(prog.get("reason") or ""),
        )
        row = locked_row or await _lock_progression_row(
            db, student_id=student_id, language_id=language_id
        )
        if row is None:
            return
        payload = dict(row.promotion_readiness_json or {})
        ledger = progression_ledger_from_payload(payload)
        record_progression_exposure(ledger, decision)
        row.promotion_readiness_json = merge_progression_ledger_into_payload(payload, ledger)
        if getattr(type(row), "__mapper__", None) is not None:
            flag_modified(row, "promotion_readiness_json")
    except Exception as exc:  # noqa: BLE001
        logger.warning("progression ledger record skipped: %s", exc)


async def _record_case_memory_after_generate(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package: Any,
    constraints: Any,
    locked_row: LanguageProgression | None = None,
) -> None:
    """Track completed Educational Case experience for longitudinal diversity."""
    try:
        from app.services.language_speaking_case_personalization import (
            case_memory_from_payload,
            merge_case_memory_into_payload,
            record_completed_case,
        )

        row = locked_row or await _lock_progression_row(
            db, student_id=student_id, language_id=language_id
        )
        if row is None:
            return
        payload = dict(row.promotion_readiness_json or {})
        ledger = case_memory_from_payload(payload)
        perso = getattr(constraints, "personalization", None) or {}
        complexity = getattr(constraints, "story_complexity_policy", None) or {}
        spine = package.story_spine
        record_completed_case(
            ledger,
            title=spine.title,
            setting=spine.setting or constraints.scenario_type,
            theme_key=str(perso.get("theme_key") or ""),
            case_category=spine.case_category or constraints.case_category,
            case_archetype=spine.case_archetype or constraints.case_archetype,
            emotional_theme=str(perso.get("emotional_framing") or ""),
            decision_pattern=str(complexity.get("decision_complexity") or ""),
            stakeholders=list(spine.stakeholders),
            vocabulary_world=str(constraints.scenario_type or ""),
        )
        row.promotion_readiness_json = merge_case_memory_into_payload(payload, ledger)
        if getattr(type(row), "__mapper__", None) is not None:
            flag_modified(row, "promotion_readiness_json")
    except Exception as exc:  # noqa: BLE001
        logger.warning("case memory record skipped: %s", exc)


async def sync_package_into_elp_index(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package_id: str,
    constraints_fingerprint: str,
    mission_id: str,
    content_item_id: int,
    locked_row: LanguageProgression | None = None,
) -> None:
    """Write the runtime ELP index for a reusable frozen package.

    Cache hits and new generation share this path so cache never changes
    runtime semantics. Idempotent for the same package_id (no duplicate order).
    """
    row = locked_row
    if row is None:
        row = await _lock_progression_row(
            db, student_id=student_id, language_id=language_id
        )
    if row is None:
        return
    payload = dict(row.promotion_readiness_json or {})
    payload = record_package_in_index(
        payload,
        package_id=package_id,
        constraints_fingerprint=constraints_fingerprint,
        mission_id=mission_id,
        content_item_id=content_item_id,
    )
    row.promotion_readiness_json = payload
    # Only ORM instances need SQLAlchemy mutation tracking.
    if getattr(type(row), "__mapper__", None) is not None:
        flag_modified(row, "promotion_readiness_json")


async def generate_speaking_learning_package(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    constraints_payload: dict[str, Any],
    author_mode: AuthorMode = "auto",
    use_cache: bool = True,
    locked_row: LanguageProgression | None = None,
) -> SpeakingLearningPackageGenerateResult:
    """Generate and persist a frozen Learning Package (E1).

    Wave C/D: grammar_id from Target Resolver only. Fail closed if resolver empty.
    """
    from app.services.language_grammar.enums import GrammarEvidenceSourceSkill
    from app.services.language_grammar_integrity import (
        GrammarIntegrityError,
        issue_and_stamp_for_context,
    )
    from app.services.language_grammar_skill_context import (
        build_skill_grammar_context,
        stamp_constraints_payload,
    )

    grammar_ctx = await build_skill_grammar_context(
        db,
        student_id=student_id,
        language_id=language_id,
        source_skill=GrammarEvidenceSourceSkill.speaking,
    )
    payload = dict(constraints_payload)
    # Wave D: reject client/pack forged grammar before fail-closed check.
    claimed = payload.get("grammar_id") or payload.get("claimed_grammar_id")
    if isinstance(claimed, str) and claimed.strip():
        if grammar_ctx is None or claimed.strip().lower() != grammar_ctx.grammar_id:
            raise ValueError("forged_speaking_grammar: client/pack grammar_id rejected")
    if grammar_ctx is None:
        return SpeakingLearningPackageGenerateResult(
            success=False,
            outcome=GenerationOutcome.hard_failure,
            package=None,
            content_item_id=None,
            audit={"error": "resolver_empty_fail_closed"},
            cached=False,
            reason="resolver_empty_fail_closed",
        )
    payload = stamp_constraints_payload(payload, grammar_ctx)
    try:
        activity_session = await issue_and_stamp_for_context(
            db,
            student_id=student_id,
            language_id=language_id,
            grammar_ctx=grammar_ctx,
            skill=GrammarEvidenceSourceSkill.speaking,
            activity_type="speaking",
            lesson_id=str(payload.get("mission_id") or ""),
            server_payload={"constraints_grammar_id": grammar_ctx.grammar_id},
        )
        payload["activity_session_id"] = str(activity_session.id)
        payload["grammar_stamp_token"] = activity_session.stamp_token
    except GrammarIntegrityError as exc:
        return SpeakingLearningPackageGenerateResult(
            success=False,
            outcome=GenerationOutcome.hard_failure,
            package=None,
            content_item_id=None,
            audit={"error": exc.code, "message": exc.message},
            cached=False,
            reason=f"integrity:{exc.code}",
        )
    # M8 — apply personalization after Curriculum enrichment unless already present
    if not isinstance(payload.get("personalization"), dict):
        try:
            from app.services.language_speaking_case_personalization import (
                apply_case_personalization,
                collect_case_personalization_signals,
            )

            row_for_signals = locked_row
            promo = (
                dict(row_for_signals.promotion_readiness_json or {})
                if row_for_signals is not None
                else None
            )
            signals = await collect_case_personalization_signals(
                db,
                student_id=student_id,
                language_id=language_id,
                promotion_readiness_json=promo,
                locale=str(payload.get("locale") or "en"),
            )
            payload = apply_case_personalization(payload, signals)
        except Exception as exc:  # noqa: BLE001 — never block generation on personalization
            logger.warning("case personalization skipped: %s", exc)

    constraints = build_speaking_package_constraints(payload)
    fp = compute_constraints_fingerprint(constraints)

    if use_cache:
        cached = await find_cached_package_item(
            db,
            student_id=student_id,
            language_id=language_id,
            constraints_fingerprint=fp,
        )
        if cached is not None:
            pkg = package_from_item(cached)
            if pkg is not None and pkg.status.value == "frozen":
                # Cache is optimization only — runtime index must still reflect
                # the reusable package (same semantics as a fresh generate).
                await sync_package_into_elp_index(
                    db,
                    student_id=student_id,
                    language_id=language_id,
                    package_id=pkg.package_id,
                    constraints_fingerprint=pkg.constraints_fingerprint,
                    mission_id=constraints.mission_id,
                    content_item_id=cached.id,
                    locked_row=locked_row,
                )
                return SpeakingLearningPackageGenerateResult(
                    success=True,
                    outcome=GenerationOutcome.success,
                    package=pkg,
                    content_item_id=cached.id,
                    audit=audit_from_item(cached),
                    cached=True,
                    reason="cache_hit",
                )

    started = time.perf_counter()
    mode = author_mode
    if mode == "auto":
        mode = "claude"

    author_meta: dict[str, Any] = {}
    if mode == "claude":
        try:
            # Claude authoring can take a while. Commit the already prepared
            # grammar/session state first so we do not hold a database
            # connection or row lock during the outbound provider wait.
            await db.commit()
            locked_row = None
            authored: ClaudeAuthorResult = await author_package_json_claude(constraints)
            raw = authored.text
            provider = AUTHOR_PROVIDER_CLAUDE
            author_meta = authored.to_metadata_dict()
        except Exception as exc:  # noqa: BLE001
            logger.warning("ELP Claude author failed; falling back to template: %s", exc)
            raw = author_package_json_template(constraints)
            provider = AUTHOR_PROVIDER_TEMPLATE
            author_meta = {"provider": AUTHOR_PROVIDER_TEMPLATE}
    else:
        raw = author_package_json_template(constraints)
        provider = AUTHOR_PROVIDER_TEMPLATE
        author_meta = {"provider": AUTHOR_PROVIDER_TEMPLATE}

    if author_meta.get("stop_reason") == "max_tokens":
        duration_ms = int((time.perf_counter() - started) * 1000)
        return SpeakingLearningPackageGenerateResult(
            success=False,
            outcome=GenerationOutcome.hard_failure,
            package=None,
            content_item_id=None,
            audit={
                "outcome": GenerationOutcome.hard_failure.value,
                "reason": "author_truncated",
                "generation_duration_ms": duration_ms,
                "package_id": None,
                **author_meta,
            },
            cached=False,
            reason="author_truncated",
        )

    duration_ms = int((time.perf_counter() - started) * 1000)
    pipeline = process_package_generation(
        constraints,
        raw,
        author_provider=provider,
        attempt_repair=True,
        generation_duration_ms=duration_ms,
    )
    # M6: if Claude package still fails validation after repair, regenerate via template
    if (not pipeline.success) and provider == AUTHOR_PROVIDER_CLAUDE:
        logger.warning(
            "ELP package failed validation after Claude+repair; regenerating via template mission=%s",
            constraints.mission_id,
        )
        raw = author_package_json_template(constraints)
        provider = AUTHOR_PROVIDER_TEMPLATE
        author_meta = {
            **author_meta,
            "regenerated_via": AUTHOR_PROVIDER_TEMPLATE,
            "prior_provider": AUTHOR_PROVIDER_CLAUDE,
        }
        duration_ms = int((time.perf_counter() - started) * 1000)
        pipeline = process_package_generation(
            constraints,
            raw,
            author_provider=provider,
            attempt_repair=True,
            generation_duration_ms=duration_ms,
        )
    audit = {**(pipeline.audit or {}), **author_meta}

    if not pipeline.success or pipeline.package is None:
        return SpeakingLearningPackageGenerateResult(
            success=False,
            outcome=pipeline.outcome,
            package=pipeline.package,
            content_item_id=None,
            audit=audit,
            cached=False,
            reason="generation_failed",
        )

    item = await persist_frozen_package(
        db,
        student_id=student_id,
        language_id=language_id,
        package=pipeline.package,
        constraints=constraints,
        audit=audit,
    )

    await sync_package_into_elp_index(
        db,
        student_id=student_id,
        language_id=language_id,
        package_id=pipeline.package.package_id,
        constraints_fingerprint=pipeline.package.constraints_fingerprint,
        mission_id=constraints.mission_id,
        content_item_id=item.id,
        locked_row=locked_row,
    )
    await _record_case_memory_after_generate(
        db,
        student_id=student_id,
        language_id=language_id,
        package=pipeline.package,
        constraints=constraints,
        locked_row=locked_row,
    )
    await _record_progression_after_generate(
        db,
        student_id=student_id,
        language_id=language_id,
        constraints=constraints,
        locked_row=locked_row,
    )

    return SpeakingLearningPackageGenerateResult(
        success=True,
        outcome=pipeline.outcome,
        package=pipeline.package,
        content_item_id=item.id,
        audit=audit,
        cached=False,
        reason="generated",
    )


__all__ = [
    "SPEAKING_ELP_VERSION",
    "generate_speaking_learning_package",
    "sync_package_into_elp_index",
    "build_speaking_package_constraints",
    "constraints_from_item",
]
