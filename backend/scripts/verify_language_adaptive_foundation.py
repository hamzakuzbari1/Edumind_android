"""Verify Phase 7.5 adaptive progression foundation (prerequisites only).

Usage (from backend/):
    python scripts/verify_language_adaptive_foundation.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]


def _static_checks() -> dict[str, bool]:
    config_src = (BACKEND / "app" / "core" / "config.py").read_text(encoding="utf-8")
    adaptive_src = (BACKEND / "app" / "services" / "language_adaptive_service.py").read_text(encoding="utf-8")
    model_src = (BACKEND / "app" / "models" / "language" / "adaptive.py").read_text(encoding="utf-8")
    cs_src = (BACKEND / "app" / "services" / "language_curriculum_service.py").read_text(encoding="utf-8")
    reading_src = (BACKEND / "app" / "services" / "language_skill_progress_service.py").read_text(encoding="utf-8")
    writing_src = (BACKEND / "app" / "services" / "language_writing_service.py").read_text(encoding="utf-8")
    speaking_src = (BACKEND / "app" / "services" / "language_speaking_service.py").read_text(encoding="utf-8")
    vocab_src = (BACKEND / "app" / "services" / "language_vocabulary_service.py").read_text(encoding="utf-8")
    conv_src = (BACKEND / "app" / "services" / "language_conversation_service.py").read_text(encoding="utf-8")
    mig42 = (BACKEND / "alembic" / "versions" / "0042_adaptive_difficulty.py").read_text(encoding="utf-8")
    mig43 = (BACKEND / "alembic" / "versions" / "0043_add_recent_scores_json.py").read_text(encoding="utf-8")

    return {
        "migration_file": (BACKEND / "alembic" / "versions" / "0042_adaptive_difficulty.py").exists(),
        "migration_table": "language_skill_level_state" in mig42,
        "migration_recent_scores": "recent_scores_json" in mig43,
        "migration_revises_0041": 'down_revision = "0041_language_curriculum_progress"' in mig42,
        "migration_0043_chain": 'down_revision = "0042_adaptive_difficulty"' in mig43,
        "model_exists": "class LanguageSkillLevelState" in model_src,
        "model_recent_scores": "recent_scores_json" in model_src,
        "adaptive_service_exists": (BACKEND / "app" / "services" / "language_adaptive_service.py").exists(),
        "record_lesson_result": "async def record_lesson_result" in adaptive_src,
        "get_or_create_skill_state": "async def get_or_create_skill_state" in adaptive_src,
        "no_level_change": ('"changed": False' in adaptive_src and '"direction": None' in adaptive_src),
        "window_helpers": "_append_score" in adaptive_src and "rolling_average" in adaptive_src,
        "config_window_size": "LANGUAGE_MASTERY_WINDOW_SIZE" in config_src,
        "config_up_threshold": "LANGUAGE_MASTERY_UP_THRESHOLD" in config_src,
        "config_down_threshold": "LANGUAGE_MASTERY_DOWN_THRESHOLD" in config_src,
        "adaptive_uses_config": "LANGUAGE_MASTERY_WINDOW_SIZE" in adaptive_src,
        "wired_reading": "record_lesson_result" in reading_src and "LanguageSkill.reading" in reading_src,
        "wired_listening": "record_lesson_result" in reading_src and "LanguageSkill.listening" in reading_src,
        "wired_writing": "record_lesson_result" in writing_src,
        "wired_speaking": "record_lesson_result" in speaking_src,
        "credit_feature_objectives": "async def credit_feature_objectives" in cs_src,
        "credit_vocabulary": 'feature="vocabulary"' in vocab_src,
        "credit_conversation": 'feature="conversation"' in conv_src,
        "model_exported": "LanguageSkillLevelState" in (
            BACKEND / "app" / "models" / "language" / "__init__.py"
        ).read_text(encoding="utf-8"),
    }


async def _logic_checks() -> dict[str, bool]:
    from app.models.language.enums import LanguageLevel, LanguageSkill
    from app.services.language_adaptive_service import (
        _append_score,
        rolling_average,
        get_or_create_skill_state,
        record_lesson_result,
    )

    window_ok = _append_score([80.0, 90.0], 95.0, 3) == [80.0, 90.0, 95.0]
    trim_ok = _append_score([1, 2, 3], 4.0, 3) == [2.0, 3.0, 4.0]
    avg_ok = rolling_average([80.0, 90.0, 100.0]) == 90.0

    db = AsyncMock()
    db.flush = AsyncMock()

    state = MagicMock()
    state.current_level = LanguageLevel.B1
    state.consecutive_pass_count = 0
    state.consecutive_fail_count = 0
    state.recent_scores_json = []

    with patch("app.services.language_adaptive_service.get_settings") as gs, patch(
        "app.services.language_adaptive_service.get_or_create_skill_state", new_callable=AsyncMock
    ) as mock_get:
        gs.return_value = MagicMock(
            LANGUAGE_MASTERY_WINDOW_SIZE=3,
            LANGUAGE_MASTERY_UP_THRESHOLD=82.0,
            LANGUAGE_MASTERY_DOWN_THRESHOLD=40.0,
        )
        mock_get.return_value = state
        create_ok = True
        r1 = await record_lesson_result(
            db, student_id=1, language_id=1, skill=LanguageSkill.reading, score_percent=90.0
        )
        r2 = await record_lesson_result(
            db, student_id=1, language_id=1, skill=LanguageSkill.reading, score_percent=50.0
        )

    record_ok = r1["recent_scores"] == [90.0] and r1["changed"] is False
    streak_ok = r1["consecutive_pass_count"] == 1 and r2["consecutive_pass_count"] == 0
    window_grow_ok = r2["recent_scores"] == [90.0, 50.0]
    avg_record_ok = r2["rolling_average"] == 70.0
    get_called = mock_get.await_count >= 2

    return {
        "window_append": window_ok,
        "window_trim": trim_ok,
        "rolling_average": avg_ok,
        "state_lookup": get_called,
        "lesson_recorded": record_ok,
        "streak_tracking": streak_ok,
        "window_grows": window_grow_ok,
        "rolling_avg_on_record": avg_record_ok,
    }


async def _migration_check() -> dict[str, bool]:
    mig_path = BACKEND / "alembic" / "versions" / "0043_add_recent_scores_json.py"
    mig_src = mig_path.read_text(encoding="utf-8") if mig_path.exists() else ""
    return {
        "migration_in_chain": (
            'revision = "0043_add_recent_scores_json"' in mig_src
            and 'down_revision = "0042_adaptive_difficulty"' in mig_src
        ),
        "migration_table_defined": "language_skill_level_state" in mig_src,
    }


def main() -> int:
    print("Phase 7.5 — verify_language_adaptive_foundation\n")

    static = _static_checks()
    print("Static checks")
    print("-------------")
    for k, v in static.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    logic = asyncio.run(_logic_checks())
    print("\nLogic checks (mocked)")
    print("---------------------")
    for k, v in logic.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    mig = asyncio.run(_migration_check())
    print("\nMigration chain")
    print("---------------")
    for k, v in mig.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    all_ok = all(static.values()) and all(logic.values()) and all(mig.values())
    total = len(static) + len(logic) + len(mig)
    passed = sum(static.values()) + sum(logic.values()) + sum(mig.values())
    print(f"\n{passed}/{total} checks passed.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
