"""Deterministic template author — fallback when Claude unavailable; also used in verifiers."""

from __future__ import annotations

import hashlib
import json

from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.evidence_policy import (
    DEFAULT_EVIDENCE_ROLE_BY_BAND,
    CorrectionMode,
)
from app.services.language_educational_package.question_ladder import QuestionBand
from app.services.language_speaking_curriculum_engine.story_complexity import (
    StoryComplexityPolicy,
    story_complexity_policy_for_cefr,
)


AUTHOR_PROVIDER_TEMPLATE = "template_fallback"

_DAILY_CASE_DETAILS = (
    "near the classroom door before the lesson starts",
    "beside a notice board after a short announcement",
    "in a quiet hallway while another student is waiting",
    "at a study table with a small misunderstanding",
    "outside a classroom after a rushed message",
)


def _seed_index(seed: str, modulo: int, *, salt: str = "") -> int:
    if modulo <= 0:
        return 0
    digest = hashlib.sha256(f"{seed}|{salt}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulo


def author_package_json_template(constraints: PackageConstraints) -> str:
    """Produce schema-shaped author JSON from constraints only (no LLM)."""
    surfaces = list(constraints.vocabulary_surface_forms) or list(constraints.vocabulary_ids)
    meanings = {
        str(v.get("vocabulary_id")): str(v.get("meaning") or v.get("surface") or "")
        for v in (constraints.vocabulary_targets or ())
        if isinstance(v, dict)
    }
    examples = {
        str(v.get("vocabulary_id")): str(v.get("example_usage") or "")
        for v in (constraints.vocabulary_targets or ())
        if isinstance(v, dict)
    }
    policy = constraints.lesson_authoring_policy or {}
    complexity = StoryComplexityPolicy.from_dict(constraints.story_complexity_policy) or (
        story_complexity_policy_for_cefr(constraints.official_cefr)
    )
    recycle_min = int(
        (constraints.lexical_recycling_policy or {}).get("min_appearances_per_item")
        or complexity.required_vocabulary_reuse
        or 2
    )

    perso = constraints.personalization or {}
    characters = list(constraints.character_hints) or ["Sam", "Lee"]
    while len(characters) < complexity.characters_min:
        characters.append(f"Speaker{len(characters)+1}")
    characters = characters[: complexity.characters_max]
    world = constraints.story_world or f"a {constraints.scenario_type} situation"
    title = constraints.story_title_hint or f"A {constraints.scenario_type} moment"
    if constraints.daily_story_seed:
        detail = _DAILY_CASE_DETAILS[
            _seed_index(constraints.daily_story_seed, len(_DAILY_CASE_DETAILS), salt="case_detail")
        ]
        world = f"{world} Today's variation starts {detail}."
        if constraints.story_title_hint:
            title = f"{constraints.story_title_hint}: {detail.split(' before ')[0].title()}"
    emotional = str(perso.get("emotional_framing") or "").strip()
    if emotional:
        world = f"{world} Emotional framing: {emotional}."
    grammar = [dict(g) for g in (constraints.grammar_targets or ())]

    dialogue_kinds = {"dialogue", "whatsapp", "conversation_transcript"}
    if constraints.input_material_kind.value in dialogue_kinds:
        body_blocks = _dialogue_body_blocks(
            surfaces, characters, world, complexity.paragraph_count_min, recycle_min
        )
    else:
        body_blocks = _story_body_blocks(
            constraints,
            surfaces=surfaces,
            characters=characters,
            world=world,
            title=title,
            complexity=complexity,
            grammar=grammar,
            recycle_min=recycle_min,
        )

    vocab_entries = []
    highlights = []
    for i, vid in enumerate(constraints.vocabulary_ids):
        surface = surfaces[i] if i < len(surfaces) else vid
        ref = body_blocks[min(i, len(body_blocks) - 1)]["block_ref"]
        vocab_entries.append(
            {
                "vocabulary_id": vid,
                "surface": surface,
                "context_span_ref": ref,
                "brief_gloss": meanings.get(vid) or surface,
                "example_reuse": examples.get(vid)
                or f"Try using '{surface}' when you speak.",
            }
        )
        highlights.append({"vocabulary_id": vid, "block_ref": ref})
        if len(body_blocks) > 1:
            highlights.append(
                {
                    "vocabulary_id": vid,
                    "block_ref": body_blocks[(i + 1) % len(body_blocks)]["block_ref"],
                }
            )

    min_chars = int(policy.get("teaching_block_min_chars") or 120)
    teaching = []
    for spec in constraints.teaching_block_specs:
        recycle_text = " ".join(
            f"You heard '{s}' inside the situation." for s in surfaces[:4]
        )
        grammar_text = ""
        if grammar and (
            "grammar" in spec.kind.lower() or spec.block_id.endswith("grammar_notice")
        ):
            g0 = grammar[0]
            forms = ", ".join(g0.get("demonstration_forms") or [])
            grammar_text = (
                f" Notice the language of {g0.get('label')}: forms like {forms} "
                f"already appeared in the case. {g0.get('focus_note') or ''}"
            )
        elif grammar:
            grammar_text = (
                f" The case also used {grammar[0].get('label')} without naming it."
            )
        body = (
            f"You already experienced this language in the case. {recycle_text}"
            f"{grammar_text} Now say it aloud in your own words."
        )
        if len(body) < min_chars:
            body = (body + " " + recycle_text)[: spec.max_len]
        teaching.append(
            {
                "block_id": spec.block_id,
                "kind": spec.kind,
                "title": spec.kind.replace("_", " ").title(),
                "body": body[: spec.max_len],
            }
        )

    steps = []
    for i, band in enumerate(constraints.question_ladder_policy.required_bands):
        planned = next(
            (s for s in constraints.evidence_slot_plan if s.ladder_band == band.value),
            None,
        )
        role = (
            planned.evidence_role
            if planned
            else DEFAULT_EVIDENCE_ROLE_BY_BAND.get(band.value, "none").value
        )
        step_id = planned.step_id if planned and planned.step_id else f"step_{i+1}_{band.value}"
        prompt = _prompt_for_band(band, constraints, surfaces, complexity)
        g_ids: list[str] = []
        if band == QuestionBand.grammar_in_context and constraints.grammar_topic_ids:
            g_ids = list(constraints.grammar_topic_ids[:1])
        elif band == QuestionBand.reasoning and constraints.grammar_topic_ids:
            # Keep grammar present across discussion for coverage
            g_ids = list(constraints.grammar_topic_ids[:1])
        steps.append(
            {
                "step_id": step_id,
                "ladder_band": band.value,
                "prompt": prompt,
                "success_cues": ["answer in full sentences"],
                "evidence_role": role,
                "allowed_correction_mode": CorrectionMode.micro.value,
                "max_assistant_turns": 3,
                "vocabulary_ids": list(constraints.vocabulary_ids[:2])
                if band in {QuestionBand.vocabulary, QuestionBand.literal}
                else list(constraints.vocabulary_ids[:1]),
                "grammar_topic_ids": g_ids,
            }
        )
    while len(steps) < constraints.question_ladder_policy.min_steps:
        band = constraints.question_ladder_policy.required_bands[-1]
        steps.append(
            {
                "step_id": f"step_extra_{len(steps)+1}",
                "ladder_band": band.value,
                "prompt": _prompt_for_band(band, constraints, surfaces, complexity),
                "success_cues": ["add one detail"],
                "evidence_role": "none",
                "allowed_correction_mode": "micro",
                "max_assistant_turns": 2,
                "vocabulary_ids": list(constraints.vocabulary_ids[:1]),
                "grammar_topic_ids": list(constraints.grammar_topic_ids[:1]),
            }
        )

    # Ensure at least one step references each grammar topic
    if constraints.grammar_topic_ids:
        covered = {gid for s in steps for gid in s.get("grammar_topic_ids") or []}
        for gid in constraints.grammar_topic_ids:
            if gid in covered:
                continue
            steps[min(1, len(steps) - 1)]["grammar_topic_ids"] = [gid]
            label = next(
                (str(g.get("label")) for g in grammar if g.get("grammar_topic_id") == gid),
                gid,
            )
            steps[min(1, len(steps) - 1)]["prompt"] = (
                f"{steps[min(1, len(steps) - 1)]['prompt']} "
                f"How did {label} shape the meaning in this case?"
            )

    surf0 = surfaces[0] if surfaces else "the target phrases"
    c0, c1 = characters[0], characters[1] if len(characters) > 1 else "Lee"
    continuation = (
        f"Continue in the same place with {', '.join(characters[:3])}: the conflict is not "
        f"fully resolved, and they must face the next decision together."
    )
    g_form = ""
    if grammar and grammar[0].get("demonstration_forms"):
        g_form = f" Try to reuse forms like {grammar[0]['demonstration_forms'][0]}."
    mini_prompt = (
        f"{continuation} Use {', '.join(surfaces[:3])} naturally.{g_form}"
        if surfaces
        else f"{continuation}{g_form}"
    )

    events = _events_for_complexity(characters, constraints, complexity)
    story_spine = {
        "title": title,
        "context": world,
        "setting": constraints.scenario_type or "everyday place",
        "characters": [
            {
                "name": name,
                "background": _character_background(name, i, constraints, perso),
            }
            for i, name in enumerate(characters)
        ],
        "stakeholders": list(constraints.stakeholder_hints)
        or list(characters)
        or [c0, c1],
        "problem": (
            f"{c0} must handle {constraints.learning_focus or 'a spoken situation'} "
            f"under real pressure in a {complexity.case_category.replace('_', ' ')} case."
        ),
        "conflict": (
            f"{complexity.conflict_depth.replace('_', ' ')}; "
            f"decision={complexity.decision_complexity.replace('_', ' ')}; "
            f"ethics={complexity.ethical_complexity.replace('_', ' ')}"
        ),
        "timeline": complexity.timeline_complexity.replace("_", " "),
        "events": events,
        "decision_point": (
            f"{c0} faces a {complexity.decision_complexity.replace('_', ' ')}: "
            f"choose the next spoken move with {complexity.possible_solution_count} "
            f"possible paths and {complexity.viewpoint_count} viewpoints in play."
        ),
        "consequences": (
            "Short-term clarity may still leave longer-term cost for other stakeholders."
            if complexity.ambiguity_level in {"high", "very_high", "moderate"}
            else "Clarity keeps trust; confusion creates delay and sharper conflict."
        ),
        "ending": (
            "The ending stays open and ambiguous — several choices remain possible."
            if complexity.ambiguous_ending or "ambiguous" in complexity.ending_type
            else f"The situation pauses unresolved so {c0} still has something to say."
        ),
        "ending_type": complexity.ending_type,
        "hidden_emotions": complexity.emotional_complexity.replace("_", " "),
        "moral": "Clear spoken choices change real situations.",
        "discussion_hooks": [
            f"What should {c0} do at the decision point?",
            f"Which stakeholder is most affected, and why?",
            *list(perso.get("discussion_interest_hooks") or [])[:2],
        ],
        "continuation_hook": continuation,
        "case_category": constraints.case_category or complexity.case_category,
        "case_archetype": constraints.case_archetype or complexity.case_archetype,
    }

    reflection_n = max(
        constraints.reflection_requirements.prompt_count,
        complexity.reflection_depth,
    )
    reflection_prompts = [
        f"What language helped most in this situation about {constraints.learning_focus}?",
        f"What decision would you make, and which phrase — maybe {surf0} — would you use?",
        "How could you use this communication in real life this week?",
        "Which viewpoint was hardest to accept, and why?",
    ]
    if perso.get("interest_labels"):
        reflection_prompts.append(
            f"How would this decision look in a {perso['interest_labels'][0]} context you care about?"
        )
    reflection_prompts = reflection_prompts[:reflection_n]

    interest_open = ""
    hooks = list(perso.get("discussion_interest_hooks") or [])
    if hooks:
        interest_open = f" {hooks[0]}"

    payload = {
        "input_material": {
            "kind": constraints.input_material_kind.value,
            "title": title,
            "body_blocks": body_blocks,
            "media_refs": [],
            "cefr_check_echo": constraints.official_cefr.upper(),
        },
        "story_spine": story_spine,
        "vocabulary_in_context": {"entries": vocab_entries, "highlight_map": highlights},
        "teaching_blocks_authored": teaching,
        "discussion": {
            "flow_id": f"flow_{constraints.mission_id or 'mission'}",
            "opening_move": (
                f"Let's discuss this situation with {', '.join(characters[:3])}."
                f"{interest_open}"
            ).strip(),
            "steps": steps[: constraints.question_ladder_policy.max_steps],
            "closing_move": (
                f"Stay in this same situation and reuse {surf0} when you speak next."
            ),
        },
        "mini_practice": {
            "task_id": constraints.mini_practice_task_id or "",
            "prompt": mini_prompt,
            "scaffold": f"Stay with {c0}. Start clearly, then justify your next step.",
            "evidence_intent_echo": constraints.evidence_intent,
        },
        "reflection": {
            "prompts": reflection_prompts,
            "self_check_cues": [
                "I discussed the real situation",
                "I used target words naturally",
                "I thought about decisions and feelings",
            ],
        },
        "teacher_notes": {"author": AUTHOR_PROVIDER_TEMPLATE},
        "metadata": {
            "locale": constraints.locale,
            "scenario_type": constraints.scenario_type,
            "story_world": constraints.story_world,
            "character_hints": list(characters),
            "story_complexity_cefr": complexity.cefr,
            "personalization": dict(perso) if perso else {},
            "personalization_engine_version": constraints.personalization_engine_version
            or str(perso.get("engine_version") or ""),
        },
    }
    while len(payload["reflection"]["prompts"]) < reflection_n:
        payload["reflection"]["prompts"].append(
            "What alternative would change the outcome of this case?"
        )
    return json.dumps(payload, ensure_ascii=False)


def _events_for_complexity(
    characters: list[str],
    constraints: PackageConstraints,
    complexity: StoryComplexityPolicy,
) -> list[str]:
    c0 = characters[0]
    others = characters[1:] or ["Lee"]
    events = [
        f"{c0} enters the {constraints.scenario_type} setting and faces pressure.",
        f"{others[0]} complicates the situation with new information.",
        f"A decision becomes unavoidable for {c0}.",
    ]
    templates = [
        f"{characters[min(i, len(characters)-1)]} reveals a conflicting need."
        for i in range(len(characters))
    ] + [
        "A small delay raises the stakes.",
        "Someone misreads a polite message.",
        "An outside rule blocks the easy option.",
        "A private feeling leaks into the conversation.",
        "A second viewpoint challenges the first plan.",
        "A nearly-made decision is paused.",
        "Trust is tested by an unclear reply.",
        "The group faces two options with unfinished consequences.",
        "An unexpected comment forces everyone to rethink.",
        "The ending remains open for the next spoken move.",
    ]
    i = 0
    while len(events) < complexity.story_events_min:
        events.append(templates[i % len(templates)])
        i += 1
    return events[: complexity.story_events_max]


def _story_body_blocks(
    constraints: PackageConstraints,
    *,
    surfaces: list[str],
    characters: list[str],
    world: str,
    title: str,
    complexity: StoryComplexityPolicy,
    grammar: list[dict],
    recycle_min: int,
) -> list[dict]:
    """Narrative-first beats; weave vocab/grammar into full sentences (no dump lists)."""
    pool = surfaces or ["hello"]
    c0 = characters[0]
    c1 = characters[1] if len(characters) > 1 else "Lee"
    c2 = characters[2] if len(characters) > 2 else c1
    para_n = max(complexity.paragraph_count_min, complexity.story_events_min)
    para_n = min(max(para_n, len(pool) + 1), complexity.paragraph_count_max + 2)

    # Pre-assign surfaces so each appears enough times across paragraphs.
    surface_plan: list[str] = []
    for s in pool:
        surface_plan.extend([s] * max(1, recycle_min))
    while len(surface_plan) < para_n:
        surface_plan.append(pool[len(surface_plan) % len(pool)])

    g_forms: list[str] = []
    for g in grammar:
        for form in g.get("demonstration_forms") or []:
            if form and form not in g_forms:
                g_forms.append(str(form))

    blocks: list[dict] = []
    for i in range(para_n):
        s = surface_plan[i]
        s2 = pool[(i + 1) % len(pool)]
        gbit = g_forms[i % len(g_forms)] if g_forms else ""
        if i == 0:
            text = (
                f"{title}. {c0} arrives in {world.split('.')[0].strip()} and feels the pressure "
                f"immediately. When {c1} appears, {c0} almost says '{s}', then waits. "
                f"The first problem is already visible."
            )
        elif i == 1:
            text = (
                f"{c1} shares a complication {c0} did not expect. '{s}', {c1} says carefully, "
                f"and {c0} answers with '{s2}'. The talk stays human, but the choice gets sharper."
            )
        elif i == para_n - 1:
            text = (
                f"The situation is not finished. {c0} looks at {c1}"
                + (f" and {c2}" if c2 != c1 else "")
                + f" and knows the next line matters. Maybe '{s}' is enough to reopen trust. "
                f"What happens next depends on clarity"
                + (f" — and whether they can still use {gbit}." if gbit else ".")
            )
        else:
            who = characters[i % len(characters)]
            text = (
                f"{who} pushes the case forward. {c0} notices that '{s}' fits this moment better "
                f"than silence, while '{s2}' keeps the exchange grounded. "
            )
            if gbit:
                text += f"The wording slides toward {gbit}, showing the tension without naming a rule. "
            if complexity.conflict_depth and i == 2:
                text += f"The conflict feels like {complexity.conflict_depth.replace('_', ' ')}. "
            if complexity.twists and i == min(3, para_n - 2):
                text += "Then a small twist appears: the easy option would hurt someone else, "
                text += "so the group hesitates. "

        blocks.append({"kind": "paragraph", "block_ref": f"b{i}", "text": text.strip()})

    # Pad to min_words with narrative sentences that reuse surfaces naturally
    word_count = sum(len(b["text"].split()) for b in blocks)
    pad_i = 0
    while word_count < complexity.min_words:
        s = pool[pad_i % len(pool)]
        who = characters[pad_i % len(characters)]
        extra = (
            f" Later, {who} returns to the same point and tries '{s}' again, this time with more "
            f"care, because the people in the room still need a workable next step."
        )
        target = blocks[pad_i % len(blocks)]
        target["text"] = f"{target['text']}{extra}"
        word_count = sum(len(b["text"].split()) for b in blocks)
        pad_i += 1
        if pad_i > 40:
            break

    # Soft trim if far over max BEFORE forced reuse (reuse may add a little back)
    word_count = sum(len(b["text"].split()) for b in blocks)
    while word_count > complexity.max_words * 1.15 and len(blocks) > complexity.paragraph_count_min:
        last = blocks[-1]["text"]
        if len(last.split()) < 20:
            blocks.pop()
        else:
            words = last.split()
            blocks[-1]["text"] = " ".join(words[: max(12, len(words) - 18)])
        word_count = sum(len(b["text"].split()) for b in blocks)

    # Guarantee required vocabulary reuse with natural sentences (never dump lists)
    # Must run after trim so counts survive.
    for s in pool:
        story = " ".join(b["text"] for b in blocks).lower()
        need = max(1, recycle_min)
        have = story.count(s.lower())
        add_i = 0
        while have < need and blocks:
            who = characters[add_i % len(characters)]
            blocks[-1]["text"] += (
                f" {who} comes back to the same idea and uses '{s}' once more, "
                f"so the meaning stays clear for everyone listening."
            )
            story = " ".join(b["text"] for b in blocks).lower()
            have = story.count(s.lower())
            add_i += 1
            if add_i > 8:
                break

    return blocks


def _dialogue_body_blocks(
    surfaces: list[str],
    characters: list[str],
    world: str,
    min_turns: int,
    recycle_min: int,
) -> list[dict]:
    pool = surfaces or ["hello"]
    turn_n = max(min_turns, len(pool) + 2)
    body_blocks: list[dict] = []
    for i in range(turn_n):
        s = pool[i % len(pool)]
        speaker = characters[i % len(characters)]
        if i == 0:
            text = f"{s} We're in {world.split('.')[0].strip()}. Let's keep this clear."
        else:
            text = f"I hear you. Using {s} here keeps the exchange natural."
        # Light recycle without list dump
        if i % 2 == 0 and recycle_min > 1:
            text = f"{text} {s}."
        body_blocks.append(
            {"kind": "turn", "block_ref": f"b{i}", "speaker": speaker, "text": text}
        )
    return body_blocks


def _character_background(
    name: str,
    index: int,
    constraints: PackageConstraints,
    perso: dict,
) -> str:
    roles = list(perso.get("character_roles") or [])
    if roles:
        role = roles[min(index, len(roles) - 1)]
        return f"{role} in a {constraints.scenario_type} case."
    return f"Involved in a {constraints.scenario_type} case."


def _prompt_for_band(
    band: QuestionBand,
    constraints: PackageConstraints,
    surfaces: list[str],
    complexity: StoryComplexityPolicy,
) -> str:
    focus = constraints.learning_focus or "this situation"
    words = ", ".join(surfaces[:3]) or "the key words"
    people = ", ".join(constraints.character_hints[:3]) or "the people"
    depth = complexity.discussion_depth
    category = (constraints.case_category or complexity.case_category).replace("_", " ")
    perso = constraints.personalization or {}
    interest_hooks = list(perso.get("discussion_interest_hooks") or [])
    base = {
        QuestionBand.literal: (
            f"In this {category} case, what is happening to {people} about {focus}?"
        ),
        QuestionBand.vocabulary: f"In this case, how are these words used: {words}?",
        QuestionBand.grammar_in_context: (
            f"How did the wording in this case show meaning around {focus}?"
        ),
        QuestionBand.reasoning: (
            f"Why is the decision about {focus} difficult, given "
            f"{complexity.decision_complexity.replace('_', ' ')}?"
        ),
        QuestionBand.personal_opinion: (
            f"Which option would you choose for {people}, and why?"
        ),
        QuestionBand.personal_experience: (
            f"Have you faced something like this {category} case about {focus}?"
        ),
        QuestionBand.real_world_transfer: (
            f"How would this case change if another stakeholder applied pressure?"
        ),
    }[band]
    if band in {
        QuestionBand.personal_opinion,
        QuestionBand.personal_experience,
        QuestionBand.real_world_transfer,
    } and interest_hooks:
        return f"{base} {interest_hooks[0]}"
    if "critical" in depth or "counterargument" in depth or "policy" in depth:
        return (
            f"{base} Defend your view, mention one counterargument, and note a societal "
            f"or long-term consequence."
        )
    if "ethical" in depth or "tradeoff" in depth or "evidence" in depth:
        return (
            f"{base} Compare at least two perspectives and explain the ethical trade-off "
            f"with evidence from the case."
        )
    if "comparison" in depth or "alternative" in depth or "reasoning_comparison" in depth:
        return f"{base} Compare alternatives and explain your reasoning."
    if "literal_understanding" in depth or "simple_opinion" in depth:
        return f"{base} Keep the answer short and clear."
    return base
