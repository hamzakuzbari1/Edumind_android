"""Compact prompt contracts for sectioned canonical grammar lesson authoring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.services.language_grammar_canonical_authoring.types import CanonicalAuthoringAdapterRequest
from app.services.language_grammar_practice_contract import (
    RICH_PRACTICE_REQUIRED_COUNTS,
    rich_practice_items_for_grammar,
)


@dataclass(frozen=True, slots=True)
class SectionPromptContract:
    unit_key: str
    target_tokens: tuple[int, int]
    max_tokens: int
    contract: str


@dataclass(frozen=True, slots=True)
class SectionPromptBundle:
    system_prompt: str
    user_prompt: str
    prompt_version: str
    max_tokens: int


SECTIONED_PROMPT_VERSION = "sectioned_canonical_authoring_v1.0"
SECTION_TOKEN_BUDGETS: dict[str, dict[str, int | tuple[int, int]]] = {
    "blueprint": {"target": (700, 1100), "max": 1500},
    "concept": {"target": (900, 1500), "max": 3000},
    "examples": {"target": (900, 1500), "max": 2000},
    "rules": {"target": (1200, 1900), "max": 3400},
    "practice": {"target": (2500, 5000), "max": 8000},
    "production": {"target": (600, 1000), "max": 3000},
}

_COMMON = (
    "Return compact valid JSON only. No markdown fences. No prose outside JSON. "
    "Do not use generic filler. Do not use the grammar display name as a fake example sentence. "
    "Preserve CEFR behavior and, when provided, blueprint stable IDs. Student-facing payload must not include "
    "expected answers, sample answers, hints, feedback reasoning, success criteria, misconceptions, "
    "or private metadata."
)

SECTION_PROMPT_CONTRACTS: dict[str, SectionPromptContract] = {
    "blueprint": SectionPromptContract(
        unit_key="blueprint",
        target_tokens=(500, 900),
        max_tokens=1500,
        contract=(
            f"{_COMMON} Produce only a compact private pedagogical plan. Do not echo identity, forms, "
            "support targets, stable IDs, versions, unit keys, or linking metadata; the server owns those. "
            "Add one compact teaching note for every server-required form key. No learner-facing lesson prose, "
            "no full examples, no task payloads, no essays."
        ),
    ),
    "concept": SectionPromptContract(
        unit_key="concept",
        target_tokens=(900, 1500),
        max_tokens=3000,
        contract=(
            f"{_COMMON} Produce public_payload with orientation, meaning_hook, concept_explanation, "
            "and arabic_clarification. A1-A2 must begin with detailed natural Arabic."
        ),
    ),
    "examples": SectionPromptContract(
        unit_key="examples",
        target_tokens=(900, 1500),
        max_tokens=2000,
        contract=(
            f"{_COMMON} Produce public_payload with real model_examples, noticing, and genuine use_cases. "
            "Also return private_metadata for noticing."
        ),
    ),
    "rules": SectionPromptContract(
        unit_key="rules",
        target_tokens=(1200, 1900),
        max_tokens=3400,
        contract=(
            f"{_COMMON} Produce public_payload with patterns, rule_notes, arabic_english_contrast, "
            "contrasts_and_mistakes, and visual_summary. Mistakes need Arabic reasons for A1-B1."
        ),
    ),
    "practice": SectionPromptContract(
        unit_key="practice",
        target_tokens=(2500, 5000),
        max_tokens=8000,
        contract=(
            f"{_COMMON} Produce a rich mini practice bank with exactly 14 tasks when server_practice_items "
            "is provided. Use exactly the server-provided public IDs and task types. Public task types: "
            "multiple_choice, fill_blank, sentence_builder, transformation, correction, short_answer, open_response. "
            "Keep learner text compact. Options and word chips must be separate arrays, never concatenated strings. "
            "Put 3 multiple_choice tasks in understanding_checks; put the remaining 11 tasks in guided_practice. "
            "Answers, acceptable-answer rules, hints, rubrics, and model answers live only in private_metadata. "
            "Keep every prompt, hint, and feedback_reasoning to one short sentence; keep open_response success_criteria to 3 short items."
        ),
    ),
    "production": SectionPromptContract(
        unit_key="production",
        target_tokens=(600, 1000),
        max_tokens=3000,
        contract=(
            f"{_COMMON} Produce supported_production, transfer, exit_check, and reflection. Prompts must "
            "ask the learner to communicate real meaning and must not claim mastery."
        ),
    ),
}


def get_section_prompt_contract(unit_key: str) -> SectionPromptContract:
    return SECTION_PROMPT_CONTRACTS[unit_key]


def build_sectioned_prompt_bundle(
    *,
    unit_key: str,
    request: CanonicalAuthoringAdapterRequest,
    blueprint: dict[str, Any] | None = None,
    accepted_prior_units: dict[str, dict[str, Any]] | None = None,
) -> SectionPromptBundle:
    contract = get_section_prompt_contract(unit_key)
    system = (
        "You are Claude, the offline canonical grammar lesson author for EduSpark. "
        "You author one sectioned unit only. The Grammar Engine owns topic selection, CEFR, "
        "progression, mastery, unlocking, completion, publication, and the declared grammar scope. "
        "You must not change, invent, remove, or narrow server-owned identity, required forms, functions, "
        "mistake categories, or forbidden extensions. Follow the fixed method: meaning before rules, examples before explanation, "
        "Arabic-first for A1-A2, real English examples, progressive practice, private answers only in "
        "private_metadata. Never include secrets, file paths, raw IDs in learner text, provider commentary, "
        "or UI instructions."
    )
    payload = {
        "unit_key": unit_key,
        "contract": contract.contract,
        "lesson_identity": {
            "grammar_target": request.grammar_id,
            "display_name": request.display_name,
            "cefr_level": request.cefr_level,
            "locale": request.locale,
            "methodology_version": request.methodology_version,
        },
        "grammar_profile": _compact_profile(request),
        "server_required_form_keys": _server_required_form_keys(request),
        "server_practice_items": _server_practice_items(unit_key, request),
        "blueprint": _blueprint_for_unit(unit_key, blueprint or {}),
        "accepted_prior_unit_summaries": _prior_summaries(accepted_prior_units or {}),
        "output_schema": _schema_for_unit(unit_key, request),
        "hard_rules": [
            "JSON only, no markdown.",
            "Use all requested stable IDs exactly; do not invent replacement IDs.",
            "Do not expose expected_answer, sample_answer, hint, feedback_reasoning, success_criteria, or misconception in public_payload.",
            "Private metadata records must use item_id matching existing public item IDs.",
            "Do not write fake examples like 'I use Present of be'.",
            "Do not write generic openings like 'Welcome' or 'Today you will learn'.",
            "Cover declared required forms/functions across the whole lesson; this unit covers only its educational ownership.",
            "Do not teach forbidden_extensions.",
            "Avoid repeating the same explanation from prior units.",
            "Keep output compact and inside this unit only.",
            "For practice metadata, use short strings only; do not add explanations beyond evaluator needs.",
        ],
    }
    if unit_key == "blueprint":
        payload["hard_rules"] = [
            "JSON only, no markdown.",
            "Return only the compact plan fields in output_schema.",
            "Do not echo grammar_target, display_name, cefr_level, locale, versions, support targets, required forms, stable IDs, unit keys, or revision IDs.",
            "form_teaching_notes must be an object with exactly the server_required_form_keys and no extension keys.",
            "Each form_teaching_notes value is one short note about how to teach that server-owned form.",
            "No learner-facing lesson prose, no full examples, no full tasks, no expected answers.",
            "Maximum 3 entries in use_case_intents, example_intents, and single_appearance_topics.",
            "mistake_intents is optional; if present, entries must use known server mistake categories only.",
            "Maximum 20 words per English planning string.",
            "Maximum 30 Arabic words in arabic_contrast.",
            "Do not duplicate the same idea across fields.",
        ]
    return SectionPromptBundle(
        system_prompt=system,
        user_prompt=json.dumps(payload, ensure_ascii=False, sort_keys=True),
        prompt_version=f"{SECTIONED_PROMPT_VERSION}:{unit_key}",
        max_tokens=int(contract.max_tokens),
    )


def _compact_profile(request: CanonicalAuthoringAdapterRequest) -> dict[str, Any]:
    profile = dict(request.grammar_profile or {})
    return {
        "selected_grammar_target": request.grammar_id,
        "display_name": request.display_name,
        "cefr_level": request.cefr_level,
        "learning_objectives": _list(profile.get("learning_objectives")),
        "canonical_patterns": _list(profile.get("canonical_patterns")),
        "required_form_keys": _list(profile.get("required_form_keys")),
        "permitted_realizations": _list(profile.get("permitted_realizations")),
        "functions": _list(profile.get("functions")),
        "mistake_categories": _list(profile.get("mistake_categories")),
        "forbidden_extensions": _list(profile.get("forbidden_extensions")),
        "model_examples": _list(profile.get("model_examples")),
        "common_mistakes": _list(profile.get("common_mistakes")),
        "arabic_speaker_misconceptions": _list(profile.get("arabic_speaker_misconceptions")),
        "teaching_notes": str(profile.get("teaching_notes") or ""),
        "focus_note": str(profile.get("focus_note") or ""),
        "recommended_contexts": _list(profile.get("recommended_contexts")),
        "support_grammar_targets": _list(profile.get("support_grammar_targets")),
    }


def _server_required_form_keys(request: CanonicalAuthoringAdapterRequest) -> list[str]:
    explicit = _list((request.grammar_profile or {}).get("required_form_keys"))
    if explicit:
        return explicit
    patterns = _list((request.grammar_profile or {}).get("canonical_patterns"))
    blob = " ".join(patterns).lower()
    forms = [form for form in ("am", "is", "are") if form in blob.split() or f" {form} " in f" {blob} "]
    if forms:
        return forms
    return patterns[:4] or [request.display_name]


def _blueprint_for_unit(unit_key: str, blueprint: dict[str, Any]) -> dict[str, Any]:
    if unit_key == "blueprint":
        return {}
    stable_ids = blueprint.get("stable_ids") if isinstance(blueprint.get("stable_ids"), dict) else {}
    common = {
        "grammar_target": blueprint.get("grammar_target"),
        "display_name": blueprint.get("display_name"),
        "cefr_level": blueprint.get("cefr_level"),
        "locale": blueprint.get("locale"),
        "core_communicative_meaning": blueprint.get("core_communicative_meaning"),
        "why_english_uses_it": blueprint.get("why_english_uses_it"),
        "required_forms": blueprint.get("required_forms"),
        "mistake_intentions": blueprint.get("mistake_intentions"),
        "mistake_teaching_notes": blueprint.get("mistake_teaching_notes"),
        "support_grammar_targets": blueprint.get("support_grammar_targets"),
        "arabic_english_contrast": blueprint.get("arabic_english_contrast"),
        "arabic_speaker_misconceptions": blueprint.get("arabic_speaker_misconceptions"),
        "production_goal": blueprint.get("production_goal"),
    }
    if unit_key == "concept":
        keys = ("meaning_hook",)
    elif unit_key == "examples":
        keys = ("examples", "noticing", "use_cases")
    elif unit_key == "rules":
        keys = ("patterns", "mistakes")
    elif unit_key == "practice":
        keys = ("understanding_checks", "guided_practice")
        common["practice_progression_plan"] = blueprint.get("practice_progression_plan")
    elif unit_key == "production":
        keys = ("supported_production", "transfer", "exit_check")
    else:
        keys = ()
    common["stable_ids"] = {key: stable_ids.get(key) for key in keys if key in stable_ids}
    return common


def _prior_summaries(units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "concept" in units:
        concept = units["concept"]
        out["concept"] = {
            "meaning_hook": concept.get("meaning_hook"),
            "concept_summary": (concept.get("concept_explanation") or {}).get("summary"),
            "arabic_clarification": concept.get("arabic_clarification"),
        }
    if "examples" in units:
        examples = units["examples"]
        out["examples"] = {
            "model_examples": [
                {
                    "id": item.get("id"),
                    "sentence": item.get("sentence"),
                    "target_form": item.get("target_form"),
                }
                for item in _dict_list(examples.get("model_examples"))[:5]
            ],
            "use_cases": examples.get("use_cases"),
        }
    if "rules" in units:
        rules = units["rules"]
        out["rules"] = {
            "patterns": [
                {
                    "id": item.get("id"),
                    "pattern": item.get("pattern"),
                    "example": item.get("example"),
                }
                for item in _dict_list(rules.get("patterns"))[:4]
            ],
            "mistake_ids": [item.get("id") for item in _dict_list(rules.get("contrasts_and_mistakes"))],
        }
    if "practice" in units:
        practice = units["practice"]
        out["practice"] = {
            "task_ids": [
                item.get("id")
                for item in [
                    *_dict_list(practice.get("understanding_checks")),
                    *_dict_list(practice.get("guided_practice")),
                ]
            ],
        }
    return out


def _schema_for_unit(unit_key: str, request: CanonicalAuthoringAdapterRequest) -> dict[str, Any]:
    if unit_key == "blueprint":
        return {
            "core_meaning": "one short sentence",
            "english_need": "one short sentence",
            "arabic_contrast": "one or two short Arabic sentences, or null",
            "form_teaching_notes": {"server form key such as affirmative_am": "short teaching note, no examples"},
            "use_case_intents": [{"label": "short label", "meaning": "short meaning"}],
            "example_intents": [{"meaning": "meaning later example should communicate"}],
            "mistake_intents": [{"error_type": "optional server mistake category", "misunderstanding": "optional short note"}],
            "practice_plan": ["recognition", "choice", "fill_blank", "reorder", "correction"],
            "production_goal": "meaningful personal communication goal",
            "cefr_language_guidance": "one short instruction",
            "single_appearance_topics": ["concepts to explain once only"],
        }
    if unit_key == "concept":
        return {
            "public_payload": {
                "orientation": {"teacher_script": "max 2 short sentences; no generic welcome"},
                "meaning_hook": {"situation": "one real situation", "why_it_matters": "meaning first"},
                "concept_explanation": {
                    "arabic_concept_introduction": "natural Arabic first for A2",
                    "english_bridge": "short English bridge",
                    "summary": "short memory handle",
                },
                "arabic_clarification": {
                    "arabic": "Arabic explanation",
                    "arabic_speaker_warning": "Arabic warning",
                    "arabic_english_contrast": "Arabic-English contrast",
                },
            }
        }
    if unit_key == "examples":
        return {
            "public_payload": {
                "model_examples": [
                    {
                        "id": "blueprint example id",
                        "sentence": "real English sentence",
                        "teaching_purpose": "meaning|form|contrast",
                        "target_form": "actual form",
                        "arabic_meaning": "Arabic meaning",
                        "arabic_explanation": "why this form is used",
                    }
                ],
                "noticing": {
                    "id": "blueprint noticing id",
                    "prompt": "one noticing prompt",
                    "expected_observations": ["1-3 observations"],
                },
                "use_cases": [
                    {
                        "id": "blueprint use case id",
                        "label": "use case",
                        "explanation": "English explanation",
                        "example": "real example",
                        "arabic_explanation": "Arabic reason",
                    }
                ],
            },
            "private_metadata": {"noticing": [{"item_id": "noticing id", "success_criteria": ["server-only"]}]},
        }
    if unit_key == "rules":
        return {
            "public_payload": {
                "patterns": [
                    {
                        "id": "blueprint pattern id",
                        "pattern": "form pattern",
                        "meaning": "meaning",
                        "explanation": "Arabic-friendly learner explanation",
                        "example": "immediate real example",
                    }
                ],
                "rule_notes": ["max 5 compact notes"],
                "arabic_english_contrast": "Arabic contrast",
                "contrasts_and_mistakes": [
                    {
                        "id": "blueprint mistake id",
                        "incorrect": "wrong sentence",
                        "correct": "correct sentence",
                        "why": "natural Arabic reason",
                        "misunderstanding": "Arabic misconception cause",
                    }
                ],
                "visual_summary": [{"label": "string", "value": "string", "warning": None}],
            }
        }
    if unit_key == "practice":
        return {
            "public_payload": {
                "understanding_checks": [
                    {
                        "id": "server id",
                        "type": "multiple_choice",
                        "round_title": "اختر الصحيح",
                        "prompt": "short Arabic instruction",
                        "context": "optional English context",
                        "options": ["separate option", "separate option"],
                    },
                ],
                "guided_practice": [
                    {
                        "id": "server id",
                        "type": "fill_blank",
                        "round_title": "أكمل الفراغ",
                        "prompt": "short Arabic instruction",
                        "sentence_with_blank": "She _____ happy.",
                    },
                    {
                        "id": "server id",
                        "type": "sentence_builder",
                        "round_title": "ركّب الجملة",
                        "prompt": "short Arabic instruction",
                        "word_chips": ["He", "is", "ready"],
                    },
                    {
                        "id": "server id",
                        "type": "transformation",
                        "round_title": "حوّل الجملة",
                        "prompt": "short Arabic instruction",
                        "original_sentence": "She is tired.",
                        "transformation_goal": "Make it negative.",
                    },
                    {
                        "id": "server id",
                        "type": "correction",
                        "round_title": "صحّح الخطأ",
                        "prompt": "short Arabic instruction",
                        "incorrect_sentence": "She are tired.",
                    },
                    {
                        "id": "server id",
                        "type": "short_answer",
                        "round_title": "جاوب واكتب",
                        "prompt": "short Arabic instruction",
                        "context": "Are you tired today?",
                    },
                    {
                        "id": "server id",
                        "type": "open_response",
                        "round_title": "جاوب واكتب",
                        "prompt": "write 2-4 connected sentences about who you are, where you are, and how you feel",
                        "sentence_count_min": 2,
                        "sentence_count_max": 4,
                        "starters": ["I am ...", "I am at ...", "I am ... today."],
                    },
                ],
            },
            "private_metadata": {
                "understanding_checks": [
                    {
                        "item_id": "public id",
                        "expected_answer": "server-only for closed tasks",
                        "target_form": "server-only",
                        "mistake_category": "server-only",
                        "hint": "server-only",
                        "feedback_reasoning": "server-only",
                    }
                ],
                "guided_practice": [
                    {
                        "item_id": "public id",
                        "expected_answer": "server-only for closed tasks",
                        "sample_answer": "server-only only for open_response",
                        "success_criteria": ["server-only rubric for open_response"],
                        "normalization": "server-only",
                        "target_form": "server-only",
                        "mistake_category": "server-only",
                        "hint": "server-only",
                        "feedback_reasoning": "server-only",
                    }
                ],
            },
        }
    return {
        "public_payload": {
            "supported_production": [
                {
                    "id": "blueprint production id",
                    "type": "production",
                    "prompt": "ask for personal meaning, not grammar name",
                    "scaffold": "optional",
                }
            ],
            "transfer": {"id": "blueprint transfer id", "type": "transfer", "context": "real context", "prompt": "transfer prompt"},
            "exit_check": {
                "recognition": {"id": "blueprint id", "type": "choice", "prompt": "string", "options": ["A", "B"]},
                "correction": {"id": "blueprint id", "type": "correction", "prompt": "string", "incorrect_sentence": "wrong sentence"},
                "production": {"id": "blueprint id", "type": "production", "prompt": "personal meaning prompt", "scaffold": None},
            },
            "reflection": {"summary": "short", "encouragement": "short", "next_step": "short"},
        },
        "private_metadata": {
            "supported_production": [{"item_id": "public id", "sample_answer": "server-only", "success_criteria": ["server-only"]}],
            "transfer": [{"item_id": "public id", "sample_answer": "server-only", "success_criteria": ["server-only"]}],
            "exit_check": [{"item_id": "public id", "expected_answer": "server-only"}],
        },
    }


def _list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item).strip()]
    return []


def _server_practice_items(unit_key: str, request: CanonicalAuthoringAdapterRequest) -> list[dict[str, Any]]:
    if unit_key != "practice":
        return []
    items = [dict(item) for item in rich_practice_items_for_grammar(request.grammar_id)]
    if not items:
        return []
    return [
        {
            "required_count_by_type": RICH_PRACTICE_REQUIRED_COUNTS,
            "items_in_exact_order": items,
            "coverage": [
                "affirmative am/is/are",
                "negative not/isn't/aren't",
                "yes/no questions with inversion",
                "short answers",
                "identity",
                "location",
                "description/state",
                "Arabic-speaker be deletion and agreement mistakes",
            ],
        }
    ]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]
