"""Speaking lesson_planner (S9 + S10.1 + S11).

RESPONSIBILITY: SpeakingLessonBlueprint producer, session orchestration, and
attempt lineage contracts.
"""

from app.services.language_speaking_lesson_planner.attempt_lineage import (
    ATTEMPT_LINEAGE_SCHEMA_VERSION,
    AmbiguousActiveAttemptError,
    SpeakingAttemptStatus,
    SpeakingSessionAttemptLineage,
    SpeakingTaskAttempt,
    apply_outcome_to_attempt,
    assert_active_attempt_integrity,
    attempts_for_task,
    find_active_attempts,
    get_active_attempt,
    get_attempt,
    latest_attempt_for_task,
    reconcile_active_attempt_on_cursor_leave,
    retry_chain_for_attempt,
    start_or_resume_attempt,
    student_safe_attempt_projection,
)
from app.services.language_speaking_lesson_planner.identity import (
    IDENTITY_SEMANTICS_VERSION,
    SPEAKING_IDENTITY_SEMANTICS,
    SpeakingAttemptIdentity,
    make_task_id,
    new_attempt_id,
    should_start_new_attempt,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import (
    SpeakingRuntimeTaskResolution,
    resolve_activity_to_task,
    resolve_current_task,
)
from app.services.language_speaking_lesson_planner.mission_types import (
    EDUCATIONAL_MISSION_SCHEMA_VERSION,
    SpeakingEducationalMission,
    SpeakingExecutableTask,
    SpeakingLearningObjective,
    SpeakingMissionOutcome,
    SpeakingTeachingBlock,
)
from app.services.language_speaking_lesson_planner.planner import (
    MISSION_LEGACY_ACTIVITY,
    assemble_speaking_lesson_blueprint,
    build_educational_missions,
    select_mission_plan,
)
from app.services.language_speaking_lesson_planner.task_taxonomy import (
    SPEAKING_MISSION_TAXONOMY,
    SpeakingTaxonomyEntry,
    is_legal_mission_combination,
    taxonomy_entry,
    validate_mission_combination,
)
from app.services.language_speaking_lesson_planner.storage import SpeakingStoredJourneyState
from app.services.language_speaking_lesson_planner.types import (
    BLUEPRINT_VERSION,
    SpeakingLessonBlueprint,
    SpeakingLearningSession,
    SpeakingSessionPhase,
)

__all__ = [
    "ATTEMPT_LINEAGE_SCHEMA_VERSION",
    "BLUEPRINT_VERSION",
    "EDUCATIONAL_MISSION_SCHEMA_VERSION",
    "IDENTITY_SEMANTICS_VERSION",
    "MISSION_LEGACY_ACTIVITY",
    "SPEAKING_IDENTITY_SEMANTICS",
    "SPEAKING_MISSION_TAXONOMY",
    "SpeakingAttemptIdentity",
    "SpeakingAttemptStatus",
    "SpeakingEducationalMission",
    "SpeakingExecutableTask",
    "SpeakingLearningObjective",
    "SpeakingLearningSession",
    "SpeakingLessonBlueprint",
    "SpeakingMissionOutcome",
    "SpeakingRuntimeTaskResolution",
    "SpeakingSessionAttemptLineage",
    "SpeakingSessionPhase",
    "SpeakingStoredJourneyState",
    "SpeakingTaskAttempt",
    "SpeakingTaxonomyEntry",
    "SpeakingTeachingBlock",
    "AmbiguousActiveAttemptError",
    "apply_outcome_to_attempt",
    "assemble_speaking_lesson_blueprint",
    "assert_active_attempt_integrity",
    "attempts_for_task",
    "build_educational_missions",
    "find_active_attempts",
    "get_active_attempt",
    "get_attempt",
    "is_legal_mission_combination",
    "latest_attempt_for_task",
    "reconcile_active_attempt_on_cursor_leave",
    "make_task_id",
    "new_attempt_id",
    "resolve_activity_to_task",
    "resolve_current_task",
    "retry_chain_for_attempt",
    "select_mission_plan",
    "should_start_new_attempt",
    "start_or_resume_attempt",
    "student_safe_attempt_projection",
    "taxonomy_entry",
    "validate_mission_combination",
]
