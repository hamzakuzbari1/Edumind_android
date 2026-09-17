"""Teaching-block generation contracts (S10) — language_speaking_generation ownership.

Generation produces typed teaching content for the educational mission foundation.
The teaching-block CONTRACT (`SpeakingTeachingBlock`) is owned by the planning layer
(`language_speaking_lesson_planner.mission_types`) so missions can embed it without a
lower->higher layer dependency. Generation (a higher layer) imports those contracts and
fills them.

Hard boundary: generation MAY author explanations, examples, contrasts, noticing cues,
scaffolds, guided prompts, and misconception corrections. Generation MUST NOT decide
mastery, stage completion, CEFR readiness, promotion, or mutate official state. The
deterministic assembler below is a template stub; a real LLM author plugs in here
without gaining any progression authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.language_speaking.enums import SpeakingTeachingBlockKind
from app.services.language_speaking_lesson_planner.mission_types import SpeakingTeachingBlock

TEACHING_GENERATION_VERSION = "10.0.0"

# Decisions the content generator is forbidden from making (mirrors writing generator).
GENERATION_FORBIDDEN_DECISIONS: frozenset[str] = frozenset(
    {
        "mastery",
        "stage_completion",
        "learning_stage",
        "cefr_readiness",
        "official_speaking_cefr",
        "promotion",
        "evidence_application",
    }
)


@dataclass(frozen=True, slots=True)
class SpeakingTeachingBlockRequest:
    """Deterministic request describing the teaching block to author."""

    request_id: str
    kind: SpeakingTeachingBlockKind
    target_skill_id: str
    target_skill_label: str
    objective_text: str = ""
    official_cefr_hint: str = "A2"
    speaking_goal: str = "general_english"

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "kind": self.kind.value,
            "target_skill_id": self.target_skill_id,
            "target_skill_label": self.target_skill_label,
            "objective_text": self.objective_text,
            "official_cefr_hint": self.official_cefr_hint,
            "speaking_goal": self.speaking_goal,
        }


_TEMPLATES: dict[SpeakingTeachingBlockKind, tuple[str, str]] = {
    SpeakingTeachingBlockKind.explanation: ("What is {label}?", "{label} helps you express yourself more clearly when you speak."),
    SpeakingTeachingBlockKind.example: ("Example: {label}", "Here is a short model that uses {label}."),
    SpeakingTeachingBlockKind.contrast: ("Compare: {label}", "Compare a weaker answer with a stronger one that uses {label}."),
    SpeakingTeachingBlockKind.noticing_cue: ("Notice: {label}", "Notice where {label} changes what the speaker means."),
    SpeakingTeachingBlockKind.scaffold: ("Sentence frame for {label}", "Use a frame like 'I think ___ because ___' to practise {label}."),
    SpeakingTeachingBlockKind.guided_prompt: ("Try it: {label}", "Answer one guided prompt and try to use {label}."),
    SpeakingTeachingBlockKind.misconception_correction: ("Common slip with {label}", "A common slip is forgetting {label}; add it next time."),
}


def draft_teaching_block(request: SpeakingTeachingBlockRequest) -> SpeakingTeachingBlock:
    """Assemble a typed teaching block from deterministic templates.

    Returns a `SpeakingTeachingBlock` with `is_evidence=False` — generated teaching
    content is never evidence. Real AI generation can replace the template body without
    changing the contract or gaining progression authority.
    """
    title_tpl, body_tpl = _TEMPLATES.get(
        request.kind,
        ("{label}", "Practise {label}."),
    )
    label = request.target_skill_label or request.target_skill_id
    return SpeakingTeachingBlock(
        block_id=f"gen-tb-{request.request_id}",
        kind=request.kind,
        title=title_tpl.format(label=label),
        body=body_tpl.format(label=label),
        target_skill_ids=(request.target_skill_id,),
        is_evidence=False,
    )
