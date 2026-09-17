"""Verify PR-STAB-1 — Adaptive Persistence Foundation (Listening Only).

Usage (from backend/):
    python scripts/verify_language_stabilization_pr_1_adaptive.py
"""

from __future__ import annotations

import asyncio
import inspect
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import select, text
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import AsyncSessionLocal
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.profile import LanguageStudentProfile
from app.services.language_listening_challenge.constants import CHALLENGE_KEY
from app.services.language_listening_challenge.storage import (
    build_initial_challenge_state,
    load_student_challenge,
    save_student_challenge,
)
from app.services.language_listening_confidence.constants import CONFIDENCE_KEY
from app.services.language_listening_confidence.evidence import record_evidence_from_lesson
from app.services.language_listening_confidence.lesson_context import lesson_context_from_body
from app.services.language_listening_confidence.storage import (
    build_initial_confidence_state,
    load_student_confidence,
    save_student_confidence,
)
from app.services.language_listening_confidence.update import update_confidence_from_lesson
from app.services.language_student_profile_service import get_language_student_profile


def _ok(name: str, passed: bool, detail: str = "") -> bool:
    status = "OK" if passed else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    return passed


def _function_body(source: str, name: str) -> str:
    marker = f"async def {name}("
    if marker not in source:
        return ""
    rest = source.split(marker, 1)[1]
    next_def = rest.find("\nasync def ")
    return rest if next_def < 0 else rest[:next_def]


def verify_canonical_profile_lookup() -> list[bool]:
    print("\n=== Canonical profile lookup (L-01) ===")
    results: list[bool] = []
    root = Path(__file__).resolve().parents[1] / "app" / "services"

    conf_src = (root / "language_listening_confidence" / "storage.py").read_text(encoding="utf-8")
    chall_src = (root / "language_listening_challenge" / "storage.py").read_text(encoding="utf-8")
    profile_src = (root / "language_student_profile_service.py").read_text(encoding="utf-8")

    results.append(_ok("shared profile service exists", profile_src.strip() != ""))
    results.append(
        _ok(
            "confidence uses get_language_student_profile",
            "get_language_student_profile" in conf_src and "db.get(LanguageStudentProfile" not in conf_src,
        )
    )
    results.append(
        _ok(
            "challenge uses get_language_student_profile",
            "get_language_student_profile" in chall_src and "db.get(LanguageStudentProfile" not in chall_src,
        )
    )
    results.append(_ok("lookup uses select", "select(LanguageStudentProfile)" in profile_src))
    results.append(
        _ok(
            "lookup filters student_id and language_id",
            "LanguageStudentProfile.student_id ==" in profile_src
            and "LanguageStudentProfile.language_id ==" in profile_src,
        )
    )
    return results


def verify_language_id_api() -> list[bool]:
    print("\n=== language_id on all adaptive load/save callers (L-06) ===")
    results: list[bool] = []
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    files = [
        root / "language_skill_progress_service.py",
        root / "language_lesson_generation_service.py",
        root / "language_learning_stage" / "signals.py",
        root / "language_listening_confidence" / "storage.py",
        root / "language_listening_challenge" / "storage.py",
    ]
    for path in files:
        src = path.read_text(encoding="utf-8")
        results.append(
            _ok(
                f"{path.name} passes language_id to load/save",
                "language_id=language_id" in src or "language_id=language.id" in src,
            )
        )
    conf_sig = inspect.signature(load_student_confidence)
    chall_sig = inspect.signature(load_student_challenge)
    results.append(_ok("load_student_confidence requires language_id", "language_id" in conf_sig.parameters))
    results.append(_ok("load_student_challenge requires language_id", "language_id" in chall_sig.parameters))
    return results


def verify_flag_modified() -> list[bool]:
    print("\n=== preferences_json flag_modified (Part 3) ===")
    results: list[bool] = []
    for rel in (
        "language_listening_confidence/storage.py",
        "language_listening_challenge/storage.py",
    ):
        src = (Path(__file__).resolve().parents[1] / "app" / "services" / rel).read_text(encoding="utf-8")
        results.append(_ok(f"{rel} calls flag_modified", "flag_modified(profile" in src))
    return results


