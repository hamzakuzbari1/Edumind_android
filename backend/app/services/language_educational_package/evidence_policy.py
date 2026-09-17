"""Discussion evidence roles — mapping hooks for future discussion runtime (E2+)."""

from __future__ import annotations

from enum import StrEnum


class DiscussionEvidenceRole(StrEnum):
    none = "none"
    formative_light = "formative_light"
    formative = "formative"
    transfer = "transfer"


class CorrectionMode(StrEnum):
    none = "none"
    micro = "micro"
    brief = "brief"


# Default role by ladder band (architecture A8) — used when constraints omit slot plan.
DEFAULT_EVIDENCE_ROLE_BY_BAND: dict[str, DiscussionEvidenceRole] = {
    "literal": DiscussionEvidenceRole.none,
    "vocabulary": DiscussionEvidenceRole.none,
    "grammar_in_context": DiscussionEvidenceRole.formative_light,
    "reasoning": DiscussionEvidenceRole.formative,
    "personal_opinion": DiscussionEvidenceRole.formative,
    "personal_experience": DiscussionEvidenceRole.formative,
    "real_world_transfer": DiscussionEvidenceRole.transfer,
}
