"""Curriculum Engine V2 — enrich speaking PackageConstraints before Claude authors."""

from __future__ import annotations

from typing import Any

from app.services.language_educational_package.constraints import ELP_CONSTRAINTS_SCHEMA_VERSION
from app.services.language_speaking_curriculum_engine.cefr_policy import (
    lesson_authoring_policy_for_cefr,
    lexical_recycling_policy_for_cefr,
    question_ladder_for_cefr_v2,
)
from app.services.language_speaking_curriculum_engine.objectives import (
    build_educational_objectives,
    flatten_objective_texts,
)
from app.services.language_speaking_curriculum_engine.educational_world import (
    sanitize_educational_text,
    sanitize_objective_list,
)
from app.services.language_speaking_curriculum_engine.progression_selector import (
    resolve_progression_from_payload,
)
from app.services.language_speaking_curriculum_engine.story_complexity import (
    build_stakeholder_hints,
    expand_character_hints,
    story_complexity_policy_for_cefr,
)
from app.services.language_speaking_curriculum_engine.types import (
    CURRICULUM_ENGINE_VERSION,
    VocabularyTarget,
)
from app.services.language_speaking_curriculum_engine.vocabulary_catalog import (
    select_vocabulary_targets,
)


def enrich_speaking_constraints_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a journey/base constraints dict with Curriculum Engine V2 intelligence.

    Does not invent CEFR/mission/blueprint identity. Selects progression graph node,
    vocabulary + grammar, CEFR story complexity, density, recycling, and ladder policy.
    """
    out = dict(payload)
    cefr = str(out.get("official_cefr") or "A2").upper()
    out["official_cefr"] = cefr

    learning_focus = sanitize_educational_text(
        str(out.get("learning_focus") or ""),
        fallback="Today's speaking lesson",
    )
    out["learning_focus"] = learning_focus
    if out.get("objectives"):
        out["objectives"] = sanitize_objective_list(
            [str(o) for o in out.get("objectives") or []],
            focus=learning_focus,
        )

    skill_ids: list[str] = []
    for block in out.get("teaching_block_specs") or []:
        if isinstance(block, dict):
            skill_ids.extend(str(s) for s in (block.get("target_skill_ids") or []) if s)
    if out.get("target_skill_ids"):
        skill_ids = [str(s) for s in out["target_skill_ids"] if s] + skill_ids
    out["target_skill_ids"] = list(dict.fromkeys(skill_ids))

    # M9 — Curriculum Progression Graph selects Educational Case seed (before complexity)
    progression = resolve_progression_from_payload(out)
    variant = progression.case_variant
    node = progression.node
    out["scenario_type"] = variant.scenario_type
    out["story_world"] = variant.story_world
    out["story_title_hint"] = variant.title_hint
    out["character_hints"] = list(variant.character_hints)
    goal = sanitize_educational_text(
        str(out.get("communicative_goal") or ""),
        fallback=f"Use {learning_focus} clearly in a real spoken situation.",
    )
    out["communicative_goal"] = (
        f"{goal} Micro-skill focus: {node.label}."
        if node.label.lower() not in goal.lower()
        else goal
    )
    out["curriculum_progression"] = progression.to_constraints_dict()
    out["progression_node_id"] = node.node_id
    out["progression_case_id"] = variant.case_id
    out["progression_action"] = progression.action

    complexity = story_complexity_policy_for_cefr(
        cefr,
        skill_ids=skill_ids,
        learning_focus=learning_focus,
        scenario_type=str(out.get("scenario_type") or ""),
    )
    authoring = lesson_authoring_policy_for_cefr(cefr)
    recycling = lexical_recycling_policy_for_cefr(cefr)
    ladder = question_ladder_for_cefr_v2(cefr)

    vocab = select_vocabulary_targets(
        cefr=cefr,
        skill_ids=skill_ids,
        learning_focus=learning_focus,
        count=authoring.target_vocabulary_count,
    )
    vocab = [
        VocabularyTarget(
            vocabulary_id=v.vocabulary_id,
            lemma=v.lemma,
            surface=v.surface,
            meaning=v.meaning,
            communicative_purpose=v.communicative_purpose,
            cefr_suitability=v.cefr_suitability,
            expected_reuse=v.expected_reuse,
            example_usage=v.example_usage,
            required_lesson_frequency=max(
                v.required_lesson_frequency,
                recycling.min_appearances_per_item,
                complexity.required_vocabulary_reuse,
            ),
        )
        for v in vocab
    ]

    # Wave D P0-3: Speaking must NEVER choose grammar. Resolver is sole authority.
    # Leave grammar empty here; author_pipeline stamps from SkillGrammarContext or fail-closed.
    grammar_targets: list = []
    existing_ids = [
        str(x) for x in (out.get("grammar_topic_ids") or []) if str(x).strip()
    ]
    # Strip any pre-seeded pack grammar so dual authority cannot survive.
    if existing_ids:
        out.pop("grammar_topic_ids", None)
        out.pop("grammar_targets", None)

    mission_objectives = [str(o) for o in (out.get("objectives") or []) if o]
    edu_objectives = build_educational_objectives(
        cefr=cefr,
        learning_focus=learning_focus,
        mission_title=learning_focus,
        mission_objectives=mission_objectives,
        vocabulary=vocab,
        transfer_expectation=authoring.transfer_expectation,
    )

    # Align legacy authoring density with StoryComplexityPolicy (single source of truth)
    authoring_dict = authoring.to_dict()
    authoring_dict.update(
        {
            "min_story_beats": complexity.paragraph_count_min,
            "min_dialogue_turns": complexity.paragraph_count_min,
            "min_input_word_count": complexity.min_words,
            "max_input_word_count": complexity.max_words,
            "sentence_complexity": complexity.sentence_complexity,
            "reasoning_level": complexity.reasoning_level,
            "question_depth": complexity.discussion_depth,
            "lesson_length_band": (
                "extended"
                if complexity.min_words >= 220
                else authoring.lesson_length_band
            ),
        }
    )

    # Expand character cast + stakeholders; prefer progression case cast as seed
    hints = expand_character_hints(
        list(out.get("character_hints") or variant.character_hints),
        complexity,
    )
    stakeholders = build_stakeholder_hints(hints, complexity)
    complexity_dict = complexity.to_dict()
    # Progression case category is Curriculum-owned seed for this graph node
    if variant.case_category:
        complexity_dict["case_category"] = variant.case_category

    dense_specs: list[dict[str, Any]] = []
    for block in out.get("teaching_block_specs") or []:
        if not isinstance(block, dict):
            continue
        b = dict(block)
        b["max_len"] = max(int(b.get("max_len") or 0), authoring.teaching_block_min_chars + 40)
        dense_specs.append(b)
    if not dense_specs:
        dense_specs = [
            {
                "block_id": "tb_focus",
                "kind": "explanation",
                "target_skill_ids": skill_ids[:3],
                "max_len": authoring.teaching_block_min_chars + 40,
            },
            {
                "block_id": "tb_example",
                "kind": "example",
                "target_skill_ids": skill_ids[:3],
                "max_len": authoring.teaching_block_min_chars + 40,
            },
            {
                "block_id": "tb_guided",
                "kind": "guided_practice",
                "target_skill_ids": skill_ids[:3],
                "max_len": authoring.teaching_block_min_chars + 20,
            },
        ]
    elif len(dense_specs) < 2:
        dense_specs.append(
            {
                "block_id": "tb_guided_understanding",
                "kind": "guided_practice",
                "target_skill_ids": skill_ids[:3]
                or list(dense_specs[0].get("target_skill_ids") or []),
                "max_len": authoring.teaching_block_min_chars + 20,
            }
        )

    # Ensure a teaching slot can name grammar after experience
    if grammar_targets and not any(
        "grammar" in str(b.get("kind") or "").lower() for b in dense_specs
    ):
        dense_specs.append(
            {
                "block_id": "tb_grammar_notice",
                "kind": "grammar_in_context",
                "target_skill_ids": skill_ids[:2],
                "max_len": authoring.teaching_block_min_chars + 60,
            }
        )

    case_category = str(
        complexity_dict.get("case_category") or complexity.case_category or ""
    )
    out.update(
        {
            "schema_version": ELP_CONSTRAINTS_SCHEMA_VERSION,
            "vocabulary_ids": [v.vocabulary_id for v in vocab],
            "vocabulary_surface_forms": [v.surface for v in vocab],
            "vocabulary_targets": [v.to_dict() for v in vocab],
            "educational_objectives": [o.to_dict() for o in edu_objectives],
            "objectives": flatten_objective_texts(edu_objectives),
            "grammar_topic_ids": [g.grammar_topic_id for g in grammar_targets],
            "grammar_targets": [g.to_dict() for g in grammar_targets],
            "story_complexity_policy": complexity_dict,
            "lesson_authoring_policy": authoring_dict,
            "lexical_recycling_policy": {
                **recycling.to_dict(),
                "min_appearances_per_item": max(
                    recycling.min_appearances_per_item,
                    complexity.required_vocabulary_reuse,
                ),
            },
            "question_ladder_policy": ladder.to_dict(),
            "lesson_length_band": authoring_dict["lesson_length_band"],
            "difficulty": authoring.difficulty,
            "reflection_requirements": {
                "prompt_count": max(
                    authoring.reflection_prompt_count,
                    complexity.reflection_depth,
                ),
            },
            "teaching_block_specs": dense_specs,
            "character_hints": hints,
            "stakeholder_hints": stakeholders,
            "case_category": case_category,
            "case_archetype": complexity.case_archetype,
            "scenario_type": variant.scenario_type,
            "story_world": variant.story_world,
            "story_title_hint": variant.title_hint,
            "curriculum_engine_version": CURRICULUM_ENGINE_VERSION,
            "curriculum_progression": progression.to_constraints_dict(),
            "progression_node_id": node.node_id,
            "progression_case_id": variant.case_id,
            "progression_action": progression.action,
            "forbidden_behaviors": list(
                out.get("forbidden_behaviors")
                or [
                    "no_grammar_lecture",
                    "no_promotion_talk",
                    "no_cefr_claims",
                    "no_invented_vocabulary_surfaces",
                    "no_alex_mentions",
                    "no_product_tutor_names",
                    "no_mechanical_vocabulary_dump",
                ]
            ),
        }
    )
    fb = list(out["forbidden_behaviors"])
    for flag in (
        "no_invented_vocabulary_surfaces",
        "no_alex_mentions",
        "no_product_tutor_names",
        "no_mechanical_vocabulary_dump",
    ):
        if flag not in fb:
            fb.append(flag)
    if "no_random_unrelated_cases" not in fb:
        fb.append("no_random_unrelated_cases")
    out["forbidden_behaviors"] = fb
    return out
