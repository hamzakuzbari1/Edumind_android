from sqlalchemy.dialects import postgresql
from types import SimpleNamespace

from app.services.language_educational_package.fingerprint import (
    compute_constraints_fingerprint,
)
from app.services.language_speaking_educational_package.constraint_builder import (
    build_speaking_package_constraints,
)
from app.services.language_speaking_educational_package.persistence import _student_owner_clause
from app.services.language_speaking_lesson_runtime.engine import (
    _clear_stale_package_runtime_references,
    _current_runtime_authoring_day,
    _package_matches_current_runtime_context,
)
from app.services.language_speaking_lesson_runtime.storage import SPEAKING_LESSON_RUNTIME_KEY
from app.services.language_speaking_runtime_api.journey_constraints import _daily_story_seed


def _compiled_sql(expr) -> str:
    return str(
        expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_speaking_package_owner_clause_supports_legacy_json_owner_rows() -> None:
    sql = _compiled_sql(_student_owner_clause(123))

    assert "language_content_items.student_id = 123" in sql
    assert "language_content_items.student_id IS NULL" in sql
    assert "owner_student_id" in sql
    assert "'123'" in sql


def _speaking_constraints_payload(*, day: str, seed: str) -> dict:
    return {
        "skill": "speaking",
        "official_cefr": "B1",
        "learning_stage": 7,
        "mission_id": "mission_speaking_rate",
        "mission_kind": "teaching",
        "execution_mode": "study",
        "evidence_intent": "formative",
        "blueprint_id": "bp_speaking_rate",
        "blueprint_hash": "blueprint_hash",
        "learning_focus": "Speaking at an appropriate rate",
        "objectives": ["Speak clearly so another person can follow the story."],
        "vocabulary_ids": ["v_slow_down"],
        "vocabulary_surface_forms": ["slow down"],
        "grammar_topic_ids": ["gram_be_present"],
        "teaching_block_specs": [
            {
                "block_id": "tb_focus",
                "kind": "explanation",
                "target_skill_ids": ["speaking_rate"],
                "max_len": 220,
            }
        ],
        "weak_skill_labels": ["Speaking rate"],
        "difficulty": "standard",
        "scenario_type": "everyday",
        "input_material_kind": "story",
        "lesson_length_band": "standard",
        "evidence_slot_plan": [],
        "character_hints": ["Sam", "Lee"],
        "authoring_day": day,
        "daily_story_key": f"speaking:mission_speaking_rate:{day}:{seed[:12]}",
        "daily_story_seed": seed,
    }


def test_daily_story_fields_are_preserved_in_package_constraints() -> None:
    constraints = build_speaking_package_constraints(
        _speaking_constraints_payload(day="2026-07-24", seed="abc123")
    )

    assert constraints.authoring_day == "2026-07-24"
    assert constraints.daily_story_key == "speaking:mission_speaking_rate:2026-07-24:abc123"
    assert constraints.daily_story_seed == "abc123"
    assert constraints.to_dict()["daily_story_seed"] == "abc123"


def test_daily_story_key_changes_constraints_fingerprint() -> None:
    today = build_speaking_package_constraints(
        _speaking_constraints_payload(day="2026-07-24", seed="abc123")
    )
    tomorrow = build_speaking_package_constraints(
        _speaking_constraints_payload(day="2026-07-25", seed="def456")
    )

    assert compute_constraints_fingerprint(today) != compute_constraints_fingerprint(tomorrow)


def test_daily_story_seed_changes_with_level_and_progression_stage() -> None:
    base = {
        "student_id": 42,
        "language_id": 1,
        "mission_id": "mission_speaking_rate",
        "blueprint_hash": "blueprint_hash",
        "authoring_day": "2026-07-24",
    }

    a2_stage = _daily_story_seed(official_cefr="A2", learning_stage=3, **base)
    b1_stage = _daily_story_seed(official_cefr="B1", learning_stage=7, **base)

    assert a2_stage != b1_stage


def test_stale_a1_package_does_not_match_b2_speaking_runtime_context() -> None:
    row = SimpleNamespace(official_speaking_cefr="B2")

    assert _package_matches_current_runtime_context(
        row,
        {
            "official_cefr": "A1",
            "authoring_day": _current_runtime_authoring_day(),
            "daily_story_key": "speaking:old",
        },
    ) is False


def test_package_without_daily_story_key_is_stale_for_runtime_context() -> None:
    row = SimpleNamespace(official_speaking_cefr="B2")

    assert _package_matches_current_runtime_context(
        row,
        {
            "official_cefr": "B2",
            "authoring_day": _current_runtime_authoring_day(),
            "daily_story_key": "",
        },
    ) is False


def test_clearing_stale_package_removes_runtime_and_index_references() -> None:
    payload = {
        SPEAKING_LESSON_RUNTIME_KEY: {"package_id": "elp_old"},
        "speaking_educational_packages": {
            "order": ["elp_keep", "elp_old"],
            "by_package_id": {"elp_old": 1, "elp_keep": 2},
            "by_fingerprint": {"fp_old": "elp_old", "fp_keep": "elp_keep"},
            "active_by_mission": {"mission_old": "elp_old", "mission_keep": "elp_keep"},
        },
    }

    cleaned = _clear_stale_package_runtime_references(
        payload,
        package_id="elp_old",
        constraints_fingerprint="fp_old",
        mission_id="mission_old",
    )

    index = cleaned["speaking_educational_packages"]
    assert SPEAKING_LESSON_RUNTIME_KEY not in cleaned
    assert index["order"] == ["elp_keep"]
    assert index["by_package_id"] == {"elp_keep": 2}
    assert index["by_fingerprint"] == {"fp_keep": "elp_keep"}
    assert index["active_by_mission"] == {"mission_keep": "elp_keep"}
