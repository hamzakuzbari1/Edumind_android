"""Deterministic speaking rule/evidence engine (S7 layer 1)."""

from __future__ import annotations

import re

from app.services.language_speaking_evaluator.evaluation_facts_types import CriterionStatus, DimensionEvidenceStatus
from app.services.language_speaking_evaluator.evaluation_result import (
    CompletionEligibilityFacts,
    DimensionFacts,
    EvidenceSummaryFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
)
from app.services.language_speaking_evaluator.input_types import SpeakingEvaluationContext, SpeakingEvaluationInput
from app.services.language_speaking_evaluator.rule_facts_types import (
    EvidenceQualityRuleFacts,
    PronunciationRuleFacts,
    ProsodyRuleFacts,
    SpeakingRuleEvaluationFacts,
    TranscriptRuleFacts,
)
from app.services.language_speaking_pronunciation.types import PhonemeAlignmentOperation

RULE_ENGINE_VERSION = "7.0.0"

# Mirrored from language_speaking_curriculum.evidence_ids — no curriculum import.
EV_PHONEME_ALIGNMENT = "phoneme_alignment"
EV_PRONUNCIATION_CONFIDENCE = "pronunciation_confidence"
EV_PAUSES = "pauses"
EV_SPEAKING_RATE = "speaking_rate"
EV_PITCH = "pitch"
EV_RHYTHM = "rhythm"
EV_ENERGY_VARIATION = "energy_variation"
EV_SEMANTIC_TASK_RESPONSE = "semantic_task_response"
EV_GRAMMAR_CONTROL = "grammar_control"
EV_VOCABULARY_FUNCTION = "vocabulary_function"
EV_TOPIC_DEVELOPMENT = "topic_development"
EV_ORGANIZATION_EVIDENCE = "organization_evidence"
EV_RESPONSE_RELEVANCE = "response_relevance"
EV_TURN_COMPLETION = "turn_completion"

