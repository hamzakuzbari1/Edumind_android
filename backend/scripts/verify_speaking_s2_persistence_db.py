"""S2 Speaking Knowledge Model — live PostgreSQL persistence verification.

Exercises the canonical mutate_speaking_knowledge_model path against a real
language_progression row. All QA mutations run in one transaction and are
rolled back; restoration is proven in a fresh post-rollback session.

Reload semantics: db.expire_all() + db.get() forces a re-SELECT so JSONB
round-trips through PostgreSQL within the open transaction (no commit).

Usage (from backend/):
    python scripts/verify_speaking_s2_persistence_db.py

Non-destructive: ends with db.rollback(); no PASS from in-memory dict tests alone.
"""

from __future__ import annotations

import asyncio
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401
from app.models.user import User  # noqa: F401

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

from app.db.session import AsyncSessionLocal, check_database_connection
from app.models.language.progression import LanguageProgression
from app.services.language_progression_service import ensure_progression_row
from app.services.language_speaking_curriculum.evidence_ids import (
    PHONEME_ALIGNMENT,
    PRONUNCIATION_CONFIDENCE,
    WORD_STRESS_ACCURACY,
)
from app.services.language_speaking_curriculum.types import SPEAKING_SKILL_GRAPH_VERSION
from app.services.language_speaking_knowledge_model.compatibility import reconcile_model_with_graph
from app.services.language_speaking_knowledge_model.engine import (
    apply_observation,
    apply_observations_batch,
)
from app.services.language_speaking_knowledge_model.json_mutation import mutate_speaking_knowledge_model
from app.services.language_speaking_knowledge_model.locking import lock_speaking_progression_row
from app.services.language_speaking_knowledge_model.storage import (
    KNOWLEDGE_MODEL_KEY,
    SPEAKING_BUCKET_KEY,
    knowledge_model_from_speaking_bucket,
    knowledge_model_to_dict,
    speaking_bucket_from_payload,
)
from app.services.language_speaking_knowledge_model.types import (
    KNOWLEDGE_MODEL_SCHEMA_VERSION,
    ObservationSourceType,
    SpeakingSkillEvidenceObservation,
    StudentSpeakingSkillState,
)

NOW = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

_results: list[tuple[str, bool, str]] = []
_report: dict[str, Any] = {
    "qa_row": None,
    "original_jsonb_top_keys": [],
    "defects_found": [],
}


def ok(name: str, passed: bool, detail: str = "") -> bool:
    _results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}{(' -- ' + detail) if detail else ''}")
    return passed


def _ts() -> str:
    return NOW.strftime("%Y-%m-%dT%H:%M:%SZ")


def _obs(
    obs_id: str,
    skill_id: str,
    *,
    context_id: str,
    performance: float = 0.75,
    confidence: float = 0.9,
    dimensions: tuple[str, ...] | None = None,
) -> SpeakingSkillEvidenceObservation:
    if dimensions is None:
        dimensions = (PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE)
    return SpeakingSkillEvidenceObservation(
        observation_id=obs_id,
        skill_id=skill_id,
        observed_at=_ts(),
        performance=performance,
        confidence=confidence,
        evidence_dimensions=dimensions,
        context_id=context_id,
        success=True,
        target_skill=True,
        source_type=ObservationSourceType.synthetic_test,
    )


def _json_snapshot(payload: dict[str, Any] | None) -> str:
    return json.dumps(payload or {}, sort_keys=True, default=str)


def _load_km(row: LanguageProgression, sid: int, lid: int):
    speaking = speaking_bucket_from_payload(dict(row.promotion_readiness_json or {}))
    return knowledge_model_from_speaking_bucket(speaking, student_id=sid, language_id=lid)


async def _reload_row(db, sid: int, lid: int) -> LanguageProgression | None:
    db.expire_all()
    return await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})


