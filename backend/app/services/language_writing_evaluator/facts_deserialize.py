"""Reconstruct canonical evaluation result from persistence dict."""

from __future__ import annotations

from app.services.language_writing_educational_analyzer.types import (
    ClaudeEducationalFacts,
    CoachGuidance,
    DimensionInsight,
    GrammarNote,
    VocabularyInsight,
)
from app.services.language_writing_evaluator.evaluation_facts_types import (
    CriterionStatus,
    DimensionResult,
    SuccessCriterionStatus,
    WritingEvaluationFacts,
)
from app.services.language_writing_evaluator.evaluation_result import (
    CEFRValidationFacts,
    CompletionFacts,
    DimensionFacts,
    ExplanationFacts,
    RevisionReadinessFacts,
    WritingEvaluationEngineResult,
)
from app.services.language_writing_revision.comparison import (
    ComparisonChange,
    DimensionComparison,
    RevisionComparisonResult,
)


def _dim_from_raw(raw: object, *, default_name: str = "") -> DimensionFacts:
    if not isinstance(raw, dict):
        return DimensionFacts(default_name, 0.0, 0.0, False, ())
    return DimensionFacts(
        dimension=str(raw.get("dimension") or default_name),
        score=float(raw.get("score") or 0),
        weight=float(raw.get("weight") or 0),
        passed=bool(raw.get("passed")),
        evidence_codes=tuple(raw.get("evidence_codes") or ()),
        errors=tuple(raw.get("errors") or ()),
    )


def _criteria(raw_list: object) -> tuple[SuccessCriterionStatus, ...]:
    if not isinstance(raw_list, list):
        return ()
    out: list[SuccessCriterionStatus] = []
    for item in raw_list:
        if isinstance(item, dict):
            out.append(
                SuccessCriterionStatus(
                    label=str(item.get("label") or ""),
                    status=CriterionStatus(str(item.get("status") or CriterionStatus.not_met.value)),
                    code=str(item.get("code") or ""),
                )
            )
    return tuple(out)


def _comparison_from_raw(raw: object) -> RevisionComparisonResult | None:
    if not isinstance(raw, dict):
        return None
    dims: list[DimensionComparison] = []
    for d in raw.get("dimensions") or []:
        if isinstance(d, dict):
            dims.append(
                DimensionComparison(
                    dimension=str(d.get("dimension") or ""),
                    change=ComparisonChange(str(d.get("change") or ComparisonChange.unchanged.value)),
                    before_score=float(d.get("before_score") or 0),
                    after_score=float(d.get("after_score") or 0),
                )
            )
    return RevisionComparisonResult(
        from_revision=int(raw.get("from_revision") or 0),
        to_revision=int(raw.get("to_revision") or 0),
        dimensions=tuple(dims),
        improved=tuple(raw.get("improved") or ()),
        unchanged=tuple(raw.get("unchanged") or ()),
        regressed=tuple(raw.get("regressed") or ()),
        improvement_summary=str(raw.get("improvement_summary") or ""),
        remaining_issues=tuple(raw.get("remaining_issues") or ()),
        comparison_version=str(raw.get("comparison_version") or "7.0.0"),
    )


