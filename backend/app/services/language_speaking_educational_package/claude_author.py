"""Claude Sonnet Learning Package author — transforms constraints only."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.services.claude_service import claude_model_name, generate_claude_json_result
from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.ownership_guard import AUTHOR_FORBIDDEN_DECISIONS

logger = logging.getLogger(__name__)
settings = get_settings()

AUTHOR_PROVIDER_CLAUDE = "claude_sonnet"

ELP_CLAUDE_SYSTEM = """You are the EduSpark Learning Package Author.
You receive ONLY PackageConstraints JSON from the backend.
You must transform those constraints into a natural educational Learning Package JSON.

EDUCATIONAL CASE + CEFR COMPLEXITY:
- Generate ONE realistic Educational Case at the required CEFR complexity.
- Follow story_complexity_policy exactly (word count, paragraphs, characters, events,
  conflict_depth, decision_points, twists, emotional_depth, reasoning_level,
  reflection_depth, discussion_depth, sentence_complexity, reading_complexity,
  case_category, case_archetype, decision_complexity, ethical_complexity,
  social_complexity, ambiguity_level, viewpoint_count, stakeholder_count,
  possible_solution_count, ending_type).
- Claude NEVER invents a category outside story_complexity_policy.case_category.
- Higher CEFR must feel like harder real-life situations (trade-offs, conflicting
  interests, hidden motivations, long-term consequences) — not only more words.
- Write the Educational Case narrative FIRST as a coherent situation.
- Use daily_story_key / daily_story_seed only as a backend variation seed: make today's
  story fresh for this student while preserving CEFR, vocabulary, grammar, and progression.
- Then satisfy vocabulary constraints by weaving EXACT surfaces into that narrative
  naturally — NEVER dump vocabulary lists or paste tokens awkwardly.
- Demonstrate every grammar_targets topic inside the story body using
  demonstration_forms (show, do not lecture). Teaching later names what students
  already experienced.
- Grammar must also reappear lightly in teaching, discussion (grammar_in_context
  when required), and mini practice — still no grammar lecture tone.
- input_material.body_blocks are narrative paragraphs (kind=paragraph / heading).
- Include complete story_spine matching character/event/decision policy.
- Discussion and reflection depth must match story_complexity_policy.

PERSONALIZATION (experience only — when constraints.personalization.applied):
- Adapt setting, characters, names, examples, culture, and small details from
  constraints.personalization and the personalized story_world / character_hints.
- Discussion may gently reference discussion_interest_hooks when natural.
- NEVER change CEFR, vocabulary, grammar, objectives, difficulty, case_category,
  case_archetype, assessment, or promotion because of personalization.
- Educational quality remains first — never force hobbies awkwardly.