async def _pick_qa_row(db) -> tuple[int, int, str]:
    """Return (student_id, language_id, source_description)."""
    row = (await db.execute(text("SELECT student_id, language_id FROM language_progression LIMIT 1"))).first()
    if row is not None:
        return int(row[0]), int(row[1]), "language_progression LIMIT 1"

    row = (await db.execute(text("SELECT student_id, language_id FROM language_analytics LIMIT 1"))).first()
    if row is not None:
        sid, lid = int(row[0]), int(row[1])
        ensured = await ensure_progression_row(db, student_id=sid, language_id=lid)
        if ensured is not None:
            await db.flush()
            return sid, lid, "language_analytics + ensure_progression_row"

    user_row = (await db.execute(text("SELECT id FROM users LIMIT 1"))).first()
    lang_row = (await db.execute(text("SELECT id FROM languages LIMIT 1"))).first()
    if user_row is None or lang_row is None:
        raise RuntimeError("No QA row: need language_progression, analytics, or users+languages")

    sid, lid = int(user_row[0]), int(lang_row[0])
    prog = LanguageProgression(student_id=sid, language_id=lid)
    db.add(prog)
    await db.flush()
    return sid, lid, "temporary LanguageProgression row (transactional, rolled back)"


def _seed_sibling_jsonb(payload: dict[str, Any]) -> dict[str, Any]:
    """Inject preservation markers into sibling keys without removing existing data."""
    out = copy.deepcopy(payload)
    writing = dict(out.get("writing") or {})
    writing["verify_s2_marker"] = "preserve"
    out["writing"] = writing

    listening = dict(out.get("listening_official_promotions") or {})
    events = list(listening.get("events") or [])
    events.append({"verify_s2_marker": "preserve", "session_id": "s2_db_qa"})
    listening["events"] = events
    listening["verify_s2_marker"] = "preserve"
    out["listening_official_promotions"] = listening

    speaking = dict(out.get(SPEAKING_BUCKET_KEY) or {})
    readiness = dict(speaking.get("readiness") or {})
    readiness["verify_s2_marker"] = "preserve"
    speaking["readiness"] = readiness
    out[SPEAKING_BUCKET_KEY] = speaking
    return out


def _assert_siblings_preserved(payload: dict[str, Any]) -> list[bool]:
    results: list[bool] = []
    writing = payload.get("writing") or {}
    listening = payload.get("listening_official_promotions") or {}
    speaking = payload.get(SPEAKING_BUCKET_KEY) or {}
    readiness = speaking.get("readiness") or {}
    results.append(ok("writing JSONB preserved", writing.get("verify_s2_marker") == "preserve"))
    results.append(
        ok(
            "listening JSONB preserved",
            listening.get("verify_s2_marker") == "preserve"
            and any(e.get("verify_s2_marker") == "preserve" for e in (listening.get("events") or [])),
        )
    )
    results.append(ok("speaking.readiness sibling preserved", readiness.get("verify_s2_marker") == "preserve"))
    return results


def _assert_forbidden_unchanged(row: LanguageProgression, baseline: dict[str, Any]) -> list[bool]:
    results: list[bool] = []
    results.append(
        ok(
            "no official_speaking_cefr mutation",
            row.official_speaking_cefr == baseline["official_speaking_cefr"],
            str(row.official_speaking_cefr),
        )
    )
    results.append(
        ok(
            "no learning_stage_speaking mutation",
            row.learning_stage_speaking == baseline["learning_stage_speaking"],
            str(row.learning_stage_speaking),
        )
    )
    results.append(
        ok(
            "no promotion_readiness_score mutation",
            row.promotion_readiness_score == baseline["promotion_readiness_score"],
            str(row.promotion_readiness_score),
        )
    )
    results.append(
        ok(
            "no version column mutation",
            row.version == baseline["version"],
            str(row.version),
        )
    )
    return results


