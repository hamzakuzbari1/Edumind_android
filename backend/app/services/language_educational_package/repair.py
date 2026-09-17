"""Structural repair — copies missing educational slots from constraints; never invents curriculum."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.evidence_policy import (
    DEFAULT_EVIDENCE_ROLE_BY_BAND,
    CorrectionMode,
    DiscussionEvidenceRole,
)
from app.services.language_educational_package.material_kinds import BodyBlockKind
from app.services.language_educational_package.question_ladder import QuestionBand
from app.services.language_educational_package.types import (
    AuthoredTeachingBlock,
    BodyBlock,
    DiscussionStep,
    EducationalPackage,
    StoryCharacter,
    StorySpine,
    VocabularyEntry,
)
from app.services.language_educational_package.validation import ValidationIssueCode, ValidationResult


@dataclass(slots=True)
class RepairResult:
    repaired: bool
    actions: list[str] = field(default_factory=list)


def repair_package(
    package: EducationalPackage,
    constraints: PackageConstraints,
    validation: ValidationResult,
) -> tuple[EducationalPackage, RepairResult]:
    actions: list[str] = []
    codes = {i.code for i in validation.issues if i.severity == "error"}
    warn_codes = {i.code for i in validation.issues}

    if not package.input_material.cefr_check_echo:
        package.input_material.cefr_check_echo = constraints.official_cefr.upper()
        actions.append("fill_cefr_echo")

    if not package.mission_id:
        package.mission_id = constraints.mission_id
        actions.append("fill_mission_id")

    if not package.blueprint_hash:
        package.blueprint_hash = constraints.blueprint_hash
        actions.append("fill_blueprint_hash")

    # Vocabulary coverage — fill missing IDs with surface forms from constraints
    present = {e.vocabulary_id for e in package.vocabulary_in_context.entries}
    for idx, vid in enumerate(constraints.vocabulary_ids):
        if vid in present:
            continue
        surface = (
            constraints.vocabulary_surface_forms[idx]
            if idx < len(constraints.vocabulary_surface_forms)
            else vid
        )
        ref = package.input_material.body_blocks[0].block_ref if package.input_material.body_blocks else "b0"
        package.vocabulary_in_context.entries.append(
            VocabularyEntry(
                vocabulary_id=vid,
                surface=surface,
                context_span_ref=ref,
                brief_gloss=surface,
                example_reuse=surface,
            )
        )
        package.vocabulary_in_context.highlight_map.append(
            {"vocabulary_id": vid, "block_ref": ref}
        )
        actions.append(f"fill_vocab:{vid}")

    # Teaching blocks
    authored = {b.block_id: b for b in package.teaching_blocks_authored}
    for spec in constraints.teaching_block_specs:
        if spec.block_id in authored:
            continue
        package.teaching_blocks_authored.append(
            AuthoredTeachingBlock(
                block_id=spec.block_id,
                kind=spec.kind,
                title=spec.kind.replace("_", " ").title(),
                body=f"Focus on {constraints.learning_focus}."[: spec.max_len],
            )
        )
        actions.append(f"fill_block:{spec.block_id}")

    # Discussion structure — rebuild minimal ladder if empty / too short
    policy = constraints.question_ladder_policy
    if (
        ValidationIssueCode.discussion_structure in codes
        or ValidationIssueCode.ladder_order in codes
        or len(package.discussion.steps) < policy.min_steps
    ):
        steps: list[DiscussionStep] = []
        for i, band in enumerate(policy.required_bands):
            role_default = DEFAULT_EVIDENCE_ROLE_BY_BAND.get(
                band.value, DiscussionEvidenceRole.none
            )
            planned = next(
                (s for s in constraints.evidence_slot_plan if s.ladder_band == band.value),
                None,
            )
            role = DiscussionEvidenceRole(planned.evidence_role) if planned else role_default
            try:
                role = DiscussionEvidenceRole(role.value)
            except Exception:
                role = role_default
            step_id = planned.step_id if planned and planned.step_id else f"step_{i+1}_{band.value}"
            vocab_ids = list(constraints.vocabulary_ids[:1]) if band == QuestionBand.vocabulary else []
            grammar_ids = (
                list(constraints.grammar_topic_ids[:1])
                if band == QuestionBand.grammar_in_context
                else []
            )
            steps.append(
                DiscussionStep(
                    step_id=step_id,
                    ladder_band=band,
                    prompt=_default_prompt(band, constraints),
                    success_cues=["answer in complete sentences"],
                    evidence_role=role,
                    allowed_correction_mode=CorrectionMode.micro,
                    max_assistant_turns=3,
                    vocabulary_ids=vocab_ids,
                    grammar_topic_ids=grammar_ids,
                )
            )
        while len(steps) < policy.min_steps:
            band = policy.required_bands[-1]
            steps.append(
                DiscussionStep(
                    step_id=f"step_extra_{len(steps)+1}",
                    ladder_band=band,
                    prompt=_default_prompt(band, constraints),
                    success_cues=["share one more detail"],
                    evidence_role=DiscussionEvidenceRole.none,
                    allowed_correction_mode=CorrectionMode.micro,
                    vocabulary_ids=[],
                    grammar_topic_ids=[],
                )
            )
        package.discussion.steps = steps[: policy.max_steps]
        if not package.discussion.flow_id:
            package.discussion.flow_id = f"flow_{constraints.mission_id or 'mission'}"
        if not package.discussion.opening_move:
            package.discussion.opening_move = "Let's discuss this Educational Case."
        if not package.discussion.closing_move:
            package.discussion.closing_move = (
                "Great work — stay in this same situation when you speak next."
            )
        actions.append("rebuild_discussion_steps")

    # Reflection
    need = constraints.reflection_requirements.prompt_count
    while len(package.reflection.prompts) < need:
        package.reflection.prompts.append(
            f"What is one thing you can say next time about {constraints.learning_focus or 'this topic'}?"
        )
        actions.append("fill_reflection_prompt")
    if not package.reflection.self_check_cues:
        package.reflection.self_check_cues = ["I used target words", "I spoke in full sentences"]
        actions.append("fill_reflection_cues")

    # Mini practice
    if constraints.mini_practice_task_id:
        if package.mini_practice.task_id != constraints.mini_practice_task_id:
            package.mini_practice.task_id = constraints.mini_practice_task_id
            actions.append("align_mini_task_id")
        if not package.mini_practice.prompt:
            package.mini_practice.prompt = (
                f"Speak for about 30 seconds about: {constraints.learning_focus}"
            )
            actions.append("fill_mini_prompt")
        if not package.mini_practice.evidence_intent_echo:
            package.mini_practice.evidence_intent_echo = constraints.evidence_intent
            actions.append("fill_mini_evidence_echo")

    # Ensure at least one body block
    if not package.input_material.body_blocks:
        package.input_material.body_blocks = [
            BodyBlock(
                kind=BodyBlockKind.paragraph,
                text=f"Scenario: {constraints.scenario_type}. Focus: {constraints.learning_focus}.",
                block_ref="b0",
            )
        ]
        actions.append("fill_body_block")
    if not package.input_material.title:
        package.input_material.title = (
            constraints.story_title_hint or constraints.learning_focus or "Speaking case"
        )
        actions.append("fill_title")

    package.input_material.kind = constraints.input_material_kind

    # Educational Case spine stub when missing (Speaking story packages)
    if (
        constraints.skill == "speaking"
        and constraints.input_material_kind.value == "story"
        and not package.story_spine.is_substantive()
    ):
        chars = list(constraints.character_hints) or ["Sam", "Lee"]
        c0, c1 = chars[0], chars[1] if len(chars) > 1 else "Lee"
        title = package.input_material.title or constraints.story_title_hint or "Today's case"
        complexity = constraints.story_complexity_policy or {}
        stakes = list(getattr(constraints, "stakeholder_hints", ()) or []) or list(chars)
        package.story_spine = StorySpine(
            title=title,
            context=constraints.story_world or f"a {constraints.scenario_type} situation",
            setting=constraints.scenario_type or "everyday",
            characters=[
                StoryCharacter(name=n, background=f"Involved in {constraints.scenario_type}.")
                for n in chars
            ],
            stakeholders=stakes,
            problem=f"{c0} must handle {constraints.learning_focus or 'the situation'}.",
            conflict=f"Pressure rises between {c0} and {c1} around a clear spoken decision.",
            timeline="One continuous episode",
            events=[
                f"{c0} faces the situation.",
                f"{c1} complicates the moment.",
                "A decision becomes unavoidable.",
            ],
            decision_point=f"{c0} must choose how to speak next.",
            consequences="Clarity keeps trust; confusion creates delay.",
            ending="The situation pauses unresolved.",
            ending_type=str(complexity.get("ending_type") or "open_obvious_next_step"),
            hidden_emotions="Worry and the wish to be understood.",
            moral="Clear spoken choices change real situations.",
            discussion_hooks=[
                f"What should {c0} do next?",
                f"How does {c1} feel?",
            ],
            continuation_hook=(
                f"Continue with {c0} and {c1} in the same {constraints.scenario_type} "
                f"situation until the next decision is clear."
            ),
            case_category=str(
                getattr(constraints, "case_category", "")
                or complexity.get("case_category")
                or ""
            ),
            case_archetype=str(
                getattr(constraints, "case_archetype", "")
                or complexity.get("case_archetype")
                or ""
            ),
        )
        actions.append("fill_story_spine")

    # Prefer continuation hook for mini practice (same Educational Case)
    if package.story_spine.continuation_hook and (
        not package.mini_practice.prompt
        or package.mini_practice.prompt.startswith("Speak for about 30 seconds")
    ):
        package.mini_practice.prompt = package.story_spine.continuation_hook
        actions.append("fill_mini_from_continuation")

    # Story complexity repairs (CEFR adaptive)
    if ValidationIssueCode.story_complexity in warn_codes or constraints.story_complexity_policy:
        complexity = constraints.story_complexity_policy or {}
        min_words = int(complexity.get("min_words") or 0)
        emin = int(complexity.get("story_events_min") or complexity.get("story_events") or 0)
        cmin = int(complexity.get("characters_min") or 0)
        pmin = int(complexity.get("paragraph_count_min") or complexity.get("paragraph_count") or 0)
        reflection_need = int(complexity.get("reflection_depth") or 0)

        # Characters
        if cmin and len(package.story_spine.characters) < cmin:
            hints = list(constraints.character_hints) or ["Sam", "Lee", "Maya", "Jordan", "Noor"]
            existing = {c.name for c in package.story_spine.characters}
            for name in hints:
                if len(package.story_spine.characters) >= cmin:
                    break
                if name not in existing:
                    package.story_spine.characters.append(
                        StoryCharacter(name=name, background=f"Involved in {constraints.scenario_type}.")
                    )
                    existing.add(name)
            actions.append("expand_characters")

        # Events
        if emin and len(package.story_spine.events) < emin:
            n = 0
            while len(package.story_spine.events) < emin:
                n += 1
                package.story_spine.events.append(
                    f"Another beat raises the stakes around {constraints.learning_focus} ({n})."
                )
            actions.append("expand_events")

        # Paragraphs / words
        story_words = sum(len((b.text or "").split()) for b in package.input_material.body_blocks)
        while pmin and len(package.input_material.body_blocks) < pmin:
            idx = len(package.input_material.body_blocks)
            package.input_material.body_blocks.append(
                BodyBlock(
                    kind=BodyBlockKind.paragraph,
                    text=(
                        f"The case continues. Someone must speak clearly about "
                        f"{constraints.learning_focus or 'the problem'} before trust is lost."
                    ),
                    block_ref=f"b{idx}",
                )
            )
            actions.append("add_paragraph")
        pad_i = 0
        surfaces = list(constraints.vocabulary_surface_forms) or ["clearly"]
        while min_words and story_words < min_words and package.input_material.body_blocks:
            s = surfaces[pad_i % len(surfaces)]
            target = package.input_material.body_blocks[pad_i % len(package.input_material.body_blocks)]
            target.text = (
                f"{target.text} Later the same people return to the point and try '{s}' "
                f"with more care."
            )
            story_words = sum(len((b.text or "").split()) for b in package.input_material.body_blocks)
            pad_i += 1
            actions.append("pad_story_words")
            if pad_i > 30:
                break

        while reflection_need and len(package.reflection.prompts) < reflection_need:
            package.reflection.prompts.append(
                f"What alternative decision would change this case about {constraints.learning_focus}?"
            )
            actions.append("fill_reflection_depth")

        # M7 — Educational Case sophistication fills
        if not package.story_spine.case_category:
            package.story_spine.case_category = str(
                getattr(constraints, "case_category", "")
                or complexity.get("case_category")
                or ""
            )
            if package.story_spine.case_category:
                actions.append("fill_case_category")
        if not package.story_spine.case_archetype:
            package.story_spine.case_archetype = str(
                getattr(constraints, "case_archetype", "")
                or complexity.get("case_archetype")
                or ""
            )
            if package.story_spine.case_archetype:
                actions.append("fill_case_archetype")
        if not package.story_spine.ending_type and complexity.get("ending_type"):
            package.story_spine.ending_type = str(complexity.get("ending_type"))
            actions.append("fill_ending_type")
        if not package.story_spine.decision_point.strip():
            c0 = (
                package.story_spine.characters[0].name
                if package.story_spine.characters
                else "Someone"
            )
            package.story_spine.decision_point = (
                f"{c0} must choose the next spoken move under "
                f"{str(complexity.get('decision_complexity') or 'pressure').replace('_', ' ')}."
            )
            actions.append("fill_decision_point")
        stake_need = int(complexity.get("stakeholder_count") or 0)
        if stake_need and len(package.story_spine.stakeholders) < stake_need:
            hints = list(getattr(constraints, "stakeholder_hints", ()) or ())
            existing = list(package.story_spine.stakeholders)
            for h in hints:
                if h not in existing:
                    existing.append(h)
                if len(existing) >= stake_need:
                    break
            institutional = [
                "family member",
                "coworker",
                "manager",
                "client",
                "institution",
                "community",
                "regulator",
            ]
            for role in institutional:
                if len(existing) >= stake_need:
                    break
                if role not in existing:
                    existing.append(role)
            package.story_spine.stakeholders = existing[: max(stake_need, len(existing))]
            actions.append("expand_stakeholders")

        # Discussion depth language for higher CEFR
        depth = str(complexity.get("discussion_depth") or "")
        if package.discussion.steps and (
            "ethical" in depth or "critical" in depth or "tradeoff" in depth or "counter" in depth
        ):
            last = package.discussion.steps[-1]
            blob = last.prompt.lower()
            if "ethical" in depth and "ethic" not in blob and "trade" not in blob:
                last.prompt = (
                    f"{last.prompt} Compare perspectives and name the ethical trade-off."
                )
                actions.append("deepen_discussion_ethical")
            if ("critical" in depth or "counter" in depth or "policy" in depth) and not any(
                k in blob for k in ("counter", "societ", "policy", "defend")
            ):
                last.prompt = (
                    f"{last.prompt} Defend your view, answer one counterargument, "
                    f"and note a long-term or societal consequence."
                )
                actions.append("deepen_discussion_critical")

    # Grammar coverage repairs
    if ValidationIssueCode.grammar_coverage in warn_codes or constraints.grammar_targets:
        story_l = " ".join(b.text for b in package.input_material.body_blocks).lower()
        for raw in constraints.grammar_targets or ():
            if not isinstance(raw, dict):
                continue
            gid = str(raw.get("grammar_topic_id") or "")
            label = str(raw.get("label") or gid)
            forms = [str(f) for f in (raw.get("demonstration_forms") or []) if f]
            form0 = forms[0] if forms else label
            if form0.lower() not in story_l and package.input_material.body_blocks:
                package.input_material.body_blocks[-1].text += (
                    f" In that moment someone used language like '{form0}'."
                )
                story_l = " ".join(b.text for b in package.input_material.body_blocks).lower()
                actions.append(f"inject_grammar_story:{gid}")
            # Teaching
            if package.teaching_blocks_authored:
                tb = package.teaching_blocks_authored[-1]
                if label.lower() not in tb.body.lower():
                    tb.body = (
                        f"{tb.body} You also experienced {label} in the case "
                        f"(forms such as {', '.join(forms[:3]) or form0})."
                    )[: max(len(tb.body), 400)]
                    actions.append(f"inject_grammar_teaching:{gid}")
            # Discussion step tags
            if package.discussion.steps and gid not in {
                x for s in package.discussion.steps for x in s.grammar_topic_ids
            }:
                step = package.discussion.steps[min(1, len(package.discussion.steps) - 1)]
                step.grammar_topic_ids = list(dict.fromkeys([*step.grammar_topic_ids, gid]))
                if label.lower() not in step.prompt.lower():
                    step.prompt = f"{step.prompt} How did {label} shape meaning here?"
                actions.append(f"inject_grammar_discussion:{gid}")
            # Mini practice
            if form0.lower() not in (package.mini_practice.prompt or "").lower():
                package.mini_practice.prompt = (
                    f"{package.mini_practice.prompt} Try reusing wording like '{form0}'."
                ).strip()
                actions.append(f"inject_grammar_mini:{gid}")

    package.metadata.setdefault("locale", constraints.locale)
    package.metadata.setdefault("length_band", constraints.lesson_length_band)
    package.metadata.setdefault("scenario_type", constraints.scenario_type)
    if package.story_spine.continuation_hook:
        package.metadata["continuation_hook"] = package.story_spine.continuation_hook
    if constraints.story_complexity_policy:
        package.metadata["story_complexity_cefr"] = constraints.story_complexity_policy.get(
            "cefr"
        )

    return package, RepairResult(repaired=bool(actions), actions=actions)


def _default_prompt(band: QuestionBand, constraints: PackageConstraints) -> str:
    focus = constraints.learning_focus or "the situation"
    surfaces = ", ".join(constraints.vocabulary_surface_forms[:3]) or "the key words"
    people = ", ".join(constraints.character_hints[:2]) or "the people"
    mapping = {
        QuestionBand.literal: f"What is happening to {people} in this case about {focus}?",
        QuestionBand.vocabulary: f"In this case, what do these words mean: {surfaces}?",
        QuestionBand.grammar_in_context: f"How is language used to communicate {focus} in this case?",
        QuestionBand.reasoning: f"Why is the decision about {focus} difficult here?",
        QuestionBand.personal_opinion: f"What would you advise {people} to do about {focus}?",
        QuestionBand.personal_experience: f"Have you experienced something like this case about {focus}?",
        QuestionBand.real_world_transfer: f"How would you handle a similar real-life case about {focus}?",
    }
    return mapping.get(band, f"Tell me about {focus}.")
