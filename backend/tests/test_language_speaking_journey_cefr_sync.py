from types import SimpleNamespace

from app.services.language_speaking_journey.api_service import (
    _blueprint_matches_official_cefr,
    _clear_stale_s9_state,
)
from app.services.language_speaking_lesson_planner.storage import (
    ACTIVE_BLUEPRINT_KEY,
    ATTEMPT_LINEAGE_KEY,
    LEARNING_PLAN_KEY,
    LEARNING_SESSION_KEY,
)


def test_stale_speaking_blueprint_is_detected_when_official_cefr_changes() -> None:
    assert _blueprint_matches_official_cefr(
        SimpleNamespace(official_cefr_hint="A1"),
        "B2",
    ) is False
    assert _blueprint_matches_official_cefr(
        SimpleNamespace(official_cefr_hint="B2"),
        "B2",
    ) is True


def test_clear_stale_s9_state_preserves_unrelated_speaking_bucket_data() -> None:
    bucket = {
        LEARNING_PLAN_KEY: {"plan_id": "old"},
        ACTIVE_BLUEPRINT_KEY: {"official_cefr_hint": "A1"},
        LEARNING_SESSION_KEY: {"session_id": "old"},
        ATTEMPT_LINEAGE_KEY: {"session_id": "old"},
        "knowledge_model": {"keep": True},
    }

    cleared = _clear_stale_s9_state(bucket)

    assert LEARNING_PLAN_KEY not in cleared
    assert ACTIVE_BLUEPRINT_KEY not in cleared
    assert LEARNING_SESSION_KEY not in cleared
    assert ATTEMPT_LINEAGE_KEY not in cleared
    assert cleared["knowledge_model"] == {"keep": True}
