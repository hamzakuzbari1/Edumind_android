"""Gemini question generation for the Learner Model.

Two models by purpose:
  A. Placement — generated OFFLINE, each passes a strict second-LLM verification before storage
     (clear, exactly one correct answer, matches the target CEFR/component). Verified rows go into
     `LanguageGeneratedQuestion` (source="placement") and the adaptive engine draws from this bank.
  B. Daily learning — generated on the fly for a learner's weak point, lightweight verification,
     not persisted (ephemeral).

Answering these questions feeds the Learner Model via `process_event` (wired by the consuming
feature, with the right `source`). Reuses the existing Gemini wrapper + Pydantic validation.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.learner_model import KnowledgeComponent, LanguageGeneratedQuestion
from app.services.ai_service import generate_llm_json
from app.services.language_conversation_prompts import level_guidance

logger = logging.getLogger(__name__)
settings = get_settings()


def _level_line(cefr_level: str) -> str:
    """Concrete CEFR difficulty criteria so the item genuinely matches the level (not just labelled)."""
    return (
        f" Calibrate the difficulty precisely to CEFR {cefr_level} — apply the vocabulary range, grammar "
        f"complexity and topic difficulty here (ignore any 'reply shape' note): {level_guidance(cefr_level)}"
    )

_GEN_SYSTEM = (
    "You are an expert English assessment item writer. Write clear, unambiguous multiple-choice "
    "questions with exactly four options and exactly one correct answer, targeted precisely at the "
    "given CEFR level and knowledge component. English only. Return ONLY valid JSON."
)
_VERIFY_SYSTEM = (
    "You are a strict reviewer of English test items. Reject any item that is ambiguous, has more "
    "than one defensible answer, has no correct answer, or does not match the stated CEFR level / "
    "component. Be conservative. Return ONLY valid JSON."
)


class GeneratedMCQ(BaseModel):
    stem: str
    choices: list[str]
    correct_index: int = Field(ge=0, le=3)

    def is_well_formed(self) -> bool:
        return bool(self.stem.strip()) and len(self.choices) == 4 and 0 <= self.correct_index < 4


class GeneratedBatch(BaseModel):
    items: list[GeneratedMCQ] = Field(default_factory=list)


class VerificationResult(BaseModel):
    is_valid: bool
    reason: str = ""


def _parse(raw: str) -> dict | None:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        data = json.loads(text[s : e + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


async def _generate_mcqs(*, component_code: str, cefr_level: str, count: int) -> list[GeneratedMCQ]:
    prompt = (
        f"Knowledge component: {component_code}. Target CEFR level: {cefr_level}. "
        f"Write {count} distinct multiple-choice questions that specifically test this component at "
        "this level." + _level_line(cefr_level) + "\n"
        'Return ONLY JSON: {"items":[{"stem": str, "choices":[4 strings], "correct_index": 0-3}]}'
    )
    raw = await generate_llm_json(prompt, system=_GEN_SYSTEM, temperature=0.8, max_output_tokens=1500)
    data = _parse(raw)
    if not data:
        return []
    try:
        batch = GeneratedBatch.model_validate(data)
    except ValidationError:
        return []
    return [q for q in batch.items if q.is_well_formed()]


async def verify_question(*, mcq: GeneratedMCQ, component_code: str, cefr_level: str) -> VerificationResult:
    """Second-LLM gate: clear, single correct answer, matches level/component."""
    prompt = (
        f"Component: {component_code}. CEFR level: {cefr_level}.\n"
        f"Question: {mcq.stem}\nChoices: {mcq.choices}\nClaimed correct index: {mcq.correct_index}.\n"
        f"Difficulty criteria for CEFR {cefr_level}: {level_guidance(cefr_level)}\n"
        "Is this item valid (unambiguous, exactly one correct answer = the claimed one, AND its "
        "vocabulary/grammar difficulty genuinely matches the level and component above — reject it if it "
        'is clearly too easy or too hard for the level)? Return ONLY JSON: {"is_valid": bool, "reason": short str}.'
    )
    try:
        raw = await generate_llm_json(prompt, system=_VERIFY_SYSTEM, temperature=0.0, max_output_tokens=200)
        data = _parse(raw)
        if data is not None:
            return VerificationResult.model_validate(data)
    except (ValidationError, Exception) as exc:  # pragma: no cover - LLM variance
        logger.warning("verify_question failed for %s: %s", component_code, exc)
    return VerificationResult(is_valid=False, reason="verification unavailable")


async def generate_placement_questions(
    db: AsyncSession, *, language_id: int, component_code: str, count: int = 3
) -> int:
    """Generate -> verify -> store placement questions for a component. Returns #stored (verified)."""
    component = (
        await db.execute(select(KnowledgeComponent).where(KnowledgeComponent.code == component_code))
    ).scalar_one_or_none()
    if component is None:
        logger.warning("generate_placement_questions: unknown component %r", component_code)
        return 0

    level = component.cefr_level.value
    mcqs = await _generate_mcqs(component_code=component_code, cefr_level=level, count=count)
    stored = 0
    for mcq in mcqs:
        result = await verify_question(mcq=mcq, component_code=component_code, cefr_level=level)
        if not result.is_valid:
            continue
        db.add(LanguageGeneratedQuestion(
            language_id=language_id,
            component_code=component_code,
            display_skill=component.display_skill,
            cefr_level=component.cefr_level,
            question_type="mcq",
            prompt_json=mcq.model_dump(),
            source="placement",
            verified=True,
            verification_note=result.reason[:400],
        ))
        stored += 1
    if stored:
        await db.commit()
    return stored


async def generate_daily_question(*, component_code: str, cefr_level: str, weak_point: str = "") -> GeneratedMCQ | None:
    """Lightweight on-the-fly question for daily practice (not persisted, light verification)."""
    hint = f" Focus on this weak point: {weak_point}." if weak_point else ""
    prompt = (
        f"Knowledge component: {component_code}. CEFR level: {cefr_level}.{hint} "
        "Write ONE multiple-choice question testing this component." + _level_line(cefr_level) + "\n"
        'Return ONLY JSON: {"items":[{"stem": str, "choices":[4 strings], "correct_index": 0-3}]}'
    )
    raw = await generate_llm_json(prompt, system=_GEN_SYSTEM, temperature=0.9, max_output_tokens=500)
    data = _parse(raw)
    if not data:
        return None
    try:
        batch = GeneratedBatch.model_validate(data)
    except ValidationError:
        return None
    return next((q for q in batch.items if q.is_well_formed()), None)


async def next_placement_question(
    db: AsyncSession, *, language_id: int, cefr_level: str, component_code: str | None = None
) -> LanguageGeneratedQuestion | None:
    """Draw a verified placement question from the bank at a level (optionally a specific component)."""
    q = select(LanguageGeneratedQuestion).where(
        LanguageGeneratedQuestion.language_id == language_id,
        LanguageGeneratedQuestion.cefr_level == LanguageLevel(cefr_level),
        LanguageGeneratedQuestion.verified.is_(True),
        LanguageGeneratedQuestion.source == "placement",
    )
    if component_code:
        q = q.where(LanguageGeneratedQuestion.component_code == component_code)
    return (await db.execute(q.order_by(func.random()).limit(1))).scalar_one_or_none()
