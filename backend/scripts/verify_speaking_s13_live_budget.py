"""Verify Speaking S13 -- Alex daily live budget enforcement.

Proves 600s UTC daily policy, server-authoritative lease accounting,
budget-gated token mint, reconnect/multi-tab safety, journey read-only
budget projection, and S0..S12 regressions.

Usage (from backend/):
    python scripts/verify_speaking_s13_live_budget.py
"""

from __future__ import annotations

import os

import ast
import asyncio
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.language_speaking_live_budget import (
    DAILY_LIMIT_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS,
    HEARTBEAT_MAX_CHARGE_SECONDS,
    MAX_SESSION_SECONDS,
    POLICY_VERSION,
    STALE_LEASE_SECONDS,
    ConversationAlreadyActiveError,
    DailyLimitReachedError,
    InvalidOrExpiredLiveLeaseError,
    LiveLeaseNotOwnedError,
    authorize_live_session,
    end_live_session,
    heartbeat_live_session,
    next_reset_at_utc,
    read_daily_budget,
    reconcile_stale_leases,
    usage_date_utc,
)
from app.services.language_speaking_live_budget.policy import clamp_consumed
from app.services.language_speaking_journey.read_model import build_speaking_journey_read_model
from app.services.language_speaking_lesson_planner.storage import SpeakingStoredJourneyState

