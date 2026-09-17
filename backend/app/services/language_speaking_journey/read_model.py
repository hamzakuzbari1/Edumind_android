"""Speaking Journey/Home student-safe read model (S12).

Pure projection over existing authoritative state (S1/S2/S9/S10.1/S11).
No new learning authority. No stage / CEFR promotion / EVI budget / Alex time.

Known deferred S11 gaps (NOT fixed here — owner S14):
- C-3: advancing onto a non-task activity may leave the prior task attempt active
- C-7: malformed persisted lineage with multiple active attempts is not rejected on load;
  this read model fail-closes (omits attempt projection) rather than silently choosing one.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking.enums import (
    SpeakingExecutionMode,
    SpeakingLearningStage,
    SpeakingMissionKind,
    SpeakingTeachingBlockKind,
)
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_diagnostic.types import TargetSelectionReason
from app.services.language_speaking_knowledge_model.types import (
    SpeakingSkillStatus,
    StudentSpeakingKnowledgeModel,
    StudentSpeakingSkillState,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    SpeakingAttemptStatus,
    SpeakingSessionAttemptLineage,
    student_safe_attempt_projection,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import (
    SpeakingRuntimeTaskResolution,
    resolve_current_task,
)
from app.services.language_speaking_lesson_planner.mission_types import SpeakingMissionOutcome
from app.services.language_speaking_lesson_planner.storage import SpeakingStoredJourneyState
from app.services.language_speaking_lesson_planner.types import (
    SpeakingLearningPlan,
    SpeakingLearningSession,
    SpeakingLessonBlueprint,
    SpeakingSessionPhase,
)

LANGUAGE_SPEAKING_JOURNEY_READ_MODEL_VERSION = "12.2.1"

# Bounded-list policy — S12 must never grow with turn/eval/retry-chain history.
MAX_WEAK_SKILLS = 3
MAX_IMPROVING_SKILLS = 3
MAX_OBJECTIVES = 3
MAX_SUPPORT_ITEMS = 4
MAX_RETENTION_ITEMS = 3
MAX_TRANSFER_ITEMS = 2
MAX_PATH_STEPS = 12

# Deterministic derivation thresholds (aligned with diagnostic selector where applicable).
WEAK_MASTERY_THRESHOLD = 0.45
RETENTION_RISK_THRESHOLD = 0.62
IMPROVING_REVISION_THRESHOLD = 0.05
IMPROVING_RECENT_DELTA = 0.10
TRANSFER_MASTERY_THRESHOLD = 0.60

# --- Student-safe copy maps (deterministic, no AI) --------------------------------

FOCUS_REASON_COPY: dict[str, str] = {
    TargetSelectionReason.sparse_evidence_safe_start.value: (
        "We're starting with a clear, foundational skill because you're still building speaking evidence."
    ),
    TargetSelectionReason.weak_mastery.value: (
        "We're strengthening this skill because it still needs more consistent practice."
    ),
    TargetSelectionReason.at_risk_retention.value: (
        "We are reviewing this skill to help it stay strong over time."
    ),
    TargetSelectionReason.pronunciation_weakness.value: (
        "We're focusing here so your pronunciation can become clearer in everyday conversation."
    ),
    TargetSelectionReason.delivery_weakness.value: (
        "We're focusing here so your speaking delivery and flow feel more natural."
    ),
    TargetSelectionReason.task_weakness.value: (
        "We're focusing here so you can respond more clearly in real speaking tasks."
    ),
    TargetSelectionReason.reinforcement.value: (
        "We're reinforcing this skill so it becomes more automatic when you speak."
    ),
    TargetSelectionReason.progression_next.value: (
        "You are ready to use this skill in a more challenging context."
    ),
    TargetSelectionReason.remediation_follow_up.value: (
        "We're returning to this skill with extra support after a tough practice."
    ),
}
FOCUS_REASON_FALLBACK = "This is your current speaking focus based on your recent practice."

MISSION_PURPOSE_COPY: dict[str, str] = {
    SpeakingMissionKind.teaching.value: "Learn the idea before using it.",
    SpeakingMissionKind.noticing.value: "Notice how this speaking pattern works.",
    SpeakingMissionKind.guided_practice.value: "Practice with support.",
    SpeakingMissionKind.speak.value: "Use the skill in your own speaking.",
    SpeakingMissionKind.feedback.value: "Review what went well and what to improve.",
    SpeakingMissionKind.transfer.value: "Use the same skill in a new situation.",
    SpeakingMissionKind.retention_review.value: "Review the skill so it stays strong.",
}

MISSION_TITLE_COPY: dict[str, str] = {
    SpeakingMissionKind.teaching.value: "Learn",
    SpeakingMissionKind.noticing.value: "Notice",
    SpeakingMissionKind.guided_practice.value: "Guided practice",
    SpeakingMissionKind.speak.value: "Speak",
    SpeakingMissionKind.feedback.value: "Feedback",
    SpeakingMissionKind.transfer.value: "Transfer",
    SpeakingMissionKind.retention_review.value: "Review",
}

# Student-safe execution mode labels — never expose provider/impl enum names (e.g. live_evi_conversation).
EXECUTION_MODE_COPY: dict[str, str] = {
    SpeakingExecutionMode.study.value: "study",
    SpeakingExecutionMode.controlled_response.value: "guided_response",
    SpeakingExecutionMode.recorded_response.value: "recorded_speaking",
    SpeakingExecutionMode.live_evi_conversation.value: "talk_with_alex",
    SpeakingExecutionMode.review.value: "review",
}

SUPPORT_ITEM_COPY: dict[str, str] = {
    "explanation": "Explanation",
    "examples": "Examples",
    "guided_help": "Guided help",
    "retry_support": "Another chance to improve",
}

MISTAKE_FOCUS_COPY: dict[str, str] = {
    "pronunciation": "Pronunciation clarity",
    "delivery": "Sentence flow",
    "fluency": "Speaking fluency",
    "task": "Task response clarity",
    "grammar": "Grammar accuracy",
    "vocabulary": "Word choice",
    "past": "Past tense clarity",
    "opinion": "Supporting your opinion",
}


@dataclass(frozen=True, slots=True)
class SpeakingJourneySkillCard:
    label: str
    improvement_focus: str = ""

    def to_student_dict(self) -> dict[str, object]:
        out: dict[str, object] = {"label": self.label}
        if self.improvement_focus:
            out["improvement_focus"] = self.improvement_focus
        return out


@dataclass(frozen=True, slots=True)
class SpeakingJourneySupportItem:
    kind: str
    label: str
    available: bool
    applied: bool = False  # applied support requires runtime evidence; always False in S12

    def to_student_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "label": self.label,
            "available": self.available,
            "applied": self.applied,
        }


@dataclass(frozen=True, slots=True)
class SpeakingJourneyPathStep:
    title: str
    purpose: str
    status: str  # done | active | upcoming
    is_task_bearing: bool

    def to_student_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "purpose": self.purpose,
            "status": self.status,
            "is_task_bearing": self.is_task_bearing,
        }


@dataclass(frozen=True, slots=True)
class SpeakingJourneyMissionSection:
    available: bool
    title: str = ""
    purpose: str = ""
    position: int = 0
    total: int = 0
    is_executable: bool = False
    execution_mode: str = ""
    uses_alex: bool = False

    def to_student_dict(self) -> dict[str, object] | None:
        if not self.available:
            return None
        return {
            "title": self.title,
            "purpose": self.purpose,
            "position": self.position,
            "total": self.total,
            "is_executable": self.is_executable,
            "execution_mode": self.execution_mode,
            "uses_alex": self.uses_alex,
        }


@dataclass(frozen=True, slots=True)
class SpeakingJourneyTaskSection:
    available: bool
    instruction: str = ""
    execution_mode: str = ""
    context_descriptor: str = ""
    uses_alex: bool = False
    recording_required: bool = False
    controlled_required: bool = False

    def to_student_dict(self) -> dict[str, object] | None:
        if not self.available:
            return None
        out: dict[str, object] = {
            "instruction": self.instruction,
            "execution_mode": self.execution_mode,
            "uses_alex": self.uses_alex,
            "recording_required": self.recording_required,
            "controlled_required": self.controlled_required,
        }
        if self.context_descriptor:
            out["context_descriptor"] = self.context_descriptor
        return out


@dataclass(frozen=True, slots=True)
class SpeakingJourneyAttemptSection:
    available: bool
    attempt_number: int = 0
    is_retry: bool = False
    completed_task_attempt_count: int = 0
    message: str = ""

    def to_student_dict(self) -> dict[str, object] | None:
        if not self.available:
            return None
        return {
            "attempt_number": self.attempt_number,
            "is_retry": self.is_retry,
            "completed_task_attempt_count": self.completed_task_attempt_count,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class SpeakingJourneyNextSection:
    available: bool
    title: str = ""
    purpose: str = ""
    is_task_bearing: bool = False

    def to_student_dict(self) -> dict[str, object] | None:
        if not self.available:
            return None
        return {
            "title": self.title,
            "purpose": self.purpose,
            "is_task_bearing": self.is_task_bearing,
        }


@dataclass(frozen=True, slots=True)
class SpeakingJourneyTeachingBlock:
    kind: str
    title: str
    body: str

    def to_student_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
        }


@dataclass(frozen=True, slots=True)
class SpeakingJourneyReadModel:
    """Authoritative student-safe Speaking Journey/Home read model (S12)."""

    version: str
    official_cefr: str
    # Student-safe stage label (e.g. "A2 Foundation") from persisted learning_stage_speaking.
    internal_stage: str | None
    # S17 student-safe promotion readiness projection (no thresholds/fingerprints).
    promotion_readiness: dict[str, object] | None
    # S13 populates this from the live-budget owner; None when unavailable.
    alex_daily_remaining_seconds: int | None
    focus_label: str
    focus_reason: str
    expected_outcome: str
    objectives: tuple[str, ...]
    has_active_session: bool
    has_plan: bool
    has_blueprint: bool
    learning_path: tuple[SpeakingJourneyPathStep, ...]
    current_mission: SpeakingJourneyMissionSection
    current_task: SpeakingJourneyTaskSection
    attempt: SpeakingJourneyAttemptSection
    support: tuple[SpeakingJourneySupportItem, ...]
    teaching_blocks: tuple[SpeakingJourneyTeachingBlock, ...]
    weak_skills: tuple[SpeakingJourneySkillCard, ...]
    improving_skills: tuple[SpeakingJourneySkillCard, ...]
    retention_needed: tuple[SpeakingJourneySkillCard, ...]
    transfer_needed: tuple[SpeakingJourneySkillCard, ...]
    next_mission: SpeakingJourneyNextSection
    # Availability flags for truthful missing-data handling.
    improving_skills_available: bool
    retention_signal_present: bool
    transfer_signal_present: bool

    def to_student_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "official_cefr": self.official_cefr,
            "internal_stage": self.internal_stage,
            "promotion_readiness": self.promotion_readiness,
            "alex_daily_remaining_seconds": self.alex_daily_remaining_seconds,
            "focus_label": self.focus_label,
            "focus_reason": self.focus_reason,
            "expected_outcome": self.expected_outcome,
            "objectives": list(self.objectives),
            "has_active_session": self.has_active_session,
            "has_plan": self.has_plan,
            "has_blueprint": self.has_blueprint,
            "learning_path": [s.to_student_dict() for s in self.learning_path],
            "current_mission": self.current_mission.to_student_dict(),
            "current_task": self.current_task.to_student_dict(),
            "attempt": self.attempt.to_student_dict(),
            "support": [s.to_student_dict() for s in self.support],
            "teaching_blocks": [b.to_student_dict() for b in self.teaching_blocks],
            "weak_skills": [s.to_student_dict() for s in self.weak_skills],
            "improving_skills": [s.to_student_dict() for s in self.improving_skills],
            "retention_needed": [s.to_student_dict() for s in self.retention_needed],
            "transfer_needed": [s.to_student_dict() for s in self.transfer_needed],
            "next_mission": self.next_mission.to_student_dict(),
            "improving_skills_available": self.improving_skills_available,
            "retention_signal_present": self.retention_signal_present,
            "transfer_signal_present": self.transfer_signal_present,
        }


def _skill_label(skill_id: str) -> str:
    node = SPEAKING_SKILL_GRAPH.node_by_id(skill_id)
    return node.label if node else skill_id.replace("_", " ").replace(":", " — ").title()


def _focus_reason_copy(selection_reason: str) -> str:
    return FOCUS_REASON_COPY.get(selection_reason, FOCUS_REASON_FALLBACK)


def _mission_purpose(kind: str) -> str:
    return MISSION_PURPOSE_COPY.get(kind, "Continue your speaking practice.")


def _mission_title(kind: str, fallback: str = "") -> str:
    return MISSION_TITLE_COPY.get(kind, fallback or kind.replace("_", " ").title())


def _execution_mode_copy(mode: str | SpeakingExecutionMode) -> str:
    value = mode.value if isinstance(mode, SpeakingExecutionMode) else str(mode)
    return EXECUTION_MODE_COPY.get(value, "speaking")


# Public alias used by journey bundle assembly.
student_safe_execution_mode = _execution_mode_copy


def _student_safe_context(descriptor: str) -> str:
    """Only expose known student-safe context descriptors; hide internal keys."""
    mapping = {
        "changed_topic_context": "A new topic",
        "spaced_review": "A spaced review",
    }
    return mapping.get(descriptor, "")


def _improvement_focus_from_tags(tags: list[str] | tuple[str, ...]) -> str:
    for tag in tags:
        lower = tag.lower()
        for key, label in MISTAKE_FOCUS_COPY.items():
            if key in lower:
                return label
    return "Clearer speaking"


def _attempt_message(*, attempt_number: int, is_retry: bool) -> str:
    if is_retry or attempt_number > 1:
        return "You're trying this task again with another chance to improve."
    if attempt_number == 1:
        return "First try — focus on using the skill naturally."
    return ""


def _lineage_has_ambiguous_active(lineage: SpeakingSessionAttemptLineage | None) -> bool:
    """C-7 fail-closed: more than one attempt with status=active is malformed."""
    if lineage is None:
        return False
    active_count = sum(1 for a in lineage.attempts if a.status is SpeakingAttemptStatus.active)
    return active_count > 1


def _is_weak(state: StudentSpeakingSkillState) -> bool:
    if state.current_status in (SpeakingSkillStatus.at_risk, SpeakingSkillStatus.developing):
        return True
    return state.evidence_count > 0 and state.mastery < WEAK_MASTERY_THRESHOLD


def _is_improving(state: StudentSpeakingSkillState) -> bool:
    if state.revision_improvement >= IMPROVING_REVISION_THRESHOLD:
        return True
    if (
        state.evidence_count >= 2
        and state.consecutive_successes >= 1
        and (state.recent_performance - state.mastery) >= IMPROVING_RECENT_DELTA
    ):
        return True
    return False


def _needs_retention(state: StudentSpeakingSkillState) -> bool:
    if state.current_status is SpeakingSkillStatus.at_risk:
        return True
    return state.retention_risk >= RETENTION_RISK_THRESHOLD


def _needs_transfer(state: StudentSpeakingSkillState) -> bool:
    well_learned = (
        state.mastery >= TRANSFER_MASTERY_THRESHOLD
        or state.current_status in (SpeakingSkillStatus.stable, SpeakingSkillStatus.mastered)
    )
    return well_learned and state.evidence_count >= 2 and state.distinct_context_count <= 1


def derive_weak_skills(
    model: StudentSpeakingKnowledgeModel | None,
    *,
    limit: int = MAX_WEAK_SKILLS,
) -> tuple[SpeakingJourneySkillCard, ...]:
    if model is None:
        return ()
    ranked: list[tuple[float, SpeakingJourneySkillCard]] = []
    for sid, st in model.skill_states.items():
        if not _is_weak(st):
            continue
        # Prefer at_risk over developing; prefer lower mastery.
        priority = (0.0 if st.current_status is SpeakingSkillStatus.at_risk else 1.0) + st.mastery
        ranked.append(
            (
                priority,
                SpeakingJourneySkillCard(
                    label=_skill_label(sid),
                    improvement_focus=_improvement_focus_from_tags(st.recent_mistake_tags),
                ),
            )
        )
    ranked.sort(key=lambda x: (x[0], x[1].label))
    return tuple(card for _, card in ranked[:limit])


def derive_improving_skills(
    model: StudentSpeakingKnowledgeModel | None,
    *,
    limit: int = MAX_IMPROVING_SKILLS,
) -> tuple[SpeakingJourneySkillCard, ...]:
    """Deterministic: based on revision_improvement / recent-vs-mastery delta + history."""
    if model is None:
        return ()
    ranked: list[tuple[float, SpeakingJourneySkillCard]] = []
    for sid, st in model.skill_states.items():
        if not _is_improving(st):
            continue
        score = max(st.revision_improvement, st.recent_performance - st.mastery)
        ranked.append((score, SpeakingJourneySkillCard(label=_skill_label(sid), improvement_focus="Keep building on recent progress")))
    ranked.sort(key=lambda x: (-x[0], x[1].label))
    return tuple(card for _, card in ranked[:limit])


def derive_retention_needed(
    model: StudentSpeakingKnowledgeModel | None,
    *,
    selection_reason: str = "",
    primary_skill_id: str = "",
    limit: int = MAX_RETENTION_ITEMS,
) -> tuple[SpeakingJourneySkillCard, ...]:
    cards: list[SpeakingJourneySkillCard] = []
    seen: set[str] = set()
    if model is not None:
        ranked: list[tuple[float, str, SpeakingJourneySkillCard]] = []
        for sid, st in model.skill_states.items():
            if not _needs_retention(st):
                continue
            ranked.append(
                (
                    -st.retention_risk,
                    sid,
                    SpeakingJourneySkillCard(
                        label=_skill_label(sid),
                        improvement_focus="Let's revisit this skill to help it stay strong.",
                    ),
                )
            )
        ranked.sort(key=lambda x: (x[0], x[1]))
        for _, sid, card in ranked:
            if sid in seen:
                continue
            seen.add(sid)
            cards.append(card)
            if len(cards) >= limit:
                return tuple(cards)
    # Explicit at_risk_retention focus signal even if skill state is sparse.
    if (
        selection_reason == TargetSelectionReason.at_risk_retention.value
        and primary_skill_id
        and primary_skill_id not in seen
        and len(cards) < limit
    ):
        cards.append(
            SpeakingJourneySkillCard(
                label=_skill_label(primary_skill_id),
                improvement_focus="Let's revisit this skill to help it stay strong.",
            )
        )
    return tuple(cards[:limit])


def derive_transfer_needed(
    model: StudentSpeakingKnowledgeModel | None,
    *,
    limit: int = MAX_TRANSFER_ITEMS,
) -> tuple[SpeakingJourneySkillCard, ...]:
    """Context-diversity signal only — not inferred from transfer mission presence."""
    if model is None:
        return ()
    ranked: list[tuple[int, str, SpeakingJourneySkillCard]] = []
    for sid, st in model.skill_states.items():
        if not _needs_transfer(st):
            continue
        ranked.append(
            (
                st.distinct_context_count,
                sid,
                SpeakingJourneySkillCard(
                    label=_skill_label(sid),
                    improvement_focus="Try this skill in a new situation.",
                ),
            )
        )
    ranked.sort(key=lambda x: (x[0], x[1]))
    return tuple(card for _, _, card in ranked[:limit])


def _support_items(
    blueprint: SpeakingLessonBlueprint | None,
    resolution: SpeakingRuntimeTaskResolution | None,
) -> tuple[SpeakingJourneySupportItem, ...]:
    if blueprint is None:
        return ()
    mission = None
    if resolution and resolution.mission_id:
        mission = next((m for m in blueprint.educational_missions if m.mission_id == resolution.mission_id), None)
    # Fall back to first content-bearing mission for availability when cursor is mid-path.
    if mission is None and blueprint.educational_missions:
        mission = next((m for m in blueprint.educational_missions if m.teaching_blocks), None) or blueprint.educational_missions[0]

    kinds_present = {b.kind for b in (mission.teaching_blocks if mission else ())}
    items: list[SpeakingJourneySupportItem] = []
    if SpeakingTeachingBlockKind.explanation in kinds_present or SpeakingTeachingBlockKind.misconception_correction in kinds_present:
        items.append(SpeakingJourneySupportItem(kind="explanation", label=SUPPORT_ITEM_COPY["explanation"], available=True, applied=False))
    if SpeakingTeachingBlockKind.example in kinds_present or SpeakingTeachingBlockKind.contrast in kinds_present:
        items.append(SpeakingJourneySupportItem(kind="examples", label=SUPPORT_ITEM_COPY["examples"], available=True, applied=False))
    if SpeakingTeachingBlockKind.scaffold in kinds_present or SpeakingTeachingBlockKind.guided_prompt in kinds_present:
        items.append(SpeakingJourneySupportItem(kind="guided_help", label=SUPPORT_ITEM_COPY["guided_help"], available=True, applied=False))
    retry_policy = (mission.retry_policy if mission else SpeakingMissionOutcome.proceed)
    if retry_policy in (SpeakingMissionOutcome.retry_same_task, SpeakingMissionOutcome.retry_with_scaffold):
        items.append(SpeakingJourneySupportItem(kind="retry_support", label=SUPPORT_ITEM_COPY["retry_support"], available=True, applied=False))
    return tuple(items[:MAX_SUPPORT_ITEMS])


def _teaching_blocks(
    blueprint: SpeakingLessonBlueprint | None,
    resolution: SpeakingRuntimeTaskResolution | None,
) -> tuple[SpeakingJourneyTeachingBlock, ...]:
    """Project teaching-block bodies (no internal ids) for the current/next content mission."""
    if blueprint is None or not blueprint.educational_missions:
        return ()
    mission = None
    if resolution and resolution.mission_id:
        mission = next(
            (m for m in blueprint.educational_missions if m.mission_id == resolution.mission_id),
            None,
        )
    if mission is None or not mission.teaching_blocks:
        mission = next(
            (m for m in sorted(blueprint.educational_missions, key=lambda m: m.order_index) if m.teaching_blocks),
            None,
        )
    if mission is None:
        return ()
    blocks: list[SpeakingJourneyTeachingBlock] = []
    for block in mission.teaching_blocks:
        body = (block.body or "").strip()
        title = (block.title or "").strip()
        if not body and not title:
            continue
        blocks.append(
            SpeakingJourneyTeachingBlock(
                kind=block.kind.value if hasattr(block.kind, "value") else str(block.kind),
                title=title or block.kind.value.replace("_", " ").title(),
                body=body,
            )
        )
        if len(blocks) >= MAX_SUPPORT_ITEMS:
            break
    return tuple(blocks)


def _path_steps(
    blueprint: SpeakingLessonBlueprint | None,
    resolution: SpeakingRuntimeTaskResolution | None,
) -> tuple[SpeakingJourneyPathStep, ...]:
    if blueprint is None or not blueprint.educational_missions:
        return ()
    current_id = resolution.mission_id if resolution and resolution.mission_id else ""
    found_current = False
    steps: list[SpeakingJourneyPathStep] = []
    for mission in sorted(blueprint.educational_missions, key=lambda m: m.order_index):
        kind = mission.mission_kind.value
        if current_id and mission.mission_id == current_id:
            status = "active"
            found_current = True
        elif not found_current and current_id:
            status = "done"
        elif not current_id:
            status = "upcoming"
        else:
            status = "upcoming"
        steps.append(
            SpeakingJourneyPathStep(
                title=_mission_title(kind, mission.title),
                purpose=_mission_purpose(kind),
                status=status,
                is_task_bearing=mission.is_executable,
            )
        )
    return tuple(steps[:MAX_PATH_STEPS])


def _current_mission_section(
    blueprint: SpeakingLessonBlueprint | None,
    resolution: SpeakingRuntimeTaskResolution | None,
) -> SpeakingJourneyMissionSection:
    if blueprint is None or not blueprint.educational_missions:
        return SpeakingJourneyMissionSection(available=False)
    missions = sorted(blueprint.educational_missions, key=lambda m: m.order_index)
    total = len(missions)
    mission = None
    position = 0
    if resolution and resolution.mission_id:
        for idx, m in enumerate(missions, start=1):
            if m.mission_id == resolution.mission_id:
                mission = m
                position = idx
                break
    if mission is None:
        # Non-task cursor (e.g. warmup) — no current educational mission claimed.
        return SpeakingJourneyMissionSection(available=False)
    kind = mission.mission_kind.value
    return SpeakingJourneyMissionSection(
        available=True,
        title=_mission_title(kind, mission.title),
        purpose=_mission_purpose(kind),
        position=position,
        total=total,
        is_executable=mission.is_executable,
        execution_mode=_execution_mode_copy(mission.execution_mode),
        uses_alex=mission.execution_mode is SpeakingExecutionMode.live_evi_conversation,
    )


def _current_task_section(
    blueprint: SpeakingLessonBlueprint | None,
    resolution: SpeakingRuntimeTaskResolution | None,
) -> SpeakingJourneyTaskSection:
    if blueprint is None or resolution is None or not resolution.is_task:
        return SpeakingJourneyTaskSection(available=False)
    mission = next((m for m in blueprint.educational_missions if m.mission_id == resolution.mission_id), None)
    task = None
    if mission:
        task = next((t for t in mission.tasks if t.task_id == resolution.task_id), None)
        if task is None and mission.tasks:
            task = mission.tasks[0]
    if task is None:
        return SpeakingJourneyTaskSection(available=False)
    mode = SpeakingExecutionMode(resolution.execution_mode) if resolution.execution_mode else task.execution_mode
    return SpeakingJourneyTaskSection(
        available=True,
        instruction=task.prompt or (mission.learner_instructions if mission else ""),
        execution_mode=_execution_mode_copy(mode),
        context_descriptor=_student_safe_context(task.context_descriptor),
        uses_alex=mode is SpeakingExecutionMode.live_evi_conversation,
        recording_required=mode is SpeakingExecutionMode.recorded_response,
        controlled_required=mode is SpeakingExecutionMode.controlled_response,
    )


def _attempt_section(
    lineage: SpeakingSessionAttemptLineage | None,
    resolution: SpeakingRuntimeTaskResolution | None,
    *,
    has_active_session: bool,
) -> SpeakingJourneyAttemptSection:
    if not has_active_session:
        return SpeakingJourneyAttemptSection(available=False)
    if _lineage_has_ambiguous_active(lineage):
        # C-7 fail-closed — do not silently choose an arbitrary attempt.
        return SpeakingJourneyAttemptSection(available=False)
    if resolution is None or not resolution.is_task:
        return SpeakingJourneyAttemptSection(available=False)
    proj = student_safe_attempt_projection(lineage, task_id=resolution.task_id)
    number = int(proj["current_attempt_number"])
    if number <= 0:
        return SpeakingJourneyAttemptSection(available=False)
    is_retry = bool(proj["is_retry"])
    return SpeakingJourneyAttemptSection(
        available=True,
        attempt_number=number,
        is_retry=is_retry,
        completed_task_attempt_count=int(proj["completed_task_attempt_count"]),
        message=_attempt_message(attempt_number=number, is_retry=is_retry),
    )


def _next_mission_section(
    blueprint: SpeakingLessonBlueprint | None,
    resolution: SpeakingRuntimeTaskResolution | None,
) -> SpeakingJourneyNextSection:
    if blueprint is None or not blueprint.educational_missions:
        return SpeakingJourneyNextSection(available=False)
    missions = sorted(blueprint.educational_missions, key=lambda m: m.order_index)
    if resolution and resolution.mission_id:
        idx = next((i for i, m in enumerate(missions) if m.mission_id == resolution.mission_id), -1)
        nxt = missions[idx + 1] if 0 <= idx < len(missions) - 1 else None
    else:
        nxt = missions[0] if missions else None
    if nxt is None:
        return SpeakingJourneyNextSection(available=False)
    kind = nxt.mission_kind.value
    return SpeakingJourneyNextSection(
        available=True,
        title=_mission_title(kind, nxt.title),
        purpose=_mission_purpose(kind),
        is_task_bearing=nxt.is_executable,
    )


_STAGE_LABELS: dict[SpeakingLearningStage, str] = {
    SpeakingLearningStage.foundation: "Foundation",
    SpeakingLearningStage.developing: "Developing",
    SpeakingLearningStage.advanced: "Advanced",
}


def student_safe_internal_stage_label(
    *,
    official_cefr: str,
    learning_stage_speaking: int | SpeakingLearningStage | None,
) -> str | None:
    """CEFR-relative student-safe stage label. Never exposes thresholds or fingerprints."""
    if learning_stage_speaking is None:
        return None
    try:
        stage = SpeakingLearningStage(max(1, min(3, int(learning_stage_speaking))))
    except (TypeError, ValueError):
        return None
    cefr = (official_cefr or "A2").upper()
    return f"{cefr} {_STAGE_LABELS[stage]}"


def build_speaking_journey_read_model(
    *,
    official_cefr: str,
    state: SpeakingStoredJourneyState | None,
    knowledge_model: StudentSpeakingKnowledgeModel | None = None,
    alex_daily_remaining_seconds: int | None = None,
    learning_stage_speaking: int | SpeakingLearningStage | None = None,
    promotion_readiness: dict[str, object] | None = None,
) -> SpeakingJourneyReadModel:
    """Build the authoritative student-safe Speaking Journey/Home read model.

    ``alex_daily_remaining_seconds`` is owned by S13 live budget. Pass None
    when budget state cannot be loaded — never invent 600.
    ``learning_stage_speaking`` is the persisted S16 stage column (defaults to
    Foundation=1 when present on the progression row).
    """
    plan: SpeakingLearningPlan | None = state.plan if state else None
    blueprint: SpeakingLessonBlueprint | None = state.blueprint if state else None
    session: SpeakingLearningSession | None = state.session if state else None
    lineage: SpeakingSessionAttemptLineage | None = state.attempt_lineage if state else None

    has_plan = plan is not None
    has_blueprint = blueprint is not None
    has_active_session = session is not None and session.phase != SpeakingSessionPhase.completed

    focus_label = plan.primary_target_label if plan else ""
    if not focus_label and blueprint:
        focus_label = _skill_label(blueprint.primary_target_skill_id)
    if not focus_label:
        focus_label = "Speaking foundations"

    selection_reason = (plan.selection_reason if plan else "") or (blueprint.selection_reason if blueprint else "")
    focus_reason = _focus_reason_copy(selection_reason) if (has_plan or has_blueprint) else ""

    objectives: list[str] = []
    expected_outcome = ""
    if blueprint:
        for mission in sorted(blueprint.educational_missions, key=lambda m: m.order_index):
            for obj in mission.objectives:
                text = obj.student_objective_text.strip()
                if text and text not in objectives:
                    objectives.append(text)
                if not expected_outcome and obj.expected_outcome:
                    expected_outcome = obj.expected_outcome.strip()
                if len(objectives) >= MAX_OBJECTIVES:
                    break
            if len(objectives) >= MAX_OBJECTIVES:
                break

    resolution: SpeakingRuntimeTaskResolution | None = None
    if blueprint and session and has_active_session:
        resolution = resolve_current_task(blueprint, session)
    elif blueprint:
        # No active session — do not invent current mission/task from cursor.
        resolution = None

    primary_skill_id = (plan.primary_target_skill_id if plan else "") or (
        blueprint.primary_target_skill_id if blueprint else ""
    )

    weak = derive_weak_skills(knowledge_model)
    improving = derive_improving_skills(knowledge_model)
    retention = derive_retention_needed(
        knowledge_model,
        selection_reason=selection_reason,
        primary_skill_id=primary_skill_id,
    )
    transfer = derive_transfer_needed(knowledge_model)

    return SpeakingJourneyReadModel(
        version=LANGUAGE_SPEAKING_JOURNEY_READ_MODEL_VERSION,
        official_cefr=official_cefr or "A2",
        internal_stage=student_safe_internal_stage_label(
            official_cefr=official_cefr or "A2",
            learning_stage_speaking=learning_stage_speaking,
        ),
        promotion_readiness=promotion_readiness,
        alex_daily_remaining_seconds=alex_daily_remaining_seconds,
        focus_label=focus_label,
        focus_reason=focus_reason,
        expected_outcome=expected_outcome,
        objectives=tuple(objectives[:MAX_OBJECTIVES]),
        has_active_session=has_active_session,
        has_plan=has_plan,
        has_blueprint=has_blueprint,
        learning_path=_path_steps(blueprint, resolution),
        current_mission=_current_mission_section(blueprint, resolution),
        current_task=_current_task_section(blueprint, resolution),
        attempt=_attempt_section(lineage, resolution, has_active_session=has_active_session),
        support=_support_items(blueprint, resolution),
        teaching_blocks=_teaching_blocks(blueprint, resolution),
        weak_skills=weak,
        improving_skills=improving,
        retention_needed=retention,
        transfer_needed=transfer,
        next_mission=_next_mission_section(blueprint, resolution),
        improving_skills_available=knowledge_model is not None,
        retention_signal_present=len(retention) > 0,
        transfer_signal_present=len(transfer) > 0,
    )
