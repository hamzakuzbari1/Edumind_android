"""Grammar Target Resolver — sole skill Runtime entry for grammar targets.

RESPONSIBILITY: Resolve current/candidate grammar_ids (+ display_codes) for
Reading, Listening, Speaking, Writing, Vocabulary, and Grammar skill surfaces.
Skills must never resolve grammar independently via progression/catalog.
"""

from __future__ import annotations

from app.services.language_grammar_target_resolver.service import (
    GrammarTargetResolver,
    resolve,
    resolve_from_snapshot,
)
from app.services.language_grammar_target_resolver.types import (
    GrammarTargetMeta,
    GrammarTargetResolution,
    GrammarTargetResolveRequest,
)

PACKAGE_VERSION = "1.0.0"
RESPONSIBILITY = (
    "Sole skill Runtime facade for grammar target resolution "
    "(grammar_id + display_code); skills never resolve independently"
)

__all__ = [
    "GrammarTargetMeta",
    "GrammarTargetResolution",
    "GrammarTargetResolveRequest",
    "GrammarTargetResolver",
    "PACKAGE_VERSION",
    "RESPONSIBILITY",
    "resolve",
    "resolve_from_snapshot",
]