_AGREEMENT_CHECKS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bI\s+are\b", re.I), "Use 'I am', not 'I are'."),
    (
        re.compile(
            r"\b(name|he|she|it|this|that|everyone|someone|each|child|man|woman|person|friend|teacher|student)\s+are\b",
            re.I,
        ),
        "Subject-verb agreement: singular subject needs 'is', not 'are'.",
    ),
)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\b[\w'-]+\b", (text or "").lower()))


def _task_overlap(task_prompt: str, words: tuple[str, ...]) -> tuple[float, tuple[str, ...]]:
    task_tokens = set(re.findall(r"\b\w+\b", (task_prompt or "").lower()))
    if not task_tokens:
        return 0.0, ()
    hits = tuple(sorted(set(words) & task_tokens))
    ratio = len(hits) / max(len(task_tokens), 1)
    return min(1.0, ratio), hits


def _signal_value(prosody, tag: str) -> float | None:
    if prosody is None:
        return None
    for obs in prosody.signal_observations:
        if obs.signal_tag == tag:
            return float(obs.value)
    return None


def _dim(
    name: str,
    *,
    status: DimensionEvidenceStatus,
    score: float,
    weight: float,
    codes: tuple[str, ...],
    confidence: float = 0.0,
    reason: str = "",
    evidence_ids: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> DimensionFacts:
    passed = status in {DimensionEvidenceStatus.met, DimensionEvidenceStatus.partial} and score >= 0.55 and not errors
    normalized = score if confidence > 0.2 else None
    return DimensionFacts(
        dimension=name,
        status=status,
        normalized_value=normalized,
        confidence=confidence,
        reason=reason,
        supporting_evidence_ids=evidence_ids,
        limitations=limitations,
        score=score,
        weight=weight,
        passed=passed,
        evidence_codes=codes,
        errors=errors,
    )


def evaluate_speaking_evidence(
    input: SpeakingEvaluationInput,
    context: SpeakingEvaluationContext,
) -> SpeakingRuleEvaluationFacts:
    """Compute deterministic evidence facts from transcript + S5 + S6."""
    text = (input.transcript_text or "").strip()
    words = input.transcript_tokens or _tokens(text)
    wc = input.transcript_word_count or len(words)
    overlap, hits = _task_overlap(context.task.task_prompt, words)
    empty = wc < 1 or not text

    agreement_errors: list[str] = []
    for pattern, message in _AGREEMENT_CHECKS:
        if pattern.search(text):
            agreement_errors.append(message)

    # --- S5 pronunciation facts ---
    pron = input.pronunciation
    sub_count = ins_count = om_count = 0
    pron_tags: list[str] = []
    pron_skills: list[str] = []
    if pron is not None:
        for obs in pron.phoneme_observations:
            if obs.operation == PhonemeAlignmentOperation.substitution:
                sub_count += 1
            elif obs.operation == PhonemeAlignmentOperation.omission:
                om_count += 1
            elif obs.operation == PhonemeAlignmentOperation.insertion:
                ins_count += 1
        for issue in pron.issue_observations:
            if issue.issue_tag and issue.issue_tag not in pron_tags:
                pron_tags.append(issue.issue_tag)
            for sid in issue.candidate_skill_ids:
                if sid not in pron_skills:
                    pron_skills.append(sid)
    pron_available = pron is not None and (input.evidence_availability.get("pronunciation", True) if input.evidence_availability else pron is not None)
    pron_coverage = float(pron.evidence_coverage) if pron else 0.0
    pron_reliability = float(pron.evidence_reliability) if pron else 0.0
    pron_facts = PronunciationRuleFacts(
        available=pron_available and pron is not None,
        substitution_count=sub_count,
        omission_count=om_count,
        insertion_count=ins_count,
        issue_tags=tuple(pron_tags),
        recurring_issue_tags=tuple(t for t in pron_tags if sub_count + om_count >= 2),
        coverage=pron_coverage,
        reliability=pron_reliability,
        affected_candidate_skill_ids=tuple(pron_skills),
        processing_warnings=pron.processing_warnings if pron else (),
    )

    # --- S6 prosody facts ---
    pro = input.prosody
    pro_tags = tuple(i.issue_tag for i in (pro.issue_observations if pro else ()) if i.issue_tag)
    pro_skills: list[str] = []
    if pro:
        for sid in pro.candidate_skill_ids:
            if sid not in pro_skills:
                pro_skills.append(sid)
        for issue in pro.issue_observations:
            for sid in issue.candidate_skill_ids:
                if sid not in pro_skills:
                    pro_skills.append(sid)
    pause_density = _signal_value(pro, "pause_density")
    long_pauses = int(_signal_value(pro, "long_pause_count") or 0) if pro else 0
    pitch_var = _signal_value(pro, "pitch_variation")
    energy_var = _signal_value(pro, "energy_variation")
    rhythm = _signal_value(pro, "rhythm_regularity")
    rate_proxy = _signal_value(pro, "speaking_rate_proxy")
    pro_available = pro is not None and bool(input.evidence_availability.get("prosody", pro is not None) if input.evidence_availability else pro is not None)
    pro_facts = ProsodyRuleFacts(
        available=pro_available and pro is not None,
        pause_density=pause_density,
        long_pause_count=long_pauses,
        pitch_variation=pitch_var,
        energy_variation=energy_var,
        rhythm_regularity=rhythm,
        rate_proxy=rate_proxy,
        issue_tags=pro_tags,
        stable_issue_tags=pro_tags,
        reliability=float(pro.evidence_reliability) if pro else 0.0,
        affected_candidate_skill_ids=tuple(pro_skills),
        unavailable_families=tuple(pro.unavailable_evidence if pro else ()),
        processing_warnings=pro.processing_warnings if pro else (),
    )

    missing: list[str] = []
    if empty:
        missing.append("transcript")
    if not pron_facts.available:
        missing.append("pronunciation")
    if not pro_facts.available:
        missing.append("prosody")

    quality = EvidenceQualityRuleFacts(
        transcript_available=not empty,
        pronunciation_available=pron_facts.available,
        prosody_available=pro_facts.available,
        overall_reliability=float(input.evidence_reliability or 0.0),
        partial_processing=bool(missing) and not empty,
        provider_warnings=tuple(input.processing_warnings),
        missing_families=tuple(missing),
    )

    evidence_summary = EvidenceSummaryFacts(
        availability=dict(input.evidence_availability) if input.evidence_availability else {
            "transcript": not empty,
            "pronunciation": pron_facts.available,
            "prosody": pro_facts.available,
        },
        reliability=quality.overall_reliability,
        provider_provenance=input.provider_provenance,
        evidence_reference_ids=input.evidence_reference_ids,
        processing_warnings=input.processing_warnings,
    )

    transcript_facts = TranscriptRuleFacts(
        has_transcript=not empty,
        word_count=wc,
        token_count=len(words),
        is_empty_response=empty,
        task_keyword_overlap_ratio=overlap,
        task_keyword_hits=hits,
    )

    # --- Dimensions (deterministic gates) ---
    task_score = 0.0 if empty else min(1.0, 0.25 + overlap * 0.55 + min(wc, 40) / 100)
    task_status = DimensionEvidenceStatus.not_met if empty else (
        DimensionEvidenceStatus.met if task_score >= 0.65 else DimensionEvidenceStatus.partial if task_score >= 0.35 else DimensionEvidenceStatus.not_met
    )
    task_dim = _dim(
        "task_response",
        status=task_status,
        score=task_score,
        weight=0.18,
        codes=(EV_SEMANTIC_TASK_RESPONSE,) if not empty else ("transcript:empty",),
        confidence=0.7 if not empty else 0.0,
        reason="Deterministic task keyword overlap and response length." if not empty else "No transcript evidence.",
        evidence_ids=input.evidence_reference_ids[:3],
        limitations=("Semantic task fit requires educational analyzer.",) if not empty else ("No spoken response detected.",),
    )

    topic_dim = _dim(
        "topic_understanding",
        status=task_status if not empty else DimensionEvidenceStatus.insufficient_evidence,
        score=task_score * 0.9,
        weight=0.08,
        codes=(EV_TOPIC_DEVELOPMENT,) if not empty else (),
        confidence=0.5,
        reason="Proxy from task overlap until analyzer enriches.",
    )

    pron_score = 0.0
    pron_codes: list[str] = []
    if pron_facts.available:
        error_load = sub_count + om_count + ins_count
        pron_score = max(0.0, min(1.0, 1.0 - error_load * 0.08))
        pron_codes.extend([EV_PHONEME_ALIGNMENT, EV_PRONUNCIATION_CONFIDENCE])
        if pron_tags:
            pron_codes.append(EV_PRONUNCIATION_CONFIDENCE)
    pron_status = (
        DimensionEvidenceStatus.insufficient_evidence
        if not pron_facts.available
        else DimensionEvidenceStatus.met
        if pron_score >= 0.65
        else DimensionEvidenceStatus.partial
        if pron_score >= 0.4
        else DimensionEvidenceStatus.not_met
    )
    pronunciation_dim = _dim(
        "pronunciation",
        status=pron_status,
        score=pron_score,
        weight=0.16,
        codes=tuple(pron_codes),
        confidence=pron_reliability,
        reason=f"S5: {sub_count} substitutions, {om_count} omissions, {len(pron_tags)} issue tags.",
        limitations=("Low pronunciation reliability.",) if pron_reliability < 0.45 else (),
    )

    fluency_score = 0.0
    fluency_codes: list[str] = []
    if pro_facts.available:
        fluency_score = 0.55
        if pause_density is not None:
            fluency_codes.append(EV_PAUSES)
            fluency_score -= min(0.35, pause_density * 0.2)
        if rate_proxy is not None:
            fluency_codes.append(EV_SPEAKING_RATE)
        if pitch_var is not None:
            fluency_codes.append(EV_PITCH)
        if rhythm is not None:
            fluency_codes.append(EV_RHYTHM)
        if energy_var is not None:
            fluency_codes.append(EV_ENERGY_VARIATION)
        if pro_tags:
            fluency_score -= min(0.3, len(pro_tags) * 0.05)
        fluency_score = max(0.0, min(1.0, fluency_score))
    fluency_status = (
        DimensionEvidenceStatus.insufficient_evidence
        if not pro_facts.available
        else DimensionEvidenceStatus.met
        if fluency_score >= 0.6
        else DimensionEvidenceStatus.partial
        if fluency_score >= 0.35
        else DimensionEvidenceStatus.not_met
    )
    fluency_dim = _dim(
        "fluency_delivery",
        status=fluency_status,
        score=fluency_score,
        weight=0.14,
        codes=tuple(fluency_codes),
        confidence=pro_facts.reliability,
        reason=f"S6: pause_density={pause_density}, issues={len(pro_tags)}.",
    )

    grammar_score = 0.0 if empty else (0.35 if agreement_errors else min(1.0, 0.5 + min(wc, 30) / 60))
    grammar_dim = _dim(
        "grammar",
        status=DimensionEvidenceStatus.insufficient_evidence if empty else (
            DimensionEvidenceStatus.not_met if agreement_errors else DimensionEvidenceStatus.partial if grammar_score < 0.65 else DimensionEvidenceStatus.met
        ),
        score=grammar_score,
        weight=0.12,
        codes=(EV_GRAMMAR_CONTROL,) if not empty else (),
        confidence=0.55 if not empty else 0.0,
        reason="Transcript grammar heuristics only.",
        errors=tuple(agreement_errors),
    )

    vocab_score = 0.0 if empty else min(1.0, wc / 25)
    vocab_dim = _dim(
        "vocabulary",
        status=DimensionEvidenceStatus.insufficient_evidence if empty else (
            DimensionEvidenceStatus.met if vocab_score >= 0.65 else DimensionEvidenceStatus.partial
        ),
        score=vocab_score,
        weight=0.1,
        codes=(EV_VOCABULARY_FUNCTION,) if not empty else (),
        confidence=0.5 if not empty else 0.0,
        reason="Token count proxy — analyzer enriches range.",
    )

    coherence_dim = _dim(
        "coherence",
        status=DimensionEvidenceStatus.insufficient_evidence if empty else DimensionEvidenceStatus.partial,
        score=0.45 if wc >= 8 else 0.25 if not empty else 0.0,
        weight=0.08,
        codes=(EV_ORGANIZATION_EVIDENCE,) if wc >= 5 else (),
        confidence=0.4,
        reason="Length-based coherence proxy.",
    )

    interaction_dim = _dim(
        "interaction",
        status=DimensionEvidenceStatus.not_applicable,
        score=0.5,
        weight=0.04,
        codes=(EV_TURN_COMPLETION,) if not empty else (),
        confidence=0.3,
        reason="Single-turn evaluation — limited interaction evidence.",
    )

    goal_dim = _dim(
        "goal_alignment",
        status=DimensionEvidenceStatus.partial if not empty else DimensionEvidenceStatus.insufficient_evidence,
        score=0.5 if not empty else 0.0,
        weight=0.06,
        codes=(EV_RESPONSE_RELEVANCE,) if not empty else (),
        confidence=0.35,
        reason=f"Goal context: {context.goal.goal_label}.",
    )

    official = (context.official_cefr.official_cefr or "B1").upper()[:2]
    cefr_dim = _dim(
        "cefr_validation",
        status=DimensionEvidenceStatus.partial if not empty else DimensionEvidenceStatus.insufficient_evidence,
        score=task_score * 0.7 + grammar_score * 0.3,
        weight=0.04,
        codes=("cefr:observation_only",),
        confidence=0.4,
        reason=f"Official band {official} — observed estimate from analyzer only.",
        limitations=("Official CEFR is never changed by S7.",),
    )

    blockers: list[str] = []
    if empty:
        blockers.append("empty_transcript")
    if task_score < 0.45:
        blockers.append("task_response_insufficient")
    if agreement_errors:
        blockers.append("grammar_agreement_errors")
    if pron_facts.available and pron_score < 0.35:
        blockers.append("pronunciation_evidence_weak")

    ready = not blockers and task_score >= 0.55 and grammar_score >= 0.45
    revision_readiness = RevisionReadinessFacts(ready=ready, blockers=tuple(blockers))

    completion_blockers = list(blockers)
    if task_score < 0.65:
        completion_blockers.append("semantic_task_not_met")
    completion_eligible = not completion_blockers and ready
    completion = CompletionEligibilityFacts(
        eligible=completion_eligible,
        reason="Task response and revision readiness gates passed." if completion_eligible else "Completion blocked by semantic or evidence gates.",
        semantic_task_met=task_score >= 0.65,
        acoustic_only_boost_blocked=task_score < 0.65 and (pron_score >= 0.7 or fluency_score >= 0.7),
    )

    explanation = ExplanationFacts(
        summary="Rule engine evidence summary — educational analyzer enriches this output.",
        priority_issue=blockers[0] if blockers else "continue_practice",
        improvements=tuple(blockers[:4]),
        strengths=("Spoken response captured.",) if not empty else (),
        focus_label="task_response" if task_score < 0.55 else "pronunciation" if pron_score < 0.5 else "fluency_delivery",
    )

    weak: list[str] = []
    strong: list[str] = []
    for dim, label in (
        (task_dim, "task_response"),
        (pronunciation_dim, "pronunciation"),
        (fluency_dim, "fluency_delivery"),
        (grammar_dim, "grammar"),
        (vocab_dim, "vocabulary"),
    ):
        if dim.score < 0.45:
            weak.append(label)
        elif dim.passed:
            strong.append(label)

    overall = (
        task_dim.score * task_dim.weight
        + pronunciation_dim.score * pronunciation_dim.weight
        + fluency_dim.score * fluency_dim.weight
        + grammar_dim.score * grammar_dim.weight
        + vocab_dim.score * vocab_dim.weight
        + coherence_dim.score * coherence_dim.weight
        + goal_dim.score * goal_dim.weight
    ) / max(
        task_dim.weight
        + pronunciation_dim.weight
        + fluency_dim.weight
        + grammar_dim.weight
        + vocab_dim.weight
        + coherence_dim.weight
        + goal_dim.weight,
        0.01,
    )

    return SpeakingRuleEvaluationFacts(
        evaluation_id=context.evaluation_id,
        session_id=context.session_id,
        attempt_id=context.attempt_id,
        revision_number=context.revision_number,
        transcript=transcript_facts,
        pronunciation=pron_facts,
        prosody=pro_facts,
        evidence_quality=quality,
        evidence_summary=evidence_summary,
        task_response=task_dim,
        topic_understanding=topic_dim,
        pronunciation_dimension=pronunciation_dim,
        fluency_delivery=fluency_dim,
        grammar=grammar_dim,
        vocabulary=vocab_dim,
        coherence=coherence_dim,
        interaction=interaction_dim,
        goal_alignment=goal_dim,
        cefr_validation=cefr_dim,
        revision_readiness=revision_readiness,
        completion_eligibility=completion,
        explanation=explanation,
        weak_skills=tuple(weak),
        strong_skills=tuple(strong),
        overall_readiness=overall,
    )