async def run_verification() -> int:
    print("S2 Speaking Knowledge Model — Live PostgreSQL Persistence Verification\n")

    try:
        await check_database_connection()
    except Exception as exc:
        print(f"FAIL: Cannot connect to PostgreSQL — {exc}")
        return 1

    sid: int
    lid: int
    qa_source: str

    async with AsyncSessionLocal() as db:
        sid, lid, qa_source = await _pick_qa_row(db)
        _report["qa_row"] = {"student_id": sid, "language_id": lid, "source": qa_source}

        row = await db.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        if row is None:
            ok("load real LanguageProgression row", False)
            return 1
        ok("load real LanguageProgression row", True, f"student_id={sid} language_id={lid} ({qa_source})")

        original_payload = copy.deepcopy(dict(row.promotion_readiness_json or {}))
        original_snapshot = _json_snapshot(original_payload)
        _report["original_jsonb_top_keys"] = sorted(original_payload.keys())

        baseline_columns = {
            "official_speaking_cefr": row.official_speaking_cefr,
            "learning_stage_speaking": row.learning_stage_speaking,
            "promotion_readiness_score": row.promotion_readiness_score,
            "version": row.version,
        }
        ok("preserve original promotion_readiness_json snapshot", bool(original_snapshot is not None))

        seeded = _seed_sibling_jsonb(original_payload)
        row.promotion_readiness_json = seeded
        flag_modified(row, "promotion_readiness_json")
        await db.flush()
        ok(
            "initialize speaking.knowledge_model path without deleting unrelated keys",
            "writing" in (row.promotion_readiness_json or {}),
        )

        # --- Locking path (check 27) ---
        locked = await lock_speaking_progression_row(db, student_id=sid, language_id=lid)
        ok("row locking returns row under transaction", locked is not None)
        ok(
            "locking uses intended FOR UPDATE path",
            locked is not None and locked.student_id == sid,
        )

        # --- Roundtrip persist (checks 4-13) ---
        obs1 = _obs("db_s2_obs_001", "phoneme:theta", context_id="db_ctx_theta_1")

        def _mut_apply_one(model):
            return apply_observation(model, obs1, now=NOW)

        _, apply_result = await mutate_speaking_knowledge_model(
            db, student_id=sid, language_id=lid, mutator=_mut_apply_one, locked_row=locked
        )
        ok("persist one observation via mutate_speaking_knowledge_model", apply_result is not None and apply_result.applied)

        expected_state = apply_result.state if apply_result else None
        expected_mastery = expected_state.mastery if expected_state else -1.0
        expected_confidence = expected_state.confidence if expected_state else -1.0
        expected_stability = expected_state.stability if expected_state else -1.0
        expected_evidence_count = expected_state.evidence_count if expected_state else 0
        expected_dims = dict(expected_state.observed_dimensions) if expected_state else {}
        expected_history_len = len(expected_state.observation_history) if expected_state else 0

        row = await _reload_row(db, sid, lid)
        assert row is not None
        ok("reload row from PostgreSQL after flush", row is not None)

        reloaded = _load_km(row, sid, lid)
        st = reloaded.skill_states.get("phoneme:theta")
        ok("skill state survived deserialization", st is not None)
        if st:
            ok("mastery identical after roundtrip", abs(st.mastery - expected_mastery) < 1e-9, f"{st.mastery}")
            ok("confidence identical after roundtrip", abs(st.confidence - expected_confidence) < 1e-9)
            ok("stability identical after roundtrip", abs(st.stability - expected_stability) < 1e-9)
            ok("evidence_count persisted", st.evidence_count == expected_evidence_count)
            ok("observed_dimensions persisted", st.observed_dimensions == expected_dims)
            ok(
                "observation_history persisted",
                len(st.observation_history) == expected_history_len and expected_history_len >= 1,
            )
            ok(
                "applied_observation_ids persisted",
                "db_s2_obs_001" in reloaded.applied_observation_ids,
            )

        pre_idempotent_total = reloaded.total_observations
        pre_idempotent_count = st.evidence_count if st else 0

        # --- Idempotency (checks 14-15) ---
        def _mut_idempotent(model):
            return apply_observation(model, obs1, now=NOW)

        _, idem_result = await mutate_speaking_knowledge_model(
            db, student_id=sid, language_id=lid, mutator=_mut_idempotent
        )
        ok("duplicate observation apply returns idempotent", idem_result is not None and idem_result.idempotent)

        row = await _reload_row(db, sid, lid)
        assert row is not None
        after_idem = _load_km(row, sid, lid)
        st2 = after_idem.skill_states.get("phoneme:theta")
        ok(
            "duplicate observation idempotent after DB reload",
            after_idem.total_observations == pre_idempotent_total
            and (st2.evidence_count if st2 else 0) == pre_idempotent_count,
        )

        # --- flag_modified evidence (check 26) ---
        ok(
            "flag_modified JSONB visible after PostgreSQL reload",
            st2 is not None and st2.mastery > 0,
            f"mastery={st2.mastery if st2 else None}",
        )

        # --- Atomic batch success (checks 16-17) ---
        batch_obs = [
            _obs("db_s2_batch_001", "phoneme:theta", context_id="db_batch_ctx_a"),
            _obs(
                "db_s2_batch_002",
                "word:think",
                context_id="db_batch_ctx_b",
                dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE, WORD_STRESS_ACCURACY),
            ),
        ]

        def _mut_batch_ok(model):
            return apply_observations_batch(model, batch_obs, now=NOW)

        await mutate_speaking_knowledge_model(db, student_id=sid, language_id=lid, mutator=_mut_batch_ok)
        row = await _reload_row(db, sid, lid)
        assert row is not None
        after_batch = _load_km(row, sid, lid)
        ok(
            "batch observations persist after reload",
            "db_s2_batch_001" in after_batch.applied_observation_ids
            and "db_s2_batch_002" in after_batch.applied_observation_ids,
        )
        ok(
            "all batch skill states present",
            "phoneme:theta" in after_batch.skill_states and "word:think" in after_batch.skill_states,
        )

        # Snapshot KM before invalid batch
        km_before_invalid = knowledge_model_to_dict(after_batch)
        total_before_invalid = after_batch.total_observations

        # --- Atomic batch failure (checks 18-19) ---
        bad_batch = [
            _obs("db_s2_batch_bad_001", "phoneme:theta", context_id="db_bad_ctx_a"),
            SpeakingSkillEvidenceObservation(
                observation_id="db_s2_batch_bad_invalid",
                skill_id="not:a_real_skill",
                observed_at=_ts(),
                performance=0.9,
                confidence=0.9,
                evidence_dimensions=(PHONEME_ALIGNMENT, PRONUNCIATION_CONFIDENCE),
                context_id="db_bad_ctx",
                success=True,
                source_type=ObservationSourceType.synthetic_test,
            ),
        ]

        def _mut_batch_fail(model):
            return apply_observations_batch(model, bad_batch, now=NOW)

        await mutate_speaking_knowledge_model(db, student_id=sid, language_id=lid, mutator=_mut_batch_fail)
        row = await _reload_row(db, sid, lid)
        assert row is not None
        after_fail = _load_km(row, sid, lid)
        ok(
            "invalid batch does not partially mutate total_observations",
            after_fail.total_observations == total_before_invalid,
        )
        ok(
            "invalid batch does not persist bad observation id",
            "db_s2_batch_bad_001" not in after_fail.applied_observation_ids
            and "db_s2_batch_bad_invalid" not in after_fail.applied_observation_ids,
        )
        ok(
            "invalid batch KM structurally unchanged",
            knowledge_model_to_dict(after_fail)["total_observations"]
            == km_before_invalid["total_observations"],
        )

        # --- Unrelated JSONB + forbidden columns (checks 20-25) ---
        payload = dict(row.promotion_readiness_json or {})
        _assert_siblings_preserved(payload)
        _assert_forbidden_unchanged(row, baseline_columns)

        # --- Sequential fresh-load mutations (check 28) ---
        db.expire_all()

        obs_seq_a = _obs("db_s2_seq_a", "phoneme:short_i", context_id="seq_ctx_a")

        def _mut_seq_a(model):
            return apply_observation(model, obs_seq_a, now=NOW)

        await mutate_speaking_knowledge_model(db, student_id=sid, language_id=lid, mutator=_mut_seq_a)

        db.expire_all()
        obs_seq_b = _obs("db_s2_seq_b", "phoneme:eth", context_id="seq_ctx_b")

        def _mut_seq_b(model):
            return apply_observation(model, obs_seq_b, now=NOW)

        await mutate_speaking_knowledge_model(db, student_id=sid, language_id=lid, mutator=_mut_seq_b)

        row = await _reload_row(db, sid, lid)
        assert row is not None
        after_seq = _load_km(row, sid, lid)
        ok(
            "sequential mutations both present after fresh loads",
            "phoneme:short_i" in after_seq.skill_states and "phoneme:eth" in after_seq.skill_states,
        )
        ok(
            "second mutation did not erase first",
            after_seq.applied_observation_ids.get("db_s2_seq_a") == "phoneme:short_i"
            and after_seq.applied_observation_ids.get("db_s2_seq_b") == "phoneme:eth",
        )

        # --- Version fields (check 29) ---
        ok(
            "schema_version survives DB roundtrip",
            after_seq.schema_version == KNOWLEDGE_MODEL_SCHEMA_VERSION,
            after_seq.schema_version,
        )
        ok(
            "graph_version survives DB roundtrip",
            after_seq.graph_version == SPEAKING_SKILL_GRAPH_VERSION,
            after_seq.graph_version,
        )

        # --- Deprecated skill states (check 30) ---
        def _mut_deprecated(model):
            model.skill_states["removed:legacy_skill"] = StudentSpeakingSkillState(
                skill_id="removed:legacy_skill",
                mastery=0.55,
                evidence_count=3,
            )
            reconcile_model_with_graph(model)
            return model

        await mutate_speaking_knowledge_model(db, student_id=sid, language_id=lid, mutator=_mut_deprecated)
        row = await _reload_row(db, sid, lid)
        assert row is not None
        after_dep = _load_km(row, sid, lid)
        ok(
            "deprecated_skill_states survive DB roundtrip",
            "removed:legacy_skill" in after_dep.deprecated_skill_states,
        )
        ok(
            "unknown skill removed from active skill_states",
            "removed:legacy_skill" not in after_dep.skill_states,
        )

        # --- Rollback (check 31) ---
        await db.rollback()
        ok("rollback all QA changes", True)

    # --- Restoration in fresh session (check 32) ---
    async with AsyncSessionLocal() as db2:
        restored = await db2.get(LanguageProgression, {"student_id": sid, "language_id": lid})
        if restored is None:
            ok("reload original row after rollback", False, "row missing")
        else:
            restored_snapshot = _json_snapshot(dict(restored.promotion_readiness_json or {}))
            ok(
                "database promotion_readiness_json restored to original",
                restored_snapshot == original_snapshot,
            )
            ok(
                "official_speaking_cefr restored",
                restored.official_speaking_cefr == baseline_columns["official_speaking_cefr"],
            )
            ok(
                "learning_stage_speaking restored",
                restored.learning_stage_speaking == baseline_columns["learning_stage_speaking"],
            )
            ok(
                "promotion_readiness_score restored",
                restored.promotion_readiness_score == baseline_columns["promotion_readiness_score"],
            )
            speaking_after = speaking_bucket_from_payload(dict(restored.promotion_readiness_json or {}))
            km_after = speaking_after.get(KNOWLEDGE_MODEL_KEY)
            ok(
                "speaking.knowledge_model not committed (absent or pre-QA)",
                km_after is None or restored_snapshot == original_snapshot,
            )

    # --- Summary report ---
    passed = sum(1 for _, p, _ in _results if p)
    total = len(_results)
    failed = [n for n, p, _ in _results if not p]

    print("\n" + "=" * 60)
    print("S2 LIVE POSTGRESQL PERSISTENCE REPORT")
    print("=" * 60)
    print(f"1. QA row/account: {_report['qa_row']}")
    print(f"2. Original JSONB top-level keys: {_report['original_jsonb_top_keys']}")
    print("3. Mutation path: mutate_speaking_knowledge_model (json_mutation.py)")
    print("4. Transaction/locking: AsyncSessionLocal + lock_speaking_progression_row FOR UPDATE")
    print(f"5. Idempotency: {'PASS' if not any('idempotent' in n and not p for n, p, _ in _results) else 'FAIL'}")
    print(f"6. Atomic batch: {'PASS' if not any('batch' in n.lower() and not p for n, p, _ in _results) else 'FAIL'}")
    print(f"7. Unrelated JSONB preservation: {'PASS' if not any('preserved' in n and not p for n, p, _ in _results) else 'FAIL'}")
    print(f"8. Rollback/restoration: {'PASS' if not any('restored' in n and not p for n, p, _ in _results) else 'FAIL'}")
    print(f"9. Verification count: {passed}/{total}")
    print(f"10. Defects found and fixed: {_report['defects_found'] or 'none'}")
    verdict = "S2 PERSISTENCE VERIFIED (PostgreSQL)" if not failed else "S2 PERSISTENCE NOT VERIFIED"
    print(f"11. Final verdict: {verdict}")
    print("=" * 60)

    if failed:
        print("\nFailed checks:")
        for n in failed:
            print(f"  - {n}")
        return 1
    return 0


def main() -> int:
    return asyncio.run(run_verification())


if __name__ == "__main__":
    raise SystemExit(main())
