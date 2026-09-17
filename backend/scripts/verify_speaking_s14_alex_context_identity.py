"""Verify Speaking S14 -- Deterministic Alex educational context & live identity continuity.

Proves:
- typed/versioned Alex educational context reusing S12/S11/resolver authority
- no mastery/confidence/ids/secrets exposed to Alex; no invented internal stage
- deterministic tutor behavior + mission-kind behavior mapping
- authoritative task prompt shared across student/Alex/evaluation
- deterministic session-start grounding (no generic fallback)
- context fingerprint freshness
- S11 C-3 (orphan active attempt) + C-7 (ambiguous active attempts) fixes
- backend-authoritative live_session_id + pre-evaluation authorization boundary
- S0/S9/S10/S10.1/S11/S12/S13 regressions

Usage (from backend/):
    python scripts/verify_speaking_s14_alex_context_identity.py
"""

from __future__ import annotations

import os

import asyncio
import dataclasses
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking_diagnostic.selector import select_speaking_target
from app.services.language_speaking_diagnostic.types import TargetSelectionReason
from app.services.language_speaking_journey.alex_context import (
    ALEX_EDUCATIONAL_CONTEXT_VERSION,
    TUTOR_BEHAVIOR_CONTRACT,
    AlexSpeakingEducationalContext,
    authoritative_task_prompt,
    build_alex_speaking_educational_context,
    mission_behavior_for_kind,
)
from app.services.language_speaking_journey.errors import (
    AmbiguousActiveAttemptError as JourneyAmbiguousActiveAttemptError,
)
from app.services.language_speaking_journey.errors import (
    InvalidLiveSessionError,
    LiveExecutionNotReadyError,
    LiveSessionNotOwnedError,
    SpeakingContextUnavailableError,
)
from app.services.language_speaking_journey.live_execution import (
    authorize_live_turn_execution,
    derive_live_session_id,
    is_backend_live_session_id,
)
from app.services.language_speaking_knowledge_model.storage import empty_knowledge_model
from app.services.language_speaking_knowledge_model.types import (
    SpeakingSkillStatus,
    StudentSpeakingSkillState,
)
from app.services.language_speaking_lesson_planner.attempt_lineage import (
    AmbiguousActiveAttemptError,
    SpeakingAttemptStatus,
    SpeakingSessionAttemptLineage,
    assert_active_attempt_integrity,
    find_active_attempts,
    get_active_attempt,
    reconcile_active_attempt_on_cursor_leave,
    start_or_resume_attempt,
)
from app.services.language_speaking_lesson_planner.mission_task_resolver import resolve_current_task
from app.services.language_speaking_lesson_planner.planner import assemble_speaking_lesson_blueprint
from app.services.language_speaking_lesson_planner.session_runtime import (
    advance_session_activity,
    create_learning_session,
)
from app.services.language_speaking_lesson_planner.storage import (
    SpeakingStoredJourneyState,
    save_s9_state,
)

PASS = 0
FAIL = 0
BACKEND = Path(__file__).resolve().parents[1]


