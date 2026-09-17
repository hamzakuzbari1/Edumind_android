"""Validate package drafts against PackageConstraints (deterministic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.services.language_educational_package.constraints import PackageConstraints
from app.services.language_educational_package.evidence_policy import DiscussionEvidenceRole
from app.services.language_educational_package.question_ladder import LADDER_ORDER, QuestionBand
from app.services.language_educational_package.types import EducationalPackage


class ValidationIssueCode(StrEnum):
    incomplete = "incomplete"
    vocabulary_coverage = "vocabulary_coverage"
    vocabulary_surface = "vocabulary_surface"
    lexical_recycling = "lexical_recycling"
    lesson_density = "lesson_density"
    story_spine = "story_spine"
    story_complexity = "story_complexity"
    grammar_coverage = "grammar_coverage"
    mission_consistency = "mission_consistency"
    objective_consistency = "objective_consistency"
    cefr_mismatch = "cefr_mismatch"
    metadata_missing = "metadata_missing"
    discussion_structure = "discussion_structure"
    reflection_structure = "reflection_structure"
    ladder_order = "ladder_order"
    evidence_slot = "evidence_slot"
    teaching_block_ids = "teaching_block_ids"
    mini_practice = "mini_practice"
    invented_vocabulary = "invented_vocabulary"
    personalization_guard = "personalization_guard"


@dataclass(slots=True)
class ValidationIssue:
    code: ValidationIssueCode
    message: str
    severity: str = "error"  # error | warning


@dataclass(slots=True)
class ValidationResult:
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


def _band_index(band: QuestionBand) -> int:
    try:
        return LADDER_ORDER.index(band)
    except ValueError:
        return -1


def validate_package_draft(
    package: EducationalPackage,
    constraints: PackageConstraints,
) -> ValidationResult:
    issues: list[ValidationIssue] = []

    if not package.input_material.title or not package.input_material.body_blocks:
        issues.append(
            ValidationIssue(
                ValidationIssueCode.incomplete,
                "input_material requires title and body_blocks",
            )
        )

    echo = (package.input_material.cefr_check_echo or "").upper()
    if echo and echo != constraints.official_cefr.upper():
        issues.append(
            ValidationIssue(
                ValidationIssueCode.cefr_mismatch,
                f"cefr_check_echo {echo} != constraints {constraints.official_cefr}",
            )
        )
    elif not echo:
        issues.append(
            ValidationIssue(
                ValidationIssueCode.cefr_mismatch,
                "cefr_check_echo missing",
                severity="warning",
            )
        )

    if package.mission_id and package.mission_id != constraints.mission_id:
        issues.append(
            ValidationIssue(
                ValidationIssueCode.mission_consistency,
                "mission_id does not match constraints",
            )
        )

    allowed_vocab = set(constraints.vocabulary_ids)
    covered: set[str] = set()
    for entry in package.vocabulary_in_context.entries:
        if entry.vocabulary_id:
            if allowed_vocab and entry.vocabulary_id not in allowed_vocab:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.invented_vocabulary,
                        f"unknown vocabulary_id {entry.vocabulary_id}",
                    )
                )
            covered.add(entry.vocabulary_id)
    if allowed_vocab and not allowed_vocab.issubset(covered):
        missing = sorted(allowed_vocab - covered)
        issues.append(
            ValidationIssue(
                ValidationIssueCode.vocabulary_coverage,
                f"missing vocabulary coverage: {missing}",
            )
        )

    # Curriculum Engine V2: exact surfaces from vocabulary_targets
    surface_by_id = {
        str(v.get("vocabulary_id")): str(v.get("surface") or "")
        for v in (constraints.vocabulary_targets or ())
        if isinstance(v, dict) and v.get("vocabulary_id")
    }
    if surface_by_id:
        for entry in package.vocabulary_in_context.entries:
            expected = surface_by_id.get(entry.vocabulary_id)
            if expected and entry.surface.strip() != expected.strip():
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.vocabulary_surface,
                        f"surface for {entry.vocabulary_id} must be exact '{expected}'",
                        severity="warning",
                    )
                )

    # Lexical recycling across lesson sections
    recycle = constraints.lexical_recycling_policy or {}
    min_hits = int(recycle.get("min_appearances_per_item") or 0)
    if min_hits and (constraints.vocabulary_targets or constraints.vocabulary_surface_forms):
        sections = [
            " ".join(b.text for b in package.input_material.body_blocks),
            " ".join(b.body for b in package.teaching_blocks_authored),
            " ".join(
                [package.discussion.opening_move, package.discussion.closing_move]
                + [s.prompt for s in package.discussion.steps]
            ),
            f"{package.mini_practice.prompt} {package.mini_practice.scaffold}",
        ]
        corpus = "\n".join(sections).lower()
        targets = list(constraints.vocabulary_targets or ())
        if targets:
            for raw in targets:
                if not isinstance(raw, dict):
                    continue
                surface = str(raw.get("surface") or "").strip()
                need = max(min_hits, int(raw.get("required_lesson_frequency") or min_hits))
                if not surface:
                    continue
                hits = corpus.count(surface.lower())
                if hits < need:
                    issues.append(
                        ValidationIssue(
                            ValidationIssueCode.lexical_recycling,
                            f"surface '{surface}' appears {hits}x; need ≥{need}",
                            severity="warning",
                        )
                    )
        else:
            for surface in constraints.vocabulary_surface_forms:
                if corpus.count(str(surface).lower()) < min_hits:
                    issues.append(
                        ValidationIssue(
                            ValidationIssueCode.lexical_recycling,
                            f"surface '{surface}' under-recycled",
                            severity="warning",
                        )
                    )

    # Lesson density (CEFR authoring policy) — dual-read story beats / dialogue turns
    policy = constraints.lesson_authoring_policy or {}
    if policy:
        beats = [
            b
            for b in package.input_material.body_blocks
            if (b.kind.value if hasattr(b.kind, "value") else str(b.kind))
            in {"turn", "paragraph", "heading"}
        ]
        word_count = sum(len((b.text or "").split()) for b in package.input_material.body_blocks)
        min_beats = int(
            policy.get("min_story_beats") or policy.get("min_dialogue_turns") or 0
        )
        min_words = int(policy.get("min_input_word_count") or 0)
        max_words = int(policy.get("max_input_word_count") or 0)
        if min_beats and len(beats) < min_beats:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.lesson_density,
                    f"story beats {len(beats)} < min_story_beats {min_beats}",
                    severity="warning",
                )
            )
        if min_words and word_count < min_words:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.lesson_density,
                    f"input words {word_count} < min_input_word_count {min_words}",
                    severity="warning",
                )
            )
        if max_words and word_count > max_words * 1.35:
            # Soft ceiling — allow some overflow; flag extreme overshoot
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.lesson_density,
                    f"input words {word_count} >> max_input_word_count {max_words}",
                    severity="warning",
                )
            )

    # Educational Case spine — required for speaking story packages
    if (
        constraints.skill == "speaking"
        and constraints.input_material_kind.value == "story"
        and not package.story_spine.is_substantive()
    ):
        issues.append(
            ValidationIssue(
                ValidationIssueCode.story_spine,
                "speaking story package requires conflict, events, ending, continuation_hook",
                severity="warning",
            )
        )

    # Story complexity policy (CEFR adaptive)
    complexity = constraints.story_complexity_policy or {}
    if complexity and constraints.skill == "speaking":
        story_text = " ".join(b.text for b in package.input_material.body_blocks)
        word_count = len(story_text.split())
        paragraphs = [
            b
            for b in package.input_material.body_blocks
            if (b.kind.value if hasattr(b.kind, "value") else str(b.kind))
            in {"paragraph", "heading"}
        ]
        min_words = int(complexity.get("min_words") or 0)
        max_words = int(complexity.get("max_words") or 0)
        pmin = int(complexity.get("paragraph_count_min") or complexity.get("paragraph_count") or 0)
        pmax = int(complexity.get("paragraph_count_max") or 0)
        cmin = int(complexity.get("characters_min") or 0)
        cmax = int(complexity.get("characters_max") or 0)
        emin = int(complexity.get("story_events_min") or complexity.get("story_events") or 0)
        emax = int(complexity.get("story_events_max") or 0)
        max_sent = int(complexity.get("max_sentence_length") or 0)
        allow_nested = bool(complexity.get("allow_nested_clauses", True))
        reflection_need = int(complexity.get("reflection_depth") or 0)

        if min_words and word_count < min_words:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"word count {word_count} < min_words {min_words}",
                    severity="warning",
                )
            )
        if max_words and word_count > int(max_words * 1.25):
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"word count {word_count} >> max_words {max_words}",
                    severity="warning",
                )
            )
        if pmin and len(paragraphs) < pmin:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"paragraphs {len(paragraphs)} < paragraph_count_min {pmin}",
                    severity="warning",
                )
            )
        if pmax and len(paragraphs) > pmax + 2:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"paragraphs {len(paragraphs)} > paragraph_count_max {pmax}",
                    severity="warning",
                )
            )
        char_n = len(package.story_spine.characters) or len(constraints.character_hints)
        if cmin and char_n < cmin:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"characters {char_n} < characters_min {cmin}",
                    severity="warning",
                )
            )
        if cmax and char_n > cmax:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"characters {char_n} > characters_max {cmax}",
                    severity="warning",
                )
            )
        event_n = len(package.story_spine.events)
        if emin and event_n < emin:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"events {event_n} < story_events_min {emin}",
                    severity="warning",
                )
            )
        if emax and event_n > emax + 2:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"events {event_n} > story_events_max {emax}",
                    severity="warning",
                )
            )
        if reflection_need and len(package.reflection.prompts) < reflection_need:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"reflection prompts {len(package.reflection.prompts)} < reflection_depth {reflection_need}",
                    severity="warning",
                )
            )
        # Sentence complexity heuristic
        sentences = [s.strip() for s in story_text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if sentences and max_sent:
            avg_len = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
            if avg_len > max_sent * 1.35:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.story_complexity,
                        f"avg sentence length {avg_len:.1f} > max_sentence_length {max_sent}",
                        severity="warning",
                    )
                )
        if not allow_nested:
            nested_hits = sum(
                story_text.lower().count(m)
                for m in (" which ", " who ", " that ", " although ", " whereas ")
            )
            if nested_hits > max(2, len(paragraphs)):
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.story_complexity,
                        f"nested-clause markers {nested_hits} exceed A1/A2 allowance",
                        severity="warning",
                    )
                )

        # M7 — Educational Case sophistication checks
        stake_need = int(complexity.get("stakeholder_count") or 0)
        stake_have = len(package.story_spine.stakeholders) or len(
            getattr(constraints, "stakeholder_hints", ()) or ()
        )
        if stake_need and stake_have < stake_need:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    f"stakeholders {stake_have} < stakeholder_count {stake_need}",
                    severity="warning",
                )
            )
        if complexity.get("case_category") and package.story_spine.case_category:
            if package.story_spine.case_category != complexity.get("case_category"):
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.story_complexity,
                        "case_category mismatch between spine and policy",
                        severity="warning",
                    )
                )
        elif complexity.get("case_category") and not package.story_spine.case_category:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    "story_spine.case_category missing",
                    severity="warning",
                )
            )
        if not package.story_spine.decision_point.strip():
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.story_complexity,
                    "decision_point missing on story_spine",
                    severity="warning",
                )
            )
        # Discussion depth: higher CEFR should ask for reasons / trade-offs / critique
        depth = str(complexity.get("discussion_depth") or "")
        discussion_blob = " ".join(
            [package.discussion.opening_move]
            + [s.prompt for s in package.discussion.steps]
        ).lower()
        if "ethical" in depth or "tradeoff" in depth or "trade-off" in depth:
            if not any(
                k in discussion_blob
                for k in ("ethic", "trade", "perspective", "evidence", "stakeholder")
            ):
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.story_complexity,
                        "discussion depth lacks ethical/trade-off language",
                        severity="warning",
                    )
                )
        if "critical" in depth or "counterargument" in depth or "policy" in depth:
            if not any(
                k in discussion_blob
                for k in ("counter", "societ", "long-term", "defend", "policy", "consequence")
            ):
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.story_complexity,
                        "discussion depth lacks critical/policy language",
                        severity="warning",
                    )
                )
        # Continuation / world consistency
        if package.story_spine.continuation_hook and package.mini_practice.prompt:
            names = {c.name.lower() for c in package.story_spine.characters if c.name}
            mini_l = package.mini_practice.prompt.lower()
            if names and not any(n in mini_l for n in names):
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.story_complexity,
                        "mini practice does not continue same characters/world",
                        severity="warning",
                    )
                )

    # Grammar: topics must be demonstrated in story and referenced across teaching/discussion
    if constraints.grammar_topic_ids or constraints.grammar_targets:
        story_l = " ".join(b.text for b in package.input_material.body_blocks).lower()
        teaching_l = " ".join(b.body for b in package.teaching_blocks_authored).lower()
        discussion_l = " ".join(
            [package.discussion.opening_move, package.discussion.closing_move]
            + [s.prompt for s in package.discussion.steps]
        ).lower()
        mini_l = f"{package.mini_practice.prompt} {package.mini_practice.scaffold}".lower()
        referenced: set[str] = set()
        for step in package.discussion.steps:
            referenced.update(step.grammar_topic_ids)
        for raw in constraints.grammar_targets or ():
            if not isinstance(raw, dict):
                continue
            gid = str(raw.get("grammar_topic_id") or "")
            forms = [str(f).lower() for f in (raw.get("demonstration_forms") or []) if f]
            label = str(raw.get("label") or "").lower()
            in_story = any(f in story_l for f in forms) if forms else bool(label and label in story_l)
            in_teaching = (label and label in teaching_l) or any(f in teaching_l for f in forms)
            in_discussion = gid in referenced or any(f in discussion_l for f in forms)
            in_mini = any(f in mini_l for f in forms) or (label and label in mini_l)
            if not in_story:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.grammar_coverage,
                        f"grammar '{gid}' not demonstrated in story",
                        severity="warning",
                    )
                )
            if not in_teaching:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.grammar_coverage,
                        f"grammar '{gid}' missing from teaching",
                        severity="warning",
                    )
                )
            if not in_discussion:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.grammar_coverage,
                        f"grammar '{gid}' missing from discussion",
                        severity="warning",
                    )
                )
            if not in_mini:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.grammar_coverage,
                        f"grammar '{gid}' missing from mini practice",
                        severity="warning",
                    )
                )
        if constraints.grammar_topic_ids and not referenced.intersection(constraints.grammar_topic_ids):
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.grammar_coverage,
                    "grammar_topic_ids not referenced in discussion steps",
                    severity="warning",
                )
            )

    if not package.discussion.steps:
        issues.append(
            ValidationIssue(
                ValidationIssueCode.discussion_structure,
                "discussion.steps empty",
            )
        )
    else:
        policy = constraints.question_ladder_policy
        if len(package.discussion.steps) < policy.min_steps:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.discussion_structure,
                    f"fewer than min_steps ({policy.min_steps})",
                )
            )
        if len(package.discussion.steps) > policy.max_steps:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.discussion_structure,
                    f"more than max_steps ({policy.max_steps})",
                )
            )
        seen_bands = {s.ladder_band for s in package.discussion.steps}
        for required in policy.required_bands:
            if required not in seen_bands:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.discussion_structure,
                        f"missing required ladder band {required.value}",
                    )
                )
        # Non-decreasing ladder order
        last_idx = -1
        for step in package.discussion.steps:
            idx = _band_index(step.ladder_band)
            if idx < last_idx:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.ladder_order,
                        f"ladder regresses at step {step.step_id}",
                    )
                )
                break
            last_idx = max(last_idx, idx)
        for step in package.discussion.steps:
            if not step.prompt.strip():
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.discussion_structure,
                        f"empty prompt on {step.step_id}",
                    )
                )

    # Evidence slots: authored roles must not invent extra transfer/formative beyond plan when plan present
    if constraints.evidence_slot_plan:
        planned_ids = {s.step_id for s in constraints.evidence_slot_plan if s.step_id}
        for step in package.discussion.steps:
            if step.evidence_role != DiscussionEvidenceRole.none and planned_ids:
                if step.step_id not in planned_ids and step.evidence_role in {
                    DiscussionEvidenceRole.formative,
                    DiscussionEvidenceRole.transfer,
                }:
                    issues.append(
                        ValidationIssue(
                            ValidationIssueCode.evidence_slot,
                            f"unplanned evidence step {step.step_id}",
                            severity="warning",
                        )
                    )

    req_count = constraints.reflection_requirements.prompt_count
    if len(package.reflection.prompts) < req_count:
        issues.append(
            ValidationIssue(
                ValidationIssueCode.reflection_structure,
                f"reflection needs >= {req_count} prompts",
            )
        )

    expected_block_ids = {b.block_id for b in constraints.teaching_block_specs if b.block_id}
    authored_ids = {b.block_id for b in package.teaching_blocks_authored if b.block_id}
    if expected_block_ids and not expected_block_ids.issubset(authored_ids):
        issues.append(
            ValidationIssue(
                ValidationIssueCode.teaching_block_ids,
                f"missing teaching blocks: {sorted(expected_block_ids - authored_ids)}",
            )
        )

    if constraints.mini_practice_task_id:
        if package.mini_practice.task_id != constraints.mini_practice_task_id:
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.mini_practice,
                    "mini_practice.task_id must match constraints",
                )
            )
        if not package.mini_practice.prompt.strip():
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.mini_practice,
                    "mini_practice.prompt empty",
                )
            )

    if constraints.objectives and not any(
        obj.lower() in " ".join(package.discussion.steps[i].prompt for i in range(len(package.discussion.steps))).lower()
        for obj in constraints.objectives[:1]
    ):
        # Soft: objectives should influence discussion — warning only
        issues.append(
            ValidationIssue(
                ValidationIssueCode.objective_consistency,
                "objectives not clearly reflected in discussion prompts",
                severity="warning",
            )
        )

    if not package.metadata.get("locale") and not constraints.locale:
        issues.append(
            ValidationIssue(
                ValidationIssueCode.metadata_missing,
                "locale metadata missing",
                severity="warning",
            )
        )

    # M8 — personalization must not rewrite curriculum ownership
    perso = constraints.personalization or {}
    if isinstance(perso, dict) and perso.get("applied"):
        if package.input_material.cefr_check_echo.upper() != constraints.official_cefr.upper():
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.personalization_guard,
                    "personalization must not alter CEFR echo",
                )
            )
        if constraints.case_category and package.story_spine.case_category:
            if package.story_spine.case_category != constraints.case_category:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.personalization_guard,
                        "personalization must not alter case_category",
                    )
                )
        if constraints.case_archetype and package.story_spine.case_archetype:
            if package.story_spine.case_archetype != constraints.case_archetype:
                issues.append(
                    ValidationIssue(
                        ValidationIssueCode.personalization_guard,
                        "personalization must not alter case_archetype",
                    )
                )
        cons_vocab = {str(v) for v in constraints.vocabulary_ids}
        pkg_vocab = {e.vocabulary_id for e in package.vocabulary_in_context.entries}
        if cons_vocab and not cons_vocab.issubset(pkg_vocab):
            issues.append(
                ValidationIssue(
                    ValidationIssueCode.personalization_guard,
                    "personalization must not drop curriculum vocabulary_ids",
                )
            )

    errors = [i for i in issues if i.severity == "error"]
    return ValidationResult(passed=len(errors) == 0, issues=issues)


def validation_to_dict(result: ValidationResult) -> dict[str, Any]:
    return {
        "passed": result.passed,
        "error_count": result.error_count,
        "warning_count": result.warning_count,
        "issues": [
            {"code": i.code.value, "message": i.message, "severity": i.severity}
            for i in result.issues
        ],
    }