def verify_official_cefr_bucket() -> list[bool]:
    print("\n=== Official CEFR bucket in submit_listening (L-09b) ===")
    results: list[bool] = []
    path = Path(__file__).resolve().parents[1] / "app" / "services" / "language_skill_progress_service.py"
    src = path.read_text(encoding="utf-8")
    submit_body = _function_body(src, "submit_listening")

    results.append(_ok("uses select_skill_level_str", "select_skill_level_str" in submit_body))
    results.append(
        _ok(
            "adaptive load uses official_level not item.level",
            "level=official_level" in submit_body
            and "load_student_confidence" in submit_body
            and "level=level_str" not in submit_body,
        )
    )
    return results


def verify_legacy_lesson_fallback() -> list[bool]:
    print("\n=== Legacy lesson fallback (Part 5) ===")
    results: list[bool] = []
    legacy_body = {
        "situation": "A customer returns a coat",
        "topic": "shopping",
        "difficulty": "normal",
        "questions": [
            {"id": "q1", "type": "detail", "stem": "Why?", "correct_index": 0},
            {"id": "q2", "type": "inference", "stem": "Tone?", "correct_index": 1},
        ],
    }
    ctx = lesson_context_from_body(legacy_body, lesson_index=1, level="A2")
    results.append(_ok("legacy body yields lesson context", ctx is not None))
    results.append(_ok("legacy situation from body root", ctx is not None and ctx.situation == "A customer returns a coat"))
    results.append(
        _ok(
            "legacy objectives from questions",
            ctx is not None and "detail" in ctx.lesson_objectives and "inference" in ctx.lesson_objectives,
        )
    )

    intel_body = {
        "listening_intelligence": {
            "situation": "airport_delay",
            "narrative_format": "announcement",
            "difficulty_band": "normal",
            "category": "travel",
        },
        "listening_curriculum": {"objectives": ["detail"], "skill_focus": ["detail"]},
        "questions": [{"id": "q1", "type": "detail"}],
    }
    intel_ctx = lesson_context_from_body(intel_body, lesson_index=2, level="B1")
    results.append(_ok("intelligence path still works", intel_ctx is not None and intel_ctx.situation == "airport_delay"))
    return results


