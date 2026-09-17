from app.services.language_grammar.enums import GrammarCandidatePriority, GrammarCEFRBand
from app.services.language_grammar_catalog.catalog import get_default_catalog
from app.services.language_grammar_catalog.cefr_order import cefr_rank
from app.services.language_grammar_progression.engine import compute_progression_snapshot
from app.services.language_grammar_progression.types import GrammarProgressionStudentState


def _snapshot(*, anchor=GrammarCEFRBand.B1, **state_kwargs):
    return compute_progression_snapshot(
        catalog=get_default_catalog(),
        anchor_cefr=anchor,
        student=GrammarProgressionStudentState(student_id=122, language_id=1, **state_kwargs),
    )


def test_b1_student_starts_on_b1_grammar_with_lower_bands_open_for_review():
    catalog = get_default_catalog()
    by_id = {topic.grammar_id: topic for topic in catalog.topics}

    snapshot = _snapshot()

    assert snapshot.current_grammar_id == "gram_present_perfect"
    assert by_id[snapshot.current_grammar_id].cefr_band == GrammarCEFRBand.B1
    assert "gram_be_present" in snapshot.unlocked_ids
    assert "gram_past_simple" in snapshot.unlocked_ids

    priorities = {entry.grammar_id: entry.priority for entry in snapshot.candidate_priorities}
    assert priorities[snapshot.current_grammar_id] == GrammarCandidatePriority.primary
    assert priorities.get("gram_be_present") != GrammarCandidatePriority.primary
    assert all(
        cefr_rank(by_id[entry.grammar_id].cefr_band) >= cefr_rank(GrammarCEFRBand.B1)
        for entry in snapshot.candidate_priorities
        if entry.priority in {GrammarCandidatePriority.primary, GrammarCandidatePriority.secondary}
    )


def test_lower_band_sticky_current_is_ignored_for_b1_student():
    snapshot = _snapshot(
        current_grammar_id="gram_be_present",
        unlocked_ids=frozenset({"gram_be_present"}),
    )

    assert snapshot.current_grammar_id == "gram_present_perfect"


def test_b1_student_advances_to_next_b1_topic_after_current_completion():
    snapshot = _snapshot(completed_ids=frozenset({"gram_present_perfect"}))

    assert snapshot.current_grammar_id == "gram_present_perfect_continuous"
    assert snapshot.next_grammar_id in {"gram_first_conditional", "gram_reported_speech_light"}
