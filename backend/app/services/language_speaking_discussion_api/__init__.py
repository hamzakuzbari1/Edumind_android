"""Guided Discussion API twin (E3) with E4 evaluation handoff + voice I/O.

RESPONSIBILITY: HTTP surface for Live Voice Discussion over frozen Learning Packages.
Claude owns tutoring; GPT owns STT/TTS only. E4 handoff after successful submit.
"""

from app.services.language_speaking_discussion_api.service import (
    DiscussionApiError,
    advance_discussion_api,
    get_discussion_api,
    open_discussion_api,
    submit_discussion_api,
    submit_discussion_voice_api,
)

__all__ = [
    "DiscussionApiError",
    "advance_discussion_api",
    "get_discussion_api",
    "open_discussion_api",
    "submit_discussion_api",
    "submit_discussion_voice_api",
]