def _claude_from_raw(raw: object) -> ClaudeEducationalFacts | None:
    if not isinstance(raw, dict) or not raw.get("available"):
        return None

    def _insight(key: str) -> DimensionInsight:
        block = raw.get(key) or {}
        if not isinstance(block, dict):
            return DimensionInsight(0.0, "")
        return DimensionInsight(score=float(block.get("score") or 0), reason=str(block.get("reason") or ""))

    def _tuple(key: str, block: dict[str, object] | None = None) -> tuple[str, ...]:
        source = block if block is not None else raw
        value = source.get(key) if isinstance(source, dict) else None
        if not isinstance(value, list):
            return ()
        return tuple(str(v).strip() for v in value if str(v).strip())

    def _vocabulary() -> VocabularyInsight:
        block = raw.get("vocabulary") or {}
        if not isinstance(block, dict):
            return VocabularyInsight(0.0, "")
        return VocabularyInsight(
            score=float(block.get("score") or 0),
            reason=str(block.get("reason") or ""),
            range_comment=str(block.get("range_comment") or ""),
            repeated_words=_tuple("repeated_words", block),
            weak_choices=_tuple("weak_choices", block),
            missing_topic_words=_tuple("missing_topic_words", block),
            suggestions=_tuple("suggestions", block),
        )

    def _grammar_notes() -> tuple[GrammarNote, ...]:
        value = raw.get("grammar_notes")
        if not isinstance(value, list):
            return ()
        notes: list[GrammarNote] = []
        for item in value:
            if isinstance(item, dict) and str(item.get("issue") or "").strip():
                notes.append(
                    GrammarNote(
                        issue=str(item.get("issue") or "").strip(),
                        rule=str(item.get("rule") or "").strip(),
                        fix=str(item.get("fix") or "").strip(),
                        example=str(item.get("example") or "").strip(),
                    )
                )
        return tuple(notes)

    def _coach_guidance() -> CoachGuidance:
        block = raw.get("coach_guidance")
        if not isinstance(block, dict) or not block.get("available"):
            return CoachGuidance()
        return CoachGuidance(
            main_issue=str(block.get("main_issue") or ""),
            why_this_is_the_priority=str(block.get("why_this_is_the_priority") or ""),
            revision_mission=str(block.get("revision_mission") or ""),
            student_friendly_explanation=str(block.get("student_friendly_explanation") or ""),
            before_example=str(block.get("before_example") or ""),
            after_example=str(block.get("after_example") or ""),
            encouragement=str(block.get("encouragement") or ""),
            available=True,
        )

    return ClaudeEducationalFacts(
        task_response=_insight("task_response"),
        coherence=_insight("coherence"),
        organization=_insight("organization"),
        topic_understanding=_insight("topic_understanding"),
        idea_development=_insight("idea_development"),
        goal_alignment=_insight("goal_alignment"),
        vocabulary=_vocabulary(),
        grammar_notes=_grammar_notes(),
        cefr_estimate=str(raw.get("cefr_estimate") or ""),
        cefr_reason=str(raw.get("cefr_reason") or ""),
        progress_comparison=str(raw.get("progress_comparison") or ""),
        learning_diagnosis=str(raw.get("learning_diagnosis") or ""),
        revision_priority=str(raw.get("revision_priority") or ""),
        encouragement=str(raw.get("encouragement") or ""),
        strengths=_tuple("strengths"),
        coach_guidance=_coach_guidance(),
        major_learning_issue=str(raw.get("major_learning_issue") or ""),
        available=True,
        analyzer_version=str(raw.get("analyzer_version") or "1.0.0"),
        model_name=str(raw.get("model_name") or ""),
        source=str(raw.get("source") or "claude"),
    )


