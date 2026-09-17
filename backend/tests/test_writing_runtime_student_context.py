from types import SimpleNamespace

from app.models.language.enums import LanguageLevel
from app.services.language_progression_service import (
    _analytics_level_if_higher,
    _analytics_overall_if_higher,
    _reconcile_stale_lower_progression_from_analytics,
)
from app.services.language_writing.enums import OfficialWritingCEFR
from app.services.language_writing.enums import WritingGoal
from app.services.language_writing_curriculum.selector import select_writing_curriculum_node
from app.services.language_writing_runtime.student_context import writing_goal_from_preferences


def test_stale_progression_a1_can_be_corrected_from_higher_analytics_level():
    analytics = SimpleNamespace(writing_level=LanguageLevel.B1)

    assert _analytics_level_if_higher(analytics, "writing", LanguageLevel.A1) == LanguageLevel.B1


def test_stale_progression_overall_a1_can_be_corrected_from_higher_analytics_overall():
    analytics = SimpleNamespace(
        overall_level_internal=LanguageLevel.B1,
        reading_level=LanguageLevel.B1,
        listening_level=LanguageLevel.B1,
        writing_level=LanguageLevel.B1,
        speaking_level=LanguageLevel.B1,
    )

    assert _analytics_overall_if_higher(analytics, LanguageLevel.A1) == LanguageLevel.B1


def test_existing_progression_row_reconciles_stale_lower_speaking_from_analytics():
    row = SimpleNamespace(
        official_reading_cefr=LanguageLevel.A1,
        official_listening_cefr=LanguageLevel.A1,
        official_writing_cefr=LanguageLevel.A1,
        official_speaking_cefr=LanguageLevel.A1,
        official_overall_cefr=LanguageLevel.A1,
        version=1,
        updated_at=None,
    )
    analytics = SimpleNamespace(
        reading_level=LanguageLevel.A1,
        listening_level=LanguageLevel.A1,
        writing_level=LanguageLevel.A1,
        speaking_level=LanguageLevel.B2,
        overall_level_internal=LanguageLevel.B1,
    )

    assert _reconcile_stale_lower_progression_from_analytics(row, analytics) is True
    assert row.official_speaking_cefr == LanguageLevel.B2
    assert row.official_reading_cefr == LanguageLevel.A1
    assert row.official_overall_cefr == LanguageLevel.B1
    assert row.version == 2


def test_writing_goal_from_learner_memory_supports_all_writing_specific_goals():
    assert writing_goal_from_preferences({"learning_goals": ["travel"]}) == WritingGoal.travel
    assert writing_goal_from_preferences({"memory": {"learning_goals": ["business"]}}) == WritingGoal.business
    assert (
        writing_goal_from_preferences({"learning_goals": ["daily communication"]})
        == WritingGoal.daily_communication
    )
    assert (
        writing_goal_from_preferences({"learning_goals": ["creative_writing"]})
        == WritingGoal.creative_writing
    )


def test_b1_writing_student_starts_from_b1_curriculum_node_not_a1_entry():
    result = select_writing_curriculum_node(
        goal=WritingGoal.general_english,
        official_cefr=OfficialWritingCEFR.B1,
        completed_node_ids=frozenset(),
        recent_node_ids=frozenset(),
    )

    assert result.node.official_cefr == OfficialWritingCEFR.B1
    assert result.remediation is False


def test_b1_writing_student_with_lower_history_stays_on_b1_curriculum():
    result = select_writing_curriculum_node(
        goal=WritingGoal.general_english,
        official_cefr=OfficialWritingCEFR.B1,
        completed_node_ids=frozenset({"myself", "parents", "siblings", "thank_you_note"}),
        recent_node_ids=frozenset(),
    )

    assert result.node.official_cefr == OfficialWritingCEFR.B1
    assert result.remediation is False
