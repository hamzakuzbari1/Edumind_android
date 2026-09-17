"""Verify Phase 2.3 — Lesson Experience Builder + Journey Builder + Render-Only Frontend.

Usage (from backend/):
    python scripts/verify_language_adaptive_learning_phase_2_3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
FRONTEND = REPO / "src"

LESSON_ALLOWED_TOP = frozenset(
    {
        "lesson_id",
        "lifecycle_state",
        "official_level",
        "lesson_level",
        "level_note",
        "lesson_title",
        "lesson_type",
        "situation",
        "lesson_goal",
        "narrative",
        "playback",
        "after_lesson",
        "meta",
    }
)
LESSON_NARRATIVE_KEYS = frozenset(
    {
        "reason_selected",
        "why_this_lesson",
        "student_focus",
        "expected_improvement",
        "challenge_reason",
        "reward",
        "next_after_this",
        "coach_summary",
    }
)
JOURNEY_ALLOWED_TOP = frozenset(
    {
        "official_level",
        "journey_target",
        "personal_goal",
        "narrative",
        "promotion",
        "active_lesson",
        "meta",
    }
)
JOURNEY_NARRATIVE_KEYS = frozenset(
    {
        "journey_headline",
        "current_step_label",
        "promotion_progress_message",
        "unlock_checklist",
        "timeline_steps",
        "history_events",
    }
)
FORBIDDEN_LESSON_KEYS = frozenset(
    {
        "journey",
        "promotion",
        "history",
        "personal_goal",
        "journey_target",
        "timeline_steps",
        "unlock_checklist",
        "history_events",
        "coach",
        "body_json",
        "transcript",
        "goal",
        "learning_goal",
        "target_goal",
    }
)
COACH_IMPORT_PATTERNS = (
    "useListeningCoach",
    "coachJourneySentence",
    "coachLessonMissionFocus",
    "coachTimelineSteps",
    "coachBlockedChecklist",
)
FORBIDDEN_FRONTEND_COPY_PATTERNS = (
    "coachJourneySentence",
    "coachLessonWhyReason",
    "coachPostLessonSummary",
    "coachTimelineHistory",
)


def test_lesson_bundle_schema_contract() -> dict[str, object]:
    from app.schemas.language_listening_bundles import (
        LESSON_BUNDLE_FORBIDDEN_KEYS,
        LessonExperienceBundleOut,
        LessonExperienceMetaOut,
        LessonNarrativeOut,
        LessonPlaybackOut,
    )

    sample = LessonExperienceBundleOut(
        lesson_id=1,
        lifecycle_state="reserved",
        official_level="A2",
        lesson_level="A2",
        lesson_title="Test",
        lesson_goal={"id": "general_english", "label": "General English"},
        narrative=LessonNarrativeOut(reason_selected="Because practice."),
        playback=LessonPlaybackOut(instructions="Listen."),
        meta=LessonExperienceMetaOut(),
    )
    dumped = sample.model_dump()
    extra_top = set(dumped) - LESSON_ALLOWED_TOP
    missing_top = LESSON_ALLOWED_TOP - set(dumped)
    narrative_keys = set(dumped["narrative"]) - LESSON_NARRATIVE_KEYS
    forbidden_present = FORBIDDEN_LESSON_KEYS & set(dumped)
    extra_forbidden = set(LESSON_BUNDLE_FORBIDDEN_KEYS) - FORBIDDEN_LESSON_KEYS

    rejects_forbidden = False
    try:
        LessonExperienceBundleOut.model_validate({**dumped, "coach": {}})
    except Exception:
        rejects_forbidden = True

    return {
        "sample_valid": True,
        "extra_top_level": sorted(extra_top),
        "missing_top_level": sorted(missing_top),
        "extra_narrative_keys": sorted(narrative_keys),
        "forbidden_in_sample": sorted(forbidden_present),
        "schema_forbidden_synced": not extra_forbidden,
        "rejects_coach_field": rejects_forbidden,
    }


def test_journey_bundle_schema_contract() -> dict[str, object]:
    from app.schemas.language_listening_bundles import ListeningJourneyBundleOut

    sample = ListeningJourneyBundleOut(
        official_level="A2",
        journey_target={"level": "B1", "label": "Unlock B1"},
        personal_goal={"id": "conversation", "label": "Conversation"},
    )
    dumped = sample.model_dump()
    extra_top = set(dumped) - JOURNEY_ALLOWED_TOP
    missing_top = JOURNEY_ALLOWED_TOP - set(dumped)
    narrative_keys = set(dumped["narrative"]) - JOURNEY_NARRATIVE_KEYS
    has_playback = "playback" in dumped or "questions" in dumped

    rejects_playback = False
    try:
        ListeningJourneyBundleOut.model_validate({**dumped, "playback": {}})
    except Exception:
        rejects_playback = True

    return {
        "sample_valid": True,
        "extra_top_level": sorted(extra_top),
        "missing_top_level": sorted(missing_top),
        "extra_narrative_keys": sorted(narrative_keys),
        "has_playback": has_playback,
        "rejects_playback_field": rejects_playback,
    }


def test_legacy_adapter_roundtrip() -> dict[str, object]:
    from app.schemas.language_listening_bundles import LessonExperienceBundleOut, LessonGoalOut, LessonNarrativeOut
    from app.services.language_listening_lesson_experience.legacy_adapter import bundle_to_legacy_payload

    bundle = LessonExperienceBundleOut(
        lesson_id=42,
        lifecycle_state="started",
        official_level="A2",
        lesson_level="A2",
        lesson_title="Office stress",
        lesson_goal=LessonGoalOut(id="business", label="Business"),
        narrative=LessonNarrativeOut(
            why_this_lesson="Practice workplace listening.",
            student_focus=("Focus on main idea",),
            reward="Build confidence.",
        ),
    )
    legacy = bundle_to_legacy_payload(bundle)
    has_bundle_embed = isinstance(legacy.get("bundle"), dict)
    has_coach = "coach" in legacy
    coach_goal = legacy.get("coach", {}).get("learning_goal")
    roundtrip_id = legacy.get("id") == 42
    forbidden_in_embed = FORBIDDEN_LESSON_KEYS & set(legacy.get("bundle") or {})
    return {
        "legacy_id": legacy.get("id"),
        "roundtrip_id": roundtrip_id,
        "has_embedded_bundle": has_bundle_embed,
        "legacy_coach_compat": has_coach,
        "coach_goal_id": coach_goal,
        "embedded_forbidden": sorted(forbidden_in_embed),
    }


def audit_frontend_render_only() -> dict[str, object]:
    violations: list[str] = []
    coach_file = FRONTEND / "composables/useListeningCoach.js"
    if coach_file.is_file():
        violations.append("useListeningCoach.js still exists")

    scan_roots = [
        FRONTEND / "components/language",
        FRONTEND / "views/student/languages",
        FRONTEND / "composables",
    ]
    for root in scan_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix not in (".vue", ".js"):
                continue
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(REPO).as_posix()
            for pat in COACH_IMPORT_PATTERNS:
                if pat in text:
                    violations.append(f"{rel}: {pat}")
            for pat in FORBIDDEN_FRONTEND_COPY_PATTERNS:
                if pat in text:
                    violations.append(f"{rel}: {pat}")

    journey_api = (FRONTEND / "api/language.js").read_text(encoding="utf-8")
    has_journey_fetch = "fetchListeningJourney" in journey_api
    return {
        "coach_composable_deleted": not coach_file.is_file(),
        "fetch_listening_journey": has_journey_fetch,
        "violations": violations,
    }


def audit_single_source_matrix() -> dict[str, object]:
    hero = (FRONTEND / "components/language/ListeningJourneyHero.vue").read_text(encoding="utf-8")
    practice = (FRONTEND / "components/language/ListeningPracticePanel.vue").read_text(encoding="utf-8")
    path = (FRONTEND / "components/language/ListeningJourneyPath.vue").read_text(encoding="utf-8")

    checks = {
        "hero_reads_journey_headline": "journey_headline" in hero,
        "hero_no_coach_import": "useListeningCoach" not in hero,
        "path_reads_timeline_steps": "timeline_steps" in path or "timelineSteps" in path,
        "practice_reads_bundle_narrative": (
            "bundle.narrative" in practice
            or "bundle.value?.narrative" in practice
            or "lessonBundle.narrative" in practice
            or "lessonBundle.value?.narrative" in practice
        ),
        "practice_reads_playback": "playback" in practice,
        "practice_after_lesson_from_bundle": "after_lesson" in practice,
    }
    return checks


def audit_api_routes() -> dict[str, object]:
    api = (ROOT / "app/api/language_student.py").read_text(encoding="utf-8")
    return {
        "journey_route": '"/listening/journey"' in api or "'/listening/journey'" in api,
        "next_bundle_model": "ListeningNextResponseOut" in api and "listening/next" in api,
        "submit_bundle_model": "ListeningLessonSubmitBundleOut" in api,
        "journey_builder_import": "build_listening_journey_bundle" in api,
        "lesson_builder_import": "build_student_lesson_bundle" in api,
    }


def audit_builders_exist() -> dict[str, object]:
    paths = {
        "lesson_builder": ROOT / "app/services/language_listening_lesson_experience/builder.py",
        "journey_builder": ROOT / "app/services/language_listening_journey/builder.py",
        "journey_narrative": ROOT / "app/services/language_learning_narrative/journey_builder.py",
        "legacy_adapter": ROOT / "app/services/language_listening_lesson_experience/legacy_adapter.py",
        "bundle_schemas": ROOT / "app/schemas/language_listening_bundles.py",
    }
    return {k: p.is_file() for k, p in paths.items()}


def run_regression_scripts() -> dict[str, object]:
    """Invoke prior listening verify scripts when Python env is available."""
    import subprocess

    scripts = [
        "verify_language_adaptive_learning_phase_2_1.py",
        "verify_language_adaptive_learning_phase_2_2.py",
        "verify_language_narrative_ownership_guard.py",
    ]
    results: dict[str, object] = {}
    for name in scripts:
        path = ROOT / "scripts" / name
        if not path.is_file():
            results[name] = {"skipped": True, "reason": "missing"}
            continue
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        results[name] = {
            "exit_code": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout_tail": (proc.stdout or "")[-500:],
            "stderr_tail": (proc.stderr or "")[-300:],
        }
    return results


def main() -> int:
    sections = {
        "builders_exist": audit_builders_exist(),
        "lesson_bundle_contract": test_lesson_bundle_schema_contract(),
        "journey_bundle_contract": test_journey_bundle_schema_contract(),
        "legacy_adapter": test_legacy_adapter_roundtrip(),
        "api_routes": audit_api_routes(),
        "frontend_render_only": audit_frontend_render_only(),
        "single_source_matrix": audit_single_source_matrix(),
        "regressions": run_regression_scripts(),
    }

    failures: list[str] = []

    if sections["frontend_render_only"]["violations"]:
        failures.append("frontend coach/copy violations")

    lb = sections["lesson_bundle_contract"]
    if lb["extra_top_level"] or lb["missing_top_level"] or lb["forbidden_in_sample"]:
        failures.append("lesson bundle contract drift")
    if not lb["rejects_coach_field"]:
        failures.append("lesson bundle must reject forbidden coach field")

    jb = sections["journey_bundle_contract"]
    if jb["extra_top_level"] or jb["missing_top_level"] or jb["has_playback"]:
        failures.append("journey bundle contract drift")
    if not jb["rejects_playback_field"]:
        failures.append("journey bundle must reject playback field")

    if not sections["frontend_render_only"]["coach_composable_deleted"]:
        failures.append("useListeningCoach.js must be deleted")

    matrix = sections["single_source_matrix"]
    if not all(matrix.values()):
        failures.append(f"single source matrix gaps: {[k for k, v in matrix.items() if not v]}")

    api = sections["api_routes"]
    if not all(api.values()):
        failures.append(f"api wiring gaps: {[k for k, v in api.items() if not v]}")

    regressions = sections["regressions"]
    for name, res in regressions.items():
        if isinstance(res, dict) and res.get("ok") is False:
            failures.append(f"regression failed: {name}")

    print(json.dumps(sections, indent=2, default=str))
    if failures:
        print("\nFAILURES:", failures)
        return 1
    print("\nPhase 2.3 verification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