def evaluation_result_from_dict(data: dict[str, object]) -> WritingEvaluationEngineResult | None:
    try:
        if data.get("engine_version") or data.get("grammar"):
            cefr_raw = data.get("cefr_validation") or {}
            expl_raw = data.get("explanation") or {}
            ready_raw = data.get("revision_readiness") or {}
            comp_raw = data.get("completion") or {}
            return WritingEvaluationEngineResult(
                draft_id=str(data.get("draft_id") or ""),
                revision_number=int(data.get("revision_number") or 0),
                chain_node_id=str(data.get("chain_node_id") or ""),
                blueprint_version=str(data.get("blueprint_version") or ""),
                blueprint_hash=str(data.get("blueprint_hash") or ""),
                generation_hash=str(data.get("generation_hash") or ""),
                word_count=int(data.get("word_count") or 0),
                meets_word_limit=bool(data.get("meets_word_limit")),
                grammar=_dim_from_raw(data.get("grammar") or data.get("grammar_result"), default_name="grammar"),
                vocabulary=_dim_from_raw(
                    data.get("vocabulary") or data.get("vocabulary_result"), default_name="vocabulary"
                ),
                organization=_dim_from_raw(
                    data.get("organization") or data.get("organization_result"), default_name="organization"
                ),
                task_completion=_dim_from_raw(
                    data.get("task_completion") or data.get("task_completion_result"), default_name="task_completion"
                ),
                goal_alignment=_dim_from_raw(
                    data.get("goal_alignment") or data.get("goal_alignment_result"), default_name="goal_alignment"
                ),
                cefr_validation=CEFRValidationFacts(
                    expected_band=str(cefr_raw.get("expected_band") or "B1") if isinstance(cefr_raw, dict) else "B1",
                    status=CriterionStatus(
                        str(cefr_raw.get("status") or CriterionStatus.not_met.value)
                    )
                    if isinstance(cefr_raw, dict)
                    else CriterionStatus.not_met,
                    notes=tuple(cefr_raw.get("notes") or ()) if isinstance(cefr_raw, dict) else (),
                ),
                success_criteria=_criteria(data.get("success_criteria") or data.get("success_criteria_status")),
                learning_outcomes=_criteria(data.get("learning_outcomes") or data.get("learning_outcomes_status")),
                revision_readiness=RevisionReadinessFacts(
                    ready=bool(ready_raw.get("ready") if isinstance(ready_raw, dict) else data.get("ready_to_complete")),
                    blockers=tuple(ready_raw.get("blockers") or ()) if isinstance(ready_raw, dict) else (),
                ),
                completion=CompletionFacts(
                    eligible=bool(comp_raw.get("eligible") if isinstance(comp_raw, dict) else data.get("ready_to_complete")),
                    reason=str(comp_raw.get("reason") or "") if isinstance(comp_raw, dict) else "",
                    criteria_met_count=int(comp_raw.get("criteria_met_count") or 0) if isinstance(comp_raw, dict) else 0,
                    criteria_total=int(comp_raw.get("criteria_total") or 0) if isinstance(comp_raw, dict) else 0,
                    outcomes_met_count=int(comp_raw.get("outcomes_met_count") or 0) if isinstance(comp_raw, dict) else 0,
                    outcomes_total=int(comp_raw.get("outcomes_total") or 0) if isinstance(comp_raw, dict) else 0,
                ),
                comparison=_comparison_from_raw(data.get("comparison")),
                explanation=ExplanationFacts(
                    summary=str(expl_raw.get("summary") or "") if isinstance(expl_raw, dict) else "",
                    priority_issue=str(expl_raw.get("priority_issue") or "") if isinstance(expl_raw, dict) else "",
                    improvements=tuple(expl_raw.get("improvements") or ()) if isinstance(expl_raw, dict) else (),
                    strengths=tuple(expl_raw.get("strengths") or ()) if isinstance(expl_raw, dict) else (),
                    focus_label=str(expl_raw.get("focus_label") or "") if isinstance(expl_raw, dict) else "",
                ),
                confidence=float(data.get("confidence") or data.get("overall_readiness") or 0),
                weak_skills=tuple(data.get("weak_skills") or data.get("weaknesses") or ()),
                strong_skills=tuple(data.get("strong_skills") or data.get("strengths") or ()),
                critical_mistakes=tuple(data.get("critical_mistakes") or ()),
            overall_readiness=float(data.get("overall_readiness") or 0),
            claude_analysis=_claude_from_raw(data.get("claude_analysis")),
            engine_version=str(data.get("engine_version") or data.get("evaluator_version") or "8.1.0"),
        )
    except (TypeError, ValueError):
        pass
    return _legacy_result_from_facts_dict(data)


