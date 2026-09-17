"""Canonical deterministic Alex educational context (S14).

Projection / orchestration ONLY. This layer:
- reuses S12 read-model authority (focus, mission, task, attempt, weak/retention/transfer, support)
- reuses the canonical S11 mission/task resolver + attempt lineage
- reuses the official CEFR from LanguageProgression (never invents an internal stage)

It NEVER computes mastery, stage, readiness, or promotion, and NEVER exposes
mastery/confidence numbers, evidence counts, internal ids, evaluation ids,
live-turn ids, retry-chain ids, provider billing state, or secrets to Alex.

Determinism: the same unchanged authoritative educational state yields the same
``context_fingerprint``; any change to task/mission/attempt/retry/weak-skill
state changes it (freshness — PART 8).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from app.services.language_speaking_knowledge_model.types import StudentSpeakingKnowledgeModel
from app.services.language_speaking_journey.errors import (
    AmbiguousActiveAttemptError,
    SpeakingContextUnavailableError,
)
from app.services.language_speaking_journey.read_model import (
    build_speaking_journey_read_model,
    student_safe_execution_mode,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    assert_active_attempt_integrity,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    AmbiguousActiveAttemptError as LineageAmbiguousActiveAttemptError,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import (
    SpeakingRuntimeTaskResolution,
    resolve_current_task,
)
from app.services.language_speaking_lesson_planner.storage import SpeakingStoredJourneyState
from app.services.language_speaking_lesson_planner.types import SpeakingLessonBlueprint

ALEX_EDUCATIONAL_CONTEXT_VERSION = "14.0.0"

# ---------------------------------------------------------------------------
# PART 4 — deterministic general tutor behavior contract
# ---------------------------------------------------------------------------

TUTOR_BEHAVIOR_CONTRACT: tuple[str, ...] = (
    "You are Alex, a warm and encouraging English speaking tutor — not a generic chatbot.",
    "Follow the current educational mission and keep the conversation on the current learning objective.",
    "Teach when the mission requires teaching; give a concise explanation before expecting performance.",
    "Model a short natural example when support is available and it helps the student.",
    "Ask one clear speaking prompt at a time, then let the student speak without interrupting.",
    "Use short, natural follow-up questions that stay inside the learning objective.",
    "Add more conversational support when the student struggles; simplify or rephrase if comprehension seems weak.",
    "Encourage the student to self-correct without revealing evaluator internals.",
    "Practice the target skill across the task context; do not turn every reply into a correction.",
    "Never use raw CEFR scoring language, and never state mastery or confidence percentages.",
    "Never tell the student they officially passed or were promoted to a level.",
    "Never claim a mission or task is complete unless the backend educational state says so.",
    "Never invent weak skills that are not in your provided context.",
    "You do not decide progression, scores, or promotion — the backend owns that.",
    "Sound like a natural tutor with personality; let tone be human, but keep the educational purpose fixed.",
)

# ---------------------------------------------------------------------------
# PART 5 — deterministic mission-kind → tutor behavior mapping
# Keyed by canonical SpeakingMissionKind value. Backend decides the kind; Alex does not.
# ---------------------------------------------------------------------------

MISSION_BEHAVIOR_CONTRACT: dict[str, tuple[str, ...]] = {
    "teaching": (
        "Explain the target speaking concept simply and briefly.",
        "Give one short spoken example the student can imitate.",
        "Check basic understanding with a light question — do not evaluate mastery yet.",
    ),
    "noticing": (
        "Present or discuss clear examples of the target pattern.",
        "Guide the student to notice how the pattern works.",
        "Ask focused noticing questions rather than asking for full performance.",
    ),
    "guided_practice": (
        "Offer scaffolded prompts with support built in.",
        "Allow short responses and give immediate lightweight help.",
        "Gradually reduce the support as the student succeeds.",
    ),
    "speak": (
        "Ask the authoritative task prompt exactly as given.",
        "Allow extended student speech and use relevant follow-ups.",
        "Do not over-interrupt and do not silently change the task.",
    ),
    "feedback": (
        "Discuss only student-safe feedback — a small number of useful improvements.",
        "Do not expose evaluator dimensions, scores, or internal evidence.",
        "End with one concrete, encouraging next step.",
    ),
    "transfer": (
        "Preserve the same target skill but use the new context provided.",
        "Do not reuse the exact previously practiced scenario when a distinct context is required.",
        "Help the student apply the skill flexibly.",
    ),
    "retention_review": (
        "Briefly revisit the skill using retrieval-style prompting.",
        "Do not reteach everything unless the student clearly struggles.",
        "Confirm the skill still feels natural to use.",
    ),
}

_DEFAULT_MISSION_BEHAVIOR: tuple[str, ...] = (
    "Keep the conversation centered on the current speaking objective.",
    "Ask one clear speaking prompt and let the student practice.",
)


def mission_behavior_for_kind(mission_kind: str) -> tuple[str, ...]:
    return MISSION_BEHAVIOR_CONTRACT.get(mission_kind, _DEFAULT_MISSION_BEHAVIOR)


def authoritative_task_prompt(blueprint: SpeakingLessonBlueprint | None) -> str:
    """The single authoritative task instruction shared by student / Alex / S7 / S9 / S11.

    Sourced from the blueprint's ``alex_context.communicative_scenario`` — the same
    value ``start_speaking_session`` returns to the student and the live-turn path
    evaluates against. Prevents prompt drift (PART 6).
    """
    if blueprint is None:
        return ""
    return blueprint.alex_context.communicative_scenario


# ---------------------------------------------------------------------------
# PART 3 — versioned typed Alex educational context contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AlexSpeakingEducationalContext:
    """Deterministic, student-safe educational grounding for the live tutor Alex.

    Contains ONLY educationally useful fields. No mastery/confidence numbers,
    no evidence counts, no internal/database/evaluation/turn/retry ids, no
    provider billing state, no promotion readiness, no invented internal stage.
    """

    context_version: str
    context_fingerprint: str
    official_cefr: str
    focus_title: str
    focus_reason: str
    learning_objectives: tuple[str, ...]
    current_mission: str
    current_mission_kind: str
    current_mission_purpose: str
    current_task_instruction: str
    current_execution_mode: str
    task_context: str
    attempt_number: int
    is_retry: bool
    support_available: tuple[str, ...]
    weak_skill_focuses: tuple[str, ...]
    retention_focuses: tuple[str, ...]
    transfer_focuses: tuple[str, ...]
    session_teaching_goal: str
    tutor_behavior_contract: tuple[str, ...] = TUTOR_BEHAVIOR_CONTRACT
    mission_behavior: tuple[str, ...] = ()
    has_current_task: bool = False

    def to_tutor_dict(self) -> dict[str, object]:
        """Serialize for delivery to Alex (EVI). Guaranteed free of ids/mastery/secrets."""
        return {
            "context_version": self.context_version,
            "context_fingerprint": self.context_fingerprint,
            "official_cefr": self.official_cefr,
            "focus_title": self.focus_title,
            "focus_reason": self.focus_reason,
            "learning_objectives": list(self.learning_objectives),
            "current_mission": self.current_mission,
            "current_mission_kind": self.current_mission_kind,
            "current_mission_purpose": self.current_mission_purpose,
            "current_task_instruction": self.current_task_instruction,
            "current_execution_mode": self.current_execution_mode,
            "task_context": self.task_context,
            "attempt_number": self.attempt_number,
            "is_retry": self.is_retry,
            "support_available": list(self.support_available),
            "weak_skill_focuses": list(self.weak_skill_focuses),
            "retention_focuses": list(self.retention_focuses),
            "transfer_focuses": list(self.transfer_focuses),
            "session_teaching_goal": self.session_teaching_goal,
            "tutor_behavior_contract": list(self.tutor_behavior_contract),
            "mission_behavior": list(self.mission_behavior),
            "has_current_task": self.has_current_task,
        }

    to_dict = to_tutor_dict


def _fingerprint(payload: dict[str, object]) -> str:
    """Stable content hash over authoritative educational fields only."""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def build_alex_speaking_educational_context(
    *,
    official_cefr: str,
    state: SpeakingStoredJourneyState | None,
    knowledge_model: StudentSpeakingKnowledgeModel | None = None,
) -> AlexSpeakingEducationalContext:
    """Build the canonical Alex educational context from authoritative state.

    Fails closed:
    - raises ``SpeakingContextUnavailableError`` when there is no blueprint to ground on
    - raises ``AmbiguousActiveAttemptError`` when persisted lineage is malformed (C-7)

    Reuses the S12 read model for focus/mission/task/attempt/weak/support/retention/
    transfer projections so there is a single learning-authority source.
    """
    blueprint = state.blueprint if state else None
    if blueprint is None:
        raise SpeakingContextUnavailableError()

    lineage = state.attempt_lineage if state else None
    if lineage is not None:
        try:
            assert_active_attempt_integrity(lineage)
        except LineageAmbiguousActiveAttemptError as exc:
            raise AmbiguousActiveAttemptError(detail=str(exc)) from exc

    read_model = build_speaking_journey_read_model(
        official_cefr=official_cefr,
        state=state,
        knowledge_model=knowledge_model,
    )

    resolution: SpeakingRuntimeTaskResolution | None = None
    session = state.session if state else None
    if session is not None:
        resolution = resolve_current_task(blueprint, session)

    mission_kind = resolution.mission_kind if (resolution and resolution.is_task) else ""
    has_current_task = bool(resolution and resolution.is_task)

    task_instruction = authoritative_task_prompt(blueprint)
    task_section = read_model.current_task
    if not task_instruction and task_section.available:
        task_instruction = task_section.instruction

    mission_section = read_model.current_mission
    support_available = tuple(item.label for item in read_model.support if item.available)
    weak = tuple(card.label for card in read_model.weak_skills)
    retention = tuple(card.label for card in read_model.retention_needed)
    transfer = tuple(card.label for card in read_model.transfer_needed)

    execution_mode = ""
    if resolution and resolution.is_task and resolution.execution_mode:
        execution_mode = student_safe_execution_mode(resolution.execution_mode)
    elif task_section.available:
        execution_mode = task_section.execution_mode

    task_context = task_section.context_descriptor if task_section.available else ""

    # Fingerprint: authoritative educational identity only (excludes copy/behavior text
    # so wording tweaks don't churn freshness, and excludes any timestamp).
    fingerprint_payload: dict[str, object] = {
        "v": ALEX_EDUCATIONAL_CONTEXT_VERSION,
        "official_cefr": read_model.official_cefr,
        "focus": read_model.focus_label,
        "objectives": list(read_model.objectives),
        "mission_kind": mission_kind,
        "mission_title": mission_section.title if mission_section.available else "",
        "mission_position": mission_section.position if mission_section.available else 0,
        "task_instruction": task_instruction,
        "execution_mode": execution_mode,
        "task_context": task_context,
        "has_task": has_current_task,
        "attempt_number": read_model.attempt.attempt_number if read_model.attempt.available else 0,
        "is_retry": read_model.attempt.is_retry if read_model.attempt.available else False,
        "weak": list(weak),
        "retention": list(retention),
        "transfer": list(transfer),
    }
    fingerprint = _fingerprint(fingerprint_payload)

    return AlexSpeakingEducationalContext(
        context_version=ALEX_EDUCATIONAL_CONTEXT_VERSION,
        context_fingerprint=fingerprint,
        official_cefr=read_model.official_cefr,
        focus_title=read_model.focus_label,
        focus_reason=read_model.focus_reason,
        learning_objectives=read_model.objectives,
        current_mission=mission_section.title if mission_section.available else "",
        current_mission_kind=mission_kind,
        current_mission_purpose=mission_section.purpose if mission_section.available else "",
        current_task_instruction=task_instruction,
        current_execution_mode=execution_mode,
        task_context=task_context,
        attempt_number=read_model.attempt.attempt_number if read_model.attempt.available else 0,
        is_retry=read_model.attempt.is_retry if read_model.attempt.available else False,
        support_available=support_available,
        weak_skill_focuses=weak,
        retention_focuses=retention,
        transfer_focuses=transfer,
        session_teaching_goal=blueprint.session_goal,
        tutor_behavior_contract=TUTOR_BEHAVIOR_CONTRACT,
        mission_behavior=mission_behavior_for_kind(mission_kind) if has_current_task else (),
        has_current_task=has_current_task,
    )
