"""Validation for Grammar-Constrained Evaluation (V1.8)."""

from __future__ import annotations

import re

from app.services.language_grammar.id_canon import is_canonical_grammar_id, normalize_grammar_id
from app.services.language_grammar_catalog.catalog import all_grammar_ids, list_topics
from app.services.language_grammar_evaluation.errors import EvaluationValidationError
from app.services.language_grammar_evaluation.types import (
    GrammarEvidenceItem,
    GrammarEvaluationRequest,
    LessonPackageView,
)

# Markers for grammar topics outside provided targets (hallucinated evaluation scope).
_EXTRA_UNSUPPORTED_PHRASES: dict[str, tuple[str, ...]] = {
    "gram_past_perfect": ("past perfect",),
    "gram_passive_voice": ("passive voice",),
    "gram_conditionals": ("second conditional", "third conditional"),
}


def validate_evaluation_request(
    request: GrammarEvaluationRequest,
    *,
    catalog_ids: frozenset[str] | None = None,
) -> None:
    ctx = request.context
    if not ctx.grammar_targets:
        raise EvaluationValidationError("missing_grammar_targets", "Grammar Targets required")

    ids = catalog_ids if catalog_ids is not None else all_grammar_ids()
    for raw in ctx.grammar_targets:
        gid = normalize_grammar_id(raw)
        if not is_canonical_grammar_id(gid):
            raise EvaluationValidationError("invalid_grammar_target", f"Invalid grammar_id: {raw!r}")
        if gid not in ids:
            raise EvaluationValidationError("unknown_grammar_target", f"Unknown grammar_id: {gid}")

    lesson = ctx.lesson_package
    if lesson is None or not isinstance(lesson, LessonPackageView):
        raise EvaluationValidationError("missing_lesson_package", "Lesson Package required")
    if lesson.is_empty() and not ctx.expected_patterns:
        raise EvaluationValidationError(
            "missing_lesson_package",
            "Lesson Package must include expected_patterns",
        )

    patterns = tuple(ctx.expected_patterns) or tuple(lesson.expected_patterns)
    if not patterns:
        raise EvaluationValidationError("missing_expected_patterns", "Expected Patterns required")

    # Patterns must stay within the lesson package set when lesson declares patterns.
    lesson_patterns = set(lesson.expected_patterns)
    if lesson_patterns:
        outside = [p for p in patterns if p not in lesson_patterns]
        if outside:
            raise EvaluationValidationError(
                "pattern_outside_lesson",
                "Pattern outside lesson expected_patterns: " + ", ".join(outside[:5]),
            )

    # Reject evaluating unrelated grammar named in patterns (not in Grammar Targets).
    unsupported = detect_unexpected_grammar_in_text(
        "\n".join(patterns),
        allowed_targets=tuple(normalize_grammar_id(t) for t in ctx.grammar_targets),
    )
    if unsupported:
        raise EvaluationValidationError(
            "unexpected_grammar_evaluated",
            "Unexpected grammar in evaluation patterns: " + ", ".join(unsupported),
        )


def detect_unexpected_grammar_in_text(
    text: str,
    *,
    allowed_targets: tuple[str, ...] | frozenset[str],
) -> tuple[str, ...]:
    allowed = frozenset(normalize_grammar_id(t) for t in allowed_targets)
    blob = (text or "").lower()
    if not blob.strip():
        return ()
    found: list[str] = []
    for topic in list_topics():
        gid = topic.grammar_id
        if gid in allowed:
            continue
        markers = [gid.lower()]
        name = (topic.display_name or "").strip().lower()
        if " " in name or len(name) >= 12:
            markers.append(name)
        markers.extend(_EXTRA_UNSUPPORTED_PHRASES.get(gid, ()))
        for marker in markers:
            if marker.startswith("gram_") or " " in marker:
                if marker in blob:
                    found.append(gid)
                    break
            elif re.search(rf"\b{re.escape(marker)}\b", blob):
                found.append(gid)
                break
    for gid, phrases in _EXTRA_UNSUPPORTED_PHRASES.items():
        if gid in allowed or gid in found:
            continue
        if any(p in blob for p in phrases):
            found.append(gid)
    return tuple(sorted(set(found)))


def validate_evidence_items(items: tuple[GrammarEvidenceItem, ...], *, allowed_targets: tuple[str, ...]) -> None:
    allowed = frozenset(normalize_grammar_id(t) for t in allowed_targets)
    if not items:
        raise EvaluationValidationError("malformed_evidence", "Evidence items required")
    for item in items:
        gid = normalize_grammar_id(item.grammar_target)
        if gid not in allowed:
            raise EvaluationValidationError(
                "unexpected_grammar_evaluated",
                f"Evidence grammar_target outside Grammar Targets: {item.grammar_target}",
            )
        if not (item.pattern or "").strip():
            raise EvaluationValidationError("malformed_evidence", "Evidence pattern required")
        if item.confidence is None or item.confidence < 0 or item.confidence > 1:
            raise EvaluationValidationError("malformed_evidence", "Evidence confidence must be 0..1")
