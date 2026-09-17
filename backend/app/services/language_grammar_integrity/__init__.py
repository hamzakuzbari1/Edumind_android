"""Wave D — Production Integrity Hardening.

Server-attested completion, signed grammar stamps, activity sessions,
append-only evidence ledger, and durable replay protection.

Never invents grammar_id. Never trusts client grammar/score.
"""

from app.services.language_grammar_integrity.attested_completion import (
    AttestedCompletionRequest,
    complete_attested_activity,
    issue_and_stamp_for_context,
)
from app.services.language_grammar_integrity.curriculum_version import (
    CURRICULUM_VERSION_PIN,
    get_curriculum_version,
)
from app.services.language_grammar_integrity.errors import GrammarIntegrityError
from app.services.language_grammar_integrity.ledger import try_append_evidence
from app.services.language_grammar_integrity.sessions import (
    find_open_session_for_content,
    issue_activity_session,
    load_owned_open_session,
)
from app.services.language_grammar_integrity.stamp import (
    GrammarStampClaims,
    issue_signed_stamp,
    verify_signed_stamp,
)
from app.services.language_grammar_integrity.types import ActivitySessionView

PACKAGE = "language_grammar_integrity"
RESPONSIBILITY = (
    "Wave D production integrity — server-attested completion, signed stamps, "
    "activity sessions, append-only evidence ledger, durable replay protection; "
    "never trusts client grammar_id/score; never invents grammar targets"
)

__all__ = [
    "PACKAGE",
    "RESPONSIBILITY",
    "CURRICULUM_VERSION_PIN",
    "ActivitySessionView",
    "AttestedCompletionRequest",
    "GrammarIntegrityError",
    "GrammarStampClaims",
    "complete_attested_activity",
    "find_open_session_for_content",
    "get_curriculum_version",
    "issue_activity_session",
    "issue_and_stamp_for_context",
    "issue_signed_stamp",
    "load_owned_open_session",
    "try_append_evidence",
    "verify_signed_stamp",
]
