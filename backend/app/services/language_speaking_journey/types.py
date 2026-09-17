"""Student-facing speaking journey bundle (S9)."""

from __future__ import annotations

from dataclasses import dataclass

LANGUAGE_SPEAKING_JOURNEY_VERSION = "9.0.0"


@dataclass(frozen=True, slots=True)
class SpeakingJourneyStepOut:
    step_id: str
    label: str
    status: str
    kind: str

    def to_student_dict(self) -> dict[str, str]:
        return {
            "step_id": self.step_id,
            "label": self.label,
            "status": self.status,
            "kind": self.kind,
        }


@dataclass(frozen=True, slots=True)
class SpeakingJourneyMissionOut:
    """Student-safe educational mission summary for the Speaking home (S10)."""

    mission_id: str
    kind: str
    execution_mode: str
    order_index: int
    title: str
    is_live: bool
    is_executable: bool = False

    def to_student_dict(self) -> dict[str, object]:
        return {
            "mission_id": self.mission_id,
            "kind": self.kind,
            "execution_mode": self.execution_mode,
            "order_index": self.order_index,
            "title": self.title,
            "is_live": self.is_live,
            "is_executable": self.is_executable,
        }


@dataclass(frozen=True, slots=True)
class SpeakingJourneyBundle:
    """Student-safe speaking journey snapshot."""

    version: str
    current_focus_label: str
    current_focus_reason: str
    session_goal: str
    official_level: str
    plan_summary: str
    today_session_id: str
    today_session_phase: str
    current_activity_title: str
    steps: tuple[SpeakingJourneyStepOut, ...]
    next_recommendation: str
    has_active_session: bool
    practice_with_alex_available: bool
    today_missions: tuple[SpeakingJourneyMissionOut, ...] = ()
    # S11 minimal student-safe attempt projection (full home model deferred to S12).
    current_attempt_number: int = 0
    is_retry: bool = False
    completed_task_attempt_count: int = 0
    # Cursor projection for Continue / Talk-with-Alex gating (server-owned).
    current_activity_id: str = ""
    current_activity_instructions: str = ""
    live_execution_ready: bool = False
    # Phase-2 progress projection (counts derived from authoritative activity cursor).
    lesson_title: str = ""
    current_activity_kind: str = ""
    activities_total: int = 0
    activities_completed: int = 0
    activities_remaining: int = 0
    # S12 authoritative student-safe Journey/Home read model (nested projection).
    read_model: dict[str, object] | None = None

    def to_student_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "current_focus_label": self.current_focus_label,
            "current_focus_reason": self.current_focus_reason,
            "session_goal": self.session_goal,
            "official_level": self.official_level,
            "plan_summary": self.plan_summary,
            "today_session_id": self.today_session_id,
            "today_session_phase": self.today_session_phase,
            "current_activity_title": self.current_activity_title,
            "steps": [s.to_student_dict() for s in self.steps],
            "next_recommendation": self.next_recommendation,
            "has_active_session": self.has_active_session,
            "practice_with_alex_available": self.practice_with_alex_available,
            "today_missions": [m.to_student_dict() for m in self.today_missions],
            "current_attempt_number": self.current_attempt_number,
            "is_retry": self.is_retry,
            "completed_task_attempt_count": self.completed_task_attempt_count,
            "current_activity_id": self.current_activity_id,
            "current_activity_instructions": self.current_activity_instructions,
            "live_execution_ready": self.live_execution_ready,
            "lesson_title": self.lesson_title,
            "current_activity_kind": self.current_activity_kind,
            "activities_total": self.activities_total,
            "activities_completed": self.activities_completed,
            "activities_remaining": self.activities_remaining,
            "read_model": self.read_model,
        }
