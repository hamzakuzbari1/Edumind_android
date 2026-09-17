"""Catalog builder helpers — assemble GrammarTopic rows and derive DAG forward edges."""

from __future__ import annotations

from app.services.language_grammar.enums import GrammarCEFRBand, GrammarReinforcementSkill
from app.services.language_grammar.id_canon import (
    assert_canonical_grammar_id,
    assert_grammar_display_code,
)
from app.services.language_grammar_catalog.types import (
    GrammarEvidenceRequirements,
    GrammarTopic,
)

R = GrammarReinforcementSkill


def topic(
    grammar_id: str,
    *,
    display_name: str,
    cefr_band: GrammarCEFRBand,
    introduction_order: int,
    prerequisite_ids: tuple[str, ...] = (),
    learning_objectives: tuple[str, ...] = (),
    demonstration_patterns: tuple[str, ...] = (),
    example_sentences: tuple[str, ...] = (),
    common_errors: tuple[str, ...] = (),
    best_reinforcement_skills: tuple[GrammarReinforcementSkill, ...] = (),
    recommended_contexts: tuple[str, ...] = (),
    minimum_context_diversity: int = 2,
    evidence_requirements: GrammarEvidenceRequirements | None = None,
    mastery_threshold: float = 80.0,
    review_priority: int = 3,
    review_half_life_days: float = 14.0,
    focus_note: str = "",
    display_code: str = "",
    estimated_duration_minutes: int = 25,
    difficulty: str = "guided",
    teaching_notes: str = "",
) -> GrammarTopic:
    """Construct a catalog topic (future_topic_ids filled by derive_future_edges)."""
    gid = assert_canonical_grammar_id(grammar_id)
    prereqs = tuple(dict.fromkeys(assert_canonical_grammar_id(p) for p in prerequisite_ids))
    skills = tuple(dict.fromkeys(best_reinforcement_skills))
    code = assert_grammar_display_code(display_code) if (display_code or "").strip() else ""
    return GrammarTopic(
        grammar_id=gid,
        display_name=display_name.strip(),
        cefr_band=cefr_band,
        introduction_order=int(introduction_order),
        prerequisite_ids=prereqs,
        future_topic_ids=(),
        learning_objectives=tuple(o.strip() for o in learning_objectives if o.strip()),
        demonstration_patterns=tuple(p for p in demonstration_patterns if str(p).strip()),
        example_sentences=tuple(s.strip() for s in example_sentences if s.strip()),
        common_errors=tuple(e.strip() for e in common_errors if e.strip()),
        best_reinforcement_skills=skills,
        recommended_contexts=tuple(c.strip() for c in recommended_contexts if c.strip()),
        minimum_context_diversity=max(1, int(minimum_context_diversity)),
        evidence_requirements=evidence_requirements or GrammarEvidenceRequirements(),
        mastery_threshold=float(mastery_threshold),
        review_priority=max(1, min(5, int(review_priority))),
        review_half_life_days=float(review_half_life_days),
        focus_note=focus_note.strip(),
        display_code=code,
        estimated_duration_minutes=max(1, int(estimated_duration_minutes)),
        difficulty=(difficulty or "guided").strip().lower(),
        teaching_notes=teaching_notes.strip(),
    )


def derive_future_edges(topics: tuple[GrammarTopic, ...]) -> tuple[GrammarTopic, ...]:
    """Derive future_topic_ids as the reverse of prerequisite edges (single source of edges)."""
    forward: dict[str, list[str]] = {t.grammar_id: [] for t in topics}
    for t in topics:
        for prereq in t.prerequisite_ids:
            if prereq in forward:
                forward[prereq].append(t.grammar_id)
    rebuilt: list[GrammarTopic] = []
    for t in topics:
        futures = tuple(dict.fromkeys(forward.get(t.grammar_id, ())))
        rebuilt.append(
            GrammarTopic(
                grammar_id=t.grammar_id,
                display_name=t.display_name,
                cefr_band=t.cefr_band,
                introduction_order=t.introduction_order,
                prerequisite_ids=t.prerequisite_ids,
                future_topic_ids=futures,
                learning_objectives=t.learning_objectives,
                demonstration_patterns=t.demonstration_patterns,
                example_sentences=t.example_sentences,
                common_errors=t.common_errors,
                best_reinforcement_skills=t.best_reinforcement_skills,
                recommended_contexts=t.recommended_contexts,
                minimum_context_diversity=t.minimum_context_diversity,
                evidence_requirements=t.evidence_requirements,
                mastery_threshold=t.mastery_threshold,
                review_priority=t.review_priority,
                review_half_life_days=t.review_half_life_days,
                focus_note=t.focus_note,
                display_code=t.display_code,
                estimated_duration_minutes=t.estimated_duration_minutes,
                difficulty=t.difficulty,
                teaching_notes=t.teaching_notes,
            )
        )
    return tuple(rebuilt)


def ev(
    *,
    min_observations: int = 3,
    min_distinct_contexts: int = 2,
    min_skills_covered: int = 1,
) -> GrammarEvidenceRequirements:
    return GrammarEvidenceRequirements(
        min_observations=min_observations,
        min_distinct_contexts=min_distinct_contexts,
        min_skills_covered=min_skills_covered,
    )
