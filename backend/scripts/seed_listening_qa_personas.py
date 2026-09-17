"""Seed QA listening personas (Students A–G) for browser verification.

Usage (from backend/):
    python scripts/seed_listening_qa_personas.py
    python scripts/seed_listening_qa_personas.py --list
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.models  # noqa: F401

from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.test_users import TEST_USER_PASSWORD
from app.db.session import AsyncSessionLocal
from app.models.enrollment import OnboardingStep as StudentOnboardingStep
from app.models.language.analytics import LanguageAnalytics
from app.models.language.content import LanguageContentItem
from app.models.language.enums import LanguageLevel, LanguageOnboardingStep, LanguageSkill
from app.models.language.profile import LanguageStudentProfile
from app.models.language.progression import LanguageProgression
from app.models.profile import StudentProfile
from app.models.user import User, UserRole
from app.services.language_learner_memory_service import update_memory
from app.services.language_learning_stage.storage import save_listening_stage
from app.services.language_learning_stage.types import STAGE_DISPLAY_NAMES, ListeningLearningStage
from app.services.language_listening_challenge.constants import CHALLENGE_KEY
from app.services.language_listening_challenge.storage import save_student_challenge
from app.services.language_listening_challenge.types import ChallengeLessonRecord, ChallengeLevel, ChallengeState
from app.services.language_listening_confidence.constants import CONFIDENCE_KEY
from app.services.language_listening_confidence.storage import (
    build_initial_confidence_state,
    save_student_confidence,
)
from app.services.language_listening_confidence.types import ObjectiveEvidenceRecord
from app.services.language_listening_curriculum.objectives import level_objectives
from app.services.language_progression_service import upsert_official_levels
from app.services.language_promotion_readiness import ReadinessStatus, evaluate_and_persist_listening_promotion_readiness
from app.services.language_promotion_test import PromotionTestOutcome, clear_sessions_for_tests
from app.services.language_promotion_test.builder import build_promotion_test_session
from app.services.language_subscription_service import get_default_language, get_default_product
from app.services.language_promotion_test_api import get_listening_promotion_test_status

QA_DOMAIN = "@eduspark-test.dev"
PASSWORD = TEST_USER_PASSWORD

STAGE_NAMES = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}


@dataclass(frozen=True, slots=True)
class PersonaSpec:
    key: str
    email: str
    name: str
    listening_cefr: LanguageLevel
    learning_stage: int
    adaptive_tier: str
    goal: str
    seed_passed_test: bool = False


PERSONAS: tuple[PersonaSpec, ...] = (
    PersonaSpec(
        "A",
        f"qa.listening.student-a{QA_DOMAIN}",
        "QA Listening Student A",
        LanguageLevel.A1,
        1,
        "fresh",
        "Build listening foundations for daily life",
    ),
    PersonaSpec(
        "B",
        f"qa.listening.student-b{QA_DOMAIN}",
        "QA Listening Student B",
        LanguageLevel.A2,
        1,
        "developing",
        "Understand everyday conversations",
    ),
    PersonaSpec(
        "C",
        f"qa.listening.student-c{QA_DOMAIN}",
        "QA Listening Student C",
        LanguageLevel.A2,
        2,
        "intermediate",
        "Follow podcasts and group discussions",
    ),
    PersonaSpec(
        "D",
        f"qa.listening.student-d{QA_DOMAIN}",
        "QA Listening Student D",
        LanguageLevel.A2,
        3,
        "near_unlock",
        "Prepare for B1 promotion",
    ),
    PersonaSpec(
        "E",
        f"qa.listening.student-e{QA_DOMAIN}",
        "QA Listening Student E",
        LanguageLevel.A2,
        3,
        "promotion_ready",
        "Unlock A2 to B1 promotion test",
    ),
    PersonaSpec(
        "F",
        f"qa.listening.student-f{QA_DOMAIN}",
        "QA Listening Student F",
        LanguageLevel.A2,
        3,
        "promotion_ready",
        "Complete official promotion to B1",
        seed_passed_test=True,
    ),
    PersonaSpec(
        "G",
        f"qa.listening.student-g{QA_DOMAIN}",
        "QA Listening Student G",
        LanguageLevel.B1,
        1,
        "normal_b1",
        "Reach B2 listening proficiency",
    ),
)


def _rich_evidence() -> ObjectiveEvidenceRecord:
    return ObjectiveEvidenceRecord(
        difficulty={"easy": 2, "normal": 3, "hard": 2, "exam": 1},
        formats={
            "dialogue": 2,
            "monologue": 2,
            "interview": 1,
            "lecture": 1,
            "discussion": 1,
            "panel": 1,
            "podcast": 1,
            "news": 1,
        },
        topics={
            "travel": 2,
            "business": 2,
            "education": 1,
            "health": 1,
            "technology": 1,
            "daily_life": 2,
            "customer_service": 1,
            "meetings": 1,
            "announcements": 1,
            "museum": 1,
        },
        speakers={"single": 2, "two": 2, "multi": 1},
        speed={"slow": 1, "normal": 2, "fast": 1},
    )


def _moderate_evidence() -> ObjectiveEvidenceRecord:
    return ObjectiveEvidenceRecord(
        difficulty={"easy": 1, "normal": 2, "hard": 1},
        formats={"dialogue": 1, "monologue": 1, "interview": 1, "podcast": 1},
        topics={"travel": 1, "daily_life": 1, "business": 1, "technology": 1},
        speakers={"single": 1, "two": 1},
        speed={"normal": 1, "slow": 1},
    )


def _minimal_evidence() -> ObjectiveEvidenceRecord:
    return ObjectiveEvidenceRecord(
        difficulty={"easy": 1},
        formats={"dialogue": 1},
        topics={"daily_life": 1},
        speakers={"single": 1},
        speed={"slow": 1},
    )


def _challenge_history(lesson_index: int, *, quality: str) -> list[ChallengeLessonRecord]:
    profiles = {
        "high": (0.80, 0.92, ChallengeLevel.hard),
        "mid": (0.74, 0.78, ChallengeLevel.normal),
        "low": (0.58, 0.62, ChallengeLevel.easy),
    }
    accuracy, review_perf, level = profiles.get(quality, profiles["mid"])
    records: list[ChallengeLessonRecord] = []
    for i in range(1, max(1, lesson_index) + 1):
        records.append(
            ChallengeLessonRecord(
                lesson_index=i,
                accuracy=accuracy,
                passed=True,
                confidence_trend=0.04,
                evidence_growth=0.06,
                review_performance=review_perf,
                was_review=(i % 4 == 0),
                success_streak=min(i, 6),
                failure_streak=0,
                lesson_score=accuracy,
            )
        )
    return records


def _build_confidence(level: str, *, lesson_index: int, confidence: float, evidence: ObjectiveEvidenceRecord):
    state = build_initial_confidence_state(level)
    state.lesson_index = lesson_index
    for rec in state.objectives.values():
        rec.confidence = confidence
        rec.last_update_index = max(0, lesson_index - 1)
        rec.trend = 0.04
        rec.exposure_count = max(1, lesson_index // 2)
        rec.evidence = evidence
        rec.history = [max(0.25, confidence - 0.08 + i * 0.015) for i in range(min(6, max(1, lesson_index)))]
    return state


def _build_challenge(level: str, *, lesson_index: int, quality: str) -> ChallengeState:
    profiles = {
        "high": (0.80, ChallengeLevel.hard),
        "mid": (0.58, ChallengeLevel.normal),
        "low": (0.45, ChallengeLevel.easy),
    }
    score, current = profiles.get(quality, profiles["mid"])
    state = ChallengeState(
        level=level,
        current_level=current,
        challenge_score=score,
        lesson_index=lesson_index,
        history=_challenge_history(lesson_index, quality=quality),
        last_adjustment_reason="qa_seed",
    )
    return state


TIER_PROFILES: dict[str, dict[str, object]] = {
    "fresh": {"lesson_index": 0, "confidence": 0.35, "evidence": "minimal", "challenge": "low"},
    "developing": {"lesson_index": 5, "confidence": 0.55, "evidence": "minimal", "challenge": "low"},
    "intermediate": {"lesson_index": 8, "confidence": 0.65, "evidence": "moderate", "challenge": "mid"},
    "near_unlock": {"lesson_index": 12, "confidence": 0.80, "evidence": "moderate", "challenge": "mid", "curriculum": 20},
    "promotion_ready": {"lesson_index": 18, "confidence": 0.95, "evidence": "rich", "challenge": "high", "curriculum": 0, "master_all": True},
    "normal_b1": {"lesson_index": 4, "confidence": 0.52, "evidence": "minimal", "challenge": "mid"},
}


def _evidence_for(kind: str) -> ObjectiveEvidenceRecord:
    if kind == "rich":
        return _rich_evidence()
    if kind == "moderate":
        return _moderate_evidence()
    return _minimal_evidence()


async def _upsert_user(db, spec: PersonaSpec) -> User:
    email = spec.email.lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            name=spec.name,
            hashed_password=hash_password(PASSWORD),
            role=UserRole.student,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()
    else:
        user.name = spec.name
        user.hashed_password = hash_password(PASSWORD)
        user.role = UserRole.student
        user.email_verified_at = datetime.now(timezone.utc)

    profile = await db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
    now = datetime.now(timezone.utc)
    if profile is None:
        db.add(
            StudentProfile(
                user_id=user.id,
                interests_json="[]",
                difficulty="medium",
                grade=10,
                onboarding_step=StudentOnboardingStep.complete,
                onboarding_completed_at=now,
                payment_completed_at=now,
            )
        )
    else:
        profile.onboarding_step = StudentOnboardingStep.complete
        profile.onboarding_completed_at = now
        profile.payment_completed_at = now
        if profile.grade is None:
            profile.grade = 10

    return user


async def _ensure_language_access(db, *, student_id: int, language_id: int, product_id: int) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        text(
            """
            INSERT INTO language_subscriptions (student_id, product_id, payment_status, activated_at, expires_at, created_at)
            VALUES (:sid, :pid, 'paid', :act, :exp, now())
            ON CONFLICT ON CONSTRAINT uq_language_subscription_student_product DO UPDATE SET
                payment_status = 'paid',
                activated_at = EXCLUDED.activated_at,
                expires_at = EXCLUDED.expires_at
            """
        ),
        {"sid": student_id, "pid": product_id, "act": now, "exp": now + timedelta(days=365)},
    )

    prof = await db.scalar(
        select(LanguageStudentProfile).where(
            LanguageStudentProfile.student_id == student_id,
            LanguageStudentProfile.language_id == language_id,
        )
    )
    if prof is None:
        prof = LanguageStudentProfile(student_id=student_id, language_id=language_id)
        db.add(prof)
    prof.onboarding_step = LanguageOnboardingStep.dashboard
    prof.selected_at = now
    prof.placement_completed_at = now
    prof.last_assessment_date = now
    prof.next_allowed_retake_date = now + timedelta(days=90)


async def _ensure_analytics(
    db,
    *,
    student_id: int,
    language_id: int,
    listening: LanguageLevel,
) -> LanguageAnalytics:
    analytics = await db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
    if analytics is None:
        analytics = LanguageAnalytics(student_id=student_id, language_id=language_id)
        db.add(analytics)
    analytics.reading_level = listening
    analytics.listening_level = listening
    analytics.writing_level = listening
    analytics.speaking_level = listening
    analytics.overall_level_internal = listening
    analytics.primary_focus_skill = "listening"
    analytics.strength_skill = "reading"
    await db.flush()
    return analytics


async def _seed_playable_listening_pool(
    db,
    *,
    student_id: int,
    language_id: int,
    level: str,
    count: int = 3,
    body_extras: dict | None = None,
) -> None:
    """Minimal ai_personalized listening pool so /listening/next works in QA."""
    templates = [
        {
            "id": "q1",
            "type": "main_idea",
            "stem": "What is the main idea?",
            "choices": [
                "A person plans a trip to the market",
                "A lecture about ancient history",
                "Instructions for a science exam",
                "A weather report from last year",
            ],
            "correct_index": 0,
        },
        {
            "id": "q2",
            "type": "detail",
            "stem": "Which detail is stated?",
            "choices": [
                "The shop opens at nine o'clock",
                "The shop closed permanently",
                "The speaker lives abroad",
                "No time is mentioned",
            ],
            "correct_index": 0,
        },
    ]
    goal_scenarios = [
        ("travel", "travel", "market trip"),
        ("business", "office", "work stress"),
        ("daily_life", "daily_life", "neighbour chat"),
    ]
    for i in range(count):
        goal_id, situation, topic = goal_scenarios[i % len(goal_scenarios)]
        body = {
            "source": "ai_personalized",
            "instructions": "Listen carefully and choose the best answer.",
            "transcript": (
                "Good morning. Today I am going to the market to buy fruit and bread. "
                "The shop opens at nine o'clock, so I will leave home soon."
            ),
            "questions": templates,
            "listening_intelligence": {
                "situation": situation,
                "category": goal_id,
                "narrative_format": "dialogue",
                "level": level,
                "selection_reason": f"qa_seed_{goal_id}_focus",
            },
            "listening_curriculum": {
                "objectives": ["main_idea", "detail"],
                "skill_focus": ["main_idea"],
                "lesson_intent": "balanced_coverage",
                "knowledge_node": f"qa_playable_node_{i}",
            },
            "listening_learning_goal": {
                "learning_goal": goal_id,
                "goal_profile": goal_id.replace("_", " ").title(),
                "goal_selection_reason": f"aligned_with_{goal_id}",
            },
        }
        if body_extras:
            body.update(body_extras)
        title = f"QA Playable {level} Lesson {i + 1}"
        if goal_id == "business":
            title = f"Work Stress — {level} Practice"
        db.add(
            LanguageContentItem(
                student_id=student_id,
                language_id=language_id,
                skill=LanguageSkill.listening,
                content_type="lesson",
                level=LanguageLevel(level),
                title=title,
                body_json=body,
                is_published=True,
                sort_order=i,
            )
        )
    await db.flush()


async def _clear_playable_listening_pool(
    db,
    *,
    student_id: int,
    language_id: int,
) -> None:
    await db.execute(
        text(
            """
            DELETE FROM language_content_items
            WHERE student_id = :sid AND language_id = :lid AND skill = 'listening'
              AND body_json->>'source' = 'ai_personalized'
            """
        ),
        {"sid": student_id, "lid": language_id},
    )


async def _clear_student_listening_content(
    db,
    *,
    student_id: int,
    language_id: int,
) -> None:
    await db.execute(
        text(
            """
            DELETE FROM language_content_items
            WHERE student_id = :sid AND language_id = :lid AND skill = 'listening'
              AND (body_json->>'source' IS DISTINCT FROM 'ai_personalized')
            """
        ),
        {"sid": student_id, "lid": language_id},
    )


async def _seed_curriculum_items(
    db,
    *,
    student_id: int,
    language_id: int,
    level: str,
    lesson_count: int,
    master_all_objectives: bool = False,
) -> None:
    objectives = [oid for oid, _ in level_objectives(level)]
    if not objectives:
        return

    entries: list[str] = []
    if master_all_objectives:
        for oid in objectives:
            entries.extend([oid] * 5)
    else:
        entries = [objectives[i % len(objectives)] for i in range(lesson_count)]

    for i, oid in enumerate(entries):
        body = {
            "listening_intelligence": {
                "situation": f"qa_seed_lesson_{level}_{i}",
                "category": "travel",
                "narrative_format": "dialogue",
                "level": level,
            },
            "listening_curriculum": {
                "objectives": [oid],
                "skill_focus": ["main_idea"],
                "lesson_intent": "balanced_coverage",
                "knowledge_node": f"qa_seed_node_{i}",
            },
        }
        db.add(
            LanguageContentItem(
                student_id=student_id,
                language_id=language_id,
                skill=LanguageSkill.listening,
                level=LanguageLevel(level),
                title=f"QA Seed {level} Lesson {i + 1}",
                body_json=body,
                is_published=True,
                sort_order=i,
            )
        )
    await db.flush()


async def _apply_adaptive_tier(
    db,
    *,
    student_id: int,
    language_id: int,
    level: str,
    tier: str,
) -> None:
    profile = TIER_PROFILES[tier]
    evidence = _evidence_for(str(profile["evidence"]))
    lesson_index = int(profile["lesson_index"])
    confidence = float(profile["confidence"])
    challenge_quality = str(profile["challenge"])

    await _clear_student_listening_content(db, student_id=student_id, language_id=language_id)
    curriculum_count = int(profile.get("curriculum") or 0)
    master_all = bool(profile.get("master_all"))
    if curriculum_count > 0 or master_all:
        await _seed_curriculum_items(
            db,
            student_id=student_id,
            language_id=language_id,
            level=level,
            lesson_count=curriculum_count,
            master_all_objectives=master_all,
        )

    conf_state = _build_confidence(level, lesson_index=lesson_index, confidence=confidence, evidence=evidence)
    ch_state = _build_challenge(level, lesson_index=lesson_index, quality=challenge_quality)

    await save_student_confidence(db, student_id=student_id, language_id=language_id, state=conf_state)
    await save_student_challenge(db, student_id=student_id, language_id=language_id, state=ch_state)


def _seed_passed_test_payload(*, session_id: str) -> dict:
    return {
        "skill": "listening",
        "official_cefr": "A2",
        "readiness_score": 100,
        "status": ReadinessStatus.PROMOTION_AVAILABLE.value,
        "listening_promotion_tests": {
            "attempts": [
                {
                    "session_id": session_id,
                    "attempt_number": 1,
                    "official_cefr": "A2",
                    "target_cefr": "B1",
                    "overall_score": 100.0,
                    "result": PromotionTestOutcome.PASS.value,
                    "objective_scores": {},
                }
            ],
            "used_lesson_ids": [],
            "used_sequences": [],
        },
        "stability": {
            "history": [
                {
                    "lesson_index": 15,
                    "readiness_score": 100,
                    "gate_eligible": True,
                    "confidence_avg": 0.9,
                    "evidence_coverage_avg": 0.8,
                    "review_completion_ratio": 1.0,
                    "recent_consistency": 0.9,
                    "challenge_score": 0.7,
                }
            ],
            "promotion_confidence": 92,
        },
    }


async def seed_persona(db, spec: PersonaSpec, *, language_id: int, product_id: int) -> dict:
    user = await _upsert_user(db, spec)
    await _ensure_language_access(db, student_id=user.id, language_id=language_id, product_id=product_id)
    await _ensure_analytics(
        db,
        student_id=user.id,
        language_id=language_id,
        listening=spec.listening_cefr,
    )

    cefr = spec.listening_cefr
    await upsert_official_levels(
        db,
        student_id=user.id,
        language_id=language_id,
        reading=cefr,
        listening=cefr,
        writing=cefr,
        speaking=cefr,
        overall=cefr,
        source=f"qa_seed_{spec.key.lower()}",
        force=True,
    )

    await save_listening_stage(
        db,
        student_id=user.id,
        language_id=language_id,
        stage=spec.learning_stage,
        official_cefr=cefr.value,
        stage_score=85 if spec.learning_stage >= 3 else 55,
        previous_stage=max(1, spec.learning_stage - 1),
        force=True,
    )

    await _apply_adaptive_tier(
        db,
        student_id=user.id,
        language_id=language_id,
        level=cefr.value,
        tier=spec.adaptive_tier,
    )

    if spec.key in {"E", "F"}:
        await clear_sessions_for_tests(db, student_id=user.id, language_id=language_id)

    await update_memory(
        db,
        student_id=user.id,
        language_id=language_id,
        updates={"learning_goals": [spec.goal]},
    )

    from app.services.language_learner_context_service import (
        get_language_learner_context,
        listening_generation_metadata,
    )

    ctx = await get_language_learner_context(db, student_id=user.id)
    profile_meta = listening_generation_metadata(ctx)
    await _clear_playable_listening_pool(db, student_id=user.id, language_id=language_id)
    await _seed_playable_listening_pool(
        db,
        student_id=user.id,
        language_id=language_id,
        level=cefr.value,
        count=3,
        body_extras=profile_meta,
    )

    readiness = await evaluate_and_persist_listening_promotion_readiness(
        db,
        student_id=user.id,
        language_id=language_id,
        official_cefr=cefr.value,
    )

    if spec.seed_passed_test:
        session = build_promotion_test_session(
            student_id=user.id,
            language_id=language_id,
            official_cefr=cefr.value,
            target_cefr="B1",
            attempt_number=1,
            used_lesson_ids=set(),
            used_sequences=set(),
        )
        row = await db.get(LanguageProgression, {"student_id": user.id, "language_id": language_id})
        if row is not None:
            payload = dict(row.promotion_readiness_json or {})
            payload.update(_seed_passed_test_payload(session_id=session.session_id))
            row.promotion_readiness_json = payload
            row.promotion_readiness_score = 100

    status = await get_listening_promotion_test_status(db, student_id=user.id, language_id=language_id)

    stage = spec.learning_stage
    promotion_status = readiness.status.value
    if spec.seed_passed_test:
        promotion_status = "PROMOTION_TEST_PASSED — ready for official promotion"
    elif status.eligibility and status.eligibility.eligible:
        promotion_status = f"{readiness.status.value} — eligible to start test"

    return {
        "key": spec.key,
        "email": spec.email,
        "password": PASSWORD,
        "official_cefr": cefr.value,
        "learning_stage": STAGE_NAMES.get(stage, str(stage)),
        "promotion_status": promotion_status,
        "readiness_score": readiness.readiness_score,
        "goal": spec.goal,
        "eligible_for_test": bool(status.eligibility and status.eligibility.eligible),
    }


async def seed_all() -> list[dict]:
    # Refuse to run against what looks like a production database (DEBUG=false).
    # This script writes directly to the DB with no dry-run mode, so a misconfigured
    # environment must fail loudly rather than seed QA persona data into production.
    if not get_settings().DEBUG:
        raise RuntimeError(
            "Refusing to seed QA listening personas: DEBUG is not enabled. This looks "
            "like a production database. Set DEBUG=true in .env if this is really a dev/test DB."
        )
    language = None
    product = None
    rows: list[dict] = []
    async with AsyncSessionLocal() as db:
        language = await get_default_language(db)
        product = await get_default_product(db)
        for spec in PERSONAS:
            rows.append(await seed_persona(db, spec, language_id=language.id, product_id=product.id))
        await db.commit()
    return rows


def _print_table(rows: list[dict]) -> None:
    print("\n=== QA Listening Personas ===\n")
    print(f"Password (all): {PASSWORD}\n")
    for row in rows:
        print(f"--- Student {row['key']} ---")
        print(f"  email:             {row['email']}")
        print(f"  password:          {row['password']}")
        print(f"  official CEFR:     {row['official_cefr']}")
        print(f"  learning stage:    {row['learning_stage']}")
        print(f"  promotion status:  {row['promotion_status']} (score={row['readiness_score']})")
        print(f"  goal:              {row['goal']}")
        print(f"  test eligible:     {row['eligible_for_test']}")
        print()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Seed QA listening personas A–G")
    parser.add_argument("--list", action="store_true", help="List persona emails only")
    args = parser.parse_args()

    if args.list:
        for spec in PERSONAS:
            print(spec.email)
        return 0

    print("Seeding QA listening personas...")
    rows = await seed_all()
    _print_table(rows)

    checks = {
        "A": lambda r: r["official_cefr"] == "A1" and r["learning_stage"] == "Beginner",
        "B": lambda r: r["official_cefr"] == "A2" and r["learning_stage"] == "Beginner",
        "C": lambda r: r["official_cefr"] == "A2" and r["learning_stage"] == "Intermediate",
        "D": lambda r: r["official_cefr"] == "A2"
        and r["readiness_score"] >= 50
        and r["readiness_score"] < 100,
        "E": lambda r: r["eligible_for_test"] and r["readiness_score"] == 100,
        "F": lambda r: "PROMOTION_TEST_PASSED" in r["promotion_status"],
        "G": lambda r: r["official_cefr"] == "B1" and r["learning_stage"] == "Beginner",
    }

    ok = True
    print("=== Seed validation ===")
    for row in rows:
        passed = checks[row["key"]](row)
        mark = "OK" if passed else "FAIL"
        print(f"  [{mark}] Student {row['key']}")
        ok = ok and passed

    if ok:
        print("\nSEED PASS")
        return 0
    print("\nSEED FAIL — review adaptive tiers")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
