"""Heuristic evaluation of generated listening transcripts (Phase 2.1 verification)."""

from __future__ import annotations

import re

from app.services.language_listening_quality.catalog import GENERIC_AI_PHRASES, OVERUSED_TOPIC_HINTS

_SPEAKER_LABEL = re.compile(
    r"(?:^|\n)\s*([A-Z][A-Za-z.'\s]{0,40}(?:\([^)]{1,40}\))?)\s*:\s*",
    re.MULTILINE,
)
_TRANSITION_MARKERS = (
    "first",
    "then",
    "next",
    "however",
    "although",
    "finally",
    "in conclusion",
    "meanwhile",
    "after that",
    "before we",
    "to summarize",
)


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def score_cliche_penalty(transcript: str, level: str) -> tuple[int, list[str]]:
    lower = transcript.lower()
    hits = [p for p in GENERIC_AI_PHRASES if p in lower]
    if level == "A1":
        return len(hits) * 5, hits
    return len(hits) * 20, hits


def score_overused_topic_penalty(title: str, transcript: str) -> tuple[int, list[str]]:
    blob = f"{title} {transcript[:400]}".lower()
    hits = [t for t in OVERUSED_TOPIC_HINTS if t in blob]
    return len(hits) * 15, hits


def score_narrative_flow(transcript: str) -> tuple[int, list[str]]:
    lower = transcript.lower()
    found = [m for m in _TRANSITION_MARKERS if m in lower]
    sentences = _split_sentences(transcript)
    score = min(100, 40 + len(found) * 10 + min(20, len(sentences)))
    return score, found


def score_dialogue_quality(transcript: str) -> tuple[int, dict[str, object]]:
    labels = _SPEAKER_LABEL.findall(transcript)
    if len(labels) < 2:
        return 70, {"speaker_labels": len(labels), "note": "monologue_or_single_voice"}

    parts = _SPEAKER_LABEL.split(transcript)
    turns = [p.strip() for p in parts if p.strip() and not _SPEAKER_LABEL.match(p + ":")]
    turn_lengths = [_count_words(t) for t in turns if _count_words(t) > 0]
    if len(turn_lengths) < 2:
        return 60, {"speaker_labels": len(set(labels)), "turns": len(turn_lengths)}

    avg = sum(turn_lengths) / len(turn_lengths)
    variance = sum((x - avg) ** 2 for x in turn_lengths) / len(turn_lengths)
    std = variance**0.5
    unique_speakers = len(set(labels))
    score = min(100, 50 + int(std * 3) + unique_speakers * 8)
    return score, {
        "speaker_labels": unique_speakers,
        "turn_count": len(turn_lengths),
        "turn_length_std": round(std, 2),
    }


def score_listening_questions(questions: list[dict], transcript: str) -> tuple[int, dict[str, object]]:
    if not questions:
        return 0, {"count": 0}
    transcript_lower = transcript.lower()
    grounded = 0
    listening_types = {"inference", "speaker_intention", "tone", "purpose", "sequence", "detail", "bias", "prediction"}
    type_hits = 0
    for q in questions:
        quote = str(q.get("evidence_quote") or "").strip().lower()
        if quote and quote in transcript_lower:
            grounded += 1
        if str(q.get("type") or "") in listening_types:
            type_hits += 1
    count = len(questions)
    score = min(100, int(grounded / count * 60 + type_hits / count * 40))
    return score, {"grounded_evidence": grounded, "listening_type_questions": type_hits, "count": count}


def evaluate_listening_lesson(
    *,
    level: str,
    title: str,
    transcript: str,
    questions: list[dict],
    situation: str | None = None,
) -> dict[str, object]:
    """Composite heuristic quality score for verification reporting."""
    cliche_penalty, cliches = score_cliche_penalty(transcript, level)
    topic_penalty, overused = score_overused_topic_penalty(title, transcript)
    narrative_score, transitions = score_narrative_flow(transcript)
    dialogue_score, dialogue_meta = score_dialogue_quality(transcript)
    question_score, question_meta = score_listening_questions(questions, transcript)

    naturalness = max(0, 100 - cliche_penalty - topic_penalty)
    realism = 80 if situation and situation.replace("_", " ") in f"{title} {transcript[:300]}".lower() else 65

    composite = round(
        naturalness * 0.25
        + narrative_score * 0.2
        + dialogue_score * 0.15
        + question_score * 0.25
        + realism * 0.15
    )

    return {
        "composite_score": composite,
        "naturalness": naturalness,
        "narrative_score": narrative_score,
        "dialogue_score": dialogue_score,
        "question_score": question_score,
        "realism": realism,
        "cliches": cliches,
        "overused_topics": overused,
        "transitions_found": transitions,
        "dialogue_meta": dialogue_meta,
        "question_meta": question_meta,
    }
