"""Promotion test session builder (Phase 5.4).

Generates fresh, balanced listening assessment sessions with anti-memorization guards.
"""

from __future__ import annotations

import hashlib
import random
import time
import uuid

from app.services.language_listening_curriculum.objective_catalog import CATALOG
from app.services.language_promotion_test.config import DEFAULT_PROMOTION_TEST_CONFIG, PromotionTestConfig
from app.services.language_promotion_test.types import PromotionAssessmentSpec, PromotionTestSession

_OBJECTIVE_LABELS = {oid: label for oid, label, _, _ in CATALOG}

_QUESTION_TEMPLATES: dict[str, str] = {
    "main_idea": "What is the main idea of this listening passage?",
    "detail": "Which detail is explicitly stated in the passage?",
    "inference": "What can you infer from what was said?",
    "purpose": "What is the speaker's purpose?",
    "speaker_intention": "What is the speaker trying to accomplish?",
    "opinion": "What opinion does the speaker express?",
    "sequence": "What happens first in the sequence of events?",
    "prediction": "What is most likely to happen next?",
    "announcements": "What is the key information in the announcement?",
    "instructions": "What should the listener do according to the instructions?",
}

_CHOICE_BANK: dict[str, tuple[tuple[str, ...], int]] = {
    "main_idea": (
        (
            "The speaker describes a travel delay and next steps.",
            "The speaker introduces personal hobbies.",
            "The speaker lists unrelated facts.",
            "The speaker only greets the audience.",
        ),
        0,
    ),
    "detail": (
        (
            "The meeting starts at 3:30 p.m.",
            "The meeting was cancelled last month.",
            "The speaker moved to another country.",
            "No time was mentioned.",
        ),
        0,
    ),
    "inference": (
        (
            "The listener should arrive earlier than planned.",
            "The speaker dislikes all forms of travel.",
            "The event already finished yesterday.",
            "The speaker is reading a recipe.",
        ),
        0,
    ),
    "purpose": (
        (
            "To inform listeners about a schedule change.",
            "To advertise a cooking class.",
            "To tell a fictional story for entertainment only.",
            "To practice alphabet pronunciation.",
        ),
        0,
    ),
    "speaker_intention": (
        (
            "To persuade the listener to confirm attendance.",
            "To recite vocabulary with no context.",
            "To describe weather from last year only.",
            "To avoid giving any actionable information.",
        ),
        0,
    ),
    "opinion": (
        (
            "The new policy is inconvenient but necessary.",
            "The speaker has no view on the topic.",
            "The speaker refuses to discuss the topic.",
            "The speaker only gives numeric data.",
        ),
        0,
    ),
    "sequence": (
        (
            "Check in, pass security, then go to the gate.",
            "Eat dinner, then sleep, then wake up.",
            "Close the window, then open the window again.",
            "No order of events is described.",
        ),
        0,
    ),
    "prediction": (
        (
            "Passengers will board soon.",
            "The airport will close permanently.",
            "The speaker will switch to written homework.",
            "The conversation will become a song.",
        ),
        0,
    ),
}


def _label_for(objective_id: str) -> str:
    return _OBJECTIVE_LABELS.get(objective_id, objective_id.replace("_", " ").title())


def _shuffle_choices_deterministic(
    choices: tuple[str, ...],
    correct_index: int,
    *,
    seed: str,
) -> tuple[tuple[str, ...], int]:
    """Shuffle choices for one session; stable for the same seed."""
    if len(choices) <= 1:
        return choices, correct_index
    order = list(range(len(choices)))
    rng = random.Random(seed)
    rng.shuffle(order)
    shuffled = tuple(choices[i] for i in order)
    return shuffled, order.index(correct_index)


def _difficulty_band(official_cefr: str) -> str:
    return f"upper_{official_cefr.lower()}"


def _balanced_objectives(
    *,
    count: int,
    config: PromotionTestConfig,
    used_sequences: set[tuple[str, ...]],
) -> tuple[str, ...]:
    pool = list(config.objective_pool)
    selected: list[str] = []
    attempts = 0
    while len(selected) < count and attempts < 50:
        idx = len(selected)
        objective = pool[idx % len(pool)]
        if selected.count(objective) >= config.max_per_objective:
            objective = pool[(idx + attempts) % len(pool)]
        if selected.count(objective) < config.max_per_objective:
            selected.append(objective)
        attempts += 1
    candidate = tuple(selected[:count])
    if candidate in used_sequences and len(pool) >= count:
        rotated = tuple(pool[i % len(pool)] for i in range(1, count + 1))
        if rotated not in used_sequences:
            return rotated
    return candidate


def build_promotion_test_session(
    *,
    student_id: int,
    language_id: int,
    official_cefr: str,
    target_cefr: str,
    attempt_number: int,
    used_lesson_ids: set[str],
    used_sequences: set[tuple[str, ...]],
    config: PromotionTestConfig = DEFAULT_PROMOTION_TEST_CONFIG,
) -> PromotionTestSession:
    """Build a fresh promotion test session — no reused lesson IDs or sequences."""
    session_id = str(uuid.uuid4())
    objective_sequence = _balanced_objectives(
        count=config.assessment_count,
        config=config,
        used_sequences=used_sequences,
    )

    assessments: list[PromotionAssessmentSpec] = []
    lesson_ids: list[str] = []

    for index, objective_id in enumerate(objective_sequence):
        assessment_id = str(uuid.uuid4())
        digest = hashlib.sha256(f"{session_id}:{objective_id}:{index}".encode()).hexdigest()[:12]
        lesson_id = f"listening-promo-{digest}"
        while lesson_id in used_lesson_ids or lesson_id in lesson_ids:
            digest = hashlib.sha256(f"{lesson_id}:{time.time_ns()}".encode()).hexdigest()[:12]
            lesson_id = f"listening-promo-{digest}"

        lesson_ids.append(lesson_id)
        bank_choices, bank_correct_index = _CHOICE_BANK.get(
            objective_id,
            _CHOICE_BANK["detail"],
        )
        choices, correct_index = _shuffle_choices_deterministic(
            bank_choices,
            bank_correct_index,
            seed=f"{session_id}:{assessment_id}",
        )
        situation = config.situation_pool[index % len(config.situation_pool)]
        fmt = config.format_pool[index % len(config.format_pool)]
        speakers = config.speaker_options[index % len(config.speaker_options)]

        assessments.append(
            PromotionAssessmentSpec(
                assessment_id=assessment_id,
                lesson_id=lesson_id,
                objective_id=objective_id,
                objective_label=_label_for(objective_id),
                situation=situation,
                format=fmt,
                speaker_count=speakers,
                difficulty_band=_difficulty_band(official_cefr),
                question=_QUESTION_TEMPLATES.get(objective_id, "Answer the listening question."),
                choices=choices,
                correct_index=correct_index,
                sequence_index=index,
            )
        )

    return PromotionTestSession(
        session_id=session_id,
        student_id=student_id,
        language_id=language_id,
        official_cefr=official_cefr.upper(),
        target_cefr=target_cefr.upper(),
        attempt_number=attempt_number,
        assessments=assessments,
        expires_at=time.time() + config.session_ttl_seconds,
        objective_sequence=objective_sequence,
        lesson_ids=tuple(lesson_ids),
    )
