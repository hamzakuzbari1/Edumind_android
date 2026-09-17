"""Journey-scoped narrative builder (Phase 2.3)."""

from __future__ import annotations

from app.services.language_learning_facts.labels import slug_label
from app.services.language_learning_facts.types import JourneyFactsBundle
from app.services.language_learning_narrative.types import (
    HistoryEventNarrative,
    JourneyNarrative,
    TimelineStepNarrative,
)
from app.services.language_promotion_readiness.types import ReadinessStatus


def _stage_key(readiness_band: str) -> str:
    mapping = {
        ReadinessStatus.NOT_READY.value: "practice",
        ReadinessStatus.ALMOST_READY.value: "improve",
        ReadinessStatus.READY.value: "master",
        ReadinessStatus.PROMOTION_AVAILABLE.value: "promotion",
    }
    return mapping.get(readiness_band, "practice")


def _journey_headline(facts: JourneyFactsBundle) -> str:
    promo = facts.promotion
    target = facts.journey_target.level
    if promo.can_start_test:
        return f"You are ready to take your promotion test for {target}."
    if promo.readiness_band == ReadinessStatus.PROMOTION_AVAILABLE.value:
        return f"You are almost ready to unlock {target}."
    if promo.readiness_score >= 80:
        return f"Strong progress toward {target} — keep building consistency."
    if promo.readiness_score >= 50:
        return f"You are building momentum toward {target}."
    return f"Practice listening regularly to progress from {facts.official_level} toward {target}."


def _current_step_label(facts: JourneyFactsBundle) -> str:
    promo = facts.promotion
    if promo.can_start_test or promo.readiness_band == ReadinessStatus.PROMOTION_AVAILABLE.value:
        return "Ready for promotion test"
    labels = {
        "practice": "Build listening practice",
        "improve": "Improve weak skills",
        "master": "Master current level",
        "promotion": "Prepare for promotion",
    }
    return labels.get(_stage_key(promo.readiness_band), "Build listening practice")


def _promotion_progress_message(facts: JourneyFactsBundle) -> str:
    promo = facts.promotion
    if promo.can_start_test:
        return "Your listening journey is ready for the official promotion test."
    if promo.readiness_score >= 80:
        return "You are very close to unlocking the next level."
    if promo.readiness_score >= 50:
        return "You are getting closer to your next official level."
    return "Great progress — keep practising listening regularly."


def _next_milestone(facts: JourneyFactsBundle) -> str:
    promo = facts.promotion
    target = facts.journey_target.level
    if promo.can_start_test:
        return f"Next milestone: start your {target} promotion test."
    remaining = promo.estimated_lessons_remaining
    if remaining is not None and remaining <= 15:
        return "Next milestone: you are almost unlocked."
    lessons = max(1, (remaining or 24) // 8) if remaining is not None else 3
    return f"Next milestone: about {lessons} more practice lesson(s)."


def _unlock_checklist(facts: JourneyFactsBundle) -> tuple[str, ...]:
    items: list[str] = []
    seen: set[str] = set()
    for raw in facts.promotion.primary_blockers:
        label = slug_label(raw) or raw
        action = f"Improve {label} through targeted listening practice."
        if action not in seen:
            seen.add(action)
            items.append(action)
    rec = facts.history.latest_recommendation
    if rec:
        cleaned = rec.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            items.append(cleaned)
    if facts.promotion.can_start_test:
        items.insert(0, "You have met the requirements — start your promotion test when ready.")
    return tuple(items[:5])


def _timeline_steps(facts: JourneyFactsBundle) -> tuple[TimelineStepNarrative, ...]:
    hist = facts.history
    promo = facts.promotion
    target = facts.journey_target.level
    official = facts.official_level
    test_done = hist.last_attempt_result == "PASS"
    test_active = hist.has_active_test_session or promo.can_start_test
    readiness_band = promo.readiness_band

    if hist.promoted or test_done:
        active_idx = 5
    elif test_active:
        active_idx = 3
    elif readiness_band in (ReadinessStatus.READY.value, ReadinessStatus.PROMOTION_AVAILABLE.value):
        active_idx = 2
    elif readiness_band == ReadinessStatus.ALMOST_READY.value:
        active_idx = 1
    else:
        active_idx = 0

    defs = [
        ("start", "Start your listening journey"),
        ("practice", "Build regular practice"),
        ("improve", "Improve weak skills"),
        ("ready", "Get ready for the test"),
        ("pass", "Pass the promotion test"),
        ("celebrate", f"Celebrate unlocking {target or official}"),
    ]
    steps: list[TimelineStepNarrative] = []
    for idx, (key, label) in enumerate(defs):
        steps.append(
            TimelineStepNarrative(
                key=key,
                label=label,
                done=idx < active_idx or (key == "pass" and test_done),
                active=idx == active_idx,
                current=idx == active_idx,
            )
        )
    return tuple(steps)


def _history_events(facts: JourneyFactsBundle) -> tuple[HistoryEventNarrative, ...]:
    events: list[HistoryEventNarrative] = []
    hist = facts.history
    last = hist.last_attempt_result
    if last == "PASS":
        events.append(
            HistoryEventNarrative(
                period="Latest",
                text=f"You passed your promotion test toward {hist.last_attempt_target_cefr or facts.journey_target.level}.",
            )
        )
    elif last:
        events.append(
            HistoryEventNarrative(
                period="Latest",
                text="Your last promotion attempt needs more practice — keep going.",
            )
        )
    promo = facts.promotion
    if promo.readiness_band == ReadinessStatus.PROMOTION_AVAILABLE.value:
        events.append(HistoryEventNarrative(period="Progress", text="You are ready for your promotion test."))
    elif promo.readiness_score >= 80:
        events.append(HistoryEventNarrative(period="Progress", text="Strong listening progress this stage."))
    elif promo.readiness_score >= 50:
        events.append(HistoryEventNarrative(period="Progress", text="Building momentum on your listening journey."))
    prediction = hist.stability_prediction
    if prediction:
        events.append(
            HistoryEventNarrative(
                period="Outlook",
                text=f"Promotion outlook: {slug_label(prediction)}.",
            )
        )
    if not events:
        events.append(
            HistoryEventNarrative(
                period="Start",
                text="Your listening journey begins with regular practice clips.",
            )
        )
    return tuple(events[:4])


def build_journey_narrative(facts: JourneyFactsBundle) -> JourneyNarrative:
    """Produce all journey-scoped student copy from structured facts."""
    _ = _next_milestone(facts)  # reserved for future narrative field expansion
    return JourneyNarrative(
        journey_headline=_journey_headline(facts),
        current_step_label=_current_step_label(facts),
        promotion_progress_message=_promotion_progress_message(facts),
        unlock_checklist=_unlock_checklist(facts),
        timeline_steps=_timeline_steps(facts),
        history_events=_history_events(facts),
    )
