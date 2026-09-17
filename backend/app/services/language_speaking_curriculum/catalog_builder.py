"""Node builder helpers for the Speaking skill catalog (S1)."""

from __future__ import annotations

from app.services.language_speaking.enums import (
    OfficialSpeakingCEFR,
    SpeakingGoal,
    SpeakingSkillType,
    SpeakingTaskType,
)
from app.services.language_speaking_curriculum.evidence_ids import (
    ACOUSTIC_SUPPORT,
    ARTICULATION_RATE,
    CLARIFICATION_BEHAVIOR,
    CONVERSATION_STATE,
    GRAMMAR_CONTROL,
    HESITATIONS,
    INTONATION,
    MEANING_SUCCESS,
    ORGANIZATION_EVIDENCE,
    PAUSES,
    PHONEME_ALIGNMENT,
    PITCH,
    PRONUNCIATION_CONFIDENCE,
    REPETITIONS,
    RESPONSE_RELEVANCE,
    RHYTHM,
    SEMANTIC_TASK_RESPONSE,
    SPEAKING_RATE,
    STRESS,
    TOPIC_DEVELOPMENT,
    TURN_COMPLETION,
    VOCABULARY_FUNCTION,
    WORD_STRESS_ACCURACY,
)
from app.services.language_speaking_curriculum.types import (
    SkillEvidenceRequirement,
    SkillMasteryRequirement,
    SpacedRepetitionProfile,
    SpeakingSkillNode,
)

_CEFR = OfficialSpeakingCEFR
_ST = SpeakingSkillType
_G = SpeakingGoal
_TT = SpeakingTaskType

_GOALS_ALL = (
    _G.general_english,
    _G.daily_communication,
)
_GOALS_TRAVEL = (_G.travel, _G.daily_communication, _G.general_english)
_GOALS_BUSINESS = (_G.business, _G.job_interview, _G.academic)
_GOALS_IELTS = (_G.ielts, _G.academic, _G.general_english)

# Public aliases for catalog modules
_goals_all = _GOALS_ALL
_goals_travel = _GOALS_TRAVEL
_goals_business = _GOALS_BUSINESS
_goals_ielts = _GOALS_IELTS


def _phoneme_mastery() -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=8,
        stability_sessions=3,
        pronunciation_threshold=0.72,
        distinct_word_contexts=4,
        notes="Phoneme must be intelligible in multiple word contexts.",
    )


def _word_mastery() -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=6,
        stability_sessions=2,
        pronunciation_threshold=0.75,
        distinct_word_contexts=3,
    )


def _phrase_mastery() -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=5,
        stability_sessions=2,
        pronunciation_threshold=0.70,
        communicative_success_threshold=0.65,
    )


def _function_mastery() -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=4,
        stability_sessions=2,
        communicative_success_threshold=0.70,
        response_relevance_threshold=0.70,
    )


def _interaction_mastery() -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=6,
        stability_sessions=3,
        minimum_interaction_turns=4,
        communicative_success_threshold=0.72,
        response_relevance_threshold=0.72,
    )


def _task_mastery(*, extended: bool = False) -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=5 if not extended else 8,
        stability_sessions=3 if not extended else 4,
        task_response_required=True,
        organization_required=extended,
        fluency_required=True,
        grammar_vocabulary_required=True,
        repeated_successful_contexts=3 if not extended else 4,
        communicative_success_threshold=0.75 if not extended else 0.78,
    )


def _fluency_mastery() -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=6,
        stability_sessions=3,
        fluency_required=True,
        repeated_successful_contexts=3,
    )


def _prosody_mastery() -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=5,
        stability_sessions=2,
        pronunciation_threshold=0.68,
    )


def _grammar_mastery() -> SkillMasteryRequirement:
    return SkillMasteryRequirement(
        minimum_evidence_count=5,
        stability_sessions=2,
        grammar_vocabulary_required=True,
        communicative_success_threshold=0.70,
    )


