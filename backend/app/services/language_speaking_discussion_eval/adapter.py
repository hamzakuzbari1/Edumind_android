"""Discussion Evaluation Adapter — forward eligible turns into S7 (no local scoring)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.progression import LanguageProgression
from app.services.language_educational_package.types import DiscussionStep, EducationalPackage
from app.services.language_speaking_discussion.types import DiscussionRuntimeState
from app.services.language_speaking_discussion_eval.context_builder import (
    build_discussion_eval_context,
    build_speaking_evaluation_input,
    build_speaking_goal_context,
    build_speaking_task_context,
    count_student_turns_for_step,
    mint_turn_reference,
)
from app.services.language_speaking_discussion_eval.policy import (
    DEFAULT_DISCUSSION_EVAL_POLICY,
    DiscussionEvalPolicy,
)
from app.services.language_speaking_discussion_eval.types import (
    DISCUSSION_EVAL_ADAPTER_VERSION,
    DiscussionEvalHandoffResult,
    DiscussionProductionMode,
)
from app.services.language_speaking_evaluation_runtime.knowledge_bridge import (
    apply_speaking_evaluation_to_knowledge_model,
)
from app.services.language_speaking_evaluator.engine import evaluate_speaking_turn, new_evaluation_context
from app.services.language_speaking_evaluator.input_types import SpeakingOfficialCefrContext
from app.services.language_speaking_knowledge_model.types import ObservationSourceType


def _skipped(
    *,
    reason: str,
    category: str | None = None,
    context=None,
    intent: str | None = None,
) -> DiscussionEvalHandoffResult:
    return DiscussionEvalHandoffResult(
        adapter_version=DISCUSSION_EVAL_ADAPTER_VERSION,
        skipped=True,
        skip_reason=reason,
        evidence_category=category,
        evaluation_id=None,
        turn_reference=None,
        session_id=None,
        knowledge_mutation_status=None,
        evidence_intent=intent,
        context=context,
    )


async def _load_official_speaking_cefr(
    db: AsyncSession, *, student_id: int, language_id: int
) -> str:
    """Read-only CEFR for S7 context packaging. Never writes CEFR."""
    result = await db.execute(
        select(LanguageProgression.official_speaking_cefr).where(
            LanguageProgression.student_id == student_id,
            LanguageProgression.language_id == language_id,
        )
    )
    value = result.scalar_one_or_none()
    if value is None:
        return "A1"
    return getattr(value, "value", None) or str(value) or "A1"


async def maybe_map_discussion_turn_to_evaluation(
    db: AsyncSession,
    *,
    student_id: int,
    language_id: int,
    package: EducationalPackage,
    state: DiscussionRuntimeState,
    step: DiscussionStep | None,
    student_response: str,
    production_mode: DiscussionProductionMode = DiscussionProductionMode.text,
    policy: DiscussionEvalPolicy | None = None,
    apply_knowledge: bool = True,
) -> DiscussionEvalHandoffResult:
    """Map one discussion student turn into S7 when policy allows; otherwise skip.

    The adapter does not calculate scores or mastery. S7 evaluates; S8 knowledge
    bridge applies observations. Discussion Runtime is not modified.
    """
    active_policy = policy or DEFAULT_DISCUSSION_EVAL_POLICY
    decision = active_policy.decide(
        step,
        student_response=student_response,
        production_mode=production_mode,
    )
    if step is None or not decision.eligible:
        return _skipped(
            reason=(decision.skip_reason.value if decision.skip_reason else "skipped"),
            category=decision.category.value,
            intent=decision.evidence_intent.value,
        )

    ctx = build_discussion_eval_context(
        package=package,
        state=state,
        step=step,
        student_response=student_response.strip(),
        category=decision.category,
        production_mode=production_mode,
    )
    student_turn_index = count_student_turns_for_step(state, step.step_id)
    turn_reference = mint_turn_reference(
        package_id=package.package_id,
        step_id=step.step_id,
        student_turn_index=student_turn_index,
    )
    session_id = ctx.discussion_id
    evaluation_id = f"disc-eval-{uuid.uuid4().hex[:12]}"
    official_cefr = await _load_official_speaking_cefr(
        db, student_id=student_id, language_id=language_id
    )

    eval_input = build_speaking_evaluation_input(
        student_response=ctx.student_response,
        reliability=decision.reliability,
    )
    task_ctx = build_speaking_task_context(
        package=package, step=step, category=decision.category
    )
    goal_ctx = build_speaking_goal_context(
        package=package, evidence_intent=decision.evidence_intent
    )
    eval_context = new_evaluation_context(
        evaluation_id=evaluation_id,
        student_id=student_id,
        language_id=language_id,
        session_id=session_id,
        task_id=task_ctx.task_id,
        attempt_id=turn_reference,
        revision_number=1,
        task=task_ctx,
        goal=goal_ctx,
        official_cefr=SpeakingOfficialCefrContext(official_cefr=official_cefr),
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )

    evaluation = await evaluate_speaking_turn(eval_input, eval_context)

    mutation_status = "not_applied"
    if apply_knowledge:
        bridge = await apply_speaking_evaluation_to_knowledge_model(
            db,
            student_id=student_id,
            language_id=language_id,
            evaluation=evaluation,
            turn_reference=turn_reference,
            session_id=session_id,
            source_type=ObservationSourceType.evaluation_turn,
        )
        mutation_status = bridge.mutation_status.value

    return DiscussionEvalHandoffResult(
        adapter_version=DISCUSSION_EVAL_ADAPTER_VERSION,
        skipped=False,
        skip_reason=None,
        evidence_category=decision.category.value,
        evaluation_id=evaluation.evaluation_id,
        turn_reference=turn_reference,
        session_id=session_id,
        knowledge_mutation_status=mutation_status,
        evidence_intent=decision.evidence_intent.value,
        context=ctx,
    )