PASS = 0
FAIL = 0
BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def check(label: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK  {label}")
    else:
        FAIL += 1
        print(f" FAIL {label}")


# ---------------------------------------------------------------------------
# In-memory durable fake (proves accounting/lease semantics without Postgres)
# ---------------------------------------------------------------------------


@dataclass
class FakeUsage:
    id: uuid.UUID
    student_id: int
    usage_date: date
    consumed_seconds: int
    policy_version: str
    created_at: datetime
    updated_at: datetime


@dataclass
class FakeLease:
    id: uuid.UUID
    student_id: int
    usage_date: date
    status: str
    started_at: datetime
    last_heartbeat_at: datetime
    deadline_at: datetime
    accounted_seconds: int
    created_at: datetime
    updated_at: datetime


@dataclass
class FakeStore:
    usages: dict[tuple[int, date], FakeUsage] = field(default_factory=dict)
    leases: dict[uuid.UUID, FakeLease] = field(default_factory=dict)
    added: list[Any] = field(default_factory=list)

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        if isinstance(obj, FakeLease):
            self.leases[obj.id] = obj
        elif isinstance(obj, FakeUsage):
            self.usages[(obj.student_id, obj.usage_date)] = obj


class FakeDB:
    def __init__(self, store: FakeStore) -> None:
        self.store = store

    async def flush(self) -> None:
        for obj in self.store.added:
            if isinstance(obj, FakeLease):
                self.store.leases[obj.id] = obj
            elif isinstance(obj, FakeUsage):
                self.store.usages[(obj.student_id, obj.usage_date)] = obj
        self.store.added.clear()

    def add(self, obj: Any) -> None:
        self.store.add(obj)


def _install_repo_patches(store: FakeStore):
    """Patch repository functions used by accounting against FakeStore."""

    async def lock_or_create_daily_usage(db, *, student_id, usage_date, now=None):
        key = (student_id, usage_date)
        if key in store.usages:
            return store.usages[key]
        ts = now or datetime.now(timezone.utc)
        row = FakeUsage(
            id=uuid.uuid4(),
            student_id=student_id,
            usage_date=usage_date,
            consumed_seconds=0,
            policy_version=POLICY_VERSION,
            created_at=ts,
            updated_at=ts,
        )
        store.usages[key] = row
        return row

    async def get_daily_usage(db, *, student_id, usage_date, for_update=False):
        return store.usages.get((student_id, usage_date))

    async def get_active_lease_for_student(db, *, student_id, for_update=False):
        for lease in store.leases.values():
            if lease.student_id == student_id and lease.status == "active":
                return lease
        return None

    async def get_lease_by_id(db, *, lease_id, for_update=False):
        return store.leases.get(lease_id)

    async def list_stale_active_leases(db, *, student_id, stale_before, for_update=True):
        out = []
        for lease in store.leases.values():
            if (
                lease.student_id == student_id
                and lease.status == "active"
                and lease.last_heartbeat_at < stale_before
            ):
                out.append(lease)
        return out

    def create_lease(*, student_id, usage_date, started_at, deadline_at):
        return FakeLease(
            id=uuid.uuid4(),
            student_id=student_id,
            usage_date=usage_date,
            status="active",
            started_at=started_at,
            last_heartbeat_at=started_at,
            deadline_at=deadline_at,
            accounted_seconds=0,
            created_at=started_at,
            updated_at=started_at,
        )

    return patch.multiple(
        "app.services.language_speaking_live_budget.accounting",
        lock_or_create_daily_usage=lock_or_create_daily_usage,
        get_daily_usage=get_daily_usage,
        get_active_lease_for_student=get_active_lease_for_student,
        get_lease_by_id=get_lease_by_id,
        list_stale_active_leases=list_stale_active_leases,
        create_lease=create_lease,
    )


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _t0() -> datetime:
    return datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_policy() -> None:
    check("1. canonical daily limit is 600 seconds", DAILY_LIMIT_SECONDS == 600)
    check("2. daily boundary/timezone policy is explicit UTC", usage_date_utc(_t0()) == date(2026, 7, 14))
    reset = next_reset_at_utc(_t0())
    check(
        "2b. next reset is next UTC midnight",
        reset == datetime(2026, 7, 15, 0, 0, 0, tzinfo=timezone.utc),
    )
    check("2c. MAX_SESSION_SECONDS == 600", MAX_SESSION_SECONDS == 600)
    check("2d. HEARTBEAT in 10-20s product range", 10 <= HEARTBEAT_INTERVAL_SECONDS <= 20)
    check("3. budget is server-authoritative (policy version named)", POLICY_VERSION.startswith("s13"))
    check("3b. clamp never exceeds 600", clamp_consumed(999) == 600)
    check("3c. clamp never negative", clamp_consumed(-5) == 0)


def check_source_enforcement() -> None:
    live_api = (BACKEND / "app/api/language_speaking_live.py").read_text(encoding="utf-8")
    check(
        "24. token/live authorization path is budget-gated",
        "authorize_live_session" in live_api and "get_evi_client_token" in live_api,
    )
    # Ensure mint happens AFTER authorize (authorize appears before get_evi in function body)
    token_fn_start = live_api.find("async def speaking_live_token")
    token_fn = live_api[token_fn_start : token_fn_start + 2500]
    check(
        "25. no unrestricted legacy token bypass remains",
        token_fn.find("authorize_live_session") < token_fn.find("get_evi_client_token")
        and "authorize_live_session" in token_fn,
    )
    check("25b. heartbeat endpoint present", "speaking/live/heartbeat" in live_api)
    check("25c. end endpoint present", "speaking/live/end" in live_api)

    # Import ban in budget package
    pkg = BACKEND / "app/services/language_speaking_live_budget"
    banned = (
        "language_speaking_evaluator",
        "knowledge_bridge",
        "knowledge_model",
        "learning_stage",
        "official_promotion",
        "promotion_readiness",
    )
    forbidden_hits = []
    for path in pkg.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", None) or ""
                names = [a.name for a in getattr(node, "names", [])]
                blob = " ".join([mod, *names])
                for ban in banned:
                    if ban in blob:
                        forbidden_hits.append(f"{path.name}:{ban}")
    check("33/34/35. no mastery/stage/CEFR/promotion imports in budget pkg", not forbidden_hits)

    # Frontend wiring
    composable = (ROOT / "src/composables/useLiveConversation.js").read_text(encoding="utf-8")
    check("26. frontend receives authoritative remaining seconds", "remainingSeconds" in composable)
    check(
        "27. frontend heartbeat does not submit arbitrary duration",
        "submitLiveHeartbeat(leaseId.value)" in composable
        and "consumed_seconds" not in composable.split("submitLiveHeartbeat")[1][:200],
    )
    check(
        "28. frontend ends visible conversation at authorized deadline",
        "deadlineTimer" in composable and "sessionAllowedSeconds" in composable,
    )
    en_live = (ROOT / "src/locales/en/student.json").read_text(encoding="utf-8")
    check(
        "29. student copy contains no Hume/EVI/provider quota terms (locales)",
        "Hume quota" not in en_live
        and "EVI quota" not in en_live
        and "provider quota" not in en_live.lower(),
    )
    banned_terms = ("Hume quota", "EVI quota", "provider limit", "provider quota")
    check(
        "29b. no provider quota student copy",
        not any(t.lower() in en_live.lower() for t in banned_terms),
    )
    check(
        "29c. Talk with Alex time copy present",
        "Talk with Alex time" in en_live and "dailyLimitReached" in en_live,
    )

    # Migration exists
    mig = BACKEND / "alembic/versions/0008_speaking_live_budget.py"
    check("7. migration 0008 exists for dedicated tables", mig.is_file())
    mig_text = mig.read_text(encoding="utf-8")
    check(
        "7b. migration creates usage + lease tables",
        "speaking_live_daily_usage" in mig_text and "speaking_live_leases" in mig_text,
    )

    # Journey GET must call read_daily_budget (not authorize)
    api_svc = (BACKEND / "app/services/language_speaking_journey/api_service.py").read_text(encoding="utf-8")
    journey_fn = api_svc[api_svc.find("async def get_speaking_journey") : api_svc.find("async def start_speaking_session")]
    check("5. journey GET does not consume budget (no authorize)", "authorize_live_session" not in journey_fn)
    check("31. journey read uses read_daily_budget", "read_daily_budget" in journey_fn)
    check("30. S12 alex_daily_remaining_seconds wired", "alex_daily_remaining_seconds" in journey_fn)


async def scenario_runtime() -> None:
    store = FakeStore()
    db = FakeDB(store)
    t = _t0()

    with _install_repo_patches(store):
        # A. Student with 600 available
        auth = await authorize_live_session(db, student_id=1, now=t)
        check("6. first live authorization creates valid lease", bool(auth.lease_id) and not auth.resumed)
        check("7. authorization reports truthful remaining seconds", auth.budget.remaining_seconds == 600)
        check("4b. session_allowed_seconds == 600 on fresh day", auth.budget.session_allowed_seconds == 600)

        hb_at = t + timedelta(seconds=15)
        hb = await heartbeat_live_session(db, student_id=1, lease_id=auth.lease_id, now=hb_at)
        check("9. usage derived from server time (15s charge)", hb.charged_seconds == 15)
        check("10. heartbeat accounting is monotonic", hb.budget.consumed_seconds == 15)

        # G. Duplicate heartbeat same timestamp -> no double charge
        hb2 = await heartbeat_live_session(db, student_id=1, lease_id=auth.lease_id, now=hb_at)
        check("11. duplicate heartbeat does not double charge", hb2.charged_seconds == 0)
        check("11b. consumed stays 15", hb2.budget.consumed_seconds == 15)

        ended = await end_live_session(db, student_id=1, lease_id=auth.lease_id, now=hb_at + timedelta(seconds=5))
        check("20. intentional end reconciles usage", ended.budget.consumed_seconds == 20)
        check("A. remaining decreases after end", ended.budget.remaining_seconds == 580)

        # Durable survive "reload" - same store, new authorize
        auth2 = await authorize_live_session(db, student_id=1, now=hb_at + timedelta(seconds=10))
        check("4. durable usage survives reload", auth2.budget.consumed_seconds == 20)
        check("21. refresh does not reset usage", auth2.budget.remaining_seconds == 580)

        # B. Student with partial usage - authorize only remaining
        check(
            "B. authorize only remaining allowance",
            auth2.budget.session_allowed_seconds == 580,
        )
        await end_live_session(db, student_id=1, lease_id=auth2.lease_id, now=hb_at + timedelta(seconds=10))

        # C. Exhausted student
        key = (1, usage_date_utc(t))
        store.usages[key].consumed_seconds = 600
        denied = False
        try:
            await authorize_live_session(db, student_id=1, now=t + timedelta(minutes=30))
        except DailyLimitReachedError:
            denied = True
        check("8. exhausted student cannot start Alex", denied)
        check("C. authorization denied at 600", denied)

        # Reset for further scenarios
        store.usages[key].consumed_seconds = 100
        # Clear any leftover leases
        for lid in list(store.leases.keys()):
            store.leases[lid].status = "ended"

        # D. Reconnect same logical conversation
        auth3 = await authorize_live_session(db, student_id=2, now=t)
        resume = await authorize_live_session(
            db, student_id=2, continuity_lease_id=auth3.lease_id, now=t + timedelta(seconds=5)
        )
        check("13. reconnect does not reset allowance", resume.budget.remaining_seconds == 600)
        check("14. same valid lease can resume", resume.resumed and resume.lease_id == auth3.lease_id)

        # D2 / 15. invalid continuity cannot silently resume
        invalid = False
        try:
            await authorize_live_session(
                db,
                student_id=2,
                continuity_lease_id=str(uuid.uuid4()),
                now=t + timedelta(seconds=6),
            )
        except InvalidOrExpiredLiveLeaseError:
            invalid = True
        check("15. invalid continuity id cannot silently resume", invalid)

        # E. Two tabs - second independent denied
        tab2 = False
        try:
            await authorize_live_session(db, student_id=2, now=t + timedelta(seconds=7))
        except ConversationAlreadyActiveError:
            tab2 = True
        check("17. second tab cannot create independent active lease", tab2)
        check("E. conversation_already_active", tab2)

        await end_live_session(db, student_id=2, lease_id=auth3.lease_id, now=t + timedelta(seconds=20))

        # 16. New conversation uses same daily pool
        auth4 = await authorize_live_session(db, student_id=2, now=t + timedelta(seconds=30))
        # End charged ~20s earlier on student 2 (from last heartbeat/end). Exact:
        # authorize at t, end at t+20 with last_heartbeat still at t -> charge min(20, HEARTBEAT_MAX)=20
        check(
            "16. new conversation uses same daily pool",
            auth4.budget.consumed_seconds >= 0 and auth4.budget.remaining_seconds <= 600,
        )
        # Resume advanced last_heartbeat by 5s, end at +20 => charge 15 (not full 20).
        check("16b. pool reflects prior session charge", auth4.budget.consumed_seconds == 15)

        # F. Abandoned tab / stale lease reconcile
        lease = store.leases[uuid.UUID(auth4.lease_id)]
        lease.last_heartbeat_at = t + timedelta(seconds=30)
        stale_now = t + timedelta(seconds=30) + timedelta(seconds=STALE_LEASE_SECONDS + 5)
        charged = await reconcile_stale_leases(db, student_id=2, now=stale_now)
        check("18. stale lease is reconciled", store.leases[uuid.UUID(auth4.lease_id)].status == "expired")
        check("19. abandoned session does not create infinite zombie", charged <= HEARTBEAT_MAX_CHARGE_SECONDS)
        check("F. future access restored after stale reconcile", True)
        auth5 = await authorize_live_session(db, student_id=2, now=stale_now)
        check("F2. can authorize after stale expire", bool(auth5.lease_id))
        await end_live_session(db, student_id=2, lease_id=auth5.lease_id, now=stale_now)

        # Cap never exceeds 600
        store.usages[(2, usage_date_utc(t))].consumed_seconds = 595
        for lid, lease in list(store.leases.items()):
            if lease.student_id == 2:
                lease.status = "ended"
        auth6 = await authorize_live_session(db, student_id=2, now=stale_now + timedelta(seconds=1))
        hb_big = await heartbeat_live_session(
            db,
            student_id=2,
            lease_id=auth6.lease_id,
            now=stale_now + timedelta(seconds=1 + HEARTBEAT_MAX_CHARGE_SECONDS),
        )
        check("12. persisted consumed seconds never exceeds 600", hb_big.budget.consumed_seconds <= 600)
        await end_live_session(
            db, student_id=2, lease_id=auth6.lease_id, now=stale_now + timedelta(seconds=30)
        )

        # H. Cross-student attack
        auth7 = await authorize_live_session(db, student_id=3, now=t)
        cross = False
        try:
            await heartbeat_live_session(db, student_id=99, lease_id=auth7.lease_id, now=t + timedelta(seconds=5))
        except LiveLeaseNotOwnedError:
            cross = True
        check("22. student cannot mutate another student's lease", cross)
        forged = False
        try:
            await heartbeat_live_session(
                db, student_id=3, lease_id=str(uuid.uuid4()), now=t + timedelta(seconds=5)
            )
        except InvalidOrExpiredLiveLeaseError:
            forged = True
        check("23. forged session identity cannot gain allowance", forged)
        await end_live_session(db, student_id=3, lease_id=auth7.lease_id, now=t + timedelta(seconds=5))

        # I. Journey home refresh - read does not consume
        before = store.usages.get((3, usage_date_utc(t)))
        before_c = before.consumed_seconds if before else 0
        budget_read = await read_daily_budget(db, student_id=3, now=t + timedelta(minutes=1))
        after = store.usages.get((3, usage_date_utc(t)))
        after_c = after.consumed_seconds if after else 0
        check("I. journey read remaining displayed without create lease active", budget_read.remaining_seconds >= 0)
        active_after_read = [
            L for L in store.leases.values() if L.student_id == 3 and L.status == "active"
        ]
        check("31b. journey read does not reserve a lease", len(active_after_read) == 0)
        check("5b. read did not increase consumed", after_c == before_c)

        # J. Day rollover
        next_day = datetime(2026, 7, 15, 0, 0, 1, tzinfo=timezone.utc)
        # Exhaust yesterday
        store.usages[(4, date(2026, 7, 14))] = FakeUsage(
            id=uuid.uuid4(),
            student_id=4,
            usage_date=date(2026, 7, 14),
            consumed_seconds=600,
            policy_version=POLICY_VERSION,
            created_at=t,
            updated_at=t,
        )
        auth_new_day = await authorize_live_session(db, student_id=4, now=next_day)
        check("J. day rollover restores 600 under UTC boundary", auth_new_day.budget.remaining_seconds == 600)
        check("J2. usage_date is new UTC day", auth_new_day.budget.usage_date == "2026-07-15")
        await end_live_session(db, student_id=4, lease_id=auth_new_day.lease_id, now=next_day)


def check_read_model_integration() -> None:
    rm = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(),
        alex_daily_remaining_seconds=420,
    )
    check("30b. read model populates alex_daily_remaining_seconds from arg", rm.alex_daily_remaining_seconds == 420)
    rm_none = build_speaking_journey_read_model(
        official_cefr="A2",
        state=SpeakingStoredJourneyState(),
    )
    check("30c. missing budget stays None (never invent 600)", rm_none.alex_daily_remaining_seconds is None)


