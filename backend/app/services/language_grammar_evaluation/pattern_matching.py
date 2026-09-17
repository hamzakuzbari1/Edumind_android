"""Deterministic pattern matching for Grammar-Constrained Evaluation (V1.8).

Evaluates ONLY lesson expected patterns against Grammar Targets.
Never scores lexical richness, speaking rate, oral delivery, regional speech, or inventiveness.
"""

from __future__ import annotations

import re

from app.services.language_grammar_evaluation.types import PatternEvaluationResult, PatternStatus

_SUBJECT_PRONOUNS = frozenset({"i", "you", "he", "she", "it", "we", "they"})
_THIRD_PERSON = frozenset({"he", "she", "it"})


def normalize_text(text: str) -> str:
    cleaned = (text or "").strip().lower()
    cleaned = cleaned.replace("’", "'")
    cleaned = re.sub(r"[^\w\s'+]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def pattern_stem(pattern: str) -> str:
    """Reduce 'I usually ...' / labels to a matchable stem."""
    raw = (pattern or "").strip()
    if "..." in raw:
        raw = raw.split("...")[0]
    # Drop parenthetical labels: "Subject + Verb (Present Simple)"
    raw = re.sub(r"\([^)]*\)", " ", raw)
    return normalize_text(raw)


def _tokens(text: str) -> list[str]:
    return [t for t in normalize_text(text).split(" ") if t]


def _is_meta_subject_verb(stem: str) -> bool:
    return "subject" in stem and "verb" in stem


def _has_subject_verb_shape(student_n: str) -> bool:
    tokens = _tokens(student_n)
    if len(tokens) < 2:
        return False
    return tokens[0] in _SUBJECT_PRONOUNS and any(ch.isalpha() for ch in tokens[1])


def _third_person_singular_issue(student_n: str) -> bool:
    """Detect classic 'he play' / 'she go' present-simple errors."""
    tokens = _tokens(student_n)
    if len(tokens) < 2:
        return False
    if tokens[0] not in _THIRD_PERSON:
        return False
    verb = tokens[1]
    if not verb.isalpha():
        return False
    # Incorrect if bare verb without 3sg -s/-es (allow irregular is/has/does)
    if verb in {"is", "has", "does", "was", "were"}:
        return False
    return not (verb.endswith("s") or verb.endswith("es"))


def assign_pattern_to_target(pattern: str, grammar_targets: tuple[str, ...]) -> str:
    """Bind a lesson pattern to one Grammar Target — never invent new targets."""
    if not grammar_targets:
        return ""
    lowered = normalize_text(pattern)
    for target in grammar_targets:
        tid = target.lower()
        if tid in lowered:
            return target
        # light label cues
        short = tid.replace("gram_", "").replace("_", " ")
        if short and short in lowered:
            return target
    return grammar_targets[0]


def evaluate_pattern(
    *,
    pattern: str,
    student_response: str,
    grammar_target: str,
) -> PatternEvaluationResult:
    """Evaluate one expected pattern against the student response."""
    student_n = normalize_text(student_response)
    source = (student_response or "").strip()
    stem = pattern_stem(pattern)

    if not student_n:
        return PatternEvaluationResult(
            pattern=pattern,
            grammar_target=grammar_target,
            status=PatternStatus.missing,
            confidence=1.0,
            reason="empty_student_response",
            source_sentence=source,
        )

    if _is_meta_subject_verb(stem):
        if _has_subject_verb_shape(student_n):
            # Present-simple 3sg check when target implies present simple.
            if "present_simple" in grammar_target and _third_person_singular_issue(student_n):
                return PatternEvaluationResult(
                    pattern=pattern,
                    grammar_target=grammar_target,
                    status=PatternStatus.incorrect,
                    confidence=0.85,
                    reason="third_person_singular_missing",
                    source_sentence=source,
                )
            return PatternEvaluationResult(
                pattern=pattern,
                grammar_target=grammar_target,
                status=PatternStatus.correct,
                confidence=0.75,
                reason="subject_verb_shape_matched",
                source_sentence=source,
            )
        return PatternEvaluationResult(
            pattern=pattern,
            grammar_target=grammar_target,
            status=PatternStatus.missing,
            confidence=0.7,
            reason="subject_verb_shape_missing",
            source_sentence=source,
        )

    if not stem:
        return PatternEvaluationResult(
            pattern=pattern,
            grammar_target=grammar_target,
            status=PatternStatus.not_applicable,
            confidence=0.0,
            reason="empty_pattern_stem",
            source_sentence=source,
        )

    # Exact stem containment: "i usually" in "i usually wake up early"
    if stem in student_n:
        return PatternEvaluationResult(
            pattern=pattern,
            grammar_target=grammar_target,
            status=PatternStatus.correct,
            confidence=0.95,
            reason="pattern_stem_matched",
            source_sentence=source,
        )

    # Near-miss: stem without final s (he plays vs he play)
    stem_tokens = _tokens(stem)
    if len(stem_tokens) >= 2 and stem_tokens[0] in _THIRD_PERSON:
        expected_verb = stem_tokens[1]
        bare = expected_verb[:-2] if expected_verb.endswith("es") else expected_verb[:-1]
        student_tokens = _tokens(student_n)
        if (
            len(student_tokens) >= 2
            and student_tokens[0] == stem_tokens[0]
            and bare
            and student_tokens[1] == bare
            and student_tokens[1] != expected_verb
        ):
            return PatternEvaluationResult(
                pattern=pattern,
                grammar_target=grammar_target,
                status=PatternStatus.incorrect,
                confidence=0.9,
                reason="third_person_singular_incorrect",
                source_sentence=source,
            )

    # Partial token overlap without full stem
    overlap = [t for t in stem_tokens if t in student_n.split(" ")]
    if stem_tokens and len(overlap) == len(stem_tokens):
        return PatternEvaluationResult(
            pattern=pattern,
            grammar_target=grammar_target,
            status=PatternStatus.correct,
            confidence=0.8,
            reason="pattern_tokens_matched",
            source_sentence=source,
        )

    if overlap:
        return PatternEvaluationResult(
            pattern=pattern,
            grammar_target=grammar_target,
            status=PatternStatus.incorrect,
            confidence=0.55,
            reason="pattern_partially_matched",
            source_sentence=source,
        )

    return PatternEvaluationResult(
        pattern=pattern,
        grammar_target=grammar_target,
        status=PatternStatus.missing,
        confidence=0.8,
        reason="pattern_not_found",
        source_sentence=source,
    )
