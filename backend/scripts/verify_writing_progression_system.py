"""Writing progression system verification (pure engine logic — no DB, no Claude).

Validates the evidence-based stage/readiness rules required by the Writing
progression spec. Each lesson entry mirrors the continuous facts the completion
writer now persists from WritingEvaluationEngineResult.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_writing_learning_stage.scoring import compute_writing_stage_score
from app.services.language_writing_learning_stage.signals import gather_writing_signals_from_state
from app.services.language_writing_promotion_readiness.engine import (
    evaluate_writing_readiness_from_signals,
)
from app.services.language_promotion_readiness.types import ReadinessStatus
from app.services.language_writing_official_promotion.ownership_guard import verify_writing_cefr_ownership
from app.services.language_writing_transition_gate.rules import evaluate_writing_transition_gate

PASS = "PASS"
FAIL = "FAIL"
_results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    _results.append((name, ok, detail))
    print(f"  {PASS if ok else FAIL}  {name}{(' — ' + detail) if detail else ''}")
    return ok


def _lesson(
    *,
    grammar: float,
    vocab: float,
    task: float,
    org: float,
    cefr_align: float,
    criteria_ratio: float = None,
    revision: int = 1,
) -> dict:
    ratio = criteria_ratio if criteria_ratio is not None else task
    total = 5
    return {
        "criteria_total": total,
        "criteria_met": round(ratio * total),
        "confidence": round((grammar + task) / 2, 4),
        "grammar_score": grammar,
        "vocabulary_score": vocab,
        "organization_score": org,
        "task_response_score": task,
        "goal_alignment_score": org,
        "overall_readiness": round((grammar + vocab + task + org) / 4, 4),
        "cefr_alignment": cefr_align,
        "revision_count": revision,
    }


def _state(
    lessons: list[dict],
    *,
    stage: int = 1,
    grammar_mastery: float = None,
    vocab_mastery: float = None,
    completed_nodes: int = None,
    repeated_mistakes: int = 0,
    weak_skills: list[str] = None,
) -> dict:
    n = len(lessons)
    gm = grammar_mastery if grammar_mastery is not None else (
        sum(x["grammar_score"] for x in lessons) / n if n else 0.5
    )
    vm = vocab_mastery if vocab_mastery is not None else (
        sum(x["vocabulary_score"] for x in lessons) / n if n else 0.5
    )
    completed = completed_nodes if completed_nodes is not None else n
    mistakes = [
        {"code": f"m{i}", "occurrence_count": 3, "last_seen_at": "x"} for i in range(repeated_mistakes)
    ]
    return {
        "grammar_mastery": {"present_simple": gm},
        "vocabulary_mastery": {"vocabulary": vm},
        "lesson_history": lessons,
        "lessons_completed_count": n,
        "completed_node_ids": [f"node_{i}" for i in range(completed)],
        "weak_skills": weak_skills or [],
        "coach_memory": {"repeated_mistakes": mistakes},
        "learning_stage": stage,
    }


def _evaluate(state: dict, *, official: str = "B1", stage: int = 1):
    snap = gather_writing_signals_from_state(state, official_cefr=official)
    score = compute_writing_stage_score(snap)
    gate = evaluate_writing_transition_gate(persistent_stage=stage, stage_score=score, snapshot=snap)
    readiness = evaluate_writing_readiness_from_signals(
        official_cefr=official, persistent_stage=stage, snapshot=snap, gate=gate, stage_score=score
    )
    return snap, score, gate, readiness


def _strong_lessons(n: int) -> list[dict]:
    return [
        _lesson(grammar=0.88, vocab=0.82, task=0.86, org=0.80, cefr_align=1.0, criteria_ratio=0.9)
        for _ in range(n)
    ]


def main() -> int:
    print("Writing Progression System — pure engine verification\n")

    # 1. B1 student starts Stage 1.
    print("Case 1: B1 student starts at Stage 1")
    snap, score, gate, readiness = _evaluate(_state([]), stage=1)
    check("fresh student is Stage 1 / NOT_READY", readiness.status == ReadinessStatus.NOT_READY, readiness.status.value)
    check("fresh student not gate-eligible", not gate.eligible)

    # 2. Lesson count alone cannot advance a stage.
    print("Case 2: lesson count alone cannot advance a stage")
    weak_lessons = [
        _lesson(grammar=0.35, vocab=0.35, task=0.30, org=0.30, cefr_align=0.3, criteria_ratio=0.4)
        for _ in range(20)
    ]
    snap, score, gate, readiness = _evaluate(_state(weak_lessons, grammar_mastery=0.35, vocab_mastery=0.35), stage=1)
    check("20 weak lessons still NOT gate-eligible", not gate.eligible, f"gate_score={gate.overall_gate_score}")
    check("lesson exposure met but blocked by quality", snap.lesson_index >= 4 and not gate.eligible)

    # 3. Strong grammar but weak task response remains blocked.
    print("Case 3: strong grammar, weak task response -> blocked")
    lessons = [
        _lesson(grammar=0.92, vocab=0.85, task=0.30, org=0.55, cefr_align=0.5, criteria_ratio=0.4)
        for _ in range(6)
    ]
    snap, score, gate, readiness = _evaluate(_state(lessons, grammar_mastery=0.92, vocab_mastery=0.85), stage=1)
    blocker = (gate.primary_blocker or "").lower()
    check("not eligible despite strong grammar", not gate.eligible)
    check("task response is the blocker", "task response" in blocker, gate.primary_blocker or "")

    # 4. Task response improves across revisions -> readiness rises.
    print("Case 4: task response improvement raises readiness")
    before = _state(
        [_lesson(grammar=0.75, vocab=0.7, task=0.35, org=0.6, cefr_align=0.6) for _ in range(6)],
        grammar_mastery=0.75,
        vocab_mastery=0.7,
    )
    after = _state(
        [_lesson(grammar=0.78, vocab=0.72, task=0.82, org=0.75, cefr_align=0.85) for _ in range(6)],
        grammar_mastery=0.78,
        vocab_mastery=0.72,
    )
    _, _, _, r_before = _evaluate(before, stage=1)
    _, _, _, r_after = _evaluate(after, stage=1)
    check(
        "readiness increases when task response improves",
        r_after.readiness_score > r_before.readiness_score,
        f"{r_before.readiness_score} -> {r_after.readiness_score}",
    )

    # 5. Repeated grammar mistakes remain a blocker.
    print("Case 5: repeated grammar mistakes remain a blocker")
    lessons = [
        _lesson(grammar=0.45, vocab=0.7, task=0.7, org=0.7, cefr_align=0.7, criteria_ratio=0.7)
        for _ in range(6)
    ]
    snap, score, gate, readiness = _evaluate(
        _state(lessons, grammar_mastery=0.45, vocab_mastery=0.7, repeated_mistakes=3), stage=1
    )
    grammar_req = next((r for r in gate.requirements if r.name == "grammar_mastery"), None)
    check("grammar requirement fails", grammar_req is not None and not grammar_req.passed)
    check("not gate-eligible with weak grammar", not gate.eligible)

    # 6. Stage 1 -> 2 only after the evidence gate passes.
    print("Case 6: Stage 1 -> 2 requires the evidence gate")
    snap, score, gate, readiness = _evaluate(
        _state(_strong_lessons(6), grammar_mastery=0.85, vocab_mastery=0.8), stage=1
    )
    check("strong sustained evidence -> gate eligible", gate.eligible, f"gate_score={gate.overall_gate_score}")
    check("next stage is 2 (one step)", gate.next_stage == 2, str(gate.next_stage))

    # 7. Stage 2 -> 3 needs stronger evidence than 1 -> 2.
    print("Case 7: Stage 2 -> 3 needs stronger evidence")
    mid = _state(
        [_lesson(grammar=0.66, vocab=0.6, task=0.62, org=0.6, cefr_align=0.6, criteria_ratio=0.65) for _ in range(8)],
        grammar_mastery=0.66,
        vocab_mastery=0.6,
    )
    _, _, gate_mid, _ = _evaluate(mid, stage=2)
    check("mid evidence NOT enough for Stage 2->3", not gate_mid.eligible)
    strong2 = _state(_strong_lessons(10), grammar_mastery=0.9, vocab_mastery=0.85)
    _, _, gate_strong2, _ = _evaluate(strong2, stage=2)
    check("strong evidence passes Stage 2->3", gate_strong2.eligible and gate_strong2.next_stage == 3)

    # 8. One excellent lesson cannot unlock promotion.
    print("Case 8: one excellent lesson cannot unlock promotion")
    _, _, _, readiness = _evaluate(_state(_strong_lessons(1), grammar_mastery=0.9, vocab_mastery=0.85), stage=1)
    check(
        "single strong lesson is not PROMOTION_AVAILABLE",
        readiness.status != ReadinessStatus.PROMOTION_AVAILABLE,
        readiness.status.value,
    )

    # 9. Readiness reacts to multiple stable lessons.
    print("Case 9: readiness climbs with multiple stable lessons")
    _, _, _, r1 = _evaluate(_state(_strong_lessons(2), grammar_mastery=0.85, vocab_mastery=0.8), stage=1)
    _, _, _, r2 = _evaluate(_state(_strong_lessons(8), grammar_mastery=0.9, vocab_mastery=0.86), stage=2)
    check("readiness increases across stable lessons", r2.readiness_score > r1.readiness_score, f"{r1.readiness_score} -> {r2.readiness_score}")

    # 10. Promotion becomes available legitimately (Stage 3, strong sustained).
    print("Case 10: promotion becomes available legitimately")
    strong3 = _state(_strong_lessons(12), stage=3, grammar_mastery=0.92, vocab_mastery=0.9, completed_nodes=12)
    snap, score, gate, readiness = _evaluate(strong3, stage=3)
    check(
        "Stage 3 strong sustained -> PROMOTION_AVAILABLE",
        readiness.status == ReadinessStatus.PROMOTION_AVAILABLE,
        f"score={readiness.readiness_score} status={readiness.status.value}",
    )

    # 14. Ownership guard — only authorized modules write official_writing_cefr.
    print("Case 14: official_writing_cefr ownership guard")
    ok, unauthorized, missing = verify_writing_cefr_ownership(Path(__file__).resolve().parents[1] / "app")
    check("no unauthorized official_writing_cefr writers", ok, f"unauthorized={sorted(unauthorized)}")
    check("authorized writers present", not missing, f"missing={sorted(missing)}")

    # 20. No fake percentages — readiness/stage are computed integers in range.
    print("Case 20: computed values are in valid ranges")
    check("readiness score 0..100", 0 <= readiness.readiness_score <= 100)
    check("stage score 0..100", 0 <= score <= 100)

    print("\n" + "=" * 50)
    failed = [n for n, ok, _ in _results if not ok]
    if failed:
        print(f"RESULT: FAIL — {len(failed)} check(s) failed:")
        for n in failed:
            print("  -", n)
        return 1
    print(f"RESULT: PASS — {len(_results)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
