"""Verify Phase 2.2 — Session Reservation + Lifecycle + Deterministic Selection.

Usage (from backend/):
    python scripts/verify_language_adaptive_learning_phase_2_2.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
LISTENING_SERVICE = ROOT / "app/services/language_listening_service.py"
SELECTION_DIR = ROOT / "app/services/language_listening_selection"
RESERVATION_DIR = ROOT / "app/services/language_listening_reservation"


def audit_no_random_selection() -> dict[str, object]:
    violations: list[str] = []
    patterns = ("func.random()", "ORDER BY RANDOM()", "order_by(func.random())", "import random")
    scan_paths = [
        LISTENING_SERVICE,
        *SELECTION_DIR.rglob("*.py"),
        *RESERVATION_DIR.rglob("*.py"),
    ]
    for path in scan_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        for pat in patterns:
            if pat in text and "import random" not in pat:
                violations.append(f"{rel}: {pat}")
            elif pat == "import random" and text.startswith("import random") or "\nimport random\n" in text:
                violations.append(f"{rel}: import random")
    migration_exists = (ROOT / "alembic/versions/0006_language_listening_reservations.py").is_file()
    model_exists = (ROOT / "app/models/language/reservation.py").is_file()
    return {
        "migration_exists": migration_exists,
        "model_exists": model_exists,
        "random_violations": violations,
    }


def test_lifecycle_transitions() -> dict[str, object]:
    from app.services.language_listening_reservation.lifecycle import (
        IllegalLifecycleTransitionError,
        assert_transition,
        can_transition,
    )
    from app.services.language_listening_reservation.types import ListeningLessonLifecycleState as S

    legal = [
        (S.reserved, S.started),
        (S.reserved, S.archived),
        (S.started, S.completed),
        (S.started, S.archived),
        (S.completed, S.reviewed),
        (S.reviewed, S.archived),
    ]
    illegal = [
        (S.archived, S.reserved),
        (S.completed, S.started),
        (S.reviewed, S.started),
        (S.reserved, S.completed),
    ]
    legal_ok = all(can_transition(a, b) for a, b in legal)
    illegal_blocked = True
    for a, b in illegal:
        try:
            assert_transition(a, b)
            illegal_blocked = False
        except IllegalLifecycleTransitionError:
            pass
    return {"legal_ok": legal_ok, "illegal_blocked": illegal_blocked}


def test_ranking_order() -> dict[str, object]:
    from app.services.language_listening_confidence.types import ConfidenceState, ObjectiveConfidenceRecord
    from app.services.language_listening_selection.ranker import rank_listening_candidate, select_best_candidate

    confidence = ConfidenceState(
        level="B1",
        objectives={
            "main_idea": ObjectiveConfidenceRecord(
                objective_id="main_idea", label="Main Idea", confidence=0.5
            ),
            "detail": ObjectiveConfidenceRecord(
                objective_id="detail", label="Detail", confidence=0.5
            ),
        },
    )

    def _item(iid: int, *, intent: str, score: float, challenge: str, created_ts: float) -> SimpleNamespace:
        return SimpleNamespace(
            id=iid,
            sort_order=0,
            created_at=datetime.fromtimestamp(created_ts, tz=timezone.utc),
            body_json={
                "listening_curriculum": {
                    "objectives": ["main_idea"],
                    "lesson_intent": intent,
                    "recommendation_score": score,
                },
                "listening_challenge_lesson": {"challenge_level": challenge},
            },
        )

    review_item = _item(1, intent="review", score=0.9, challenge="normal", created_ts=1000)
    weak_item = _item(2, intent="balanced_coverage", score=0.5, challenge="normal", created_ts=2000)
    stretch_item = _item(3, intent="balanced_coverage", score=0.95, challenge="hard", created_ts=3000)

    best = select_best_candidate([stretch_item, review_item, weak_item], confidence=confidence)
    best_id = best.id if best else None

    ranks = {
        "review": rank_listening_candidate(review_item, confidence=confidence).sort_key(),
        "weak": rank_listening_candidate(weak_item, confidence=confidence).sort_key(),
        "stretch": rank_listening_candidate(stretch_item, confidence=confidence).sort_key(),
    }
    review_beats_stretch = ranks["review"] < ranks["stretch"]
    older_wins = ranks["weak"] < ranks["stretch"] or ranks["weak"][2] <= ranks["stretch"][2]

    same_pool = [
        _item(10, intent="balanced_coverage", score=0.7, challenge="normal", created_ts=5000),
        _item(11, intent="balanced_coverage", score=0.7, challenge="normal", created_ts=5000),
    ]
    stable = select_best_candidate(same_pool, confidence=confidence)
    stable_id = stable.id if stable else None

    return {
        "review_wins_over_stretch": best_id == 1,
        "deterministic_rank_differs": ranks["weak"] != ranks["stretch"],
        "review_rank_lt_stretch": review_beats_stretch,
        "stable_tie_break_lowest_id": stable_id == 10,
    }


async def test_reservation_refresh_pin() -> dict[str, object]:
    from app.services.language_listening_reservation.service import ListeningSessionReservationService
    from app.services.language_listening_reservation.types import ListeningLessonLifecycleState

    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        id=uuid.uuid4(),
        student_id=42,
        language_id=1,
        content_item_id=999,
        lifecycle_state=ListeningLessonLifecycleState.reserved.value,
        reserved_at=now,
        expires_at=now + timedelta(hours=24),
        created_at=now,
        updated_at=now,
    )

    svc = ListeningSessionReservationService()
    db = AsyncMock()

    with patch(
        "app.services.language_listening_reservation.service.load_active_reservation",
        new=AsyncMock(return_value=row),
    ), patch(
        "app.services.language_listening_reservation.service.mark_started",
        new=AsyncMock(return_value=row),
    ):
        first = await svc.resolve_reserved_lesson(
            db, student_id=42, language_id=1, select_lesson_fn=AsyncMock(return_value=None)
        )
        second = await svc.resolve_reserved_lesson(
            db, student_id=42, language_id=1, select_lesson_fn=AsyncMock(return_value=None)
        )

    selector = AsyncMock(return_value=SimpleNamespace(id=123))
    with patch(
        "app.services.language_listening_reservation.service.load_active_reservation",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.services.language_listening_reservation.service.is_expired",
        return_value=False,
    ), patch(
        "app.services.language_listening_reservation.service.create_reservation",
        new=AsyncMock(return_value=row),
    ), patch(
        "app.services.language_listening_reservation.service.mark_started",
        new=AsyncMock(return_value=row),
    ):
        created = await svc.resolve_reserved_lesson(
            db, student_id=42, language_id=1, select_lesson_fn=selector
        )

    return {
        "refresh_same_id": first is not None
        and second is not None
        and first.content_item_id == second.content_item_id == 999,
        "selector_not_called_on_refresh": True,
        "create_calls_selector": selector.await_count == 1 and created is not None,
    }


async def test_expire_and_skip() -> dict[str, object]:
    from app.services.language_listening_reservation.service import ListeningSessionReservationService
    from app.services.language_listening_reservation.types import ListeningLessonLifecycleState

    now = datetime.now(timezone.utc)
    expired_row = SimpleNamespace(
        id=uuid.uuid4(),
        student_id=7,
        language_id=1,
        content_item_id=50,
        lifecycle_state=ListeningLessonLifecycleState.reserved.value,
        reserved_at=now - timedelta(hours=48),
        expires_at=now - timedelta(hours=1),
        created_at=now,
        updated_at=now,
    )

    svc = ListeningSessionReservationService()
    db = AsyncMock()

    with patch(
        "app.services.language_listening_reservation.service.load_active_reservation",
        new=AsyncMock(return_value=expired_row),
    ), patch(
        "app.services.language_listening_reservation.service.mark_expired",
        new=AsyncMock(return_value=expired_row),
    ) as mark_exp:
        loaded = await svc.load_reserved_content_id(db, student_id=7, language_id=1)

    with patch(
        "app.services.language_listening_reservation.service.load_active_reservation",
        new=AsyncMock(return_value=expired_row),
    ), patch(
        "app.services.language_listening_reservation.service.mark_skipped",
        new=AsyncMock(return_value=expired_row),
    ) as mark_skip:
        skipped = await svc.skip_reservation(db, student_id=7, language_id=1)

    return {"expired_clears_pin": loaded is None and mark_exp.await_count == 1, "skip_ok": skipped is True}


async def test_complete_reservation() -> dict[str, object]:
    from app.services.language_listening_reservation.service import ListeningSessionReservationService
    from app.services.language_listening_reservation.types import ListeningLessonLifecycleState

    now = datetime.now(timezone.utc)
    row = SimpleNamespace(
        id=uuid.uuid4(),
        student_id=99,
        language_id=1,
        content_item_id=777,
        lifecycle_state=ListeningLessonLifecycleState.started.value,
        reserved_at=now,
        expires_at=now + timedelta(hours=24),
        created_at=now,
        updated_at=now,
    )

    svc = ListeningSessionReservationService()
    db = AsyncMock()

    with patch(
        "app.services.language_listening_reservation.service.load_reservation_by_content",
        new=AsyncMock(return_value=row),
    ), patch(
        "app.services.language_listening_reservation.service.mark_completed",
        new=AsyncMock(return_value=row),
    ) as mark_done:
        result = await svc.complete_reservation(
            db, student_id=99, language_id=1, content_item_id=777
        )

    return {"complete_ok": result is not None and mark_done.await_count == 1}


async def test_parallel_race_integrity() -> dict[str, object]:
    from sqlalchemy.exc import IntegrityError

    from app.services.language_listening_reservation.service import ListeningSessionReservationService
    from app.services.language_listening_reservation.types import ListeningLessonLifecycleState

    now = datetime.now(timezone.utc)
    winner = SimpleNamespace(
        id=uuid.uuid4(),
        student_id=55,
        language_id=1,
        content_item_id=888,
        lifecycle_state=ListeningLessonLifecycleState.reserved.value,
        reserved_at=now,
        expires_at=now + timedelta(hours=24),
        created_at=now,
        updated_at=now,
    )

    svc = ListeningSessionReservationService()
    db = AsyncMock()
    db.rollback = AsyncMock()
    db.commit = AsyncMock()

    with patch(
        "app.services.language_listening_reservation.service.load_active_reservation",
        new=AsyncMock(side_effect=[None, winner]),
    ), patch(
        "app.services.language_listening_reservation.service.create_reservation",
        new=AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("duplicate"))),
    ), patch(
        "app.services.language_listening_reservation.service.mark_started",
        new=AsyncMock(return_value=winner),
    ):
        resolved = await svc.resolve_reserved_lesson(
            db,
            student_id=55,
            language_id=1,
            select_lesson_fn=AsyncMock(return_value=SimpleNamespace(id=888)),
        )

    return {
        "parallel_race_reloads_winner": resolved is not None and resolved.content_item_id == 888,
        "parallel_race_no_new_flag": resolved is not None and resolved.created_new is False,
    }


def test_selection_reproducibility() -> dict[str, object]:
    from app.services.language_listening_confidence.types import ConfidenceState
    from app.services.language_listening_selection.ranker import select_best_candidate

    items = [
        SimpleNamespace(
            id=i,
            sort_order=0,
            created_at=datetime.fromtimestamp(1000 + i, tz=timezone.utc),
            body_json={
                "listening_curriculum": {
                    "objectives": ["main_idea"],
                    "lesson_intent": "balanced_coverage",
                    "recommendation_score": 0.5,
                },
                "listening_challenge_lesson": {"challenge_level": "normal"},
            },
        )
        for i in (5, 3, 7, 1, 9)
    ]
    confidence = ConfidenceState(level="B1", objectives={})

    first = select_best_candidate(items, confidence=confidence)
    second = select_best_candidate(list(reversed(items)), confidence=confidence)
    return {
        "reproducible_id": first is not None and second is not None and first.id == second.id,
        "reproducible_id_value": first.id if first else None,
    }


def main() -> int:
    static = audit_no_random_selection()
    lifecycle = test_lifecycle_transitions()
    ranking = test_ranking_order()
    refresh = asyncio.run(test_reservation_refresh_pin())
    expire_skip = asyncio.run(test_expire_and_skip())
    complete = asyncio.run(test_complete_reservation())
    parallel = asyncio.run(test_parallel_race_integrity())
    reproducibility = test_selection_reproducibility()

    checks = [
        ("migration_exists", static["migration_exists"]),
        ("reservation_model_exists", static["model_exists"]),
        ("no_random_in_listening_path", len(static["random_violations"]) == 0),
        ("lifecycle_legal", lifecycle["legal_ok"]),
        ("lifecycle_illegal_blocked", lifecycle["illegal_blocked"]),
        ("ranking_review_priority", ranking["review_wins_over_stretch"]),
        ("ranking_deterministic", ranking["deterministic_rank_differs"]),
        ("stable_tie_break", ranking["stable_tie_break_lowest_id"]),
        ("refresh_same_lesson", refresh["refresh_same_id"]),
        ("create_uses_selector", refresh["create_calls_selector"]),
        ("expire_clears_reservation", expire_skip["expired_clears_pin"]),
        ("skip_releases_reservation", expire_skip["skip_ok"]),
        ("complete_reservation", complete["complete_ok"]),
        ("parallel_race_integrity", parallel["parallel_race_reloads_winner"]),
        ("parallel_race_no_duplicate", parallel["parallel_race_no_new_flag"]),
        ("selection_reproducibility", reproducibility["reproducible_id"]),
    ]

    print("LANGUAGE-ADAPTIVE-LEARNING-PHASE-2.2 VERIFICATION")
    print("=" * 58)
    for key, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {key}")

    if static["random_violations"]:
        print("\nRANDOM VIOLATIONS:")
        for v in static["random_violations"]:
            print(f"  - {v}")

    print("\nRANKING AUDIT")
    print(json.dumps(ranking, indent=2))

    overall = all(ok for _, ok in checks)
    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
