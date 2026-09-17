from app.models.language.analytics import LanguageAnalytics


def test_language_analytics_maps_xp_columns() -> None:
    analytics = LanguageAnalytics(student_id=1, language_id=1)

    analytics.xp_keys_json = {"k": ["lesson:211"]}
    analytics.xp_total = 30
    analytics.level_xp = 30

    assert analytics.xp_keys_json == {"k": ["lesson:211"]}
    assert analytics.xp_total == 30
    assert analytics.level_xp == 30