You must NEVER decide or change: CEFR, learning stage, mission, objectives, vocabulary IDs,
vocabulary surfaces, grammar topic IDs, progression, readiness, or promotion.
You must NEVER invent vocabulary_ids or grammar_topic_ids not listed in constraints.
Never mention Alex or product tutor branding.
Output JSON only.
"""


@dataclass(slots=True)
class ClaudeAuthorResult:
    """Author text plus preserved Anthropic response metadata."""

    text: str
    model: str | None
    stop_reason: str | None
    input_tokens: int | None
    output_tokens: int | None
    provider: str = AUTHOR_PROVIDER_CLAUDE

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "stop_reason": self.stop_reason,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "provider": self.provider,
        }


def build_author_user_prompt(constraints: PackageConstraints) -> str:
    surfaces = list(constraints.vocabulary_surface_forms)
    authoring = constraints.lesson_authoring_policy or {}
    recycling = constraints.lexical_recycling_policy or {}
    complexity = constraints.story_complexity_policy or {}
    min_beats = (
        complexity.get("paragraph_count_min")
        or authoring.get("min_story_beats")
        or authoring.get("min_dialogue_turns")
    )
    schema_hint = {
        "input_material": {
            "kind": constraints.input_material_kind.value,
            "title": "natural educational case title",
            "body_blocks": [
                {"kind": "paragraph|heading", "text": "narrative beat...", "block_ref": "b0"}
            ],
            "media_refs": [],
            "cefr_check_echo": constraints.official_cefr,
        },
        "story_spine": {
            "title": "same as case title",
            "context": "brief situation frame",
            "setting": "place",
            "characters": [{"name": "from character_hints", "background": "short"}],
            "stakeholders": ["people + institutions from stakeholder_hints"],
            "problem": "what goes wrong / needs solving",
            "conflict": "match conflict_depth + ethical/social complexity",
            "timeline": "match timeline_complexity",
            "events": ["ordered beats — count in story_events_min..max"],
            "decision_point": "primary decision matching decision_complexity",
            "consequences": "include trade-offs / long-term effects when CEFR requires",
            "ending": "match ending_type",
            "ending_type": "echo policy ending_type",
            "hidden_emotions": "match emotional_complexity",
            "moral": "soft takeaway",
            "discussion_hooks": ["depth matches discussion_depth"],
            "continuation_hook": "same-world next chapter",
            "case_category": "from constraints.case_category",
            "case_archetype": "from constraints.case_archetype",
        },
        "vocabulary_in_context": {
            "entries": [
                {
                    "vocabulary_id": "from constraints",
                    "surface": "EXACT surface",
                    "context_span_ref": "b0",
                    "brief_gloss": "from vocabulary_targets",
                    "example_reuse": "from vocabulary_targets",
                }
            ],
            "highlight_map": [{"vocabulary_id": "...", "block_ref": "b0"}],
        },
        "teaching_blocks_authored": [
            {"block_id": "from constraints", "kind": "...", "title": "...", "body": "..."}
        ],
        "discussion": {
            "flow_id": "string",
            "opening_move": "discuss this case",
            "steps": [
                {
                    "step_id": "string",
                    "ladder_band": "literal|vocabulary|grammar_in_context|...",
                    "prompt": "depth matches discussion_depth",
                    "success_cues": ["..."],
                    "evidence_role": "none|formative_light|formative|transfer",
                    "allowed_correction_mode": "none|micro|brief",
                    "max_assistant_turns": 3,
                    "vocabulary_ids": [],
                    "grammar_topic_ids": [],
                }
            ],
            "closing_move": "same case world",
        },
        "mini_practice": {
            "task_id": constraints.mini_practice_task_id,
            "prompt": "continuation_hook + target language/grammar",
            "scaffold": "string",
            "evidence_intent_echo": constraints.evidence_intent,
        },
        "reflection": {
            "prompts": ["count/depth from reflection_depth"],
            "self_check_cues": ["..."],
        },
        "teacher_notes": {},
        "metadata": {"locale": constraints.locale},
    }
    density_rules = {
        "story_complexity_policy": complexity,
        "min_story_beats": min_beats,
        "min_input_word_count": complexity.get("min_words") or authoring.get("min_input_word_count"),
        "max_input_word_count": complexity.get("max_words") or authoring.get("max_input_word_count"),
        "sentence_complexity": complexity.get("sentence_complexity")
        or authoring.get("sentence_complexity"),
        "max_sentence_length": complexity.get("max_sentence_length"),
        "question_depth": complexity.get("discussion_depth") or authoring.get("question_depth"),
        "reasoning_level": complexity.get("reasoning_level") or authoring.get("reasoning_level"),
        "transfer_expectation": authoring.get("transfer_expectation"),
        "required_sections": authoring.get("required_sections"),
        "teaching_block_min_chars": authoring.get("teaching_block_min_chars"),
        "min_recycle_per_item": recycling.get("min_appearances_per_item"),
        "recycle_across": recycling.get("required_sections"),
        "exact_surfaces": surfaces,
        "grammar_targets": [dict(g) for g in constraints.grammar_targets],
        "daily_story_key": constraints.daily_story_key,
        "daily_story_seed": constraints.daily_story_seed,
    }
    return (
        "PackageConstraints (backend-owned; do not alter educational decisions):\n"
        f"{json.dumps(constraints.to_dict(), ensure_ascii=False)}\n\n"
        f"Forbidden educational decisions: {sorted(AUTHOR_FORBIDDEN_DECISIONS)}\n\n"
        "Story complexity + density / recycling / grammar rules (MUST satisfy):\n"
        f"{json.dumps(density_rules, ensure_ascii=False)}\n\n"
        "Produce ONE Learning Package JSON matching this shape:\n"
        f"{json.dumps(schema_hint, ensure_ascii=False)}\n"
        "Authoring order: (1) Educational Case narrative that matches complexity, "
        "(2) weave exact vocabulary surfaces naturally into that narrative, "
        "(3) demonstrate grammar forms in the narrative, "
        "(4) teaching names patterns students already saw, "
        "(5) discussion/reflection at required depth, "
        "(6) mini practice continues the same case. "
        "Use daily_story_seed to vary names, setting details, conflict details, and events "
        "without changing any backend-owned targets. "
        "Never mechanically dump vocabulary. Never invent IDs. Never mention Alex."
    )


async def author_package_json_claude(constraints: PackageConstraints) -> ClaudeAuthorResult:
    model = claude_model_name(settings.CLAUDE_MODEL)
    call = await generate_claude_json_result(
        build_author_user_prompt(constraints),
        system=ELP_CLAUDE_SYSTEM,
        temperature=0.35,
        max_output_tokens=16000,
        model_name=model,
        timeout=float(getattr(settings, "SPEAKING_PROSODY_TIMEOUT_SECONDS", None) or 120),
    )
    logger.info(
        "ELP Claude author completed model=%s mission=%s stop_reason=%s output_tokens=%s",
        call.model or model,
        constraints.mission_id,
        call.stop_reason,
        call.output_tokens,
    )
    return ClaudeAuthorResult(
        text=call.text,
        model=call.model or model,
        stop_reason=call.stop_reason,
        input_tokens=call.input_tokens,
        output_tokens=call.output_tokens,
        provider=AUTHOR_PROVIDER_CLAUDE,
    )
