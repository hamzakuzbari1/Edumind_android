"""Build PackageConstraints from backend-owned dicts (no planner mutation)."""

from __future__ import annotations

from typing import Any

from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.question_ladder import (
    default_ladder_policy_for_cefr,
)


def build_speaking_package_constraints(raw: dict[str, Any]) -> PackageConstraints:
    """Construct constraints from an already-decided backend payload.

    Does not query knowledge, progression, or planner services. Callers supply
    educational decisions; this helper only shapes and defaults schema fields.
    """
    data = dict(raw)
    data.setdefault("skill", "speaking")
    cefr = str(data.get("official_cefr") or "A2").upper()
    data["official_cefr"] = cefr
    if not isinstance(data.get("question_ladder_policy"), dict):
        data["question_ladder_policy"] = default_ladder_policy_for_cefr(cefr).to_dict()
    data.setdefault(
        "forbidden_behaviors",
        ["no_grammar_lecture", "no_promotion_talk", "no_cefr_claims"],
    )
    return PackageConstraints.from_dict(data)
