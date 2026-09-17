"""Adaptive Challenge Engine constants (Phase 3.3)."""

from __future__ import annotations

CHALLENGE_KEY = "listening_challenge"
LESSON_CHALLENGE_KEY = "listening_challenge_lesson"
CHALLENGE_INFLUENCE = 0.075

HISTORY_WINDOW = 15
DEFAULT_CHALLENGE = "normal"

PROMOTE_SCORE_THRESHOLD = 0.68
DEMOTE_SCORE_THRESHOLD = 0.42
STRONG_LESSON_THRESHOLD = 0.62
WEAK_LESSON_THRESHOLD = 0.40
PROMOTE_STREAK_REQUIRED = 4
DEMOTE_STREAK_REQUIRED = 4

CHALLENGE_LEVEL_ORDER: tuple[str, ...] = ("easy", "normal", "hard", "exam")

TRANSCRIPT_LENGTH_MULTIPLIER: dict[str, float] = {
    "easy": 0.88,
    "normal": 1.0,
    "hard": 1.06,
    "exam": 1.10,
}
