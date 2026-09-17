"""Writing Promotion Assessment engine — grades only; never promotes CEFR."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.language.enums import LanguageLevel
from app.services.language_level_utils import CEFR_RANK, RANK_CEFR
from app.services.language_progression_service import ensure_progression_row
from app.services.language_promotion_readiness.types import ReadinessStatus
from app.services.language_writing.enums import OfficialWritingCEFR, PromotionStatus, WritingGoal
from app.services.language_writing_evaluator.blueprint_snapshot import EvaluatorBlueprintSnapshot, EvaluationPlanSnapshot, SuccessCriteriaSnapshot
from app.services.language_writing_evaluator.engine import evaluate_writing_draft_sync
from app.services.language_writing_progression.locking import lock_writing_progression_row
from app.services.language_writing_promotion_readiness import evaluate_writing_promotion_readiness
from app.services.language_writing_promotion_test.builder import build_writing_promotion_session, session_to_dict
from app.services.language_writing_promotion_test.storage import WRITING_TESTS_KEY, get_active_session, tests_bucket
from app.services.language_writing_promotion_test.types import WritingPromotionResult, WritingPromotionTaskResult

PASS_THRESHOLD = 80.0


def _next_cefr(level: str) -> str:
    try:
        current = LanguageLevel(level.upper())
    except ValueError:
        return level.upper()
    nxt = CEFR_RANK.get(current, 1) + 1
    if nxt in RANK_CEFR:
        return RANK_CEFR[nxt].value
    return current.value


def _minimal_blueprint(*, task: dict, goal: WritingGoal) -> EvaluatorBlueprintSnapshot:
    return EvaluatorBlueprintSnapshot(
        blueprint_version="wpa:1.0.0",
        blueprint_hash="wpa",
        generation_hash="wpa",
        chain_id="wpa",
        chain_node_id=f"wpa_{goal.value}",
        task_type=str(task.get("task_type") or "essay"),
        genre=str(task.get("genre") or "paragraph"),
        personal_goal=goal.value,
        learning_outcomes=("Address the prompt clearly", "Use accurate grammar"),
        common_mistakes=(),
        difficulty_drivers=(),
        grammar_primary="present_simple",
        grammar_secondary="",
        vocabulary_primary=("because", "however", "therefore"),
        evaluation_plan=EvaluationPlanSnapshot(0.2, 0.2, 0.2, 0.2, 0.2, (), (), ()),
        success_criteria=SuccessCriteriaSnapshot(
            int(task.get("min_words") or 60),
            int(task.get("max_words") or 200),
            ("present_simple",),
            ("because",),
            (),
            str(task.get("genre") or "paragraph"),
            (f"Write at least {task.get('min_words')} words", "Use present simple correctly"),
        ),
    )


async def check_writing_promotion_test_eligibility(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
) -> tuple[bool, str, int, str]:
    readiness = await evaluate_writing_promotion_readiness(db, student_id=student_id, language_id=language_id)
    target = _next_cefr(readiness.official_cefr)
    if readiness.status != ReadinessStatus.PROMOTION_AVAILABLE:
        return (
            False,
            f"WPA requires PROMOTION_AVAILABLE (current: {readiness.status.value}, score: {readiness.readiness_score}).",
            readiness.readiness_score,
            target,
        )
    return True, "Writing promotion readiness is PROMOTION_AVAILABLE.", readiness.readiness_score, target


async def create_writing_promotion_test_session(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    goal: WritingGoal,
) -> dict:
    eligible, reason, score, target = await check_writing_promotion_test_eligibility(
        db, student_id=student_id, language_id=language_id
    )
    if not eligible:
        return {"eligible": False, "reason": reason, "readiness_score": score}
    row = await lock_writing_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        row = await ensure_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return {"eligible": False, "reason": "Progression row unavailable."}
    try:
        official = OfficialWritingCEFR(row.official_writing_cefr.value)
        target_level = OfficialWritingCEFR(target)
    except ValueError:
        official = OfficialWritingCEFR.B1
        target_level = OfficialWritingCEFR.B2
    bundle = build_writing_promotion_session(
        student_id=student_id,
        language_id=language_id,
        official_cefr=official,
        target_cefr=target_level,
        goal=goal,
    )
    payload = dict(row.promotion_readiness_json or {})
    bucket = tests_bucket(payload)
    bucket["active_session"] = session_to_dict(bundle)
    payload[WRITING_TESTS_KEY] = bucket
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return {"eligible": True, "session": bucket["active_session"]}


async def submit_writing_promotion_test(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    session_id: str,
    submissions: dict[str, str],
) -> WritingPromotionResult | None:
    row = await lock_writing_progression_row(db, student_id=student_id, language_id=language_id)
    if row is None:
        return None
    payload = dict(row.promotion_readiness_json or {})
    active = get_active_session(payload)
    if not active or str(active.get("session_id")) != session_id:
        return None
    goal = WritingGoal(str(active.get("goal") or "general_english"))
    task_results: list[WritingPromotionTaskResult] = []
    scores: list[float] = []
    for task in active.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        tid = str(task.get("task_id"))
        text = str(submissions.get(tid) or "").strip()
        bp = _minimal_blueprint(task=task, goal=goal)
        ev = evaluate_writing_draft_sync(text, draft_id=tid, revision_number=1, blueprint=bp)
        task_score = round(ev.overall_readiness * 100, 1)
        scores.append(task_score)
        passed = task_score >= PASS_THRESHOLD
        task_results.append(
            WritingPromotionTaskResult(
                task_id=tid,
                submitted_text=text,
                word_count=ev.word_count,
                criterion_scores={"overall": task_score / 100.0},
                passed=passed,
            )
        )
    overall = round(sum(scores) / len(scores), 1) if scores else 0.0
    overall_passed = overall >= PASS_THRESHOLD and all(t.passed for t in task_results)
    result_str = "PASS" if overall_passed else "FAIL"
    attempt = {
        "session_id": session_id,
        "official_cefr": active.get("official_cefr"),
        "target_cefr": active.get("target_cefr"),
        "goal": goal.value,
        "overall_score": overall,
        "result": result_str,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "task_results": [
            {
                "task_id": tr.task_id,
                "word_count": tr.word_count,
                "passed": tr.passed,
                "score": tr.criterion_scores.get("overall", 0),
            }
            for tr in task_results
        ],
    }
    bucket = tests_bucket(payload)
    bucket["attempts"] = list(bucket.get("attempts") or []) + [attempt]
    bucket["active_session"] = None
    payload[WRITING_TESTS_KEY] = bucket
    row.promotion_readiness_json = payload
    flag_modified(row, "promotion_readiness_json")
    await db.flush()
    return WritingPromotionResult(
        session_id=session_id,
        overall_passed=overall_passed,
        task_results=tuple(task_results),
        status=PromotionStatus.passed if overall_passed else PromotionStatus.failed,
    )
