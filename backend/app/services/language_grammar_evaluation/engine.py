"""Grammar-Constrained Evaluation engine (V1.8).

ExecutionResult / ActivitySpecification → target/pattern scores → evidence observations.
Never writes Mastery / Progression / Review. Never a general English scorer.
"""

from __future__ import annotations

from uuid import uuid4

from app.services.language_grammar.id_canon import normalize_grammar_id
from app.services.language_grammar_activity_spec import ActivitySpecification
from app.services.language_grammar_evaluation.errors import EvaluationDisabledError
from app.services.language_grammar_evaluation.evidence_mapper import (
    evidence_items_to_observations,
    pattern_results_to_evidence_items,
)
from app.services.language_grammar_evaluation.fingerprint import fingerprint_evaluation_request
from app.services.language_grammar_evaluation.flags import grammar_evaluation_enabled
from app.services.language_grammar_evaluation.lesson_view import (
    lesson_view_from_specification,
    merge_expected_patterns,
)
from app.services.language_grammar_evaluation.pattern_matching import (
    assign_pattern_to_target,
    evaluate_pattern,
    normalize_text,
)
from app.services.language_grammar_evaluation.types import (
    GRAMMAR_EVALUATION_PACKAGE_VERSION,
    GrammarEvaluationContext,
    GrammarEvaluationRequest,
    GrammarEvaluationResult,
    LessonPackageView,
    PatternEvaluationResult,
    PatternStatus,
    TargetEvaluationResult,
    TargetStatus,
)
from app.services.language_grammar_evaluation.validation import (
    detect_unexpected_grammar_in_text,
    validate_evaluation_request,
    validate_evidence_items,
)


def _new_id() -> str:
    return f"geval_{uuid4().hex[:12]}"


def build_evaluation_request(
    *,
    grammar_targets: tuple[str, ...],
    student_response: str,
    expected_patterns: tuple[str, ...] = (),
    lesson_package: LessonPackageView | None = None,
    specification: ActivitySpecification | None = None,
    student_id: int = 0,
    language_id: int = 0,
    localization: str = "en",
    as_of: str = "",
    evaluation_id: str = "",
    source_skill: str = "grammar_lesson",
) -> GrammarEvaluationRequest:
    """Build a validated-ready evaluation request from constrained inputs only."""
    lesson = lesson_package
    if lesson is None and specification is not None:
        lesson = lesson_view_from_specification(specification)
    if lesson is None:
        lesson = LessonPackageView(expected_patterns=tuple(expected_patterns))

    patterns = merge_expected_patterns(explicit=expected_patterns, lesson=lesson)
    targets = tuple(normalize_grammar_id(t) for t in grammar_targets)
    if not targets and specification is not None:
        targets = tuple(normalize_grammar_id(t) for t in specification.grammar_targets)

    ctx = GrammarEvaluationContext(
        grammar_targets=targets,
        expected_patterns=patterns,
        student_response=student_response,
        lesson_package=lesson,
        specification=specification,
        student_id=student_id,
        language_id=language_id,
        localization=localization,
        as_of=as_of,
        evaluation_id=evaluation_id or _new_id(),
        source_skill=source_skill,
    )
    return GrammarEvaluationRequest(context=ctx)


def _aggregate_targets(
    *,
    grammar_targets: tuple[str, ...],
    pattern_results: tuple[PatternEvaluationResult, ...],
) -> tuple[TargetEvaluationResult, ...]:
    by_target: dict[str, list[PatternEvaluationResult]] = {t: [] for t in grammar_targets}
    for result in pattern_results:
        by_target.setdefault(result.grammar_target, []).append(result)

    aggregates: list[TargetEvaluationResult] = []
    for target in grammar_targets:
        results = by_target.get(target, [])
        matched = tuple(r.pattern for r in results if r.status is PatternStatus.correct)
        missing = tuple(
            r.pattern
            for r in results
            if r.status in {PatternStatus.missing, PatternStatus.incorrect}
        )
        unexpected = tuple(r.pattern for r in results if r.status is PatternStatus.unexpected)
        if not results:
            status = TargetStatus.not_attempted
            confidence = 0.0
        elif matched and not missing:
            status = TargetStatus.correct
            confidence = sum(r.confidence for r in results) / len(results)
        elif matched and missing:
            status = TargetStatus.partial
            confidence = sum(r.confidence for r in results) / len(results)
        else:
            status = TargetStatus.incorrect
            confidence = sum(r.confidence for r in results) / max(1, len(results))
        aggregates.append(
            TargetEvaluationResult(
                target_id=target,
                status=status,
                confidence=round(confidence, 4),
                matched_patterns=matched,
                missing_patterns=missing,
                unexpected_patterns=unexpected,
            )
        )
    return tuple(aggregates)


def evaluate_grammar(
    request: GrammarEvaluationRequest,
    *,
    require_enabled: bool = False,
) -> GrammarEvaluationResult:
    """Run grammar-constrained evaluation — sole public evaluation entry."""
    if require_enabled and not grammar_evaluation_enabled():
        raise EvaluationDisabledError(
            "evaluation_disabled",
            "Grammar evaluation disabled (LANG_GRAMMAR_EVALUATION_ENABLED)",
        )

    validate_evaluation_request(request)
    ctx = request.context
    evaluation_id = ctx.evaluation_id or _new_id()
    fingerprint = fingerprint_evaluation_request(request)

    # Guard: student response must not pull evaluation onto unrelated grammar topics.
    # We do not score those topics; if response is only about out-of-scope grammar markers
    # while ignoring all expected patterns, patterns simply mark missing/incorrect.
    _ = detect_unexpected_grammar_in_text(
        ctx.student_response,
        allowed_targets=ctx.grammar_targets,
    )

    pattern_results: list[PatternEvaluationResult] = []
    for pattern in ctx.expected_patterns:
        target = assign_pattern_to_target(pattern, ctx.grammar_targets)
        pattern_results.append(
            evaluate_pattern(
                pattern=pattern,
                student_response=ctx.student_response,
                grammar_target=target,
            )
        )

    pattern_tuple = tuple(pattern_results)
    target_results = _aggregate_targets(
        grammar_targets=ctx.grammar_targets,
        pattern_results=pattern_tuple,
    )
    evidence_items = pattern_results_to_evidence_items(
        pattern_tuple,
        timestamp=ctx.as_of,
    )
    validate_evidence_items(evidence_items, allowed_targets=ctx.grammar_targets)
    observations = evidence_items_to_observations(
        evidence_items,
        evaluation_id=evaluation_id,
        student_id=ctx.student_id,
        language_id=ctx.language_id,
        source_skill=ctx.source_skill,
        observed_at=ctx.as_of,
    )

    notes = (
        f"targets={len(target_results)};patterns={len(pattern_tuple)};"
        f"response_len={len(normalize_text(ctx.student_response))}"
    )
    return GrammarEvaluationResult(
        evaluation_id=evaluation_id,
        target_results=target_results,
        pattern_results=pattern_tuple,
        evidence_items=evidence_items,
        observations=observations,
        request_fingerprint=fingerprint,
        evaluation_version=GRAMMAR_EVALUATION_PACKAGE_VERSION,
        notes=notes,
    )
