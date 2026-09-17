"""Speaking coach (S7.6 live context).

RESPONSIBILITY: Canonical priority + render-only guidance; read-only live context for EVI.
"""

from app.services.language_speaking_coach.evi_serialization import (
    EVI_CONTEXT_MAX_CHARS,
    serialize_live_context_for_evi,
)
from app.services.language_speaking_coach.live_context import assemble_student_speaking_live_context
from app.services.language_speaking_coach.live_context_loader import (
    load_student_speaking_live_context,
    opaque_student_reference,
)
from app.services.language_speaking_coach.types import (
    LANGUAGE_SPEAKING_COACH_VERSION,
    PrioritySkillTarget,
    STUDENT_SPEAKING_LIVE_CONTEXT_VERSION,
    SpeakingCoachGuidance,
    StudentSpeakingLiveContext,
)

__all__ = [
    "EVI_CONTEXT_MAX_CHARS",
    "LANGUAGE_SPEAKING_COACH_VERSION",
    "PrioritySkillTarget",
    "STUDENT_SPEAKING_LIVE_CONTEXT_VERSION",
    "SpeakingCoachGuidance",
    "StudentSpeakingLiveContext",
    "assemble_student_speaking_live_context",
    "load_student_speaking_live_context",
    "opaque_student_reference",
    "serialize_live_context_for_evi",
]