def _ev_phoneme() -> SkillEvidenceRequirement:
    return SkillEvidenceRequirement(
        (PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE, ACOUSTIC_SUPPORT),
        minimum_dimensions=2,
    )


def _ev_word() -> SkillEvidenceRequirement:
    return SkillEvidenceRequirement(
        (PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE, WORD_STRESS_ACCURACY),
        minimum_dimensions=2,
    )


def _ev_phrase() -> SkillEvidenceRequirement:
    return SkillEvidenceRequirement(
        (PRONUNCIATION_CONFIDENCE, GRAMMAR_CONTROL, MEANING_SUCCESS),
        minimum_dimensions=2,
    )


def _ev_function() -> SkillEvidenceRequirement:
    return SkillEvidenceRequirement(
        (SEMANTIC_TASK_RESPONSE, MEANING_SUCCESS, VOCABULARY_FUNCTION, GRAMMAR_CONTROL),
        minimum_dimensions=2,
    )


def _ev_interaction() -> SkillEvidenceRequirement:
    return SkillEvidenceRequirement(
        (
            RESPONSE_RELEVANCE,
            TURN_COMPLETION,
            CLARIFICATION_BEHAVIOR,
            CONVERSATION_STATE,
        ),
        minimum_dimensions=2,
    )


def _ev_fluency() -> SkillEvidenceRequirement:
    return SkillEvidenceRequirement(
        (SPEAKING_RATE, ARTICULATION_RATE, PAUSES, HESITATIONS, REPETITIONS),
        minimum_dimensions=2,
    )


def _ev_prosody() -> SkillEvidenceRequirement:
    return SkillEvidenceRequirement(
        (PITCH, STRESS, RHYTHM, INTONATION),
        minimum_dimensions=2,
    )


def _ev_task(*, extended: bool = False) -> SkillEvidenceRequirement:
    codes = (
        SEMANTIC_TASK_RESPONSE,
        TOPIC_DEVELOPMENT,
        ORGANIZATION_EVIDENCE,
        GRAMMAR_CONTROL,
        VOCABULARY_FUNCTION,
        SPEAKING_RATE,
        PAUSES,
    )
    return SkillEvidenceRequirement(codes, minimum_dimensions=3 if extended else 2)


def N(
    skill_id: str,
    skill_type: SpeakingSkillType,
    label: str,
    description: str,
    *,
    cefr_min: OfficialSpeakingCEFR,
    cefr_max: OfficialSpeakingCEFR,
    prereqs: tuple[str, ...] = (),
    next_skills: tuple[str, ...] = (),
    related: tuple[str, ...] = (),
    difficulty: int,
    mastery: SkillMasteryRequirement,
    evidence: SkillEvidenceRequirement,
    activities: tuple[SpeakingTaskType, ...],
    goals: tuple[SpeakingGoal, ...],
    functions: tuple[str, ...] = (),
    tasks: tuple[str, ...] = (),
    diagnostic_tags: tuple[str, ...],
    remediation_tags: tuple[str, ...] = (),
    transfer_targets: tuple[str, ...] = (),
    is_root: bool = False,
    srs_days: int | None = 3,
) -> SpeakingSkillNode:
    srs = SpacedRepetitionProfile(initial_interval_days=srs_days) if srs_days else None
    return SpeakingSkillNode(
        skill_id=skill_id,
        skill_type=skill_type,
        label=label,
        description=description,
        cefr_min=cefr_min,
        cefr_max=cefr_max,
        prerequisite_skill_ids=prereqs,
        next_skill_ids=next_skills,
        related_skill_ids=related,
        difficulty=difficulty,
        mastery_requirements=mastery,
        evidence_requirements=evidence,
        recommended_activity_types=activities,
        spaced_repetition_profile=srs,
        goal_relevance=goals,
        speaking_functions=functions,
        task_relevance=tasks,
        diagnostic_tags=diagnostic_tags,
        remediation_tags=remediation_tags,
        transfer_targets=transfer_targets,
        is_root=is_root,
    )
