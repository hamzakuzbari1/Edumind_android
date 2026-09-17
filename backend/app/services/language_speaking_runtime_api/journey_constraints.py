"""Map active journey blueprint → E1 constraints payload (API layer only)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.models.language.progression import LanguageProgression
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_curriculum_engine import enrich_speaking_constraints_payload
from app.services.language_speaking_curriculum_engine.educational_world import (
    build_educational_world,
    sanitize_educational_text,
    sanitize_objective_list,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import (
    resolve_current_task,
)
from app.services.language_speaking_lesson_planner.types import (
    SpeakingLearningSession,
    SpeakingLessonBlueprint,
)


def _official_cefr(row: LanguageProgression) -> str:
    val = row.official_speaking_cefr
    return (val.value if hasattr(val, "value") else str(val or "A2")).upper()


def _current_authoring_day() -> str:
    try:
        return datetime.now(ZoneInfo("Asia/Damascus")).date().isoformat()
    except Exception:  # noqa: BLE001 - local timezone data may be unavailable in CI
        return datetime.now(timezone.utc).date().isoformat()


def _daily_story_seed(
    *,
    student_id: int,
    language_id: int,
    mission_id: str,
    official_cefr: str,
    learning_stage: int,
    blueprint_hash: str,
    authoring_day: str,
) -> str:
    blob = "|".join(
        (
            str(student_id),
            str(language_id),
            mission_id,
            official_cefr.upper(),
            str(learning_stage),
            blueprint_hash,
            authoring_day,
        )
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _mission_for_blueprint(
    blueprint: SpeakingLessonBlueprint,
    session: SpeakingLearningSession | None,
):
    if session is not None:
        resolution = resolve_current_task(blueprint, session)
        if resolution.mission_id:
            for mission in blueprint.educational_missions:
                if mission.mission_id == resolution.mission_id:
                    return mission, resolution
    if blueprint.educational_missions:
        mission = blueprint.educational_missions[0]
        return mission, None
    return None, None


def build_constraints_payload_from_journey(
    *,
    row: LanguageProgression,
    blueprint: SpeakingLessonBlueprint,
    session: SpeakingLearningSession | None = None,
    personalization_signals: dict[str, Any] | Any | None = None,
) -> dict[str, Any]:
    """Backend-owned constraint dict for E1 — FE must not invent this payload.

    Curriculum Engine V2 enriches vocabulary, grammar targets, CEFR story complexity,
    density, and recycling before Claude authors. Optional personalization_signals
    then adapt experience fields only (never curriculum ownership).
    """
    mission, resolution = _mission_for_blueprint(blueprint, session)
    primary = blueprint.primary_target_skill_id
    node = SPEAKING_SKILL_GRAPH.node_by_id(primary)
    label = node.label if node else primary.replace("_", " ")
    world = build_educational_world(
        skill_ids=list(blueprint.target_skill_ids or ()) + ([primary] if primary else []),
        skill_label=label,
    )
    # Ownership: learning_focus is the educational topic (skill), never Alex / mission marketing.
    learning_focus = world["learning_focus"]

    if mission is not None:
        mission_id = mission.mission_id
        mission_kind = mission.mission_kind.value
        execution_mode = mission.execution_mode.value
        evidence_intent = mission.evidence_intent.value
        objectives = [
            o.student_objective_text
            for o in mission.objectives
            if getattr(o, "student_objective_text", None)
        ]
        if not objectives:
            objectives = [f"Use {learning_focus} clearly when you speak."]
        teaching_specs = [
            {
                "block_id": b.block_id,
                "kind": b.kind.value if hasattr(b.kind, "value") else str(b.kind),
                "target_skill_ids": list(b.target_skill_ids),
                "max_len": 220,
            }
            for b in mission.teaching_blocks
        ]
        target_skills = list(mission.target_skill_ids) or list(blueprint.target_skill_ids)
        mini_task = ""
        if resolution and resolution.task_id:
            mini_task = resolution.task_id
        elif mission.tasks:
            mini_task = mission.tasks[0].task_id
    else:
        mission_id = f"mission_{blueprint.blueprint_id}"
        mission_kind = "guided_practice"
        execution_mode = "controlled_response"
        evidence_intent = "formative"
        objectives = [f"Practice {learning_focus}"]
        teaching_specs = [
            {
                "block_id": f"tb_{primary or 'focus'}",
                "kind": "explanation",
                "target_skill_ids": list(blueprint.target_skill_ids)[:3],
                "max_len": 220,
            }
        ]
        target_skills = list(blueprint.target_skill_ids)
        mini_task = f"task_{blueprint.blueprint_id}"

    if not teaching_specs:
        teaching_specs = [
            {
                "block_id": "tb_focus",
                "kind": "explanation",
                "target_skill_ids": list(target_skills)[:3],
                "max_len": 220,
            }
        ]

    objectives = sanitize_objective_list(list(objectives), focus=learning_focus)
    session_goal = sanitize_educational_text(
        blueprint.session_goal,
        fallback=f"Build confidence with {learning_focus}",
    )

    stage = int(getattr(row, "learning_stage_speaking", None) or 1)
    official_cefr = str(blueprint.official_cefr_hint or _official_cefr(row)).upper()
    authoring_day = _current_authoring_day()
    student_id = int(getattr(row, "student_id", 0) or 0)
    language_id = int(getattr(row, "language_id", 0) or 0)
    daily_seed = _daily_story_seed(
        student_id=student_id,
        language_id=language_id,
        mission_id=mission_id,
        official_cefr=official_cefr,
        learning_stage=max(1, stage),
        blueprint_hash=blueprint.blueprint_hash,
        authoring_day=authoring_day,
    )
    promo = dict(getattr(row, "promotion_readiness_json", None) or {})
    # Pass progression + case memory snapshots so Curriculum Graph can adapt
    from app.services.language_speaking_case_personalization.memory import (
        SPEAKING_CASE_MEMORY_KEY,
        case_memory_from_payload,
    )
    from app.services.language_speaking_curriculum_engine.progression_memory import (
        SPEAKING_PROGRESSION_KEY,
        progression_ledger_from_payload,
    )

    case_mem = case_memory_from_payload(promo)
    prog_ledger = progression_ledger_from_payload(promo)

    base = {
        "skill": "speaking",
        "official_cefr": official_cefr,
        "learning_stage": max(1, stage),
        "mission_id": mission_id,
        "mission_kind": mission_kind,
        "execution_mode": execution_mode,
        "evidence_intent": evidence_intent,
        "blueprint_id": blueprint.blueprint_id,
        "blueprint_hash": blueprint.blueprint_hash,
        "learning_focus": learning_focus,
        "objectives": objectives[:6],
        "target_skill_ids": list(target_skills)[:6],
        "grammar_topic_ids": [],
        "teaching_block_specs": teaching_specs,
        "weak_skill_labels": [label] if label else [],
        "scenario_type": world["scenario_type"],
        "story_world": world["story_world"],
        "communicative_goal": world["communicative_goal"],
        "character_hints": world["character_hints"],
        "story_title_hint": world["story_title_hint"],
        "authoring_day": authoring_day,
        "daily_story_key": f"speaking:{mission_id}:{authoring_day}:{daily_seed[:12]}",
        "daily_story_seed": daily_seed,
        "session_goal": session_goal,
        "input_material_kind": "story",
        "mini_practice_task_id": mini_task or f"task_{mission_id}",
        "locale": "en",
        "forbidden_behaviors": [
            "no_grammar_lecture",
            "no_promotion_talk",
            "no_cefr_claims",
            "no_invented_vocabulary_surfaces",
            "no_alex_mentions",
            "no_product_tutor_names",
        ],
        SPEAKING_PROGRESSION_KEY: prog_ledger.to_dict(),
        "speaking_progression_mastery": prog_ledger.to_dict(),
        "case_memory_snapshot": case_mem.to_dict(),
        SPEAKING_CASE_MEMORY_KEY: case_mem.to_dict(),
    }
    enriched = enrich_speaking_constraints_payload(base)
    if personalization_signals is None:
        return enriched
    from app.services.language_speaking_case_personalization import (
        apply_case_personalization,
    )

    return apply_case_personalization(enriched, personalization_signals)
