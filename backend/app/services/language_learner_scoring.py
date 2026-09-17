"""Pure estimation logic for the Learner Model — the heart of the system.

No I/O, no DB, no async — every function here is deterministic and unit-tested. The service layer
(`language_learner_model_service`) calls these and persists the results.

Three layers:
  1. BKT  — `update_bkt`      (probabilistic mastery from correct/incorrect evidence)
  2. decay — `apply_decay`    (exponential forgetting toward a baseline)
  3. derive — `derive_skill_cefr`, `update_confidence` (roll component mastery up to a skill level)

SM-2 is NOT reimplemented here — import `compute_sm2` from `language_vocabulary_sr_service`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

# CEFR rank helpers (kept local + pure; mirror language_level_utils ordering A1..C2 = 0..5).
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def cefr_rank(level: str) -> int:
    try:
        return CEFR_ORDER.index(level)
    except ValueError:
        return 0


def cefr_from_rank(rank: int) -> str:
    return CEFR_ORDER[max(0, min(len(CEFR_ORDER) - 1, int(rank)))]


# --- source sensitivity ---------------------------------------------------------------
# Evidence quality differs by where it came from. A vetted placement question is strong
# evidence (low guess/slip); an AI-generated daily item is weaker (higher guess/slip), and
# placement measures rather than teaches (p_learn = 0).
@dataclass(frozen=True)
class BktParams:
    p_learn: float
    p_slip: float
    p_guess: float


BKT_PARAMS: dict[str, BktParams] = {
    "placement": BktParams(p_learn=0.0, p_slip=0.10, p_guess=0.20),
    "vocab": BktParams(p_learn=0.15, p_slip=0.15, p_guess=0.25),
    "writing": BktParams(p_learn=0.10, p_slip=0.20, p_guess=0.10),
    "speaking": BktParams(p_learn=0.10, p_slip=0.20, p_guess=0.10),
    "daily": BktParams(p_learn=0.15, p_slip=0.20, p_guess=0.30),
}
_DEFAULT_PARAMS = BktParams(p_learn=0.10, p_slip=0.20, p_guess=0.25)

# Evidence weight per source (drives confidence growth & which source "owns" the row).
SOURCE_WEIGHT: dict[str, float] = {
    "placement": 1.0,
    "writing": 0.8,
    "speaking": 0.8,
    "vocab": 0.6,
    "daily": 0.5,
}

CONFIDENCE_K = 5.0          # evidence count at which confidence reaches 0.5
MASTERY_THRESHOLD = 0.6     # weighted p_mastery needed to count a CEFR band as "reached"


def params_for(source: str) -> BktParams:
    return BKT_PARAMS.get(source, _DEFAULT_PARAMS)


def source_weight(source: str) -> float:
    return SOURCE_WEIGHT.get(source, 0.5)


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def update_bkt(p_mastery: float, correct: bool, p_learn: float, p_slip: float, p_guess: float) -> float:
    """Bayesian Knowledge Tracing posterior + learning step. Returns new P(mastery) in [0,1].

    A correct answer is discounted by guessing; a wrong answer by slipping.
    """
    p = _clamp(p_mastery)
    if correct:
        num = p * (1.0 - p_slip)
        den = num + (1.0 - p) * p_guess
    else:
        num = p * p_slip
        den = num + (1.0 - p) * (1.0 - p_guess)
    posterior = (num / den) if den > 0 else p
    # Account for learning during the interaction (placement uses p_learn=0 — it only measures).
    updated = posterior + (1.0 - posterior) * p_learn
    return _clamp(updated)


def apply_decay(mastery: float, days_since: float, half_life_days: float, floor: float = 0.0) -> float:
    """Exponential forgetting toward ``floor``. After ``half_life_days`` the gap above floor halves."""
    if days_since <= 0 or half_life_days <= 0:
        return _clamp(mastery)
    factor = 0.5 ** (days_since / half_life_days)
    floor = _clamp(floor)
    return _clamp(floor + (mastery - floor) * factor)


def update_confidence(current_confidence: float, evidence_count: int) -> float:
    """Confidence saturates with evidence: count/(count+K). Monotonic, never drops."""
    n = max(0, int(evidence_count))
    grown = n / (n + CONFIDENCE_K) if (n + CONFIDENCE_K) > 0 else 0.0
    return _clamp(max(current_confidence, grown))


def derive_skill_cefr(masteries: list[tuple[str, float, float]]) -> str:
    """Roll component masteries up to a single CEFR level for the skill.

    ``masteries``: list of (component_cefr, p_mastery_after_decay, confidence). The level is the
    highest CEFR band whose confidence-weighted mean mastery clears MASTERY_THRESHOLD (a band with
    evidence that fails the threshold stops the climb). No evidence -> A1.
    """
    if not masteries:
        return "A1"
    num: dict[int, float] = defaultdict(float)
    den: dict[int, float] = defaultdict(float)
    for level, p_mastery, confidence in masteries:
        r = cefr_rank(level)
        w = max(float(confidence), 0.01)
        num[r] += _clamp(p_mastery) * w
        den[r] += w

    reached = -1
    for r in range(len(CEFR_ORDER)):
        if den.get(r, 0.0) <= 0.0:
            continue  # no evidence at this band — skip, don't block
        mean = num[r] / den[r]
        if mean >= MASTERY_THRESHOLD:
            reached = r
        else:
            break  # evidence says this band isn't mastered — stop climbing
    return cefr_from_rank(reached if reached >= 0 else 0)
