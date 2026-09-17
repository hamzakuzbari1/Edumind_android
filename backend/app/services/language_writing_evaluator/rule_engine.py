"""Rule-based Writing Evaluation Engine — deterministic facts only (hybrid layer 1)."""

from __future__ import annotations

import re

from app.services.language_writing_evaluator.blueprint_snapshot import EvaluatorBlueprintSnapshot
from app.services.language_writing_evaluator.evaluation_facts_types import CriterionStatus, SuccessCriterionStatus
from app.services.language_writing_evaluator.evaluation_result import (
    CEFRValidationFacts,
    CompletionFacts,
    DimensionFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
)
from app.services.language_writing_evaluator.rule_facts_types import RULE_FACTS_VERSION, RuleEvaluationFacts

RULE_ENGINE_VERSION = RULE_FACTS_VERSION

_GRAMMAR_HINTS: dict[str, tuple[str, ...]] = {
    "past_simple": ("ed ", " was ", " were ", " went ", " said ", " had "),
    "present_simple": (" is ", " are ", " am ", " do ", " does ", " have ", " has "),
    "present_continuous": (" am ", " is ", " are ", " ing ", " going to "),
    "present_perfect": (" have ", " has ", " been ", " since ", " for "),
    "modal_verbs": (" can ", " could ", " should ", " would ", " must ", " may ", " might "),
    "passive_voice": (" was ", " were ", " been ", " by "),
    "future_forms": (" will ", " going to ", " shall "),
    "because": (" because ", " since ", " as "),
    "comparatives": (" than ", " more ", " less ", " better ", " worse "),
    "possessives": (" my ", " your ", " his ", " her ", " our ", " their "),
    "questions": ("?", " what ", " where ", " when ", " why ", " how "),
    "linking_words": (" however ", " therefore ", " moreover ", " although ", " first ", " finally "),
    "there_is_are": (" there is ", " there are ", " there's ", " there isn't ", " there aren't "),
    "sequencers": (" first ", " then ", " next ", " finally ", " after ", " before "),
    "polite_requests": (" please ", " could you ", " would you ", " kindly "),
}

_GENRE_HINTS: dict[str, tuple[str, ...]] = {
    "email": ("dear", "subject", "regards", "sincerely", "@"),
    "business_email": ("dear", "meeting", "schedule", "regards"),
    "complaint_email": ("dear", "complaint", "refund", "issue", "apolog"),
    "narrative": (" then ", " after ", " when ", " story"),
    "paragraph": (".",),
    "report": ("summary", "outcome", "recommend", "finding"),
    "cover_letter": ("position", "apply", "experience", "qualif"),
    "review": ("recommend", "overall", "experience", "worth"),
}

_AGREEMENT_CHECKS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(name|he|she|it|this|that|everyone|someone|each|child|man|woman|person|friend|teacher|student)\s+are\b",
            re.I,
        ),
        "Subject-verb agreement: a singular subject needs 'is', not 'are' (e.g. 'My name is …').",
    ),
    (
        re.compile(r"\bI\s+are\b", re.I),
        "Subject-verb agreement: use 'I am', not 'I are'.",
    ),
    (
        re.compile(r"\b(they|we|these|those|people|students|friends)\s+is\b", re.I),
        "Subject-verb agreement: a plural subject needs 'are', not 'is'.",
    ),
)


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text.strip()))


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    lower = f" {haystack.lower()} "
    return any(n in lower for n in needles)


def _detect_agreement_errors(text: str) -> tuple[str, ...]:
    errors: list[str] = []
    for pattern, message in _AGREEMENT_CHECKS:
        if pattern.search(text):
            errors.append(message)
    return tuple(errors)