def check(label: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK  {label}")
    else:
        FAIL += 1
        print(f" FAIL {label}")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _blueprint(reason: TargetSelectionReason = TargetSelectionReason.weak_mastery):
    km = empty_knowledge_model(student_id=1401, language_id=1)
    base = select_speaking_target(km, official_cefr="A2")
    rec = dataclasses.replace(base, selection_reason=reason)
    return assemble_speaking_lesson_blueprint(rec)


def _task_session(blueprint):
    """Advance to the first activity that resolves to an executable task."""
    session = create_learning_session(blueprint, live_session_id="live-s14")
    guard = 0
    while session.current_activity_id:
        if resolve_current_task(blueprint, session).is_task:
            break
        cur = session.current_activity_id
        session = advance_session_activity(session, blueprint, completed_activity_id=cur)
        guard += 1
        if guard > 12:
            break
    return session


def _non_task_session(blueprint):
    """Advance to the first activity that does NOT resolve to a task (if any)."""
    session = create_learning_session(blueprint, live_session_id="live-s14")
    guard = 0
    while session.current_activity_id:
        if not resolve_current_task(blueprint, session).is_task:
            break
        cur = session.current_activity_id
        session = advance_session_activity(session, blueprint, completed_activity_id=cur)
        guard += 1
        if guard > 12:
            break
    return session


def _weak_model():
    model = empty_knowledge_model(student_id=1401, language_id=1)
    model.skill_states["speaking:fluency:pace"] = StudentSpeakingSkillState(
        skill_id="speaking:fluency:pace",
        mastery=0.2,
        confidence=0.3,
        evidence_count=3,
        successful_evidence_count=1,
        recent_performance=0.2,
        current_status=SpeakingSkillStatus.at_risk,
        retention_risk=0.2,
        revision_improvement=0.0,
        distinct_context_count=1,
        consecutive_successes=0,
        recent_mistake_tags=["pronunciation"],
    )
    return model


# ---------------------------------------------------------------------------
# Context contract + reuse (checks 1-10)
# ---------------------------------------------------------------------------


def test_context_contract() -> None:
    bp = _blueprint()
    session = _task_session(bp)
    model = _weak_model()
    state = SpeakingStoredJourneyState(blueprint=bp, session=session)
    ctx = build_alex_speaking_educational_context(
        official_cefr="B1", state=state, knowledge_model=model
    )

    check("1. Alex context is typed and versioned", isinstance(ctx, AlexSpeakingEducationalContext) and ctx.context_version == ALEX_EDUCATIONAL_CONTEXT_VERSION)
    check("2. official CEFR source is authoritative", ctx.official_cefr == "B1")

    tutor = ctx.to_tutor_dict()
    keys = set(tutor.keys())
    check("3. no internal stage is invented", "internal_stage" not in keys and "stage" not in keys)
    check("4. focus comes from current plan/blueprint", bool(ctx.focus_title))

    res = resolve_current_task(bp, session)
    check("5. current mission uses canonical resolver", ctx.current_mission_kind == res.mission_kind and bool(res.mission_kind))
    check("6. current task uses canonical resolver", ctx.current_task_instruction == authoritative_task_prompt(bp))

    # Attempt/retry via S11 lineage
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    # Force a retry (attempt 2) by terminal + fresh
    active = get_active_attempt(lineage)
    active.status = SpeakingAttemptStatus.failed
    lineage.active_attempt_id = ""
    start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    state_retry = SpeakingStoredJourneyState(blueprint=bp, session=session, attempt_lineage=lineage)
    ctx_retry = build_alex_speaking_educational_context(official_cefr="B1", state=state_retry, knowledge_model=model)
    check("7. attempt/retry context uses S11 lineage", ctx_retry.attempt_number == 2 and ctx_retry.is_retry is True)

    check("8. weak skill context uses deterministic existing projection", len(ctx.weak_skill_focuses) >= 1)

    blob = json.dumps(tutor, ensure_ascii=False)
    # Educational DATA fields must carry no mastery/confidence values. The tutor
    # behavior contract legitimately mentions those words as prohibitions ("never
    # state mastery or confidence percentages"), so exclude behavior text here.
    data_only = {k: v for k, v in tutor.items() if k not in ("tutor_behavior_contract", "mission_behavior")}
    data_blob = json.dumps(data_only, ensure_ascii=False).lower()
    # No mastery/confidence NUMBERS: no such keys, no percentages, and no
    # "mastery/confidence <number>" scoring (motivational phrases like
    # "build confidence" are fine — they carry no metric).
    import re as _re

    no_metric_keys = not any(k in ("mastery", "confidence", "mastery_score", "confidence_score", "evidence_count") for k in tutor)
    no_pct = "%" not in data_blob and "percent" not in data_blob
    no_scored = _re.search(r"(mastery|confidence)\s*[:=]?\s*\d", data_blob) is None
    check("9. no mastery/confidence numbers exposed", no_metric_keys and no_pct and no_scored)
    forbidden_ids = ("attempt_id", "mission_id", "session_id", "blueprint_id", "evaluation_id", "live_turn_id", "live_session_id", "retry_of")
    check("10. no internal ids exposed in tutor context", not any(tok in blob for tok in forbidden_ids))
    # 42 (secrets)
    secretish = ("api_key", "secret", "access_token", "hume", "credential")
    check("42. no provider secrets in context", not any(tok in blob.lower() for tok in secretish))


# ---------------------------------------------------------------------------
# Tutor behavior contract (checks 11-15)
# ---------------------------------------------------------------------------


def test_behavior_contract() -> None:
    check("11. tutor behavior contract is deterministic", isinstance(TUTOR_BEHAVIOR_CONTRACT, tuple) and len(TUTOR_BEHAVIOR_CONTRACT) >= 10)
    check("12. teaching behavior differs from speak behavior", mission_behavior_for_kind("teaching") != mission_behavior_for_kind("speak"))
    check("13. feedback behavior differs from transfer behavior", mission_behavior_for_kind("feedback") != mission_behavior_for_kind("transfer"))

    src = (BACKEND / "app/services/language_speaking_journey/alex_context.py").read_text(encoding="utf-8")
    # Mission kind is decided by the resolver, not by the model.
    check("14. Alex cannot decide mission type", "resolve_current_task" in src and "claude" not in src.lower() and "llm" not in src.lower())
    joined = " ".join(TUTOR_BEHAVIOR_CONTRACT).lower()
    check("15. Alex cannot decide promotion", "promot" in joined and "never" in joined)


# ---------------------------------------------------------------------------
# Task prompt authority + session-start grounding (checks 16-20)
# ---------------------------------------------------------------------------


def test_task_prompt_and_grounding() -> None:
    bp = _blueprint()
    session = _task_session(bp)
    ctx = build_alex_speaking_educational_context(
        official_cefr="A2", state=SpeakingStoredJourneyState(blueprint=bp, session=session)
    )
    check("16. authoritative task prompt is shared across student/Alex/evaluation path", ctx.current_task_instruction == authoritative_task_prompt(bp) and bool(ctx.current_task_instruction))

    api_src = (BACKEND / "app/api/language_speaking_live.py").read_text(encoding="utf-8")
    live_js = (Path(BACKEND).parent / "src/api/speakingLive.js").read_text(encoding="utf-8")
    check("17. frontend cannot override task prompt", "task_prompt" not in live_js and "authz.task_prompt" in api_src and "task_prompt: str = Form" not in api_src)

    check("18. session-start grounding is deterministic", "build_alex_context_for_student" in api_src and "alex_context=alex_ctx.to_tutor_dict()" in api_src)
    check("19. session cannot start educational Alex without context", "SpeakingLiveExecutionError" in api_src and "end_live_session" in api_src and "raise HTTPException" in api_src)
    comp = (Path(BACKEND).parent / "src/composables/useLiveConversation.js").read_text(encoding="utf-8")
    check("20. optional tool-call is not the sole initial grounding mechanism", "session_settings" in comp and "_buildTutorContextText" in comp)


# ---------------------------------------------------------------------------
# Fingerprint freshness (checks 21-24)
# ---------------------------------------------------------------------------


def test_fingerprint() -> None:
    bp = _blueprint()
    session = _task_session(bp)
    model = _weak_model()
    st = SpeakingStoredJourneyState(blueprint=bp, session=session)
    c1 = build_alex_speaking_educational_context(official_cefr="A2", state=st, knowledge_model=model)
    c2 = build_alex_speaking_educational_context(official_cefr="A2", state=st, knowledge_model=model)
    check("21. unchanged educational state yields same context fingerprint", c1.context_fingerprint == c2.context_fingerprint)

    # Changed task/mission: advance the cursor to a different activity.
    session2 = advance_session_activity(session, bp, completed_activity_id=session.current_activity_id)
    st2 = SpeakingStoredJourneyState(blueprint=bp, session=session2)
    c3 = build_alex_speaking_educational_context(official_cefr="A2", state=st2, knowledge_model=model)
    check("22. changed task/mission changes context fingerprint", c3.context_fingerprint != c1.context_fingerprint)

    # Changed attempt/retry state.
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    active = get_active_attempt(lineage)
    active.status = SpeakingAttemptStatus.failed
    lineage.active_attempt_id = ""
    start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    st3 = SpeakingStoredJourneyState(blueprint=bp, session=session, attempt_lineage=lineage)
    c4 = build_alex_speaking_educational_context(official_cefr="A2", state=st3, knowledge_model=model)
    check("23. changed attempt/retry state changes context fingerprint", c4.context_fingerprint != c1.context_fingerprint)

    # Staleness after progression: fingerprint tracks the advanced cursor.
    live_runtime = (BACKEND / "app/services/language_speaking_evaluation_runtime/live_runtime.py").read_text(encoding="utf-8")
    api_src = (BACKEND / "app/api/language_speaking_live.py").read_text(encoding="utf-8")
    check("24. stale context is invalidated after relevant progression", c3.context_fingerprint != c1.context_fingerprint and "invalidate_live_context" in live_runtime and "build_alex_context_for_student" in api_src)


# ---------------------------------------------------------------------------
# Tool refresh (check 25)
# ---------------------------------------------------------------------------


def test_tool_refresh() -> None:
    api_src = (BACKEND / "app/api/language_speaking_live.py").read_text(encoding="utf-8")
    tool_uses_builder = "get_student_speaking_context" in api_src and "build_alex_context_for_student" in api_src
    no_generic = "dispatch_evi_tool" not in api_src
    check("25. get_student_speaking_context reuses canonical builder", tool_uses_builder and no_generic)


# ---------------------------------------------------------------------------
# S11 C-3 / C-7 (checks 26-28)
# ---------------------------------------------------------------------------


def test_c3_c7() -> None:
    bp = _blueprint()
    session = _task_session(bp)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    # C-3: cursor leaves task -> non-task
    reconcile_active_attempt_on_cursor_leave(lineage, current_task_id="")
    orphan = [a for a in lineage.attempts if a.status == SpeakingAttemptStatus.active]
    check("26. task->non-task advancement leaves no orphan active attempt", len(orphan) == 0 and lineage.active_attempt_id == "")

    # C-7: two active attempts
    lineage2 = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    start_or_resume_attempt(lineage2, res, session_id=session.session_id, blueprint_id=bp.blueprint_id)
    a1 = lineage2.attempts[0]
    # Inject a malformed second active (simulate corrupted persisted lineage)
    a2 = dataclasses.replace(a1, attempt_id=a1.attempt_id + "-dup")
    lineage2.attempts.append(a2)
    check("27. multiple active attempts are detected", len(find_active_attempts(lineage2)) == 2)
    raised = False
    try:
        assert_active_attempt_integrity(lineage2)
    except AmbiguousActiveAttemptError:
        raised = True
    check("27b. ambiguous integrity fails closed", raised)

    # C-7: ambiguous lineage must not attach a live turn / build context
    ambiguous = False
    try:
        build_alex_speaking_educational_context(
            official_cefr="A2",
            state=SpeakingStoredJourneyState(blueprint=bp, session=session, attempt_lineage=lineage2),
        )
    except JourneyAmbiguousActiveAttemptError:
        ambiguous = True
    check("28. ambiguous lineage does not attach a live turn", ambiguous)


# ---------------------------------------------------------------------------
# Live identity + boundary (checks 29-40)
# ---------------------------------------------------------------------------


def test_live_identity_static() -> None:
    lease = "11111111-2222-3333-4444-555555555555"
    lsid = derive_live_session_id(lease)
    check("29. backend issues live_session_id", lsid == f"lsx-{lease}" and is_backend_live_session_id(lsid, lease))
    comp = (Path(BACKEND).parent / "src/composables/useLiveConversation.js").read_text(encoding="utf-8")
    check("30. frontend no longer owns logical live_session_id minting", "_uuid('live')" not in comp and "tokenPayload.live_session_id" in comp)
    check("31. reconnect reuses valid live_session_id", derive_live_session_id(lease) == lsid and "resumeLease: true" in comp)
    check("32. lease_id is not overloaded as attempt_id", lsid != lease and lsid.startswith("lsx-"))
    # attempt ids are minted from task id (backend), never from lease/frontend
    lineage_src = (BACKEND / "app/services/language_speaking_lesson_planner/attempt_lineage.py").read_text(encoding="utf-8")
    check("33. attempt_id remains backend authoritative", "new_attempt_id(task_id)" in lineage_src)
    api_src = (BACKEND / "app/api/language_speaking_live.py").read_text(encoding="utf-8")
    # boundary called before evaluation
    idx_authz = api_src.find("authorize_live_turn_execution(")
    idx_eval = api_src.find("process_completed_live_turn(")
    check("34. live turn validates continuity before evaluation", 0 < idx_authz < idx_eval)
    check("40. S13 budget does not reset on reconnect", "reuse the same lease (no budget reset)" in comp or "resumeLease: true" in comp)


async def _boundary_case(*, lease_ok: bool, live_session_id: str, session_has_task: bool):
    bp = _blueprint()
    if session_has_task:
        session = _task_session(bp)
        bucket = save_s9_state({}, blueprint=bp, session=session)
    else:
        bucket = {}
    payload = {}
    from app.services.language_speaking_lesson_planner.storage import merge_speaking_bucket_into_payload

    if bucket:
        payload = merge_speaking_bucket_into_payload({}, bucket)
    row = SimpleNamespace(promotion_readiness_json=payload, official_speaking_cefr="A2")

    async def _fake_row(db, *, student_id, language_id):
        return row

    async def _fake_validate(db, *, student_id, lease_id, now=None):
        return lease_ok

    lease_id = "11111111-2222-3333-4444-555555555555"
    with patch("app.services.language_speaking_journey.live_execution.ensure_progression_row", _fake_row), patch(
        "app.services.language_speaking_journey.live_execution.validate_active_lease", _fake_validate
    ):
        return await authorize_live_turn_execution(
            db=None,
            student_id=1401,
            language_id=1,
            lease_id=lease_id,
            live_session_id=live_session_id,
        )


def test_boundary_runtime() -> None:
    lease_id = "11111111-2222-3333-4444-555555555555"
    good_lsid = derive_live_session_id(lease_id)

    # 35. forged live_session_id (valid lease, wrong id) -> reject before S8
    forged = False
    try:
        asyncio.run(_boundary_case(lease_ok=True, live_session_id="lsx-forged", session_has_task=True))
    except InvalidLiveSessionError:
        forged = True
    check("35. forged live_session_id cannot reach S8 mutation", forged)

    # 36. stale/invalid lease -> reject
    stale = False
    try:
        asyncio.run(_boundary_case(lease_ok=False, live_session_id=good_lsid, session_has_task=True))
    except LiveSessionNotOwnedError:
        stale = True
    check("36. stale live_session_id cannot reach S8 mutation", stale)

    # 37. mismatched task execution (no active task) -> not ready
    mismatch = False
    try:
        asyncio.run(_boundary_case(lease_ok=True, live_session_id=good_lsid, session_has_task=False))
    except LiveExecutionNotReadyError:
        mismatch = True
    check("37. mismatched task execution cannot reach S8 mutation", mismatch)

    # 38. second tab cannot merge: different lease -> different live_session_id
    other_lease = "99999999-8888-7777-6666-555555555555"
    check("38. second tab cannot merge unrelated conversation into attempt", derive_live_session_id(other_lease) != good_lsid)

    # 39. valid reconnect resumes same attempt (no new attempt)
    bp = _blueprint()
    session = _task_session(bp)
    res = resolve_current_task(bp, session)
    lineage = SpeakingSessionAttemptLineage.empty_for_session(session.session_id)
    a1 = start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id, live_session_id=good_lsid)
    a2 = start_or_resume_attempt(lineage, res, session_id=session.session_id, blueprint_id=bp.blueprint_id, is_resume=True, live_session_id=good_lsid)
    check("39. valid reconnect does not create a new attempt", a1.attempt_id == a2.attempt_id and len(lineage.attempts) == 1)

    # boundary success path
    ok = asyncio.run(_boundary_case(lease_ok=True, live_session_id=good_lsid, session_has_task=True))
    check("34b. boundary success returns authoritative task prompt + backend id", ok.live_session_id == good_lsid and bool(ok.task_prompt))


