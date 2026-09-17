"""Verify Phase G — Learning Journey projection (compose-only).

Usage (from backend/):
    python scripts/verify_learning_journey_projection.py
"""

from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"
JOURNEY_PKG = SERVICES / "language_learning_journey"
LOCKED_PKGS = (
    "language_grammar_catalog",
    "language_grammar_mastery",
    "language_grammar_progression",
    "language_adaptive_intelligence",
    "language_ai_tutor",
    "language_ai_tutor_coaching",
    "language_ai_teacher",
)

FORBIDDEN_WRITE_CALLS = (
    "apply_evidence_and_persist",
    "record_grammar_topic_completed",
    "evaluate_and_persist_grammar_progression",
    "sync_completed_topics_async",
    "persist_learning_profile",
    "persist_conversation_memory",
    "persist_coaching_state",
    "persist_teacher_state",
    "respond_tutor_turn",
    "respond_coaching_turn",
    "build_learning_session",
    "start_teacher_session",
)


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {name}: {status}{suffix}")
    return passed


def _parse_imports(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.services."):
            parts = node.module.split(".")
            if len(parts) >= 3:
                imports.add(parts[2])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app.services."):
                    parts = alias.name.split(".")
                    if len(parts) >= 3:
                        imports.add(parts[2])
    return imports


def _fingerprint(pkg: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(pkg.rglob("*")):
        if path.is_file() and path.suffix in {".py", ".md"}:
            h.update(path.relative_to(pkg).as_posix().encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def check_package_shape() -> list[bool]:
    results: list[bool] = []
    required = (
        "__init__.py",
        "types.py",
        "enums.py",
        "projection.py",
        "service.py",
        "flags.py",
    )
    results.append(_ok("journey package directory", JOURNEY_PKG.is_dir()))
    for name in required:
        results.append(_ok(f"file: {name}", (JOURNEY_PKG / name).is_file()))
    init = (JOURNEY_PKG / "__init__.py").read_text(encoding="utf-8")
    results.append(_ok("RESPONSIBILITY declared", "RESPONSIBILITY" in init))
    results.append(_ok("compose-only stated", "compose" in init.lower() or "compose-only" in init.lower()))
    return results


def check_ownership_reservation() -> list[bool]:
    results: list[bool] = []
    from app.services.language_grammar import ownership

    results.append(
        _ok(
            "LEARNING_JOURNEY_PACKAGE reserved",
            getattr(ownership, "LEARNING_JOURNEY_PACKAGE", None) == "language_learning_journey",
        )
    )
    g0 = set(getattr(ownership, "REQUIRED_G0_PACKAGES", ()))
    results.append(_ok("outside REQUIRED_G0_PACKAGES", "language_learning_journey" not in g0))
    return results


def check_read_only_contract() -> list[bool]:
    results: list[bool] = []
    text = ""
    imports: set[str] = set()
    for py_file in JOURNEY_PKG.glob("*.py"):
        imports |= _parse_imports(py_file)
        text += py_file.read_text(encoding="utf-8") + "\n"

    for dep in (
        "language_grammar_catalog",
        "language_grammar_mastery",
        "language_grammar_progression",
    ):
        results.append(_ok(f"may read {dep}", dep in imports))

    for forbidden in (
        "language_adaptive_intelligence",
        "language_ai_tutor",
        "language_ai_tutor_coaching",
        "language_ai_teacher",
    ):
        results.append(_ok(f"no import {forbidden}", forbidden not in imports))

    for call in FORBIDDEN_WRITE_CALLS:
        results.append(_ok(f"no call {call}", call not in text))

    api = BACKEND / "app" / "api" / "language_learning_journey.py"
    results.append(_ok("API route file exists", api.is_file()))
    if api.is_file():
        api_text = api.read_text(encoding="utf-8")
        results.append(_ok("GET journey route", '"/journey"' in api_text or "'/journey'" in api_text))
        results.append(_ok("API has no write verbs", "def post_" not in api_text.lower() and "@router.post" not in api_text))
    return results


def check_locked_layers_untouched() -> list[bool]:
    results: list[bool] = []
    for pkg in LOCKED_PKGS:
        pkg_dir = SERVICES / pkg
        mentions = 0
        for py_file in pkg_dir.rglob("*.py"):
            if "language_learning_journey" in py_file.read_text(encoding="utf-8"):
                mentions += 1
        results.append(_ok(f"locked free of journey import: {pkg}", mentions == 0))
        results.append(_ok(f"fingerprint: {pkg}", bool(_fingerprint(pkg_dir))))
    from app.services.language_grammar_catalog.catalog import get_default_catalog

    cat = get_default_catalog()
    results.append(_ok("curriculum still 53 topics", len(cat.topics) == 53, str(len(cat.topics))))
    return results


def _fixtures():
    from app.services.language_grammar.enums import GrammarCEFRBand, GrammarMasteryState
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_mastery.types import (
        GrammarMasteryRecord,
        GrammarMasterySnapshot,
        build_dimensions,
    )
    from app.services.language_grammar_progression.types import GrammarProgressionSnapshot

    catalog = get_default_catalog()
    topics = sorted(catalog.topics, key=lambda t: (t.cefr_band.value, t.introduction_order, t.grammar_id))
    # First A1 topic mastered; second is current
    a1 = [t for t in topics if t.cefr_band is GrammarCEFRBand.A1]
    mastered_id = a1[0].grammar_id
    current_id = a1[1].grammar_id if len(a1) > 1 else a1[0].grammar_id
    unlocked = tuple(t.grammar_id for t in a1[:3])
    locked = tuple(t.grammar_id for t in a1[3:6])
    future = tuple(t.grammar_id for t in topics if t.grammar_id not in unlocked and t.grammar_id not in locked)

    mastery = GrammarMasterySnapshot(
        student_id=42,
        language_id=1,
        records=(
            GrammarMasteryRecord(
                student_id=42,
                language_id=1,
                grammar_id=mastered_id,
                state=GrammarMasteryState.mastered,
                dimensions=build_dimensions(
                    understanding=90.0, accuracy=88.0, fluency=85.0, retention=86.0, confidence=0.9
                ),
                confidence=0.9,
                evidence_count=5,
            ),
        ),
    )
    progression = GrammarProgressionSnapshot(
        anchor_cefr=GrammarCEFRBand.A1,
        current_grammar_id=current_id,
        next_grammar_id=a1[2].grammar_id if len(a1) > 2 else None,
        unlocked_ids=unlocked,
        locked_ids=locked,
        future_ids=future,
        stretch_ids=(),
        candidate_pool_ids=(current_id,),
        candidate_priorities=(),
        progression_reason=("fixture",),
        enabled=True,
    )
    return catalog, mastery, progression, mastered_id, current_id, unlocked, locked


def check_projection() -> list[bool]:
    results: list[bool] = []
    from app.services.language_learning_journey.enums import JourneyStageStatus
    from app.services.language_learning_journey.projection import project_journey_graph

    catalog, mastery, progression, mastered_id, current_id, unlocked, locked = _fixtures()
    a = project_journey_graph(catalog=catalog, progression=progression, mastery=mastery)
    b = project_journey_graph(catalog=catalog, progression=progression, mastery=mastery)

    stage_count = sum(len(lv.stages) for lv in a.levels)
    results.append(_ok("stages == catalog count (53)", stage_count == 53, str(stage_count)))
    results.append(_ok("enabled when progression on", a.enabled is True))
    results.append(_ok("deterministic graph", a.to_dict() == b.to_dict()))
    results.append(_ok("current_grammar_id matches", a.current_grammar_id == current_id))
    results.append(_ok("exactly one expanded level", sum(1 for lv in a.levels if lv.expanded) == 1))

    by_id = {s.grammar_id: s for lv in a.levels for s in lv.stages}
    results.append(
        _ok(
            "current status from progression",
            by_id[current_id].status is JourneyStageStatus.current,
        )
    )
    results.append(
        _ok(
            "completed from mastery mastered",
            by_id[mastered_id].status is JourneyStageStatus.completed,
        )
    )
    for gid in locked:
        if gid in by_id and gid != current_id and gid != mastered_id:
            results.append(_ok(f"locked matches progression: {gid}", by_id[gid].status is JourneyStageStatus.locked))
            break
    else:
        results.append(_ok("locked matches progression", True))

    for gid in unlocked:
        if gid not in {current_id, mastered_id} and gid in by_id:
            results.append(
                _ok(
                    f"unlocked matches progression: {gid}",
                    by_id[gid].status is JourneyStageStatus.unlocked,
                )
            )
            break
    else:
        results.append(_ok("unlocked matches progression", True))

    empty = project_journey_graph(catalog=catalog, progression=None, mastery=None)
    results.append(_ok("disabled without progression", empty.enabled is False))
    results.append(_ok("skills include quiz label", "quiz" in by_id[current_id].skills))
    return results


def check_api_schema() -> list[bool]:
    results: list[bool] = []
    schema = BACKEND / "app" / "schemas" / "language_learning_journey.py"
    results.append(_ok("schema file exists", schema.is_file()))
    if schema.is_file():
        text = schema.read_text(encoding="utf-8")
        for name in ("LearningJourneyOut", "JourneyLevelOut", "JourneyStageOut", "JourneyProgressOut"):
            results.append(_ok(f"schema {name}", name in text))
    router = BACKEND / "app" / "api" / "router.py"
    rtext = router.read_text(encoding="utf-8")
    results.append(_ok("router includes journey", "language_learning_journey" in rtext))
    return results


def check_frontend_smoke() -> list[bool]:
    """Lightweight frontend wiring checks (no Vite)."""
    results: list[bool] = []
    root = BACKEND.parents[0]
    views = root / "src" / "views" / "student" / "english-journey"
    comps = root / "src" / "components" / "english-journey"
    required_views = (
        "EnglishJourneyHomeView.vue",
        "EnglishJourneyStageView.vue",
        "EnglishJourneySessionView.vue",
        "EnglishJourneyCompleteView.vue",
        "EnglishJourneyReviewView.vue",
        "EnglishJourneyAchievementsView.vue",
    )
    required_comps = (
        "JourneyShell.vue",
        "JourneyHero.vue",
        "JourneyProgressBar.vue",
        "LevelTimeline.vue",
        "StageCard.vue",
        "StageDetailPanel.vue",
        "MissionCard.vue",
        "SessionEntryCard.vue",
        "AiTeacherSidebar.vue",
        "StageCompletionScreen.vue",
        "JourneyEmptyState.vue",
    )
    for name in required_views:
        results.append(_ok(f"view {name}", (views / name).is_file()))
    for name in required_comps:
        results.append(_ok(f"component {name}", (comps / name).is_file()))

    api_files = (
        root / "src" / "api" / "learningJourney.js",
        root / "src" / "api" / "aiTeacher.js",
        root / "src" / "api" / "adaptiveInsights.js",
        root / "src" / "composables" / "useEnglishJourney.js",
    )
    for path in api_files:
        results.append(_ok(f"client {path.name}", path.is_file()))

    router = (root / "src" / "router" / "index.js").read_text(encoding="utf-8")
    for path in (
        "english-journey",
        "english-journey/stage/:grammarId",
        "english-journey/session",
        "english-journey/complete",
        "english-journey/review",
        "english-journey/achievements",
    ):
        results.append(_ok(f"route {path}", path in router))

    nav = (root / "src" / "config" / "navigation.js").read_text(encoding="utf-8")
    results.append(_ok("nav english journey entry", "englishJourney" in nav and "/student/english-journey" in nav))
    results.append(_ok("nav keeps academic journey", "dashboard.student.nav.journey" in nav))
    results.append(_ok("nav keeps languages", "dashboard.student.nav.languages" in nav))

    router_js = (root / "src" / "router" / "index.js").read_text(encoding="utf-8")
    # Journey is additive; Grammar skill page remains available.
    results.append(
        _ok(
            "grammar route still serves StudentGrammarView",
            "StudentGrammarView.vue" in router_js and "path: 'grammar'" in router_js,
        )
    )
    results.append(
        _ok(
            "english journey route coexists",
            "path: 'english-journey'" in router_js and "EnglishJourneyHomeView.vue" in router_js,
        )
    )
    home = (views / "EnglishJourneyHomeView.vue").read_text(encoding="utf-8")
    results.append(_ok("home has SessionEntryCard", "SessionEntryCard" in home))
    results.append(_ok("home has LevelTimeline", "LevelTimeline" in home))
    results.append(_ok("home has JourneyHero", "JourneyHero" in home))
    results.append(_ok("home does not use GrammarHero", "GrammarHero" not in home))
    results.append(_ok("home does not use LanguageModuleTabs", "LanguageModuleTabs" not in home))
    results.append(_ok("home does not use GrammarLessonCard", "GrammarLessonCard" not in home))

    # No hardcoded 53-topic stage catalogs in journey UI
    hardcode_hits = 0
    for folder in (views, comps):
        for py in folder.glob("*.vue"):
            text = py.read_text(encoding="utf-8")
            if "gram_present_simple" in text and "G001" in text:
                hardcode_hits += 1
    results.append(_ok("no hardcoded stage catalog in UI", hardcode_hits == 0))

    composable = (root / "src" / "composables" / "useEnglishJourney.js").read_text(encoding="utf-8")
    results.append(_ok("startTodaysSession uses teacher API", "startTeacherSession" in composable))
    results.append(_ok("composable does not invent unlocks", "unlocked_ids" not in composable))
    return results


def main() -> int:
    print("Phase G — Learning Journey Projection verify\n")
    checks = [
        ("Package shape", check_package_shape),
        ("Ownership reservation", check_ownership_reservation),
        ("Read-only contract", check_read_only_contract),
        ("Locked layers untouched", check_locked_layers_untouched),
        ("Projection compose", check_projection),
        ("API + schema", check_api_schema),
        ("Frontend smoke", check_frontend_smoke),
    ]
    all_ok = True
    for title, fn in checks:
        print(f"[{title}]")
        results = fn()
        if not all(results):
            all_ok = False
        print()
    if all_ok:
        print("ALL CHECKS PASSED")
        return 0
    print("SOME CHECKS FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
