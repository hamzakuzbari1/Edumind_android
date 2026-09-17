"""CEFR validation engine for AI-generated Listening lessons (Phase 1.5)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from app.models.language.enums import LanguageLevel
from app.services.language_cefr.engine import get_cefr_profile
from app.services.language_cefr.transcript_format import (
    ListeningTranscriptFormat,
    classify_transcript_format,
    count_words as format_count_words,
    extract_speaker_turns,
    get_format_sentence_limits,
    is_multi_speaker_format,
    min_average_turn_words,
)
from app.services.language_cefr.types import CefrListeningProfile, ListeningQuestionType

LISTENING_CEFR_MAX_ATTEMPTS = 3

_STOPWORDS = frozenset(
    """
    the a an and or but in on at to for of with from by as is are was were be been being
    have has had do does did will would could should may might must can this that these those
    it its they them their he she we you i my your his her our their not no yes very
    understand short simple messages when speech clear what learner able
    """.split()
)

# Regex heuristics keyed by forbidden-grammar labels in CEFR profiles.
_GRAMMAR_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "past perfect": (
        re.compile(r"\bhad\s+(?:\w+ed|\w+en|\w+n)\b", re.I),
        re.compile(r"\bhad\s+been\b", re.I),
    ),
    "past simple": (
        re.compile(
            r"\b(?:went|came|said|told|bought|got|made|did|was|were|visited|walked|talked|played|worked|lived|started|stopped)\b",
            re.I,
        ),
    ),
    "present perfect": (
        re.compile(r"\b(?:have|has|had)\s+(?:\w+ed|\w+en|\w+n)\b", re.I),
    ),
    "conditionals": (
        re.compile(r"\bif\s+[^.?!]{0,80}\b(?:would|could|might|'d)\b", re.I),
        re.compile(r"\bwould have\b", re.I),
        re.compile(r"\bhad\s+\w+\s*,?\s*(?:I|you|he|she|we|they)\s+would\b", re.I),
    ),
    "passive voice": (
        re.compile(r"\b(?:am|is|are|was|were|been|being)\s+(?:\w+ed|\w+en)\b", re.I),
        re.compile(r"\b(?:was|were)\s+\w+ing\b", re.I),
    ),
    "relative clauses": (
        re.compile(r"\b(?:who|whom|whose|which|that)\s+(?:is|are|was|were|has|have|had|will|can|could)\b", re.I),
    ),
    "reported speech": (
        re.compile(r"\b(?:said|told|asked|explained|mentioned)\s+(?:that\s+)?(?:he|she|they|I|we|you)\b", re.I),
    ),
    "subjunctive": (
        re.compile(r"\b(?:essential|important|necessary|vital)\s+that\s+\w+\s+be\b", re.I),
    ),
    "second conditional": (
        re.compile(r"\bif\s+[^.?!]{0,80}\bwould\b", re.I),
    ),
    "third conditional": (
        re.compile(r"\bif\s+[^.?!]{0,80}\bwould have\b", re.I),
    ),
    "mixed conditionals": (
        re.compile(r"\bif\s+[^.?!]{0,80}\b(?:had|were)\b[^.?!]{0,40}\bwould\b", re.I),
    ),
    "inversion for emphasis": (
        re.compile(r"^(?:Never|rarely|seldom|hardly|scarcely|not only)\s+(?:have|has|had|do|does|did|was|were)\b", re.I),
    ),
    "cleft sentences": (
        re.compile(r"\b(?:what|it)\s+(?:is|was)\s+[^.?!]{0,40}\s+that\b", re.I),
    ),
    "complex nominalization": (
        re.compile(r"\b(?:implementation|utilization|characterization|operationalization)\s+of\b", re.I),
    ),
    "dense subordination": (
        re.compile(r"\b(?:although|whereas|nevertheless|notwithstanding|furthermore|moreover)\b", re.I),
    ),
    "dense academic syntax": (
        re.compile(r"\b(?:notwithstanding|heretofore|aforementioned|paradigmatic)\b", re.I),
    ),
    "literary inversion": (
        re.compile(r"^(?:Never|rarely|seldom)\s+\w+\s+(?:have|has|had)\b", re.I),
    ),
    "complex passive chains": (
        re.compile(r"\b(?:has|have|had)\s+been\s+(?:\w+ed|\w+en)\b", re.I),
    ),
    "embedded relative clauses": (
        re.compile(r"\b(?:who|which|that)\s+\w+\s*,?\s*(?:who|which|that)\s+", re.I),
    ),
}

# Lexemes that are too advanced for beginner/intermediate bands (heuristic).
_ADVANCED_LEXEMES = frozenset(
    """
    hypothesis paradigm mitigate jurisdiction geopolitical epistemology nevertheless
    notwithstanding interdisciplinary infrastructure globalization cognitive rhetoric nuanced
    explicitly fundamentally subsequently consequently furthermore implementation geopolitics
    operational proficiency nominalization subordinate clause modality pragmatic connotation
    epistemological jurisprudence obscurantist geopolitics interdisciplinary
    """.split()
)

_LEVEL_ADVANCED_WORD_LIMIT: dict[str, int] = {
    "A1": 0,
    "A2": 1,
    "B1": 3,
    "B2": 8,
    "C1": 15,
    "C2": 25,
}



@dataclass(frozen=True, slots=True)
class ValidationCheckResult:
    name: str
    passed: bool
    score: int
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ListeningValidationReport:
    passed: bool
    score: int
    level: str
    checks: dict[str, dict[str, Any]]

    def failed_check_names(self) -> list[str]:
        return [name for name, data in self.checks.items() if not data.get("passed")]

    def failure_summary(self) -> str:
        parts = [
            f"{name}: {self.checks[name].get('message', '')}"
            for name in self.failed_check_names()
        ]
        return "; ".join(parts) if parts else "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "level": self.level,
            "checks": self.checks,
        }


class ListeningCefrValidationExhaustedError(RuntimeError):
    """Raised when all CEFR validation regeneration attempts fail for one lesson."""

    def __init__(self, level: str, report: ListeningValidationReport | None = None):
        self.level = level
        self.report = report
        summary = report.failure_summary() if report else "unknown"
        super().__init__(f"Listening CEFR validation exhausted for {level}: {summary}")


def _count_words(text: str) -> int:
    return format_count_words(text)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _average_sentence_length(text: str) -> float:
    sentences = _split_sentences(text)
    if not sentences:
        return 0.0
    return sum(_count_words(s) for s in sentences) / len(sentences)


def _check_word_count(transcript: str, profile: CefrListeningProfile) -> ValidationCheckResult:
    count = _count_words(transcript)
    wl = profile.word_limits
    passed = wl.min_words <= count <= wl.max_words
    if passed:
        message = f"Word count {count} within {wl.min_words}–{wl.max_words}."
    else:
        message = f"Word count {count} outside {wl.min_words}–{wl.max_words}."
    return ValidationCheckResult(
        name="word_count",
        passed=passed,
        score=100 if passed else max(0, 100 - abs(count - wl.ideal_words)),
        message=message,
        details={"word_count": count, "min": wl.min_words, "max": wl.max_words, "ideal": wl.ideal_words},
    )


def _has_duplicate_sentences(transcript: str, fmt: ListeningTranscriptFormat) -> bool:
    sentences = _split_sentences(transcript)
    substantive = [s for s in sentences if _count_words(s) >= 7]
    if len(substantive) < 2:
        return False
    normalized = [s.lower().strip() for s in substantive]
    counts: dict[str, int] = {}
    for sentence in normalized:
        counts[sentence] = counts.get(sentence, 0) + 1
    if is_multi_speaker_format(fmt):
        return max(counts.values()) >= 3
    return len(set(normalized)) != len(normalized)


def _check_sentence_length(
    transcript: str,
    profile: CefrListeningProfile,
    fmt: ListeningTranscriptFormat,
) -> ValidationCheckResult:
    avg = _average_sentence_length(transcript)
    sl = get_format_sentence_limits(profile, fmt)
    sentence_ok = sl.min_words <= avg <= sl.max_words if avg > 0 else False

    turn_details: dict[str, Any] = {}
    turn_ok = True
    min_turn = min_average_turn_words(profile, fmt)
    if min_turn is not None:
        turns = extract_speaker_turns(transcript)
        turn_lengths = [_count_words(t) for t in turns if t.strip()]
        avg_turn = sum(turn_lengths) / len(turn_lengths) if turn_lengths else 0.0
        turn_ok = avg_turn >= min_turn if turn_lengths else False
        turn_details = {
            "average_turn_words": round(avg_turn, 2),
            "min_turn_words": min_turn,
            "turn_count": len(turn_lengths),
        }

    passed = sentence_ok and turn_ok
    parts = [
        f"sentence avg {avg:.1f} (need {sl.min_words}–{sl.max_words})",
    ]
    if min_turn is not None:
        parts.append(
            f"turn avg {turn_details.get('average_turn_words', 0):.1f} (need >={min_turn})"
        )
    message = (
        f"Length OK for format '{fmt.value}': {', '.join(parts)}."
        if passed
        else f"Length FAIL for format '{fmt.value}': {', '.join(parts)}."
    )

    return ValidationCheckResult(
        name="sentence_length",
        passed=passed,
        score=100 if passed else max(0, 60),
        message=message,
        details={
            "average_sentence_words": round(avg, 2),
            "min": sl.min_words,
            "max": sl.max_words,
            "transcript_format": fmt.value,
            "profile_sentence_min": profile.sentence_min_words,
            "profile_sentence_max": profile.sentence_max_words,
            **turn_details,
        },
    )


def _check_grammar(transcript: str, profile: CefrListeningProfile) -> ValidationCheckResult:
    hits: list[str] = []
    for label in profile.forbidden_grammar:
        key = label.strip().lower()
        patterns = _GRAMMAR_PATTERNS.get(key, ())
        for pattern in patterns:
            if pattern.search(transcript):
                hits.append(label)
                break
    passed = not hits
    message = "No forbidden grammar patterns detected." if passed else f"Forbidden grammar detected: {', '.join(hits)}."
    return ValidationCheckResult(
        name="grammar",
        passed=passed,
        score=100 if passed else max(0, 100 - 25 * len(hits)),
        message=message,
        details={"violations": hits},
    )


def _check_vocabulary(transcript: str, profile: CefrListeningProfile) -> ValidationCheckResult:
    tokens = {t.lower() for t in re.findall(r"\b[a-z]{5,}\b", transcript.lower())}
    advanced_hits = sorted(tokens & _ADVANCED_LEXEMES)
    limit = _LEVEL_ADVANCED_WORD_LIMIT.get(profile.level.value, 8)
    passed = len(advanced_hits) <= limit
    message = (
        f"Advanced vocabulary within limit ({len(advanced_hits)}/{limit})."
        if passed
        else f"Too many advanced words ({len(advanced_hits)} > {limit}): {', '.join(advanced_hits[:5])}."
    )
    return ValidationCheckResult(
        name="vocabulary",
        passed=passed,
        score=100 if passed else max(0, 100 - 20 * max(0, len(advanced_hits) - limit)),
        message=message,
        details={"advanced_hits": advanced_hits, "limit": limit, "vocabulary_band": profile.vocabulary_band},
    )


def _check_questions(questions: list[dict], profile: CefrListeningProfile) -> ValidationCheckResult:
    allowed = {t.value for t in profile.allowed_question_types}
    forbidden = {t.value for t in profile.forbidden_question_types}
    invalid: list[str] = []
    if not questions:
        return ValidationCheckResult(
            name="questions",
            passed=False,
            score=0,
            message="No questions present.",
            details={"invalid_types": [], "allowed": sorted(allowed)},
        )
    for q in questions:
        qtype = str(q.get("type") or "detail").strip()
        if qtype in forbidden or qtype not in allowed:
            invalid.append(qtype)
    passed = not invalid
    message = (
        "All question types allowed."
        if passed
        else f"Forbidden or disallowed question types: {', '.join(sorted(set(invalid)))}."
    )
    return ValidationCheckResult(
        name="questions",
        passed=passed,
        score=100 if passed else 0,
        message=message,
        details={"invalid_types": sorted(set(invalid)), "allowed": sorted(allowed), "count": len(questions)},
    )


def _check_learning_objectives(transcript: str, profile: CefrListeningProfile) -> ValidationCheckResult:
    text = transcript.lower()
    keywords: set[str] = set()
    for objective in profile.listening_objectives:
        for word in re.findall(r"[a-z]{4,}", objective.lower()):
            if word not in _STOPWORDS:
                keywords.add(word)
    suitable = profile.topic_complexity.lower().split("unsuitable:")[0]
    if "suitable:" in suitable:
        suitable = suitable.split("suitable:", 1)[1]
    for word in re.findall(r"[a-z]{4,}", suitable):
        if word not in _STOPWORDS:
            keywords.add(word)
    hits = sorted(k for k in keywords if k in text)
    # Lightweight heuristic: at least one objective/topic keyword OR simple comprehension markers.
    comprehension_markers = ("hello", "name", "price", "time", "today", "tomorrow", "please", "thank")
    marker_hit = any(m in text for m in comprehension_markers)
    passed = bool(hits) or marker_hit or _count_words(transcript) >= profile.word_limits.min_words
    message = (
        f"Objective/topic alignment OK ({len(hits)} keyword hits)."
        if passed
        else "Transcript does not reflect listening objectives or suitable topics."
    )
    return ValidationCheckResult(
        name="learning_objectives",
        passed=passed,
        score=100 if passed else 50,
        message=message,
        details={"keyword_hits": hits[:10], "keywords_considered": len(keywords)},
    )


def _check_transcript_quality(
    transcript: str,
    profile: CefrListeningProfile,
    fmt: ListeningTranscriptFormat,
) -> ValidationCheckResult:
    issues: list[str] = []
    if not transcript or not transcript.strip():
        issues.append("empty")
    if transcript and sum(c.isalpha() for c in transcript) < 10:
        issues.append("broken")
    if re.search(r'[{}\[\]"]\s*[{}\[\]"]', transcript):
        issues.append("malformed")
    words = re.findall(r"\b[\w']+\b", transcript.lower())
    if words:
        unique_words = len(set(words))
        unique_ratio = unique_words / len(words)
        min_unique_ratio = {
            "A1": 0.20,
            "A2": 0.24,
            "B1": 0.28,
            "B2": 0.30,
            "C1": 0.28,
            "C2": 0.26,
        }.get(profile.level.value, 0.32)
        min_unique_words = {
            "A1": 12,
            "A2": 18,
            "B1": 28,
            "B2": 35,
            "C1": 40,
            "C2": 40,
        }.get(profile.level.value, 30)
        if (
            len(words) >= 25
            and unique_ratio < min_unique_ratio
            and unique_words < min_unique_words
        ):
            issues.append("too_repetitive")
    if _has_duplicate_sentences(transcript, fmt):
        issues.append("duplicate_sentences")
    passed = not issues
    message = "Transcript quality OK." if passed else f"Transcript quality issues: {', '.join(issues)}."
    return ValidationCheckResult(
        name="transcript_quality",
        passed=passed,
        score=100 if passed else 0,
        message=message,
        details={"issues": issues, "word_count": len(words), "transcript_format": fmt.value},
    )


def validate_listening_lesson(
    body: dict[str, Any],
    level: str | LanguageLevel,
) -> ListeningValidationReport:
    """Validate a normalized listening ``body_json`` against the CEFR profile."""
    profile = get_cefr_profile(level)
    transcript = str(body.get("audio_transcript") or "").strip()
    questions = body.get("questions") if isinstance(body.get("questions"), list) else []
    fmt = classify_transcript_format(transcript)

    results = [
        _check_transcript_quality(transcript, profile, fmt),
        _check_word_count(transcript, profile),
        _check_sentence_length(transcript, profile, fmt),
        _check_grammar(transcript, profile),
        _check_vocabulary(transcript, profile),
        _check_questions(questions, profile),
        _check_learning_objectives(transcript, profile),
    ]

    checks = {r.name: {"passed": r.passed, "score": r.score, "message": r.message, **r.details} for r in results}
    passed = all(r.passed for r in results)
    score = round(sum(r.score for r in results) / len(results)) if results else 0
    return ListeningValidationReport(
        passed=passed,
        score=score,
        level=profile.level.value,
        checks=checks,
    )


def validation_check_result_to_dict(result: ValidationCheckResult) -> dict[str, Any]:
    return asdict(result)
