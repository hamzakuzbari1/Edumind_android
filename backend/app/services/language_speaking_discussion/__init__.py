"""Speaking Live Voice Discussion Runtime (E3).

RESPONSIBILITY: Claude Discussion Tutor over frozen Learning Package discussion steps,
with GPT STT/TTS I/O only. Claude owns follow-ups, corrections, reasoning, and
progression. Never regenerates packages, never evaluates mastery, never writes
CEFR/stage/promotion, never calls evaluation runtime, Alex, or Scene Practice.
"""

from app.services.language_speaking_discussion.engine import (
    DISCUSSION_RUNTIME_VERSION,
    advance_discussion_step,
    get_discussion_view,
    open_discussion,
    submit_discussion_response,
)
from app.services.language_speaking_discussion.types import (
    DiscussionPhase,
    DiscussionRuntimeState,
)

__all__ = [
    "DISCUSSION_RUNTIME_VERSION",
    "DiscussionPhase",
    "DiscussionRuntimeState",
    "advance_discussion_step",
    "get_discussion_view",
    "open_discussion",
    "submit_discussion_response",
]
