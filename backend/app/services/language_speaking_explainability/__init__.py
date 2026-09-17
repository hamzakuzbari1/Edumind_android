"""Speaking explainability — student/teacher display mapping from canonical facts.

RESPONSIBILITY: Render-only student and teacher display from canonical evaluation.
"""

from app.services.language_speaking_explainability.student_session_summary import (
    SPEAKING_STUDENT_SESSION_SUMMARY_VERSION,
    SpeakingStudentSessionSummary,
    build_speaking_student_session_summary,
)
from app.services.language_speaking_explainability.types import SpeakingFactsBundle

__all__ = [
    "SPEAKING_STUDENT_SESSION_SUMMARY_VERSION",
    "SpeakingFactsBundle",
    "SpeakingStudentSessionSummary",
    "build_speaking_student_session_summary",
]
