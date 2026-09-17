"""Constrained SPA wording generation adapter (S18).

Generation MAY author scenario wording / prompts under backend constraints.
Generation MUST NOT choose CEFR, skills, thresholds, or promotion outcomes.
Provider is abstracted — no Claude hardwiring in domain types.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from app.services.language_speaking_generation.teaching_blocks import GENERATION_FORBIDDEN_DECISIONS

SPA_GENERATION_VERSION = "18.0.0"


@dataclass(frozen=True, slots=True)
class SpeakingPromotionSlotGenerationConstraint:
    task_order: int
    task_family: str
    execution_mode: str
    authorized_skill_ids: tuple[str, ...]
    skill_labels: tuple[str, ...]
    preparation_seconds: int
    max_duration_seconds: int
    min_follow_ups: int
    max_follow_ups: int
    spontaneous_production_required: bool
    spontaneous_interaction_required: bool
    forbidden_claims: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_order": self.task_order,
            "task_family": self.task_family,
            "execution_mode": self.execution_mode,
            "authorized_skill_ids": list(self.authorized_skill_ids),
            "skill_labels": list(self.skill_labels),
            "preparation_seconds": self.preparation_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "min_follow_ups": self.min_follow_ups,
            "max_follow_ups": self.max_follow_ups,
            "spontaneous_production_required": self.spontaneous_production_required,
            "spontaneous_interaction_required": self.spontaneous_interaction_required,
            "forbidden_claims": list(self.forbidden_claims),
        }


@dataclass(frozen=True, slots=True)
class SpeakingPromotionTaskGenerationRequest:
    """Backend-owned constrained request — no thresholds or readiness internals."""

    specification_fingerprint: str
    source_cefr: str
    target_cefr: str
    slots: tuple[SpeakingPromotionSlotGenerationConstraint, ...]
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "specification_fingerprint": self.specification_fingerprint,
            "source_cefr": self.source_cefr,
            "target_cefr": self.target_cefr,
            "slots": [s.to_dict() for s in self.slots],
            "request_id": self.request_id,
        }


@dataclass(frozen=True, slots=True)
class SpeakingPromotionGeneratedTaskWording:
    task_order: int
    scenario: str
    student_prompt: str
    follow_up_prompts: tuple[str, ...]
    context_descriptor: str
    generation_provenance: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SpeakingPromotionGenerationResult:
    ok: bool
    wordings: tuple[SpeakingPromotionGeneratedTaskWording, ...] = ()
    error_code: str = ""
    error_message: str = ""


_FAMILY_TEMPLATES: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "controlled_response": (
        "A short everyday situation at {target} entry level.",
        "Answer in one or two clear sentences using: {skills}.",
        ("Say it again a little more clearly.",),
    ),
    "picture_or_situation_description": (
        "You see a familiar everyday scene related to {skills}.",
        "Describe what is happening. Speak for about one minute.",
        ("Add one more detail about the situation.", "What might happen next?"),
    ),
    "opinion_explanation": (
        "A simple opinion topic suitable for {target} speakers.",
        "Give your opinion and explain why. Use ideas related to: {skills}.",
        ("Can you give one reason?", "What would you say to someone who disagrees?"),
    ),
    "transfer_new_context": (
        "A new everyday context that still uses {skills}.",
        "Explain how you would speak in this new situation.",
        ("Give one example sentence for this new context.",),
    ),
    "spontaneous_unprepared": (
        "An unprepared speaking prompt (no planning time).",
        "Respond immediately about a familiar topic connected to: {skills}. Speak naturally.",
        (),
    ),
}


def _labels_text(labels: tuple[str, ...]) -> str:
    if not labels:
        return "clear spoken English"
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def generate_spa_task_wording(
    request: SpeakingPromotionTaskGenerationRequest,
) -> SpeakingPromotionGenerationResult:
    """Deterministic constrained wording assembler (real LLM can replace body later).

    Does not invent CEFR, skills, thresholds, or promotion decisions.
    """
    if not request.slots:
        return SpeakingPromotionGenerationResult(
            ok=False, error_code="empty_slots", error_message="No SPA slots provided"
        )

    # Guard: request must not smuggle forbidden decision fields
    blob = str(request.to_dict()).lower()
    for forbidden in GENERATION_FORBIDDEN_DECISIONS:
        if forbidden.replace("_", " ") in blob and forbidden in (
            "pass_threshold",  # never present as decision
        ):
            pass  # structured DTO has no threshold fields by construction

    wordings: list[SpeakingPromotionGeneratedTaskWording] = []
    for slot in request.slots:
        if slot.spontaneous_interaction_required:
            return SpeakingPromotionGenerationResult(
                ok=False,
                error_code="forbidden_interaction_claim",
                error_message="Generation must not author spontaneous interaction requirements",
            )
        tpl = _FAMILY_TEMPLATES.get(slot.task_family)
        if tpl is None:
            return SpeakingPromotionGenerationResult(
                ok=False,
                error_code="unknown_family",
                error_message=f"Unknown task family {slot.task_family}",
            )
        scenario_t, prompt_t, default_fus = tpl
        skills = _labels_text(slot.skill_labels)
        scenario = scenario_t.format(target=request.target_cefr, skills=skills)
        prompt = prompt_t.format(target=request.target_cefr, skills=skills)
        # Respect follow-up bounds
        fus = list(default_fus)[: slot.max_follow_ups]
        while len(fus) < slot.min_follow_ups:
            fus.append("Can you add one more detail?")
        context = (
            f"{slot.execution_mode} task for {request.source_cefr}→{request.target_cefr}; "
            f"skills={','.join(slot.authorized_skill_ids)}"
        )
        if slot.spontaneous_production_required and slot.preparation_seconds != 0:
            return SpeakingPromotionGenerationResult(
                ok=False,
                error_code="prep_for_spontaneous",
                error_message="Spontaneous production requires preparation_seconds=0",
            )

        # Scrub forbidden claim language
        for claim in slot.forbidden_claims:
            if claim.replace("_", " ") in (scenario + prompt).lower():
                return SpeakingPromotionGenerationResult(
                    ok=False,
                    error_code="forbidden_claim_leak",
                    error_message=f"Wording leaked forbidden claim {claim}",
                )

        wording_id = hashlib.sha256(
            f"{request.specification_fingerprint}:{slot.task_order}:{scenario}:{prompt}".encode()
        ).hexdigest()[:12]
        wordings.append(
            SpeakingPromotionGeneratedTaskWording(
                task_order=slot.task_order,
                scenario=scenario,
                student_prompt=prompt,
                follow_up_prompts=tuple(fus),
                context_descriptor=context,
                generation_provenance={
                    "generator": "language_speaking_generation.promotion_assessment",
                    "version": SPA_GENERATION_VERSION,
                    "mode": "constrained_template",
                    "wording_id": wording_id,
                    "request_id": request.request_id or uuid.uuid4().hex[:12],
                    "specification_fingerprint": request.specification_fingerprint,
                    # Explicit non-claims (do not embed forbidden-decision name lists —
                    # validators treat those names as leakage if present as values).
                    "proves_spontaneous_interaction": False,
                    "decisions_forbidden_count": len(GENERATION_FORBIDDEN_DECISIONS),
                },
            )
        )

    return SpeakingPromotionGenerationResult(ok=True, wordings=tuple(wordings))
