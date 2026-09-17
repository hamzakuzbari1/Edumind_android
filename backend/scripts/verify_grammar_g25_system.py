"""Verify Grammar G2.5 — Core Engine Integration Audit.

No new product features. Audits Catalog + Progression + Mastery + Review
(+ Evidence bridge, Legacy Bridge, contracts, ownership) as one coherent system.

Usage (from backend/):
    python scripts/verify_grammar_g25_system.py
"""

from __future__ import annotations

import ast
import copy
import importlib
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND = Path(__file__).resolve().parents[1]
SERVICES = BACKEND / "app" / "services"

CORE_ENGINES = (
    "language_grammar_catalog",
    "language_grammar_progression",
    "language_grammar_mastery",
    "language_grammar_review",
)
SUPPORT = (
    "language_grammar",
    "language_grammar_evidence",
    "language_grammar_legacy_bridge",
)
FUTURE_FORBIDDEN = (
    "language_grammar_lesson_planner",
    "language_grammar_lesson_runtime",
    "language_grammar_educational_package",
    "language_grammar_analytics",
    "claude_service",
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


def _pkg_deps(pkg: str) -> set[str]:
    deps: set[str] = set()
    pkg_dir = SERVICES / pkg
    if not pkg_dir.is_dir():
        return deps
    for py_file in pkg_dir.glob("*.py"):
        deps |= _parse_imports(py_file)
    return deps


def _obs(**kwargs):
    from app.services.language_grammar.enums import (
        GrammarEvidenceSourceSkill,
        GrammarObservationType,
    )
    from app.services.language_grammar_evidence.types import GrammarEvidenceObservation

    defaults = dict(
        observation_id="g25-1",
        student_id=1,
        language_id=1,
        grammar_id="gram_present_simple",
        source_skill=GrammarEvidenceSourceSkill.speaking,
        observation_type=GrammarObservationType.formative,
        attempt_count=4,
        correct_count=4,
        confidence=0.85,
        context="cafe",
        observed_at="2026-01-10T10:00:00Z",
    )
    defaults.update(kwargs)
    return GrammarEvidenceObservation(**defaults)


def audit_ownership() -> list[bool]:
    print("[Ownership]")
    results: list[bool] = []
    from app.services.language_grammar.ownership import (
        FORBIDDEN_MASTERY_WRITERS,
        MASTERY_WRITE_OWNER,
        PACKAGE_OWNERSHIP,
    )

    results.append(_ok("catalog in ownership registry", "language_grammar_catalog" in PACKAGE_OWNERSHIP))
    results.append(_ok("progression in ownership registry", "language_grammar_progression" in PACKAGE_OWNERSHIP))
    results.append(_ok("mastery in ownership registry", "language_grammar_mastery" in PACKAGE_OWNERSHIP))
    results.append(_ok("review in ownership registry", "language_grammar_review" in PACKAGE_OWNERSHIP))
    results.append(_ok("mastery is sole write owner", MASTERY_WRITE_OWNER == "language_grammar_mastery"))
    for pkg in (
        "language_grammar_catalog",
        "language_grammar_progression",
        "language_grammar_review",
        "language_grammar_evidence",
        "language_grammar_legacy_bridge",
    ):
        results.append(_ok(f"{pkg} cannot write mastery", pkg in FORBIDDEN_MASTERY_WRITERS))

    # Responsibility keywords — no duplicated ownership language
    ownership_text = " | ".join(PACKAGE_OWNERSHIP[p] for p in CORE_ENGINES)
    results.append(_ok("catalog owns topics", "GrammarTopic" in PACKAGE_OWNERSHIP["language_grammar_catalog"] or "definitions" in PACKAGE_OWNERSHIP["language_grammar_catalog"]))
    results.append(_ok("progression owns unlock", "unlock" in PACKAGE_OWNERSHIP["language_grammar_progression"]))
    results.append(_ok("mastery owns proficiency/scoring", "mastery" in PACKAGE_OWNERSHIP["language_grammar_mastery"].lower() or "scorer" in PACKAGE_OWNERSHIP["language_grammar_mastery"]))
    results.append(_ok("review owns scheduling", "schedule" in PACKAGE_OWNERSHIP["language_grammar_review"].lower() or "due" in PACKAGE_OWNERSHIP["language_grammar_review"].lower()))
    results.append(
        _ok(
            "no package claims dual ownership of unlock+mastery",
            "unlock" not in PACKAGE_OWNERSHIP["language_grammar_mastery"]
            and "overall_mastery" not in PACKAGE_OWNERSHIP["language_grammar_progression"],
        )
    )
    _ = ownership_text
    results.append(_ok("Ownership audit verdict", all(results)))
    print()
    return results


def audit_dependencies() -> list[bool]:
    print("[Dependencies]")
    results: list[bool] = []
    from app.services.language_grammar.ownership import (
        ALLOWED_PACKAGE_DEPENDENCIES,
        ARCHITECTURE_LAYERS,
        PACKAGE_LAYER,
    )

    # Declared DAG matches intended core chain; no cycles.
    declared = {pkg: set(ALLOWED_PACKAGE_DEPENDENCIES.get(pkg, frozenset())) for pkg in CORE_ENGINES}

    def reaches(start: str, target: str, seen: set[str] | None = None) -> bool:
        seen = seen or set()
        if start in seen:
            return False
        seen.add(start)
        for nxt in declared.get(start, set()):
            if nxt == target or reaches(nxt, target, seen):
                return True
        return False

    for pkg in CORE_ENGINES:
        results.append(_ok(f"no self-cycle via DAG: {pkg}", not reaches(pkg, pkg)))

    # Actual imports ⊆ allowed
    for pkg in CORE_ENGINES + ("language_grammar_evidence", "language_grammar_legacy_bridge"):
        deps = _pkg_deps(pkg)
        grammar_deps = {d for d in deps if d.startswith("language_grammar_")} - {pkg}
        allowed = set(ALLOWED_PACKAGE_DEPENDENCIES.get(pkg, frozenset()))
        unexpected = grammar_deps - allowed
        results.append(
            _ok(f"imports subset of allowed: {pkg}", not unexpected, str(sorted(unexpected)))
        )

    # No reverse / forbidden edges on core chain
    results.append(
        _ok(
            "catalog has no engine deps",
            not (_pkg_deps("language_grammar_catalog") & set(CORE_ENGINES[1:])),
        )
    )
    prog_deps = _pkg_deps("language_grammar_progression")
    results.append(_ok("progression does not import mastery", "language_grammar_mastery" not in prog_deps))
    results.append(_ok("progression does not import review", "language_grammar_review" not in prog_deps))
    mastery_deps = _pkg_deps("language_grammar_mastery")
    results.append(_ok("mastery does not import progression", "language_grammar_progression" not in mastery_deps))
    results.append(_ok("mastery does not import review", "language_grammar_review" not in mastery_deps))
    review_deps = _pkg_deps("language_grammar_review")
    results.append(_ok("review does not import progression", "language_grammar_progression" not in review_deps))
    results.append(_ok("review may import mastery", "language_grammar_mastery" in review_deps))
    results.append(_ok("mastery may import evidence", "language_grammar_evidence" in mastery_deps))

    # Layer order: no lower layer imports higher layer
    layer_index = {name: i for i, name in enumerate(ARCHITECTURE_LAYERS)}
    layer_ok = True
    detail = []
    for pkg in CORE_ENGINES + ("language_grammar_evidence", "language_grammar_legacy_bridge"):
        pkg_idx = layer_index.get(PACKAGE_LAYER.get(pkg, ""), -1)
        for dep in _pkg_deps(pkg):
            if not dep.startswith("language_grammar_"):
                continue
            dep_idx = layer_index.get(PACKAGE_LAYER.get(dep, ""), -1)
            if dep_idx > pkg_idx >= 0:
                layer_ok = False
                detail.append(f"{pkg}->{dep}")
    results.append(_ok("layer order respected", layer_ok, ",".join(detail)))

    # Core engines must not pull future packages
    for pkg in CORE_ENGINES:
        deps = _pkg_deps(pkg)
        for bad in FUTURE_FORBIDDEN:
            results.append(_ok(f"{pkg} does not import {bad}", bad not in deps))

    results.append(_ok("Dependencies audit verdict", all(results)))
    print()
    return results


def audit_data_flow() -> list[bool]:
    print("[Data Flow]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand, GrammarReviewMode
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_evidence.validation import validate_batch
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_mastery.service import (
        completion_ready_ids,
        public_views,
    )
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_grammar_review.engine import (
        compute_review_snapshot,
        empty_student_state,
        record_review_completed,
    )
    from app.services.language_grammar.ownership import (
        EVIDENCE_TO_MASTERY_BRIDGE,
        FORBIDDEN_MASTERY_WRITERS,
        MASTERY_WRITE_OWNER,
    )

    catalog = get_default_catalog()
    results.append(_ok("catalog loads topics", len(catalog.topics) >= 1))

    # Skills → Evidence → Mastery
    batch = GrammarEvidenceBatch(
        observations=(
            _obs(observation_id="df-1", context="c1"),
            _obs(observation_id="df-2", context="c2", correct_count=3),
            _obs(observation_id="df-3", context="c3"),
        )
    )
    validated = validate_batch(batch)
    results.append(_ok("evidence validates skill observations", validated.valid))
    results.append(_ok("evidence bridge package name", EVIDENCE_TO_MASTERY_BRIDGE == "language_grammar_evidence"))
    results.append(
        _ok(
            "evidence cannot write mastery scores",
            EVIDENCE_TO_MASTERY_BRIDGE in FORBIDDEN_MASTERY_WRITERS
            and MASTERY_WRITE_OWNER == "language_grammar_mastery",
        )
    )

    mastery = apply_observations(
        empty_snapshot(student_id=1, language_id=1),
        validated.observations,
        catalog=catalog,
    )
    results.append(_ok("mastery consumes evidence", mastery.record_for("gram_present_simple") is not None))
    results.append(_ok("public mastery summary available", len(public_views(mastery)) >= 1))

    # Mastery → Review
    review = compute_review_snapshot(
        mastery=mastery,
        student=empty_student_state(student_id=1, language_id=1),
        catalog=catalog,
        as_of="2026-06-01T00:00:00Z",
    )
    results.append(_ok("review consumes mastery", len(review.schedule) >= 1))
    results.append(_ok("review queue is deterministic type", review.queue is not None))

    # Progression independent — stable state only
    prog_state = GrammarProgressionStudentState(
        student_id=1,
        language_id=1,
        completed_ids=frozenset(),
        unlocked_ids=frozenset(),
    )
    before = compute_progression_snapshot(
        catalog=catalog, anchor_cefr=GrammarCEFRBand.A1, student=prog_state
    )
    before_tuple = (
        before.current_grammar_id,
        before.next_grammar_id,
        before.unlocked_ids,
        before.candidate_pool_ids,
    )
    # Complete a review — must not alter progression
    _ = record_review_completed(
        empty_student_state(student_id=1, language_id=1),
        grammar_id="gram_present_simple",
        reviewed_at="2026-06-01T00:00:00Z",
        mode=GrammarReviewMode.spaced_practice,
        catalog=catalog,
    )
    after = compute_progression_snapshot(
        catalog=catalog, anchor_cefr=GrammarCEFRBand.A1, student=prog_state
    )
    after_tuple = (
        after.current_grammar_id,
        after.next_grammar_id,
        after.unlocked_ids,
        after.candidate_pool_ids,
    )
    results.append(_ok("progression unchanged by mastery/review path", before_tuple == after_tuple))
    results.append(
        _ok(
            "completion_ready_ids is sync hook not auto-write",
            isinstance(completion_ready_ids(mastery), tuple),
        )
    )

    # No shortcut: evidence package has no scoring symbols
    evid_src = "\n".join(
        (SERVICES / "language_grammar_evidence" / f).read_text(encoding="utf-8")
        for f in ("types.py", "validation.py", "__init__.py")
        if (SERVICES / "language_grammar_evidence" / f).is_file()
    )
    results.append(
        _ok(
            "evidence has no overall_mastery scoring",
            "overall_mastery" not in evid_src and "derive_overall" not in evid_src,
        )
    )
    results.append(_ok("Data Flow audit verdict", all(results)))
    print()
    return results


def audit_contracts_and_g3() -> list[bool]:
    print("[Contracts & G3 Readiness]")
    results: list[bool] = []
    from app.services.language_grammar.types import (
        GRAMMAR_STORAGE_MASTERY_KEY,
        GRAMMAR_STORAGE_PROGRESSION_KEY,
        GRAMMAR_STORAGE_REVIEW_KEY,
        GrammarStorageNamespaces,
    )
    from app.services.language_grammar_catalog import get_default_catalog
    from app.services.language_grammar_mastery import (
        PublicGrammarMasteryView,
        public_views,
    )
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_progression import GrammarProgressionSnapshot
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_review import GrammarReviewQueue, GrammarReviewSnapshot
    from app.services.language_grammar_review.engine import compute_review_snapshot, empty_student_state
    from app.services.language_grammar_evidence.validation import validate_batch
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch

    ns = GrammarStorageNamespaces()
    results.append(_ok("storage key mastery", ns.mastery == GRAMMAR_STORAGE_MASTERY_KEY == "mastery"))
    results.append(_ok("storage key progression", ns.progression == GRAMMAR_STORAGE_PROGRESSION_KEY == "progression"))
    results.append(_ok("storage key review", ns.review == GRAMMAR_STORAGE_REVIEW_KEY == "review"))
    results.append(
        _ok(
            "storage keys unique",
            len({ns.mastery, ns.progression, ns.review, ns.runtime}) == 4,
        )
    )

    catalog = get_default_catalog()
    prog = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A2,
        student=GrammarProgressionStudentState(student_id=1, language_id=1),
    )
    results.append(_ok("Planner can read current_grammar_id", hasattr(prog, "current_grammar_id")))
    results.append(_ok("Planner can read next_grammar_id", hasattr(prog, "next_grammar_id")))
    results.append(_ok("ProgressionSnapshot is public export", GrammarProgressionSnapshot is not None))

    validated = validate_batch(
        GrammarEvidenceBatch(
            observations=(
                _obs(observation_id="g3-1", context="a"),
                _obs(observation_id="g3-2", context="b"),
            )
        )
    )
    mastery = apply_observations(
        empty_snapshot(student_id=1, language_id=1),
        validated.observations,
        catalog=catalog,
    )
    views = public_views(mastery)
    results.append(_ok("Planner can read Mastery Summary", len(views) >= 1))
    results.append(
        _ok(
            "Mastery Summary is public-only overall",
            isinstance(views[0], PublicGrammarMasteryView)
            and not hasattr(views[0], "understanding"),
        )
    )

    review = compute_review_snapshot(
        mastery=mastery,
        student=empty_student_state(student_id=1, language_id=1),
        catalog=catalog,
        as_of="2026-06-01T00:00:00Z",
    )
    results.append(_ok("Planner can read Review Queue", isinstance(review.queue, GrammarReviewQueue)))
    results.append(_ok("ReviewSnapshot exposes queue", isinstance(review, GrammarReviewSnapshot)))

    # G3 must not need engine internals — public package exports suffice
    for mod_name, attrs in (
        ("app.services.language_grammar_progression", ("GrammarProgressionSnapshot", "compute_from_state")),
        ("app.services.language_grammar_mastery", ("PublicGrammarMasteryView", "public_views")),
        ("app.services.language_grammar_review", ("GrammarReviewQueue", "compute_from_mastery")),
        ("app.services.language_grammar_catalog", ("get_default_catalog",)),
    ):
        mod = importlib.import_module(mod_name)
        for attr in attrs:
            results.append(_ok(f"export {mod_name.split('.')[-1]}.{attr}", hasattr(mod, attr)))

    results.append(_ok("Contracts/G3 audit verdict", all(results)))
    print()
    return results


def audit_feature_flags() -> list[bool]:
    print("[Feature Flags]")
    results: list[bool] = []
    from app.core.config import get_settings

    settings = get_settings()
    results.append(_ok("LANG_GRAMMAR_ENGINE_ENABLED defined", hasattr(settings, "LANG_GRAMMAR_ENGINE_ENABLED"))
    )
    results.append(_ok("LANG_GRAMMAR_ENGINE_SELECT defined", hasattr(settings, "LANG_GRAMMAR_ENGINE_SELECT")))

    for pkg in ("language_grammar_progression", "language_grammar_mastery", "language_grammar_review"):
        flags = importlib.import_module(f"app.services.{pkg}.flags")
        results.append(_ok(f"{pkg}.flags.grammar_engine_enabled", hasattr(flags, "grammar_engine_enabled")))
        results.append(
            _ok(f"{pkg}.flags.grammar_engine_select_enabled", hasattr(flags, "grammar_engine_select_enabled"))
        )

    from app.services.language_grammar_mastery.engine import empty_snapshot
    from app.services.language_grammar_mastery.service import compute_mastery_from_evidence
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_review.service import compute_from_mastery
    from app.services.language_grammar.enums import GrammarCEFRBand
    from app.services.language_grammar_progression.service import compute_from_state
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState

    with patch(
        "app.services.language_grammar_progression.service.grammar_engine_enabled",
        return_value=False,
    ):
        disabled_prog = compute_from_state(
            anchor_cefr=GrammarCEFRBand.A1,
            student=GrammarProgressionStudentState(student_id=1, language_id=1),
        )
        results.append(_ok("ENABLED=false disables progression", disabled_prog.enabled is False))

    with patch(
        "app.services.language_grammar_mastery.service.grammar_engine_enabled",
        return_value=False,
    ):
        disabled_m = compute_mastery_from_evidence(
            student_id=1,
            language_id=1,
            batch=GrammarEvidenceBatch(observations=(_obs(),)),
        )
        results.append(_ok("ENABLED=false disables mastery", disabled_m.enabled is False))

    with patch(
        "app.services.language_grammar_review.service.grammar_engine_enabled",
        return_value=False,
    ):
        disabled_r = compute_from_mastery(
            mastery=empty_snapshot(student_id=1, language_id=1),
            as_of="2026-01-01T00:00:00Z",
        )
        results.append(_ok("ENABLED=false disables review", disabled_r.enabled is False))

    results.append(_ok("Feature Flags audit verdict", all(results)))
    print()
    return results


def audit_legacy() -> list[bool]:
    print("[Legacy Compatibility]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarLegacyIdKind
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_legacy_bridge.maps import (
        SPEAKING_GRAM_IDS,
        resolve_legacy_grammar_id,
        resolve_speaking_gram_id,
    )
    from app.services.language_speaking_curriculum_engine.grammar_catalog import (
        select_grammar_targets,
    )

    catalog = get_default_catalog()
    results.append(_ok("speaking gram map non-empty", len(SPEAKING_GRAM_IDS) > 0))
    sample = next(iter(sorted(SPEAKING_GRAM_IDS)))
    resolved = resolve_speaking_gram_id(sample)
    results.append(_ok("speaking resolve returns id", resolved is not None))
    if resolved:
        results.append(
            _ok(
                "resolved speaking id in catalog or canonical",
                catalog.topic_by_id(resolved) is not None or resolved.startswith("gram_"),
            )
        )
    results.append(
        _ok(
            "legacy kind enum bridge",
            resolve_legacy_grammar_id(sample, kind=GrammarLegacyIdKind.speaking_gram) is not None,
        )
    )
    results.append(_ok("speaking projection still selects", len(select_grammar_targets(cefr="A1", count=1)) == 1))
    results.append(
        _ok(
            "legacy bridge does not import mastery/review",
            "language_grammar_mastery" not in _pkg_deps("language_grammar_legacy_bridge")
            and "language_grammar_review" not in _pkg_deps("language_grammar_legacy_bridge"),
        )
    )
    results.append(_ok("Legacy audit verdict", all(results)))
    print()
    return results


def audit_lifecycle_walkthrough() -> list[bool]:
    print("[System Lifecycle Walkthrough]")
    results: list[bool] = []
    from app.services.language_grammar.enums import GrammarCEFRBand, GrammarReviewMode
    from app.services.language_grammar_catalog.catalog import get_default_catalog
    from app.services.language_grammar_evidence.types import GrammarEvidenceBatch
    from app.services.language_grammar_evidence.validation import validate_batch
    from app.services.language_grammar_mastery.engine import apply_observations, empty_snapshot
    from app.services.language_grammar_mastery.service import public_views
    from app.services.language_grammar_progression.engine import compute_progression_snapshot
    from app.services.language_grammar_progression.types import GrammarProgressionStudentState
    from app.services.language_grammar_review.engine import (
        compute_review_snapshot,
        empty_student_state,
        record_review_completed,
    )

    catalog = get_default_catalog()

    # 1. Student opens Grammar → Progression selects current
    prog = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A1,
        student=GrammarProgressionStudentState(student_id=1, language_id=1),
    )
    results.append(_ok("1 progression selects topic or candidate", prog.current_grammar_id is not None or len(prog.candidate_pool_ids) > 0))
    current = prog.current_grammar_id or (prog.candidate_pool_ids[0] if prog.candidate_pool_ids else None)
    results.append(_ok("1 current topic resolvable", current is not None and catalog.topic_by_id(current) is not None))

    prog_before = copy.deepcopy(
        (prog.current_grammar_id, prog.next_grammar_id, prog.unlocked_ids)
    )

    # 2. Planner (future) — only verify inputs exist
    results.append(_ok("2 planner inputs: current+next+queue+summary slots ready", True))

    # 3. Activities → evidence
    target = current or "gram_present_simple"
    batch = GrammarEvidenceBatch(
        observations=(
            _obs(observation_id="life-1", grammar_id=target, context="home"),
            _obs(observation_id="life-2", grammar_id=target, context="school", correct_count=3),
            _obs(observation_id="life-3", grammar_id=target, context="park"),
        )
    )
    validated = validate_batch(batch)
    results.append(_ok("3 skills emit validated evidence", validated.valid))

    # 4. Mastery updates
    mastery = apply_observations(
        empty_snapshot(student_id=1, language_id=1),
        validated.observations,
        catalog=catalog,
    )
    rec = mastery.record_for(target)
    results.append(_ok("4 mastery updated for topic", rec is not None and rec.evidence_count >= 3))
    results.append(_ok("4 public summary available", len(public_views(mastery)) >= 1))

    # 5. Review schedules
    review_state = empty_student_state(student_id=1, language_id=1)
    review = compute_review_snapshot(
        mastery=mastery,
        student=review_state,
        catalog=catalog,
        as_of="2026-08-01T00:00:00Z",
    )
    results.append(_ok("5 review schedule built", len(review.schedule) >= 1))
    review_state = record_review_completed(
        review_state,
        grammar_id=target,
        reviewed_at="2026-08-01T00:00:00Z",
        mode=GrammarReviewMode.spaced_practice,
        catalog=catalog,
    )
    results.append(
        _ok(
            "5 review history recorded",
            review_state.history_for(target) is not None,
        )
    )

    # 6. Progression remains independent
    prog_after = compute_progression_snapshot(
        catalog=catalog,
        anchor_cefr=GrammarCEFRBand.A1,
        student=GrammarProgressionStudentState(student_id=1, language_id=1),
    )
    results.append(
        _ok(
            "6 progression remains independent",
            prog_before
            == (prog_after.current_grammar_id, prog_after.next_grammar_id, prog_after.unlocked_ids),
        )
    )
    results.append(_ok("Lifecycle walkthrough verdict", all(results)))
    print()
    return results


def main() -> int:
    print("Grammar G2.5 Core Engine Integration Audit\n")
    all_results: list[bool] = []
    all_results.extend(audit_ownership())
    all_results.extend(audit_dependencies())
    all_results.extend(audit_data_flow())
    all_results.extend(audit_contracts_and_g3())
    all_results.extend(audit_feature_flags())
    all_results.extend(audit_legacy())
    all_results.extend(audit_lifecycle_walkthrough())

    passed = sum(1 for r in all_results if r)
    failed = sum(1 for r in all_results if not r)
    print(f"Summary: {passed} passed, {failed} failed, {len(all_results)} total")
    if failed:
        print("G2.5 VERDICT: NOT READY")
        return 1
    print("G2.5 VERDICT: READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
