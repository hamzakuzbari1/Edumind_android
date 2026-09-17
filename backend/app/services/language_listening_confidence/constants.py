"""Confidence engine constants (Phase 3.2)."""

from __future__ import annotations

MASTERY_THRESHOLD = 0.90
MASTERY_SCORE_THRESHOLD = 0.81
MIN_COVERAGE_FOR_MASTERY = 0.50
EVIDENCE_INFLUENCE = 0.08
INITIAL_CONFIDENCE = 0.35
CONFIDENCE_FLOOR = 0.25

MAX_GAIN_PER_LESSON = 0.10
MAX_LOSS_PER_LESSON = 0.06
MAX_SINGLE_STEP = 0.10

BASE_ALPHA = 0.15
MAX_ALPHA = 0.24

DIFFICULTY_WEIGHT: dict[str, float] = {
    "easy": 0.80,
    "normal": 1.0,
    "challenging": 1.30,
}

DECAY_START_LESSONS = 28
DECAY_RATE_PER_LESSON = 0.0007
MAX_DECAY_PER_APPLICATION = 0.05

REVIEW_INTERVAL = 12
REVIEW_CONFIDENCE_MIN = 0.75

CONFIDENCE_INFLUENCE = 0.10
CONFIDENCE_KEY = "listening_confidence"
LESSON_CONFIDENCE_KEY = "listening_confidence_lesson"

QUESTION_TYPE_TO_OBJECTIVE: dict[str, str] = {
    "main_idea": "main_idea",
    "detail": "detail",
    "inference": "inference",
    "purpose": "purpose",
    "speaker_intention": "speaker_intention",
    "tone": "tone",
    "prediction": "prediction",
    "sequence": "sequence",
    "opinion": "opinion",
    "bias": "bias",
    "vocab_in_context": "detail",
    "true_false_notgiven": "detail",
    "sentence_completion": "detail",
    "heading_match": "main_idea",
}

DIFFICULTY_EVIDENCE_DIMS: tuple[str, ...] = ("easy", "normal", "hard", "exam")
FORMAT_EVIDENCE_DIMS: tuple[str, ...] = (
    "dialogue",
    "monologue",
    "interview",
    "lecture",
    "discussion",
    "panel",
    "podcast",
    "news",
)
TOPIC_EVIDENCE_DIMS: tuple[str, ...] = (
    "travel",
    "business",
    "education",
    "health",
    "technology",
    "daily_life",
    "customer_service",
    "meetings",
    "announcements",
    "museum",
)
SPEAKER_EVIDENCE_DIMS: tuple[str, ...] = ("single", "two", "multi")
SPEED_EVIDENCE_DIMS: tuple[str, ...] = ("slow", "normal", "fast")

COVERAGE_AXIS_WEIGHTS: dict[str, float] = {
    "difficulty": 0.22,
    "format": 0.22,
    "topic": 0.22,
    "speaker": 0.17,
    "speed": 0.17,
}
