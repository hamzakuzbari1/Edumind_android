"""Ensure frozen package + open lesson for Start Learning (integration only)."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.services.language_educational_package.types import EducationalPackage
from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking_educational_package.author_pipeline import (
    sync_package_into_elp_index,
)
from app.services.language_speaking_educational_package.persistence import (
    get_package_item_by_id,
    package_from_item,
)
from app.services.language_speaking_educational_package_api.service import (
    SpeakingLearningPackageApiError,
    create_speaking_learning_package_api,
)
from app.services.language_speaking_journey.api_service import (
    get_speaking_journey,
    start_speaking_session,
)
from app.services.language_speaking_knowledge_model.storage import (
    SPEAKING_BUCKET_KEY,
    speaking_bucket_from_payload,
)
from app.services.language_speaking_lesson_planner.planner import continue_alex_from_story_spine
from app.services.language_speaking_lesson_planner.storage import load_s9_state, save_s9_state
from app.services.language_speaking_lesson_planner.types import SpeakingLessonBlueprint
from app.services.language_speaking_lesson_runtime_api.service import (
    LessonRuntimeApiError,
    open_lesson_runtime_api,
)
from app.services.language_speaking_runtime_api.journey_constraints import (
    build_constraints_payload_from_journey,
)


class RuntimeIntegrationError(Exception):
    def __init__(self, status_code: int, detail: Any, code: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail if isinstance(detail, str) else str(detail))


@dataclass(slots=True)
class EnsurePackageResult:
    reused: bool
    package_id: str
    content_item_id: int | None
    status: str
    cached: bool
    package: dict[str, Any]
    constraints_fingerprint: str
    content_fingerprint: str


def _bind_alex_to_educational_case(
    *,
    row: Any,
    blueprint: SpeakingLessonBlueprint | None,
    package: EducationalPackage,
) -> SpeakingLessonBlueprint | None:
    """Project authored Educational Case spine onto Alex so he continues the same world."""
    if blueprint is None or not package.story_spine.is_substantive():
        return blueprint
    spine = package.story_spine
    new_alex = continue_alex_from_story_spine(
        blueprint.alex_context,
        title=spine.title,
        setting=spine.setting,
        characters=[c.name for c in spine.characters],
        conflict=spine.conflict,
        continuation_hook=spine.continuation_hook,
        case_category=spine.case_category,
        case_archetype=spine.case_archetype,
        stakeholders=list(spine.stakeholders),
        decision_point=spine.decision_point,
    )
    # Soft experience notes from Personalization Engine (same case; no new world)
    perso = (package.metadata or {}).get("personalization") or {}
    notes = [str(n) for n in (perso.get("alex_notes") or []) if str(n).strip()]
    if notes:
        extra = " ".join(notes[:3])
        scenario = f"{new_alex.communicative_scenario} {extra}".strip()
        new_alex = dataclasses.replace(new_alex, communicative_scenario=scenario)
    new_bp = dataclasses.replace(blueprint, alex_context=new_alex)
    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    bucket = save_s9_state(
        bucket,
        plan=state.plan,
        blueprint=new_bp,
        session=state.session,
        attempt_lineage=state.attempt_lineage,
    )
    payload[SPEAKING_BUCKET_KEY] = bucket
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    return new_bp


async def ensure_learning_package_for_journey(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    author_mode: str = "auto",
    use_cache: bool = True,
) -> EnsurePackageResult:
    """Reuse active frozen package for the current mission, else generate via E1.

    On every successful path the ELP runtime index is synchronized so Open Latest
    / resume never depend on whether the package was generated or cache-hit.
    """
    await get_speaking_journey(db, student_id=student_id, language_id=language_id)
    row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        raise RuntimeIntegrationError(404, "Progression not found.", "no_progression")

    payload = dict(row.promotion_readiness_json or {})
    bucket = speaking_bucket_from_payload(payload)
    state = load_s9_state(bucket)
    blueprint = state.blueprint
    if blueprint is None:
        raise RuntimeIntegrationError(
            409,
            "No speaking blueprint available to build a Learning Package.",
            "no_blueprint",
        )

    constraints = build_constraints_payload_from_journey(
        row=row, blueprint=blueprint, session=state.session
    )
    mission_id = str(constraints.get("mission_id") or "")

    # Reuse only through the full constraints fingerprint after grammar/date stamping.
    reusable_id = None
    if reusable_id:
        item = await get_package_item_by_id(
            db, student_id=student_id, language_id=language_id, package_id=reusable_id
        )
        pkg = package_from_item(item) if item is not None else None
        # M5: expire dialogue-default / pre–Educational Case packages so story-first regenerates
        if pkg is not None and (
            pkg.input_material.kind.value == "dialogue"
            or not str(pkg.schema_version or "").startswith("2.")
            or not pkg.story_spine.is_substantive()
        ):
            pkg = None
        if pkg is not None and pkg.status == PackageLifecycleStatus.frozen:
            _bind_alex_to_educational_case(row=row, blueprint=blueprint, package=pkg)
            result = EnsurePackageResult(
                reused=True,
                package_id=pkg.package_id,
                content_item_id=item.id if item else None,
                status=pkg.status.value,
                cached=True,
                package=project_package_for_student(pkg),
                constraints_fingerprint=pkg.constraints_fingerprint,
                content_fingerprint=pkg.content_fingerprint,
            )
            if result.content_item_id is not None:
                await sync_package_into_elp_index(
                    db,
                    student_id=student_id,
                    language_id=language_id,
                    package_id=result.package_id,
                    constraints_fingerprint=result.constraints_fingerprint,
                    mission_id=mission_id,
                    content_item_id=int(result.content_item_id),
                    locked_row=row,
                )
            await db.flush()
            return result

    try:
        created = await create_speaking_learning_package_api(
            db,
            student_id=student_id,
            language_id=language_id,
            constraints=constraints,
            author_mode=author_mode,  # type: ignore[arg-type]
            use_cache=use_cache,
        )
    except SpeakingLearningPackageApiError as exc:
        code = (
            "author_truncated"
            if isinstance(exc.detail, dict) and exc.detail.get("reason") == "author_truncated"
            else "package_failed"
        )
        raise RuntimeIntegrationError(exc.status_code, exc.detail, code) from exc

    if not created.success or not created.package_id:
        raise RuntimeIntegrationError(422, "Learning package generation failed.", "package_failed")

    if created.package_id:
        item = await get_package_item_by_id(
            db,
            student_id=student_id,
            language_id=language_id,
            package_id=str(created.package_id),
        )
        typed = package_from_item(item) if item is not None else None
        if typed is not None:
            _bind_alex_to_educational_case(row=row, blueprint=blueprint, package=typed)

    result = EnsurePackageResult(
        reused=bool(created.cached),
        package_id=str(created.package_id),
        content_item_id=created.content_item_id,
        status=str(created.status or "frozen"),
        cached=bool(created.cached),
        package=created.package or {},
        constraints_fingerprint=str(created.constraints_fingerprint or ""),
        content_fingerprint=str(created.content_fingerprint or ""),
    )
    if result.content_item_id is not None:
        await sync_package_into_elp_index(
            db,
            student_id=student_id,
            language_id=language_id,
            package_id=result.package_id,
            constraints_fingerprint=result.constraints_fingerprint,
            mission_id=mission_id,
            content_item_id=int(result.content_item_id),
            locked_row=row,
        )
    await db.flush()
    return result


async def start_learning_runtime(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    author_mode: str = "auto",
    use_cache: bool = True,
    force_restart_lesson: bool = False,
) -> dict[str, Any]:
    """Start Learning: journey session → ensure package → open lesson."""
    await get_speaking_journey(db, student_id=student_id, language_id=language_id)
    try:
        session_payload = await start_speaking_session(
            db, student_id=student_id, language_id=language_id
        )
    except ValueError as exc:
        raise RuntimeIntegrationError(409, str(exc), "session_failed") from exc

    ensured = await ensure_learning_package_for_journey(
        db,
        student_id=student_id,
        language_id=language_id,
        author_mode=author_mode,
        use_cache=use_cache,
    )

    try:
        lesson = await open_lesson_runtime_api(
            db,
            student_id=student_id,
            language_id=language_id,
            package_id=ensured.package_id,
            force_restart=force_restart_lesson,
        )
    except LessonRuntimeApiError as exc:
        raise RuntimeIntegrationError(exc.status_code, exc.detail, "lesson_open_failed") from exc

    lesson_dict = lesson.model_dump() if hasattr(lesson, "model_dump") else dict(lesson)
    return {
        "success": True,
        "session": session_payload,
        "package": {
            "reused": ensured.reused,
            "cached": ensured.cached,
            "package_id": ensured.package_id,
            "content_item_id": ensured.content_item_id,
            "status": ensured.status,
            "constraints_fingerprint": ensured.constraints_fingerprint,
            "content_fingerprint": ensured.content_fingerprint,
            "package": ensured.package,
        },
        "lesson": lesson_dict,
    }
