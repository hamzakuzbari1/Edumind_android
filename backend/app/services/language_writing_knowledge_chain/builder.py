"""Chain builder helpers for Topic Universe catalog (W1.2)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.services.language_writing.enums import (
    ChainTopology,
    ContextComplexity,
    ExpectedWritingOutput,
    LexisCategory,
    OfficialWritingCEFR,
    WritingArc,
    WritingGoal,
    WritingTopicId,
)
from app.services.language_writing_knowledge_chain.metadata_enrichment import enrich_node_pedagogy
from app.services.language_writing_knowledge_chain.types import (
    FutureBranchPoint,
    WritingKnowledgeChain,
    WritingKnowledgeChainNode,
    WritingTimeEstimate,
)

# Base drafting minutes by CEFR; complexity adds pressure.
_WRITING_BASE_MINUTES: dict[OfficialWritingCEFR, int] = {
    OfficialWritingCEFR.A1: 8,
    OfficialWritingCEFR.A2: 10,
    OfficialWritingCEFR.B1: 12,
    OfficialWritingCEFR.B2: 15,
    OfficialWritingCEFR.C1: 18,
    OfficialWritingCEFR.C2: 22,
}

_GENRE_TO_OUTPUT: dict[str, ExpectedWritingOutput] = {
    "paragraph": ExpectedWritingOutput.paragraph,
    "short_note": ExpectedWritingOutput.message,
    "message": ExpectedWritingOutput.message,
    "email_short": ExpectedWritingOutput.email,
    "short_email": ExpectedWritingOutput.email,
    "formal_email": ExpectedWritingOutput.email,
    "business_email": ExpectedWritingOutput.email,
    "narrative": ExpectedWritingOutput.story,
    "story": ExpectedWritingOutput.story,
    "dialogue_paragraph": ExpectedWritingOutput.dialogue,
    "review": ExpectedWritingOutput.review,
    "essay": ExpectedWritingOutput.essay,
    "essay_outline": ExpectedWritingOutput.essay,
    "academic_paragraph": ExpectedWritingOutput.essay,
    "report": ExpectedWritingOutput.report,
    "memo": ExpectedWritingOutput.report,
    "proposal": ExpectedWritingOutput.report,
    "executive_summary": ExpectedWritingOutput.summary,
    "summary": ExpectedWritingOutput.summary,
    "article": ExpectedWritingOutput.article,
    "list": ExpectedWritingOutput.paragraph,
}


@dataclass(frozen=True, slots=True)
class _NodeSpec:
    node_id: str
    label: str
    narrative_why: str
    official_cefr: OfficialWritingCEFR
    arc_stage: WritingArc
    context_complexity: ContextComplexity
    vocabulary_primary: tuple[str, ...]
    vocabulary_secondary: tuple[str, ...]
    vocabulary_review: tuple[str, ...]
    vocabulary_categories: tuple[LexisCategory, ...]
    grammar_focus_primary: str
    grammar_focus_secondary: str
    grammar_focus_review: str
    suggested_goals: tuple[WritingGoal, ...]
    learning_objectives: tuple[str, ...]
    carry_forward_template: str
    task_type: str
    genre: str
    expected_output: ExpectedWritingOutput | None
    writing_minutes: int | None
    revision_minutes: int | None
    learning_outcomes: tuple[str, ...] = ()
    common_mistakes: tuple[str, ...] = ()
    difficulty_drivers: tuple[str, ...] = ()
    prerequisite_skills: tuple[str, ...] = ()
    review_node_ids: tuple[str, ...] = ()
    future_node_ids: tuple[str, ...] = ()


def estimate_time(
    *,
    cefr: OfficialWritingCEFR,
    complexity: ContextComplexity,
    arc: WritingArc,
) -> WritingTimeEstimate:
    base = _WRITING_BASE_MINUTES[cefr]
    cx = int(complexity)
    writing = base + max(0, cx - 1) * 2
    if arc in (WritingArc.academic_writing, WritingArc.professional_writing):
        writing += 3
    revision = max(5, int(writing * 0.45) + max(0, cx - 2))
    return WritingTimeEstimate(writing_minutes=writing, revision_minutes=revision, total_minutes=writing + revision)


def expected_output_for_genre(genre: str) -> ExpectedWritingOutput:
    return _GENRE_TO_OUTPUT.get(genre, ExpectedWritingOutput.paragraph)


def _split_vocabulary(seeds: tuple[str, ...], grammar_secondary: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not seeds:
        return (), ()
    if len(seeds) == 1:
        return seeds, ()
    primary = seeds[: max(1, len(seeds) // 2 + len(seeds) % 2)]
    secondary = seeds[len(primary) :]
    if grammar_secondary and grammar_secondary not in primary and grammar_secondary not in secondary:
        secondary = secondary + (grammar_secondary.replace("_", " "),)
    return primary, secondary


def _enrich_specs(specs: tuple[_NodeSpec, ...]) -> tuple[_NodeSpec, ...]:
    enriched: list[_NodeSpec] = []
    prev_primary_grammar = ""
    prev_vocab: tuple[str, ...] = ()

    for spec in specs:
        primary, secondary = spec.vocabulary_primary, spec.vocabulary_secondary
        if not primary and not secondary:
            primary, secondary = (), ()

        grammar_review = spec.grammar_focus_review or prev_primary_grammar
        vocab_review = spec.vocabulary_review or prev_vocab

        time = (
            WritingTimeEstimate(
                writing_minutes=spec.writing_minutes,
                revision_minutes=spec.revision_minutes,
                total_minutes=spec.writing_minutes + spec.revision_minutes,
            )
            if spec.writing_minutes is not None and spec.revision_minutes is not None
            else estimate_time(cefr=spec.official_cefr, complexity=spec.context_complexity, arc=spec.arc_stage)
        )
        output = spec.expected_output or expected_output_for_genre(spec.genre)

        enriched.append(
            replace(
                spec,
                vocabulary_primary=primary,
                vocabulary_secondary=secondary,
                vocabulary_review=vocab_review,
                grammar_focus_review=grammar_review,
                expected_output=output,
                writing_minutes=time.writing_minutes,
                revision_minutes=time.revision_minutes,
            )
        )
        prev_primary_grammar = spec.grammar_focus_primary
        prev_vocab = primary + secondary

    return tuple(enriched)


def build_linear_chain(
    *,
    chain_id: str,
    topic_id: WritingTopicId,
    label: str,
    description: str,
    primary_arc: WritingArc,
    node_specs: tuple[_NodeSpec, ...],
    topology: ChainTopology = ChainTopology.linear,
    documented_future_branches: tuple[FutureBranchPoint, ...] = (),
) -> WritingKnowledgeChain:
    """Build a linear chain with enriched metadata (v1.2)."""
    specs = _enrich_specs(node_specs)
    nodes: list[WritingKnowledgeChainNode] = []
    id_list = [s.node_id for s in specs]
    prev_label: str | None = None

    for i, spec in enumerate(specs):
        prev_ids = (id_list[i - 1],) if i > 0 else ()
        next_ids = (id_list[i + 1],) if i < len(specs) - 1 else ()
        time = WritingTimeEstimate(
            writing_minutes=spec.writing_minutes or 0,
            revision_minutes=spec.revision_minutes or 0,
            total_minutes=(spec.writing_minutes or 0) + (spec.revision_minutes or 0),
        )
        raw = WritingKnowledgeChainNode(
            chain_id=chain_id,
            node_id=spec.node_id,
            topic_id=topic_id,
            label=spec.label,
            narrative_why=spec.narrative_why,
            official_cefr=spec.official_cefr,
            arc_stage=spec.arc_stage,
            context_complexity=spec.context_complexity,
            position=i + 1,
            previous_node_ids=prev_ids,
            next_node_ids=next_ids,
            review_node_ids=spec.review_node_ids,
            future_node_ids=spec.future_node_ids,
            grammar_focus_primary=spec.grammar_focus_primary,
            grammar_focus_secondary=spec.grammar_focus_secondary,
            grammar_focus_review=spec.grammar_focus_review,
            vocabulary_primary=spec.vocabulary_primary,
            vocabulary_secondary=spec.vocabulary_secondary,
            vocabulary_review=spec.vocabulary_review,
            vocabulary_categories=spec.vocabulary_categories,
            time_estimate=time,
            expected_output=spec.expected_output or ExpectedWritingOutput.paragraph,
            suggested_goals=spec.suggested_goals,
            learning_objectives=spec.learning_objectives,
            carry_forward_template=spec.carry_forward_template,
            task_type=spec.task_type,
            genre=spec.genre,
        )
        nodes.append(
            enrich_node_pedagogy(
                raw,
                previous_label=prev_label,
                learning_outcomes=spec.learning_outcomes,
                common_mistakes=spec.common_mistakes,
                difficulty_drivers=spec.difficulty_drivers,
                prerequisite_skills=spec.prerequisite_skills,
            )
        )
        prev_label = spec.label

    return WritingKnowledgeChain(
        chain_id=chain_id,
        topic_id=topic_id,
        label=label,
        description=description,
        primary_arc=primary_arc,
        nodes=tuple(nodes),
        topology=topology,
        documented_future_branches=documented_future_branches,
    )


def N(  # noqa: N802 — compact catalog DSL
    node_id: str,
    label: str,
    why: str,
    *,
    cefr: OfficialWritingCEFR,
    arc: WritingArc,
    complexity: ContextComplexity,
    goals: tuple[WritingGoal, ...],
    objectives: tuple[str, ...],
    grammar: str,
    grammar2: str = "",
    grammar_review: str = "",
    vocab_cats: tuple[LexisCategory, ...] = (LexisCategory.core, LexisCategory.topic),
    seeds: tuple[str, ...] = (),
    vocab_primary: tuple[str, ...] = (),
    vocab_secondary: tuple[str, ...] = (),
    vocab_review: tuple[str, ...] = (),
    task: str = "describe",
    genre: str = "paragraph",
    expected: ExpectedWritingOutput | None = None,
    carry: str = "",
    review: tuple[str, ...] = (),
    future: tuple[str, ...] = (),
    writing_min: int | None = None,
    revision_min: int | None = None,
    outcomes: tuple[str, ...] = (),
    mistakes: tuple[str, ...] = (),
    drivers: tuple[str, ...] = (),
    prerequisites: tuple[str, ...] = (),
) -> _NodeSpec:
    if vocab_primary or vocab_secondary:
        primary, secondary = vocab_primary, vocab_secondary
    else:
        primary, secondary = _split_vocabulary(seeds, grammar2)

    return _NodeSpec(
        node_id=node_id,
        label=label,
        narrative_why=why,
        official_cefr=cefr,
        arc_stage=arc,
        context_complexity=complexity,
        vocabulary_primary=primary,
        vocabulary_secondary=secondary,
        vocabulary_review=vocab_review,
        vocabulary_categories=vocab_cats,
        grammar_focus_primary=grammar,
        grammar_focus_secondary=grammar2,
        grammar_focus_review=grammar_review,
        suggested_goals=goals,
        learning_objectives=objectives,
        learning_outcomes=outcomes,
        common_mistakes=mistakes,
        difficulty_drivers=drivers,
        prerequisite_skills=prerequisites,
        carry_forward_template=carry,
        task_type=task,
        genre=genre,
        expected_output=expected,
        writing_minutes=writing_min,
        revision_minutes=revision_min,
        review_node_ids=review,
        future_node_ids=future,
    )