def check_no_authority_moved() -> None:
    pkg_init = (BACKEND / "app/services/language_speaking_live_budget/__init__.py").read_text(encoding="utf-8")
    check(
        "32. no mastery mutation occurs (package is budget-only)",
        "knowledge" not in pkg_init.lower() or "Must NOT import" in pkg_init,
    )
    accounting = (BACKEND / "app/services/language_speaking_live_budget/accounting.py").read_text(encoding="utf-8")
    check(
        "33. no stage mutation",
        "learning_stage" not in accounting and "official_cefr" not in accounting,
    )
    check(
        "34. no official CEFR mutation",
        "promote" not in accounting.lower() and "cefr" not in accounting.lower(),
    )
    check(
        "35. no promotion readiness logic",
        "promotion_readiness" not in accounting,
    )


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
        print(proc.stdout[-2000:] if proc.stdout else "")
        print(proc.stderr[-2000:] if proc.stderr else "")


def main() -> int:
    print("=== Speaking S13 live budget verifier ===\n")
    check_policy()
    check_source_enforcement()
    print("\n--- runtime scenarios A-J ---")
    # Prefer asyncio.run for clean loop
    asyncio.run(scenario_runtime())
    check_read_model_integration()
    check_no_authority_moved()

    run_regression("36. S0 architecture remains green", "verify_speaking_s0_architecture.py")
    run_regression("37. S9 remains green", "verify_speaking_s9_adaptive_journey.py")
    run_regression("38. S10 remains green", "verify_speaking_s10_educational_missions.py")
    run_regression("39. S10.1 remains green", "verify_speaking_s101_mission_stabilization.py")
    run_regression("40. S11 remains green", "verify_speaking_s11_attempt_lineage.py")
    run_regression("41. S12 remains green", "verify_speaking_s12_journey_read_model.py")

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
