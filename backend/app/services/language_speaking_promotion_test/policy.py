"""Deterministic SPA composition, coverage, and capability policy (S18).

AI must never choose CEFR, skills, families, thresholds, or promotion outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.language_speaking.enums import SpeakingSkillType, SpeakingTaskType
from app.services.language_speaking_curriculum.skill_catalog import SPEAKING_SKILL_GRAPH
from app.services.language_speaking_curriculum.types import SpeakingSkillNode

SPA_POLICY_VERSION = "18.0.0"
SPA_SCHEMA_VERSION = "18.0.0"
SPA_COMPOSITION_VERSION = "18.0.0"
CURRICULUM_VERSION_PIN = SPEAKING_SKILL_GRAPH.version

# Bounded JSONB retention — never an unbounded blueprints_by_id archive.
MAX_PERSISTED_BLUEPRINTS = 2  # active + most_recent_terminal

GENERATION_MAX_RETRIES = 2
SPA_TASK_COUNT = 5

# S18 recorded-only SPA does not require interaction evidence (and cannot claim it).
SPA_REQUIRES_INTERACTION_EVIDENCE = False

CORE_DIFFICULTY_FLOOR = 2
MIN_DISTINCT_SKILL_IDS = 3
MAX_SHARE_PER_SKILL = 2  # max tasks claiming the same skill id
MAX_SHARE_PER_SKILL_TYPE = 3

MIN_DURATION_SECONDS = 30
MAX_DURATION_SECONDS = 180
DEFAULT_DURATION_SECONDS = 90
MAX_FOLLOW_UP_PROMPTS = 3
MAX_PREPARATION_SECONDS = 60

# Evidence quarantine label for S19 (S18 contracts only — no S8 apply).
EVIDENCE_SOURCE_PROMOTION_ASSESSMENT = "promotion_assessment"

# Skill types that fundamentally require interactive turn-taking.
INTERACTIVE_SKILL_TYPES: frozenset[SpeakingSkillType] = frozenset(
    {
        SpeakingSkillType.interaction_skill,
        SpeakingSkillType.conversation_skill,
    }
)

# Activity types evaluable via recorded monologue / controlled response (S7 audio path).
PRODUCTION_COMPATIBLE_ACTIVITIES: frozenset[SpeakingTaskType] = frozenset(
    {
        SpeakingTaskType.monologue,
        SpeakingTaskType.picture_description,
        SpeakingTaskType.pronunciation_drill,
        SpeakingTaskType.shadowing,
    }
)

INTERACTIVE_SPEAKING_FUNCTIONS: frozenset[str] = frozenset(
    {
        "clarification_request",
        "interaction",
        "repair",
        "turn_taking",
    }
)

PROHIBITED_SUPPORT_MARKERS: frozenset[str] = frozenset(
    {
        "model answer",
        "sample answer key",
        "pass threshold",
        "mark as",
        "score as",
        "ignore rules",
        "promote to",
        "official cefr",
        "spa_pass",
        "overall_passed",
    }
)


class SpaTaskFamily(StrEnum):
    controlled_response = "controlled_response"
    picture_or_situation_description = "picture_or_situation_description"
    opinion_explanation = "opinion_explanation"
    transfer_new_context = "transfer_new_context"
    spontaneous_unprepared = "spontaneous_unprepared"


class SpaExecutionMode(StrEnum):
    controlled_response = "controlled_response"
    recorded_response = "recorded_response"


class SpaCapabilityKind(StrEnum):
    """Truthful evaluator capability claims."""

    spontaneous_production = "spontaneous_production"
    spontaneous_interaction = "spontaneous_interaction"
    controlled_production = "controlled_production"
    extended_production = "extended_production"
    opinion_reasoning = "opinion_reasoning"
    transfer_production = "transfer_production"


class SpaSkillEvaluatorCompatibility(StrEnum):
    production_compatible = "production_compatible"
    interaction_required = "interaction_required"
    unsupported = "unsupported"


@dataclass(frozen=True, slots=True)
class SpaTaskSlotPolicy:
    task_order: int
    task_family: SpaTaskFamily
    execution_mode: SpaExecutionMode
    proves_capabilities: frozenset[SpaCapabilityKind]
    spontaneous_production_required: bool
    spontaneous_interaction_required: bool
    preparation_seconds: int
    max_duration_seconds: int
    min_follow_ups: int
    max_follow_ups: int
    preferred_skill_types: frozenset[SpeakingSkillType]


# Fixed composition — not an AI choice range.
SPA_TASK_SLOTS: tuple[SpaTaskSlotPolicy, ...] = (
    SpaTaskSlotPolicy(
        task_order=1,
        task_family=SpaTaskFamily.controlled_response,
        execution_mode=SpaExecutionMode.controlled_response,
        proves_capabilities=frozenset({SpaCapabilityKind.controlled_production}),
        spontaneous_production_required=False,
        spontaneous_interaction_required=False,
        preparation_seconds=15,
        max_duration_seconds=60,
        min_follow_ups=0,
        max_follow_ups=1,
        preferred_skill_types=frozenset(
            {
                SpeakingSkillType.phrase,
                SpeakingSkillType.speaking_function,
                SpeakingSkillType.vocabulary_function,
                SpeakingSkillType.grammar_structure,
            }
        ),
    ),
    SpaTaskSlotPolicy(
        task_order=2,
        task_family=SpaTaskFamily.picture_or_situation_description,
        execution_mode=SpaExecutionMode.recorded_response,
        proves_capabilities=frozenset({SpaCapabilityKind.extended_production}),
        spontaneous_production_required=False,
        spontaneous_interaction_required=False,
        preparation_seconds=30,
        max_duration_seconds=120,
        min_follow_ups=0,
        max_follow_ups=2,
        preferred_skill_types=frozenset(
            {
                SpeakingSkillType.task_skill,
                SpeakingSkillType.fluency_skill,
                SpeakingSkillType.speaking_function,
                SpeakingSkillType.prosody_skill,
            }
        ),
    ),
    SpaTaskSlotPolicy(
        task_order=3,
        task_family=SpaTaskFamily.opinion_explanation,
        execution_mode=SpaExecutionMode.recorded_response,
        proves_capabilities=frozenset({SpaCapabilityKind.opinion_reasoning}),
        spontaneous_production_required=False,
        spontaneous_interaction_required=False,
        preparation_seconds=20,
        max_duration_seconds=120,
        min_follow_ups=0,
        max_follow_ups=2,
        preferred_skill_types=frozenset(
            {
                SpeakingSkillType.speaking_function,
                SpeakingSkillType.vocabulary_function,
                SpeakingSkillType.grammar_structure,
                SpeakingSkillType.fluency_skill,
            }
        ),
    ),
    SpaTaskSlotPolicy(
        task_order=4,
        task_family=SpaTaskFamily.transfer_new_context,
        execution_mode=SpaExecutionMode.recorded_response,
        proves_capabilities=frozenset({SpaCapabilityKind.transfer_production}),
        spontaneous_production_required=False,
        spontaneous_interaction_required=False,
        preparation_seconds=20,
        max_duration_seconds=120,
        min_follow_ups=0,
        max_follow_ups=2,
        preferred_skill_types=frozenset(
            {
                SpeakingSkillType.task_skill,
                SpeakingSkillType.speaking_function,
                SpeakingSkillType.fluency_skill,
                SpeakingSkillType.phrase,
            }
        ),
    ),
    SpaTaskSlotPolicy(
        task_order=5,
        task_family=SpaTaskFamily.spontaneous_unprepared,
        execution_mode=SpaExecutionMode.recorded_response,
        proves_capabilities=frozenset({SpaCapabilityKind.spontaneous_production}),
        # Recorded unprepared response = spontaneous spoken PRODUCTION only.
        # Must NEVER be documented as spontaneous INTERACTION proof.
        spontaneous_production_required=True,
        spontaneous_interaction_required=False,
        preparation_seconds=0,
        max_duration_seconds=90,
        min_follow_ups=0,
        max_follow_ups=0,
        preferred_skill_types=frozenset(
            {
                SpeakingSkillType.fluency_skill,
                SpeakingSkillType.speaking_function,
                SpeakingSkillType.task_skill,
                SpeakingSkillType.prosody_skill,
            }
        ),
    ),
)


def _cefr_rank(level: str) -> int:
    order = ("A1", "A2", "B1", "B2", "C1", "C2")
    key = level.upper()[:2] if len(level) > 2 else level.upper()
    try:
        return order.index(key)
    except ValueError:
        return -1


def skill_within_official_cefr(node: SpeakingSkillNode, official_cefr: str) -> bool:
    rank = _cefr_rank(official_cefr)
    if rank < 0:
        return False
    return _cefr_rank(node.cefr_min.value) <= rank <= _cefr_rank(node.cefr_max.value)


def curriculum_skills_for_official_cefr(
    official_cefr: str,
    *,
    graph=SPEAKING_SKILL_GRAPH,
) -> tuple[SpeakingSkillNode, ...]:
    return tuple(
        sorted(
            (n for n in graph.nodes if skill_within_official_cefr(n, official_cefr)),
            key=lambda n: (n.difficulty, n.skill_id),
        )
    )


def core_curriculum_skills(
    nodes: tuple[SpeakingSkillNode, ...],
    *,
    difficulty_floor: int = CORE_DIFFICULTY_FLOOR,
) -> tuple[SpeakingSkillNode, ...]:
    return tuple(n for n in nodes if n.is_root or n.difficulty <= difficulty_floor)


def skill_requires_interactive_evaluation(node: SpeakingSkillNode) -> bool:
    """True when the skill fundamentally needs interactive turn-taking to evaluate truthfully.

    Dialogue-preferred activity tags alone are NOT enough — many catalog nodes list
    dialogue as a preferred practice mode while remaining evaluable via recorded
    production. Interaction is required only when the skill itself demands
    turn-taking, clarification, repair, reactive follow-up, or conversational adaptation.
    """
    if node.skill_type in INTERACTIVE_SKILL_TYPES:
        return True
    mr = node.mastery_requirements
    if mr.minimum_interaction_turns is not None:
        return True
    if any(f in INTERACTIVE_SPEAKING_FUNCTIONS for f in node.speaking_functions):
        return True

    sid = node.skill_id.lower()
    if sid.startswith("interaction:") or sid.startswith("conversation:"):
        return True
    if any(token in sid for token in ("interactive", "clarification", "repair", "turn_taking")):
        return True
    if "breakdown_repair" in node.remediation_tags:
        return True

    activities = frozenset(node.recommended_activity_types)
    if activities and activities.isdisjoint(PRODUCTION_COMPATIBLE_ACTIVITIES):
        # Exclusive role-play / interview service dialogues cannot be covered by monologue SPA.
        if SpeakingTaskType.role_play in activities or SpeakingTaskType.interview in activities:
            return True
        if any(t.startswith("service") or t.endswith("_interaction") for t in node.task_relevance):
            return True
    return False


def classify_skill_evaluator_compatibility(
    node: SpeakingSkillNode,
) -> SpaSkillEvaluatorCompatibility:
    if skill_requires_interactive_evaluation(node):
        return SpaSkillEvaluatorCompatibility.interaction_required
    if node.skill_type == SpeakingSkillType.phoneme:
        # Pronunciation still evaluable via recorded audio (S7), treat as production-compatible.
        return SpaSkillEvaluatorCompatibility.production_compatible
    return SpaSkillEvaluatorCompatibility.production_compatible


def slot_by_order(task_order: int) -> SpaTaskSlotPolicy:
    for slot in SPA_TASK_SLOTS:
        if slot.task_order == task_order:
            return slot
    raise KeyError(f"unknown SPA task order: {task_order}")


def estimated_duration_seconds() -> int:
    return sum(s.max_duration_seconds + s.preparation_seconds for s in SPA_TASK_SLOTS)