def _grammar_score(text: str, grammar_ids: tuple[str, ...]) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    agreement_errors = _detect_agreement_errors(text)
    if agreement_errors:
        return 0.0, ("grammar:agreement_error",), agreement_errors
    if not grammar_ids:
        return 0.7, ("grammar:unchecked",), ()
    hits: list[str] = []
    for gid in grammar_ids:
        hints = _GRAMMAR_HINTS.get(gid, (gid.replace("_", " "),))
        if _contains_any(text, hints):
            hits.append(f"grammar:{gid}:present")
    ratio = len(hits) / max(len(grammar_ids), 1)
    score = min(1.0, ratio + (0.2 if ratio >= 0.5 else 0.0))
    return score, tuple(hits), ()


def _vocabulary_score(text: str, lemmas: tuple[str, ...]) -> tuple[float, tuple[str, ...]]:
    if not lemmas:
        return 0.7, ("vocab:unchecked",)
    lower = text.lower()
    hits = [f"vocab:{lemma}:present" for lemma in lemmas if lemma.lower() in lower]
    ratio = len(hits) / max(len(lemmas), 1)
    return min(1.0, ratio + (0.15 if ratio >= 0.5 else 0.0)), tuple(hits)


def _organization_score(text: str) -> tuple[float, tuple[str, ...]]:
    sentences = _sentences(text)
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    codes: list[str] = []
    score = 0.4
    if len(sentences) >= 2:
        score += 0.25
        codes.append("org:multiple_sentences")
    if len(paragraphs) >= 1 and len(text) > 80:
        score += 0.15
        codes.append("org:paragraph_structure")
    if _contains_any(text, _GRAMMAR_HINTS["linking_words"]):
        score += 0.2
        codes.append("org:linking_words")
    return min(1.0, score), tuple(codes)


def _goal_alignment_score(text: str, genre: str, task_type: str) -> tuple[float, tuple[str, ...]]:
    hints = _GENRE_HINTS.get(genre, ()) + _GENRE_HINTS.get(task_type, ())
    if not hints:
        return 0.65, ("goal:generic",)
    hits = [f"goal:{h}:present" for h in hints if h in text.lower()]
    ratio = len(hits) / max(len(hints[:6]), 1)
    return min(1.0, 0.35 + ratio * 0.65), tuple(hits[:6])


def _criterion_status(passed: bool, partial: bool = False) -> CriterionStatus:
    if passed:
        return CriterionStatus.met
    if partial:
        return CriterionStatus.partial
    return CriterionStatus.not_met


def _match_critical_mistakes(text: str, mistakes: tuple[str, ...]) -> tuple[str, ...]:
    lower = text.lower()
    matched: list[str] = []
    for mistake in mistakes:
        token = mistake.split(":", 1)[-1].strip().lower()
        if token and token in lower:
            matched.append(mistake)
    return tuple(matched)


def _dim_facts(
    name: str,
    score: float,
    weight: float,
    codes: tuple[str, ...],
    *,
    errors: tuple[str, ...] = (),
    pass_threshold: float = 0.55,
) -> DimensionFacts:
    passed = score >= pass_threshold and not errors
    return DimensionFacts(
        dimension=name,
        score=score,
        weight=weight,
        passed=passed,
        evidence_codes=codes,
        errors=errors,
    )


def _cefr_validation(
    *,
    expected_band: str,
    meets_word_limit: bool,
    grammar: DimensionFacts,
    agreement_errors: tuple[str, ...],
    overall: float,
) -> CEFRValidationFacts:
    notes: list[str] = []
    if agreement_errors:
        notes.append(f"Grammar below {expected_band} expectations: subject-verb agreement error.")
    if not grammar.passed:
        notes.append(f"Required grammar for {expected_band} level not demonstrated.")
    if not meets_word_limit:
        notes.append("Draft length outside the range expected for this level.")
    if not notes and overall >= 0.6:
        status = CriterionStatus.met
    elif notes and overall >= 0.45:
        status = CriterionStatus.partial
    else:
        status = CriterionStatus.not_met
    return CEFRValidationFacts(expected_band=expected_band, status=status, notes=tuple(notes))


