"""Question ladder bands and policy (author-once discussion steps)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class QuestionBand(StrEnum):
    literal = "literal"
    vocabulary = "vocabulary"
    grammar_in_context = "grammar_in_context"
    reasoning = "reasoning"
    personal_opinion = "personal_opinion"
    personal_experience = "personal_experience"
    real_world_transfer = "real_world_transfer"


LADDER_ORDER: tuple[QuestionBand, ...] = (
    QuestionBand.literal,
    QuestionBand.vocabulary,
    QuestionBand.grammar_in_context,
    QuestionBand.reasoning,
    QuestionBand.personal_opinion,
    QuestionBand.personal_experience,
    QuestionBand.real_world_transfer,
)


@dataclass(frozen=True, slots=True)
class QuestionLadderPolicy:
    """Backend-owned required bands + counts for package authoring."""

    required_bands: tuple[QuestionBand, ...]
    min_steps: int = 4
    max_steps: int = 10

    def to_dict(self) -> dict[str, object]:
        return {
            "required_bands": [b.value for b in self.required_bands],
            "min_steps": self.min_steps,
            "max_steps": self.max_steps,
        }

    @staticmethod
    def from_dict(raw: dict[str, object] | None) -> QuestionLadderPolicy:
        if not isinstance(raw, dict):
            return QuestionLadderPolicy(required_bands=LADDER_ORDER[:4])
        bands_raw = raw.get("required_bands") or []
        bands: list[QuestionBand] = []
        if isinstance(bands_raw, list):
            for item in bands_raw:
                try:
                    bands.append(QuestionBand(str(item)))
                except ValueError:
                    continue
        if not bands:
            bands = list(LADDER_ORDER[:4])
        return QuestionLadderPolicy(
            required_bands=tuple(bands),
            min_steps=max(1, int(raw.get("min_steps") or 4)),
            max_steps=max(1, int(raw.get("max_steps") or 10)),
        )


def default_ladder_policy_for_cefr(cefr: str) -> QuestionLadderPolicy:
    level = (cefr or "A2").upper()
    if level in {"A1", "A2"}:
        return QuestionLadderPolicy(
            required_bands=(
                QuestionBand.literal,
                QuestionBand.vocabulary,
                QuestionBand.reasoning,
                QuestionBand.personal_opinion,
            ),
            min_steps=4,
            max_steps=7,
        )
    if level in {"B1", "B2"}:
        return QuestionLadderPolicy(
            required_bands=(
                QuestionBand.literal,
                QuestionBand.vocabulary,
                QuestionBand.grammar_in_context,
                QuestionBand.reasoning,
                QuestionBand.personal_experience,
                QuestionBand.real_world_transfer,
            ),
            min_steps=6,
            max_steps=9,
        )
    return QuestionLadderPolicy(required_bands=LADDER_ORDER, min_steps=7, max_steps=10)
