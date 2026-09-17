"""Speaking learning stage engine (S15 + S16 persist boundary).

RESPONSIBILITY:
- S15: Deterministic internal stage signal aggregation (read-only projection).
- S16: ``stage_runtime`` is the sole writer of ``learning_stage_speaking``
  after pure transition_gate authorization.

Never mutates official CEFR / promotion readiness decisions / S2 mastery from
the signal aggregation path. Stage advances are one-step only within the
current official CEFR.
"""

from app.services.language_speaking_learning_stage.curriculum_scope import (
    core_curriculum_skills,
    curriculum_skills_for_official_cefr,
    skill_within_official_cefr,
)
from app.services.language_speaking_learning_stage.fingerprint import compute_snapshot_fingerprint
from app.services.language_speaking_learning_stage.service import build_speaking_stage_signal_snapshot
from app.services.language_speaking_learning_stage.signals import gather_speaking_stage_signals
from app.services.language_speaking_learning_stage.stage_runtime import (
    SpeakingStagePersistResult,
    StaleSpeakingStageDecisionError,
    apply_speaking_stage_transition,
    evaluate_and_persist_speaking_stage,
)
from app.services.language_speaking_learning_stage.types import (
    LANGUAGE_SPEAKING_LEARNING_STAGE_VERSION,
    STAGE_SIGNAL_SCHEMA_VERSION,
    SUPPORT_DEPENDENCE_UNKNOWN,
    DataSufficiencyVerdict,
    SpeakingLearningStageResult,
    SpeakingStageBlocker,
    SpeakingStageBlockerKind,
    SpeakingStageSignalSnapshot,
    speaking_stage_label,
)

__all__ = [
    "LANGUAGE_SPEAKING_LEARNING_STAGE_VERSION",
    "STAGE_SIGNAL_SCHEMA_VERSION",
    "SUPPORT_DEPENDENCE_UNKNOWN",
    "DataSufficiencyVerdict",
    "SpeakingLearningStageResult",
    "SpeakingStageBlocker",
    "SpeakingStageBlockerKind",
    "SpeakingStagePersistResult",
    "SpeakingStageSignalSnapshot",
    "StaleSpeakingStageDecisionError",
    "apply_speaking_stage_transition",
    "build_speaking_stage_signal_snapshot",
    "compute_snapshot_fingerprint",
    "core_curriculum_skills",
    "curriculum_skills_for_official_cefr",
    "evaluate_and_persist_speaking_stage",
    "gather_speaking_stage_signals",
    "skill_within_official_cefr",
    "speaking_stage_label",
]