def _build_explanation(
    *,
    chain_node_id: str,
    grammar: DimensionFacts,
    vocabulary: DimensionFacts,
    organization: DimensionFacts,
    meets_word_limit: bool,
    word_count_val: int,
    min_words: int,
    success_criteria: tuple[SuccessCriterionStatus, ...],
    blockers: tuple[str, ...],
    ready: bool,
    strong_skills: tuple[str, ...],
) -> ExplanationFacts:
    improvements: list[str] = []
    for err in grammar.errors:
        if "name is" in err.lower() or "singular subject" in err.lower():
            improvements.append("Fix subject-verb agreement: say 'My name is …', not 'My name are …'.")
        else:
            improvements.append(err)
    if not vocabulary.passed:
        improvements.append("Use more of the lesson vocabulary in your draft.")
    if not organization.passed:
        improvements.append("Strengthen paragraph organization with clear sentences and linking words.")
    if not meets_word_limit and word_count_val < min_words:
        improvements.append(f"Add enough detail to reach at least {min_words} words (you have {word_count_val}).")
    for c in success_criteria:
        if c.status == CriterionStatus.not_met:
            improvements.append(f"Meet this success criterion: {c.label}")
        elif c.status == CriterionStatus.partial:
            improvements.append(f"Strengthen: {c.label}")
    for b in blockers:
        if b not in improvements and b not in grammar.errors:
            improvements.append(b)

    priority = grammar.errors[0] if grammar.errors else (blockers[0] if blockers else "")
    if not priority:
        unmet = [c.label for c in success_criteria if c.status != CriterionStatus.met]
        priority = unmet[0] if unmet else "task completion"

    focus = priority.split(":", 1)[-1] if ":" in priority else priority
    node_label = chain_node_id.replace("_", " ")

    if ready:
        summary = (
            f"Your draft meets the lesson success criteria for '{node_label}'. "
            "Review the checklist once more before completing."
        )
    elif grammar.errors:
        summary = (
            f"Your draft for '{node_label}' has a grammar issue that must be fixed before completion. "
            f"{grammar.errors[0]}"
        )
    else:
        summary = (
            f"Your writing on '{node_label}' is progressing, but it does not yet meet all lesson requirements. "
            f"Focus on: {focus}."
        )

    strength_msgs: list[str] = []
    for s in strong_skills[:4]:
        if s.startswith("grammar:"):
            strength_msgs.append("You used grammar clearly for this task.")
        elif s.startswith("vocabulary:"):
            strength_msgs.append("Your vocabulary fits the topic well.")
        elif "organization" in s:
            strength_msgs.append("Your paragraph is well organized.")
        elif "word_count" in s:
            strength_msgs.append("Your draft meets the word count range.")
        else:
            strength_msgs.append(f"You showed strength in {s.split(':', 1)[-1].replace('_', ' ')}.")

    return ExplanationFacts(
        summary=summary,
        priority_issue=grammar.errors[0] if grammar.errors else priority,
        improvements=tuple(dict.fromkeys(improvements))[:6],
        strengths=tuple(strength_msgs),
        focus_label=focus,
    )