def _legacy_result_from_facts_dict(data: dict[str, object]) -> WritingEvaluationEngineResult | None:
    legacy = _legacy_facts_from_dict(data)
    if legacy is None:
        return None
    return WritingEvaluationEngineResult(
        draft_id=legacy.draft_id,
        revision_number=legacy.revision_number,
        chain_node_id="",
        blueprint_version=legacy.blueprint_version,
        blueprint_hash=legacy.blueprint_hash,
        generation_hash=legacy.generation_hash,
        word_count=legacy.word_count,
        meets_word_limit=legacy.meets_word_limit,
        grammar=DimensionFacts(
            legacy.grammar_result.dimension,
            legacy.grammar_result.score,
            legacy.grammar_result.weight,
            legacy.grammar_result.passed,
            legacy.grammar_result.evidence_codes,
        ),
        vocabulary=DimensionFacts(
            legacy.vocabulary_result.dimension,
            legacy.vocabulary_result.score,
            legacy.vocabulary_result.weight,
            legacy.vocabulary_result.passed,
            legacy.vocabulary_result.evidence_codes,
        ),
        organization=DimensionFacts(
            legacy.organization_result.dimension,
            legacy.organization_result.score,
            legacy.organization_result.weight,
            legacy.organization_result.passed,
            legacy.organization_result.evidence_codes,
        ),
        task_completion=DimensionFacts(
            legacy.task_completion_result.dimension,
            legacy.task_completion_result.score,
            legacy.task_completion_result.weight,
            legacy.task_completion_result.passed,
            legacy.task_completion_result.evidence_codes,
        ),
        goal_alignment=DimensionFacts(
            legacy.goal_alignment_result.dimension,
            legacy.goal_alignment_result.score,
            legacy.goal_alignment_result.weight,
            legacy.goal_alignment_result.passed,
            legacy.goal_alignment_result.evidence_codes,
        ),
        cefr_validation=CEFRValidationFacts("B1", CriterionStatus.partial, ()),
        success_criteria=legacy.success_criteria_status,
        learning_outcomes=legacy.learning_outcomes_status,
        revision_readiness=RevisionReadinessFacts(ready=legacy.ready_to_complete, blockers=()),
        completion=CompletionFacts(
            eligible=legacy.ready_to_complete,
            reason="",
            criteria_met_count=sum(1 for c in legacy.success_criteria_status if c.status == CriterionStatus.met),
            criteria_total=len(legacy.success_criteria_status),
            outcomes_met_count=sum(1 for o in legacy.learning_outcomes_status if o.status == CriterionStatus.met),
            outcomes_total=len(legacy.learning_outcomes_status),
        ),
        comparison=None,
        explanation=ExplanationFacts("", "", (), (), ""),
        confidence=legacy.overall_readiness,
        weak_skills=legacy.weaknesses,
        strong_skills=legacy.strengths,
        critical_mistakes=legacy.critical_mistakes,
        overall_readiness=legacy.overall_readiness,
        claude_analysis=None,
    )


def evaluation_facts_from_dict(data: dict[str, object]) -> WritingEvaluationFacts | None:
    result = evaluation_result_from_dict(data)
    if result is not None:
        return result.to_evaluation_facts()
    return _legacy_facts_from_dict(data)


def _legacy_facts_from_dict(data: dict[str, object]) -> WritingEvaluationFacts | None:
    try:

        def _dim(raw: dict[str, object]) -> DimensionResult:
            return DimensionResult(
                dimension=str(raw.get("dimension") or ""),
                score=float(raw.get("score") or 0),
                weight=float(raw.get("weight") or 0),
                passed=bool(raw.get("passed")),
                evidence_codes=tuple(raw.get("evidence_codes") or ()),
            )

        def _criteria_list(raw_list: object) -> tuple[SuccessCriterionStatus, ...]:
            return _criteria(raw_list)

        return WritingEvaluationFacts(
            draft_id=str(data.get("draft_id") or ""),
            revision_number=int(data.get("revision_number") or 0),
            blueprint_version=str(data.get("blueprint_version") or ""),
            blueprint_hash=str(data.get("blueprint_hash") or ""),
            generation_hash=str(data.get("generation_hash") or ""),
            grammar_result=_dim(data.get("grammar_result") or {}),
            vocabulary_result=_dim(data.get("vocabulary_result") or {}),
            organization_result=_dim(data.get("organization_result") or {}),
            task_completion_result=_dim(data.get("task_completion_result") or {}),
            goal_alignment_result=_dim(data.get("goal_alignment_result") or {}),
            word_count=int(data.get("word_count") or 0),
            meets_word_limit=bool(data.get("meets_word_limit")),
            critical_mistakes=tuple(data.get("critical_mistakes") or ()),
            strengths=tuple(data.get("strengths") or ()),
            weaknesses=tuple(data.get("weaknesses") or ()),
            success_criteria_status=_criteria_list(data.get("success_criteria_status")),
            learning_outcomes_status=_criteria_list(data.get("learning_outcomes_status")),
            overall_readiness=float(data.get("overall_readiness") or 0),
            ready_to_complete=bool(data.get("ready_to_complete")),
        )
    except (TypeError, ValueError):
        return None