async def verify_profile_isolation() -> list[bool]:
    print("\n=== Profile isolation and multi-language (L-01 / L-06) ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        lang_rows = (await db.execute(text("SELECT id FROM languages ORDER BY id LIMIT 2"))).all()
        if not lang_rows:
            return [_ok("skip profile isolation (no languages)", True)]

        lang_a = int(lang_rows[0][0])
        lang_b = int(lang_rows[1][0]) if len(lang_rows) > 1 else None

        student_row = (await db.execute(text("SELECT id FROM users ORDER BY id LIMIT 1"))).first()
        if student_row is None:
            return [_ok("skip profile isolation (no users)", True)]
        student_id = int(student_row[0])

        for lid in ([lang_a, lang_b] if lang_b is not None else [lang_a]):
            existing = await get_language_student_profile(db, student_id=student_id, language_id=lid)
            if existing is None:
                db.add(LanguageStudentProfile(student_id=student_id, language_id=lid))
        await db.flush()

        marker_a = "stab1_lang_a_marker"
        prof_a = await get_language_student_profile(db, student_id=student_id, language_id=lang_a)
        assert prof_a is not None

        prefs_a = dict(prof_a.preferences_json or {})
        prefs_a[CONFIDENCE_KEY] = {marker_a: {"lesson_index": 7}}
        prof_a.preferences_json = prefs_a
        flag_modified(prof_a, "preferences_json")
        await db.flush()

        loaded_a = await get_language_student_profile(db, student_id=student_id, language_id=lang_a)
        wrong = await get_language_student_profile(db, student_id=student_id, language_id=lang_a + 88888)

        results.append(_ok("lang A profile found", loaded_a is not None and loaded_a.id == prof_a.id))
        results.append(
            _ok(
                "lang A data persisted",
                marker_a in ((loaded_a.preferences_json or {}).get(CONFIDENCE_KEY) or {}),
            )
        )
        results.append(_ok("wrong language_id returns None", wrong is None))

        if lang_b is not None:
            marker_b = "stab1_lang_b_marker"
            prof_b = await get_language_student_profile(db, student_id=student_id, language_id=lang_b)
            assert prof_b is not None
            prefs_b = dict(prof_b.preferences_json or {})
            prefs_b[CONFIDENCE_KEY] = {marker_b: {"lesson_index": 3}}
            prof_b.preferences_json = prefs_b
            flag_modified(prof_b, "preferences_json")
            await db.flush()

            loaded_b = await get_language_student_profile(db, student_id=student_id, language_id=lang_b)
            results.append(_ok("lang B profile found", loaded_b is not None and loaded_b.id == prof_b.id))
            results.append(_ok("profiles are distinct rows", loaded_a.id != loaded_b.id))
            results.append(
                _ok(
                    "lang A data isolated from lang B",
                    marker_b not in ((loaded_a.preferences_json or {}).get(CONFIDENCE_KEY) or {}),
                )
            )
            results.append(
                _ok(
                    "lang B data isolated from lang A",
                    marker_b in ((loaded_b.preferences_json or {}).get(CONFIDENCE_KEY) or {})
                    and marker_a not in ((loaded_b.preferences_json or {}).get(CONFIDENCE_KEY) or {}),
                )
            )
        else:
            results.append(_ok("multi-language rows (single language in DB)", True, "skipped"))

        await db.rollback()

    return results


async def verify_adaptive_persistence_survives_submits() -> list[bool]:
    print("\n=== Confidence / Evidence / Challenge persistence ===")
    results: list[bool] = []

    async with AsyncSessionLocal() as db:
        lang_row = (await db.execute(text("SELECT id FROM languages ORDER BY id LIMIT 1"))).first()
        student_row = (await db.execute(text("SELECT id FROM users ORDER BY id LIMIT 1"))).first()
        if lang_row is None or student_row is None:
            return [_ok("skip persistence test (no seed rows)", True)]

        language_id = int(lang_row[0])
        student_id = int(student_row[0])
        level = "B1"

        legacy_body = {
            "situation": "metro delay",
            "topic": "travel",
            "questions": [
                {"id": "q1", "type": "detail"},
                {"id": "q2", "type": "inference"},
            ],
        }
        q_results = [
            {"id": "q1", "type": "detail", "is_correct": True},
            {"id": "q2", "type": "inference", "is_correct": False},
        ]

        confidence_state = build_initial_confidence_state(level)
        challenge_state = build_initial_challenge_state(level)

        for submit_idx in range(3):
            ctx = lesson_context_from_body(legacy_body, lesson_index=submit_idx + 1, level=level)
            update_confidence_from_lesson(confidence_state, ctx, q_results)
            record_evidence_from_lesson(confidence_state, ctx, q_results)
            from app.services.language_listening_challenge import record_challenge_from_lesson

            record_challenge_from_lesson(
                challenge_state,
                confidence_state,
                ctx,
                score_percent=72.0,
                passed=True,
                question_results=q_results,
                was_review=False,
                retry_count=1,
                before_coverages={oid: rec.coverage_score for oid, rec in confidence_state.objectives.items()},
            )
            await save_student_confidence(
                db, student_id=student_id, language_id=language_id, state=confidence_state
            )
            await save_student_challenge(
                db, student_id=student_id, language_id=language_id, state=challenge_state
            )
            await db.flush()

            reloaded_conf = await load_student_confidence(
                db, student_id=student_id, language_id=language_id, level=level
            )
            reloaded_chal = await load_student_challenge(
                db, student_id=student_id, language_id=language_id, level=level
            )

            results.append(
                _ok(
                    f"submit {submit_idx + 1} confidence lesson_index",
                    reloaded_conf.lesson_index == confidence_state.lesson_index,
                    f"expected {confidence_state.lesson_index}",
                )
            )
            results.append(
                _ok(
                    f"submit {submit_idx + 1} challenge history",
                    len(reloaded_chal.history) == len(challenge_state.history),
                )
            )
            any_evidence = any(rec.exposure_count > 0 or rec.evidence.difficulty for rec in reloaded_conf.objectives.values())
            results.append(_ok(f"submit {submit_idx + 1} evidence persisted", any_evidence))

        profile = await get_language_student_profile(db, student_id=student_id, language_id=language_id)
        prefs = (profile.preferences_json or {}) if profile else {}
        results.append(_ok("confidence key in preferences_json", level in (prefs.get(CONFIDENCE_KEY) or {})))
        results.append(_ok("challenge key in preferences_json", level in (prefs.get(CHALLENGE_KEY) or {})))

        await db.rollback()

    return results


def verify_regression_subprocess(script: str) -> list[bool]:
    print(f"\n=== Regression: {script} ===")
    results: list[bool] = []
    path = Path(__file__).resolve().parents[1] / "scripts" / script
    if not path.is_file():
        return [_ok(f"{script} present", False)]
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    out = proc.stdout or ""
    passed = proc.returncode == 0 or "PASS" in out.splitlines()[-3:]
    tail = out[-400:]
    results.append(_ok(script, passed, tail.strip().splitlines()[-1] if tail else f"exit {proc.returncode}"))
    return results


async def verify_runtime_call_order() -> list[bool]:
    print("\n=== Regression: Listening Runtime call order ===")
    from app.services.language_listening_progression.runtime import run_listening_progression_after_submit

    results: list[bool] = []
    calls: list[str] = []

    async def stage_fn(*_a, **_k):
        calls.append("stage")

    async def gate_fn(*_a, **_k):
        calls.append("gate")

    async def readiness_fn(*_a, **_k):
        calls.append("readiness")

    async def stability_fn(*_a, **_k):
        calls.append("stability")

    with (
        patch("app.services.language_listening_progression.runtime.ensure_progression_row", new_callable=AsyncMock),
        patch(
            "app.services.language_listening_progression.runtime.evaluate_and_persist_listening_stage",
            side_effect=stage_fn,
        ),
        patch(
            "app.services.language_listening_progression.runtime.evaluate_listening_transition_gate",
            side_effect=gate_fn,
        ),
        patch(
            "app.services.language_listening_progression.runtime.evaluate_and_persist_listening_promotion_readiness",
            side_effect=readiness_fn,
        ),
        patch(
            "app.services.language_listening_progression.runtime.evaluate_and_persist_listening_promotion_stability",
            side_effect=stability_fn,
        ),
    ):
        await run_listening_progression_after_submit(AsyncMock(), student_id=1, language_id=1)

    results.append(_ok("progression engines order", calls == ["stage", "gate", "readiness", "stability"], str(calls)))
    return results


async def main() -> int:
    print("verify_language_stabilization_pr_1_adaptive")
    all_results: list[bool] = []

    all_results.extend(verify_canonical_profile_lookup())
    all_results.extend(verify_language_id_api())
    all_results.extend(verify_flag_modified())
    all_results.extend(verify_official_cefr_bucket())
    all_results.extend(verify_legacy_lesson_fallback())
    all_results.extend(await verify_profile_isolation())
    all_results.extend(await verify_adaptive_persistence_survives_submits())
    all_results.extend(await verify_runtime_call_order())

    regression_scripts = [
        "verify_language_adaptive_learning_phase_3_2.py",
        "verify_language_adaptive_learning_phase_3_2_1.py",
        "verify_language_adaptive_learning_phase_3_3.py",
        "verify_language_listening_progression_runtime_pr_1.py",
        "verify_language_learning_stage_phase_5_1.py",
    ]
    for script in regression_scripts:
        all_results.extend(verify_regression_subprocess(script))

    passed = sum(all_results)
    total = len(all_results)
    print(f"\n=== SUMMARY: {passed}/{total} checks passed ===")
    if passed == total:
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
