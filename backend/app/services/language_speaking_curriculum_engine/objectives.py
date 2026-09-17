"""Objective engine — typed educational objectives from mission + vocab + CEFR."""

from __future__ import annotations

from app.services.language_speaking_curriculum_engine.types import (
    EducationalObjective,
    ObjectiveKind,
    VocabularyTarget,
)
from app.services.language_speaking_curriculum_engine.educational_world import (
    sanitize_educational_text,
)


def build_educational_objectives(
    *,
    cefr: str,
    learning_focus: str,
    mission_title: str,
    mission_objectives: list[str],
    vocabulary: list[VocabularyTarget],
    transfer_expectation: str,
) -> list[EducationalObjective]:
    """Replace a single shallow objective with a structured set."""
    focus = sanitize_educational_text(
        learning_focus or mission_title,
        fallback="spoken communication",
    )
    surfaces = [v.surface for v in vocabulary[:4] if v.surface]
    surface_list = ", ".join(f"“{s}”" for s in surfaces[:3]) if surfaces else "the lesson phrases"

    seed = next(
        (
            sanitize_educational_text(o, fallback="")
            for o in mission_objectives
            if o and str(o).strip()
        ),
        "",
    )
    communicative = seed or f"Handle a short spoken exchange about {focus}."
    if "alex" in communicative.lower():
        communicative = f"Handle a short spoken exchange about {focus}."

    objs: list[EducationalObjective] = [
        EducationalObjective(
            kind=ObjectiveKind.communicative,
            text=communicative if "speak" in communicative.lower() or "use" in communicative.lower()
            else f"Communicate clearly in a real spoken situation related to {focus}.",
            priority=1,
        ),
        EducationalObjective(
            kind=ObjectiveKind.vocabulary,
            text=f"Use {surface_list} accurately in context.",
            priority=2,
        ),
        EducationalObjective(
            kind=ObjectiveKind.speaking,
            text=_speaking_objective_for_cefr(cefr, focus),
            priority=3,
        ),
        EducationalObjective(
            kind=ObjectiveKind.transfer,
            text=_transfer_objective(transfer_expectation, focus, surfaces),
            priority=4,
        ),
    ]
    # Grammar objective reserved — omitted while Grammar module not ready
    return objs


def _speaking_objective_for_cefr(cefr: str, focus: str) -> str:
    level = (cefr or "A2").upper()
    if level == "A1":
        return f"Say short, clear sentences about {focus} with support."
    if level == "A2":
        return f"Speak in connected short turns about {focus} with understandable pacing."
    if level == "B1":
        return f"Sustain a conversation about {focus} with reasons and follow-up answers."
    return f"Manage speaking delivery (clarity, pacing, elaboration) while discussing {focus}."


def _transfer_objective(expectation: str, focus: str, surfaces: list[str]) -> str:
    sample = surfaces[0] if surfaces else "the target phrases"
    exp = (expectation or "").lower()
    if "near" in exp or "greeting" in exp:
        return f"Reuse {sample} when meeting someone in a similar arrival situation."
    if "personal" in exp:
        return f"Adapt the lesson language to a personal situation related to {focus}."
    if "independent" in exp or "strategy" in exp:
        return f"Apply a speaking strategy from this lesson in a new real-world task about {focus}."
    return f"Reuse the lesson language in a new situation related to {focus}."


def flatten_objective_texts(objectives: list[EducationalObjective]) -> list[str]:
    return [o.text for o in objectives if o.text]