def compute_rule_evaluation_facts(
    draft_text: str,
    *,
    draft_id: str,
    revision_number: int,
    blueprint: EvaluatorBlueprintSnapshot,
    official_cefr: str = "B1",
) -> RuleEvaluationFacts:
    """Deterministic rule evaluation — pass/fail and technical validation only."""
    text = draft_text.strip()
    wc = word_count(text)
    plan = blueprint.evaluation_plan
    sc = blueprint.success_criteria

    grammar_ids = sc.required_grammar or (blueprint.grammar_primary,)
    grammar_score, grammar_codes, grammar_errors = _grammar_score(text, grammar_ids)
    vocab_lemmas = sc.required_vocabulary or blueprint.vocabulary_primary
    vocab_score, vocab_codes = _vocabulary_score(text, vocab_lemmas)
    org_score, org_codes = _organization_score(text)
    goal_score, goal_codes = _goal_alignment_score(text, blueprint.genre, blueprint.task_type)

    meets_min = wc >= sc.min_words
    meets_max = wc <= sc.max_words
    meets_word_limit = meets_min and meets_max

    criteria_status: list[SuccessCriterionStatus] = []
    criteria_pass = 0
    for label in sc.success_criteria_labels:
        lower_label = label.lower()
        passed = False
        partial = False
        code = "criterion:generic"
        if "word" in lower_label and "least" in lower_label:
            passed = meets_min
            partial = wc >= sc.min_words * 0.7 and not meets_min
            code = "criterion:word_min"
        elif "format" in lower_label or "output" in lower_label:
            passed = goal_score >= 0.5
            partial = 0.35 <= goal_score < 0.5
            code = "criterion:output_format"
        elif "vocabulary" in lower_label:
            passed = vocab_score >= 0.5
            partial = 0.3 <= vocab_score < 0.5
            code = "criterion:vocabulary"
        elif "grammar" in lower_label or "use " in lower_label:
            passed = grammar_score >= 0.5 and not grammar_errors
            partial = 0.3 <= grammar_score < 0.5 and not grammar_errors
            code = "criterion:grammar"
        elif "objective" in lower_label:
            passed = org_score >= 0.45 and meets_min
            partial = org_score >= 0.35 and not meets_min
            code = "criterion:objective"
        else:
            passed = (
                meets_min
                and grammar_score >= 0.5
                and not grammar_errors
                and vocab_score >= 0.45
                and org_score >= 0.4
            )
            partial = meets_min and not passed
            code = "criterion:holistic"
        if passed:
            criteria_pass += 1
        criteria_status.append(
            SuccessCriterionStatus(label=label, status=_criterion_status(passed, partial), code=code)
        )

    task_ratio = criteria_pass / max(len(sc.success_criteria_labels), 1)
    if not meets_min:
        task_ratio = min(task_ratio, 0.4)
    if grammar_errors:
        task_ratio = min(task_ratio, 0.35)

    outcomes_status: list[SuccessCriterionStatus] = []
    for outcome in blueprint.learning_outcomes:
        tokens = [t for t in outcome.lower().split() if len(t) > 4][:3]
        passed = (
            any(t in text.lower() for t in tokens)
            and meets_min
            and not grammar_errors
            and grammar_score >= 0.5
        ) or (task_ratio >= 0.85 and meets_min and not grammar_errors)
        outcomes_status.append(
            SuccessCriterionStatus(
                label=outcome,
                status=_criterion_status(passed, not passed and task_ratio >= 0.4),
                code="outcome:check",
            )
        )

    weighted = (
        grammar_score * plan.grammar_weight
        + vocab_score * plan.vocabulary_weight
        + org_score * plan.organization_weight
        + task_ratio * plan.task_completion_weight
        + goal_score * plan.goal_alignment_weight
    )
    critical = _match_critical_mistakes(text, plan.critical_mistakes)

    weak_skills: list[str] = list(critical)
    if grammar_errors:
        weak_skills.append("grammar:subject_verb_agreement")
    elif grammar_score < 0.5:
        weak_skills.append(f"grammar:{blueprint.grammar_primary}")
    if vocab_score < 0.5:
        weak_skills.append("vocabulary:required_lemmas")
    if not meets_min:
        weak_skills.append("word_count:below_minimum")
    if org_score < 0.45:
        weak_skills.append("organization:structure")

    strong_skills: list[str] = []
    if grammar_score >= 0.7 and not grammar_errors:
        strong_skills.append(f"grammar:{blueprint.grammar_primary}")
    if vocab_score >= 0.7:
        strong_skills.append("vocabulary:target_lemmas")
    if org_score >= 0.7:
        strong_skills.append("organization:structure")
    if meets_word_limit:
        strong_skills.append("word_count:within_range")

    grammar = _dim_facts("grammar", grammar_score, plan.grammar_weight, grammar_codes, errors=grammar_errors)
    vocabulary = _dim_facts("vocabulary", vocab_score, plan.vocabulary_weight, vocab_codes, pass_threshold=0.5)
    organization = _dim_facts("organization", org_score, plan.organization_weight, org_codes, pass_threshold=0.45)
    task_completion = _dim_facts("task_completion", task_ratio, plan.task_completion_weight, (f"ratio:{task_ratio:.2f}",))
    goal_alignment = _dim_facts("goal_alignment", goal_score, plan.goal_alignment_weight, goal_codes, pass_threshold=0.5)

    cefr = _cefr_validation(
        expected_band=official_cefr,
        meets_word_limit=meets_word_limit,
        grammar=grammar,
        agreement_errors=grammar_errors,
        overall=weighted,
    )

    criteria_met = sum(1 for c in criteria_status if c.status == CriterionStatus.met)
    criteria_total = len(criteria_status)
    outcomes_met = sum(1 for o in outcomes_status if o.status == CriterionStatus.met)
    outcomes_total = len(outcomes_status)
    min_required_criteria = max(criteria_total - 1, int(criteria_total * 0.85)) if criteria_total else 0
    min_required_outcomes = max(1, int(outcomes_total * 0.67)) if outcomes_total else 0

    blockers: list[str] = []
    if grammar_errors:
        blockers.extend(grammar_errors)
    if critical:
        blockers.append("Critical mistakes remain — address before completion")
    if not meets_min:
        blockers.append(f"Word count {wc} below minimum {sc.min_words}")
    elif not meets_max:
        blockers.append(f"Word count {wc} above maximum {sc.max_words}")
    if criteria_met < min_required_criteria:
        blockers.append("Success criteria checklist incomplete")
    if outcomes_met < min_required_outcomes:
        blockers.append("Learning outcomes not yet demonstrated")
    if cefr.status == CriterionStatus.not_met and grammar_errors:
        blockers.append(f"Draft does not meet {official_cefr} grammar expectations")

    ready = len(blockers) == 0 and criteria_met >= min_required_criteria and outcomes_met >= min_required_outcomes

    completion_reason = "Blueprint success criteria met" if ready else blockers[0] if blockers else "Requirements not yet met"

    explanation = _build_explanation(
        chain_node_id=blueprint.chain_node_id,
        grammar=grammar,
        vocabulary=vocabulary,
        organization=organization,
        meets_word_limit=meets_word_limit,
        word_count_val=wc,
        min_words=sc.min_words,
        success_criteria=tuple(criteria_status),
        blockers=tuple(blockers),
        ready=ready,
        strong_skills=tuple(strong_skills),
    )

    confidence = round(min(1.0, weighted * (0.5 + 0.5 * (1.0 if not grammar_errors else 0.3))), 4)

    return RuleEvaluationFacts(
        draft_id=draft_id,
        revision_number=revision_number,
        chain_node_id=blueprint.chain_node_id,
        blueprint_version=blueprint.blueprint_version,
        blueprint_hash=blueprint.blueprint_hash,
        generation_hash=blueprint.generation_hash,
        word_count=wc,
        meets_word_limit=meets_word_limit,
        grammar=grammar,
        vocabulary=vocabulary,
        organization=organization,
        task_completion=task_completion,
        goal_alignment=goal_alignment,
        cefr_validation=cefr,
        success_criteria=tuple(criteria_status),
        learning_outcomes=tuple(outcomes_status),
        revision_readiness=RevisionReadinessFacts(ready=ready, blockers=tuple(blockers)),
        completion=CompletionFacts(
            eligible=ready,
            reason=completion_reason,
            criteria_met_count=criteria_met,
            criteria_total=criteria_total,
            outcomes_met_count=outcomes_met,
            outcomes_total=outcomes_total,
        ),
        explanation=explanation,
        confidence=confidence,
        weak_skills=tuple(dict.fromkeys(weak_skills)),
        strong_skills=tuple(strong_skills),
        critical_mistakes=critical,
        overall_readiness=weighted,
    )