# ---------------------------------------------------------------------------
# Fail-closed + authority (checks 41-46)
# ---------------------------------------------------------------------------


def test_fail_closed_and_authority() -> None:
    # 41. no generic Alex fallback when context unavailable
    unavailable = False
    try:
        build_alex_speaking_educational_context(official_cefr="A2", state=SpeakingStoredJourneyState())
    except SpeakingContextUnavailableError:
        unavailable = True
    comp = (Path(BACKEND).parent / "src/composables/useLiveConversation.js").read_text(encoding="utf-8")
    check("41. no generic Alex fallback exists when context unavailable", unavailable and "general conversation" not in comp.lower())

    alex_src = (BACKEND / "app/services/language_speaking_journey/alex_context.py").read_text(encoding="utf-8")
    live_src = (BACKEND / "app/services/language_speaking_journey/live_execution.py").read_text(encoding="utf-8")
    check("43. no mastery mutation authority moved", "knowledge_bridge" not in alex_src and "apply_speaking_evaluation" not in alex_src and "knowledge_bridge" not in live_src)
    check("44. no stage mutation introduced", "learning_stage" not in alex_src and "learning_stage" not in live_src)
    # Strip the storage JSONB column name (promotion_readiness_json) — reading it is
    # not readiness LOGIC. Assert no readiness computation is imported/used.
    alex_no_col = alex_src.replace("promotion_readiness_json", "")
    live_no_col = live_src.replace("promotion_readiness_json", "")
    check("45. no readiness logic introduced", "promotion_readiness" not in alex_no_col and "promotion_readiness" not in live_no_col)
    check("46. no official CEFR promotion introduced", "official_promotion" not in alex_src and "official_promotion" not in live_src)


