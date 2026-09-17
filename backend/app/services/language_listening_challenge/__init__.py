"""Adaptive Challenge Engine (Phase 3.3)."""

from app.services.language_listening_challenge.constants import (
    CHALLENGE_INFLUENCE,
    CHALLENGE_KEY,
    LESSON_CHALLENGE_KEY,
)
from app.services.language_listening_challenge.engine import recommend_challenge_adaptive_listening_plan
from app.services.language_listening_challenge.prompt import build_adaptive_challenge_prompt_block
from app.services.language_listening_challenge.record import record_challenge_from_lesson
from app.services.language_listening_challenge.scoring import (
    map_challenge_to_difficulty_band,
    plan_challenge_match_score,
)
from app.services.language_listening_challenge.storage import (
    build_initial_challenge_state,
    load_challenge_state,
    load_student_challenge,
    save_student_challenge,
    serialize_challenge_state,
)
from app.services.language_listening_challenge.telemetry import compute_challenge_telemetry
from app.services.language_listening_challenge.types import (
    ChallengeAwareRecommendation,
    ChallengeLevel,
    ChallengeState,
    ChallengeTelemetry,
)

__all__ = (
    "CHALLENGE_INFLUENCE",
    "CHALLENGE_KEY",
    "LESSON_CHALLENGE_KEY",
    "ChallengeAwareRecommendation",
    "ChallengeLevel",
    "ChallengeState",
    "ChallengeTelemetry",
    "build_adaptive_challenge_prompt_block",
    "build_initial_challenge_state",
    "compute_challenge_telemetry",
    "load_challenge_state",
    "load_student_challenge",
    "map_challenge_to_difficulty_band",
    "plan_challenge_match_score",
    "recommend_challenge_adaptive_listening_plan",
    "record_challenge_from_lesson",
    "save_student_challenge",
    "serialize_challenge_state",
)