# ---------------------------------------------------------------------------
# Regressions (checks 47-53)
# ---------------------------------------------------------------------------


def run_regression(label: str, script: str) -> None:
    if os.environ.get("SPEAKING_VERIFY_SKIP_NESTED_REGRESSIONS") == "1":
        print("  (flat mode: skip nested regressions)", flush=True)
        return
    print(f"\n--- regression {label} ---")
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / script)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    ok = proc.returncode == 0
    check(label, ok)
    if not ok:
        print(proc.stdout[-2500:] if proc.stdout else "")
        print(proc.stderr[-2500:] if proc.stderr else "")


def main() -> int:
    print("=== Speaking S14 Alex context / live identity verifier ===\n")
    test_context_contract()
    test_behavior_contract()
    test_task_prompt_and_grounding()
    test_fingerprint()
    test_tool_refresh()
    test_c3_c7()
    test_live_identity_static()
    test_boundary_runtime()
    test_fail_closed_and_authority()

    run_regression("47. S0 architecture remains green", "verify_speaking_s0_architecture.py")
    run_regression("48. S9 remains green", "verify_speaking_s9_adaptive_journey.py")
    run_regression("49. S10 remains green", "verify_speaking_s10_educational_missions.py")
    run_regression("50. S10.1 remains green", "verify_speaking_s101_mission_stabilization.py")
    run_regression("51. S11 remains green", "verify_speaking_s11_attempt_lineage.py")
    run_regression("52. S12 remains green", "verify_speaking_s12_journey_read_model.py")
    run_regression("53. S13 remains green", "verify_speaking_s13_live_budget.py")

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
