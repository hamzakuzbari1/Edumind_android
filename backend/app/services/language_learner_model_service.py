"""LanguageLearnerModelService — the single write/read entry point for the Learner Model.

Every feature reports evidence through `process_event()`; nothing touches the mastery tables
directly. Writes derived CEFR back onto the existing `LanguageAnalytics` (skill levels only — XP
and primary_focus_skill keep being recomputed by their own services from analytics data).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.language.analytics import LanguageAnalytics
from app.models.language.enums import LanguageLevel, LanguageSkill
from app.models.language.learner_model import ComponentMastery, KnowledgeComponent
from app.services import language_learner_scoring as scoring
from app.services.language_vocabulary_sr_service import compute_sm2

logger = logging.getLogger(__name__)

DECAY_HALF_LIFE_DAYS = 21.0
DECAY_FLOOR = 0.05
# Placement is derived from a whole multi-section exam, so each seeded component is far stronger
# evidence than one practice question — it counts for several observations toward confidence.
PLACEMENT_EVIDENCE_WEIGHT = 3
_SKILL_ATTR = {
    "reading": "reading_level",
    "listening": "listening_level",
    "writing": "writing_level",
    "speaking": "speaking_level",
}

# Reference catalogue of knowledge components (code, display_skill, category, cefr_level).
# Curated baseline — extend over time. Seeded idempotently by `ensure_components`.
KNOWLEDGE_COMPONENT_SEED: list[tuple[str, str, str, str]] = [
    # reading
    ("reading.skim_gist", "reading", "reading", "A2"),
    ("reading.scan_detail", "reading", "reading", "A2"),
    ("reading.infer_meaning", "reading", "reading", "B1"),
    ("reading.vocab_in_context", "reading", "vocabulary", "B1"),
    ("reading.authors_purpose", "reading", "reading", "B2"),
    ("reading.implicit_attitude", "reading", "reading", "C1"),
    # listening
    ("listening.main_idea", "listening", "listening", "A2"),
    ("listening.specific_info", "listening", "listening", "A2"),
    ("listening.speaker_opinion", "listening", "listening", "B1"),
    ("listening.inference", "listening", "listening", "B1"),
    ("listening.relationship_context", "listening", "listening", "B2"),
    ("listening.nuance_tone", "listening", "listening", "C1"),
    # writing / grammar
    ("grammar.present_simple", "writing", "grammar", "A1"),
    ("grammar.past_tenses", "writing", "grammar", "A2"),
    ("grammar.present_perfect", "writing", "grammar", "B1"),
    ("writing.cohesion_linkers", "writing", "writing", "B1"),
    ("grammar.conditionals", "writing", "grammar", "B2"),
    ("writing.formal_register", "writing", "writing", "C1"),
    # speaking
    ("speaking.intro_personal", "speaking", "speaking", "A1"),
    ("speaking.describe_routine", "speaking", "speaking", "A2"),
    ("speaking.justify_opinion", "speaking", "speaking", "B1"),
    ("speaking.narrate_past", "speaking", "speaking", "B1"),
    ("speaking.hypothetical", "speaking", "speaking", "B2"),
    ("speaking.fluency_discourse", "speaking", "speaking", "C1"),
]


async def ensure_components(db: AsyncSession) -> int:
    """Idempotently insert any missing reference KnowledgeComponents. Returns #inserted."""
    existing = {
        c for (c,) in (await db.execute(select(KnowledgeComponent.code))).all()
    }
    inserted = 0
    for code, skill, category, level in KNOWLEDGE_COMPONENT_SEED:
        if code in existing:
            continue
        db.add(KnowledgeComponent(
            code=code, display_skill=LanguageSkill(skill), category=category, cefr_level=LanguageLevel(level),
            title=code.split(".", 1)[-1].replace("_", " ").title(),
        ))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted


@dataclass
class LearningEvent:
    """One unit of evidence about a learner, from any feature."""

    student_id: int
    language_id: int
    component_code: str
    correct: bool
    source: str = "daily"  # placement | vocab | writing | speaking | daily
    response_quality: int | None = None  # 0-5 (SM-2). Derived from `correct` if omitted.
    evidence_weight: int = 1  # how much this counts toward confidence (placement > a single question)
    initial_mastery: float | None = None  # set p_mastery directly (authoritative seed) instead of BKT
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def quality(self) -> int:
        if self.response_quality is not None:
            return max(0, min(5, int(self.response_quality)))
        return 4 if self.correct else 1


class LanguageLearnerModelService:
    """Thin orchestrator over the pure scoring layer + the mastery tables."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _decayed(cm: ComponentMastery, now: datetime) -> float:
        """Current mastery with forgetting applied since the component was last seen.

        Read paths use this so displayed mastery, the skill-CEFR rollup and smart-review targeting
        all reflect decay consistently — without mutating the stored value (that happens on the next
        event)."""
        p = cm.p_mastery
        if cm.last_seen_at:
            last = cm.last_seen_at if cm.last_seen_at.tzinfo else cm.last_seen_at.replace(tzinfo=timezone.utc)
            days = max(0.0, (now - last).total_seconds() / 86400.0)
            p = scoring.apply_decay(p, days, DECAY_HALF_LIFE_DAYS, floor=DECAY_FLOOR)
        return p

    # ---- write -----------------------------------------------------------------------
    async def process_event(
        self, event: LearningEvent, *, commit: bool = True, sync_cefr: bool = True
    ) -> ComponentMastery | None:
        """Record one piece of evidence.

        ``commit``    — commit the transaction here. Pass ``False`` when called from inside a host
                        submit flow that owns its own commit (router-level), so the event is finalized
                        atomically with the rest of the submit instead of mid-flow.
        ``sync_cefr`` — roll the component masteries up to the skill's headline CEFR on
                        LanguageAnalytics. Placement seeding keeps this ``True`` (authoritative initial
                        level); ongoing feature practice passes ``False`` so the model accumulates
                        evidence without fighting the existing per-skill level management.
        """
        component = (
            await self.db.execute(
                select(KnowledgeComponent).where(KnowledgeComponent.code == event.component_code)
            )
        ).scalar_one_or_none()
        if component is None:
            logger.warning("process_event: unknown component_code %r — skipping", event.component_code)
            return None

        cm = (
            await self.db.execute(
                select(ComponentMastery).where(
                    ComponentMastery.student_id == event.student_id,
                    ComponentMastery.language_id == event.language_id,
                    ComponentMastery.component_id == component.id,
                )
            )
        ).scalar_one_or_none()
        if cm is None:
            # Set initial values explicitly — column defaults only populate at flush, but we read
            # these fields immediately below.
            cm = ComponentMastery(
                student_id=event.student_id, language_id=event.language_id, component_id=component.id,
                p_mastery=0.1, confidence=0.0, evidence_count=0,
                ease_factor=2.5, interval_days=1, repetition_number=0, source_weight=0.0,
            )
            self.db.add(cm)

        now = event.timestamp

        if event.initial_mastery is not None:
            # Authoritative seed (placement): set mastery directly. A single BKT step from the 0.1
            # prior can only reach ~0.33, so seeding via BKT would make a confirmed B1 learner look
            # like 33% — set the demonstrated level outright instead.
            cm.p_mastery = max(0.0, min(1.0, float(event.initial_mastery)))
        else:
            # 1) Forget a little since we last saw this component.
            if cm.last_seen_at:
                last = cm.last_seen_at if cm.last_seen_at.tzinfo else cm.last_seen_at.replace(tzinfo=timezone.utc)
                days = max(0.0, (now - last).total_seconds() / 86400.0)
                cm.p_mastery = scoring.apply_decay(cm.p_mastery, days, DECAY_HALF_LIFE_DAYS, floor=DECAY_FLOOR)

            # 2) BKT update with source-specific sensitivity.
            p = scoring.params_for(event.source)
            cm.p_mastery = scoring.update_bkt(cm.p_mastery, event.correct, p.p_learn, p.p_slip, p.p_guess)

        # 3) SM-2 reschedule (reuse the existing implementation).
        cm.ease_factor, cm.interval_days, cm.repetition_number = compute_sm2(
            cm.ease_factor, cm.interval_days, cm.repetition_number, event.quality()
        )
        cm.next_review_at = now + timedelta(days=cm.interval_days)

        # 4) Evidence bookkeeping. evidence_weight lets a strong signal (placement, derived from a
        #    whole exam) count for more than a single practice question toward confidence.
        cm.evidence_count = (cm.evidence_count or 0) + max(1, int(event.evidence_weight or 1))
        cm.confidence = scoring.update_confidence(cm.confidence or 0.0, cm.evidence_count)
        cm.source_weight = max(cm.source_weight or 0.0, scoring.source_weight(event.source))
        cm.last_seen_at = now

        await self.db.flush()

        # 5) Roll up to the skill's CEFR on LanguageAnalytics (display layer).
        if sync_cefr:
            await self._sync_skill_cefr(
                student_id=event.student_id, language_id=event.language_id, skill=component.display_skill, now=now
            )
        if commit:
            await self.db.commit()
        return cm

    async def _sync_skill_cefr(self, *, student_id: int, language_id: int, skill: LanguageSkill, now: datetime) -> None:
        rows = (
            await self.db.execute(
                select(ComponentMastery, KnowledgeComponent)
                .join(KnowledgeComponent, KnowledgeComponent.id == ComponentMastery.component_id)
                .where(
                    ComponentMastery.student_id == student_id,
                    ComponentMastery.language_id == language_id,
                    KnowledgeComponent.display_skill == skill,
                )
            )
        ).all()
        masteries: list[tuple[str, float, float]] = []
        for cm, comp in rows:
            masteries.append((comp.cefr_level.value, self._decayed(cm, now), cm.confidence or 0.0))

        derived = scoring.derive_skill_cefr(masteries)
        analytics = await self.db.get(LanguageAnalytics, {"student_id": student_id, "language_id": language_id})
        if analytics is None:
            analytics = LanguageAnalytics(student_id=student_id, language_id=language_id)
            self.db.add(analytics)
        attr = _SKILL_ATTR.get(skill.value)
        if attr:
            try:
                setattr(analytics, attr, LanguageLevel(derived))
            except ValueError:
                pass

    async def seed_from_placement(
        self, *, student_id: int, language_id: int, skill_levels: dict[str, str]
    ) -> int:
        """Seed the learner model from a finished placement: for each skill, components at/below the
        measured CEFR count as correct evidence, those above as incorrect. Returns #events processed.

        ``skill_levels``: {"reading": "B1", "listening": "A2", ...} (CEFR strings).
        """
        await ensure_components(self.db)
        components = (await self.db.execute(select(KnowledgeComponent))).scalars().all()
        processed = 0
        # Seed all components in ONE transaction (commit=False, sync_cefr=False), then roll up each
        # skill's CEFR once and commit a single time — avoids a per-component commit that could leave
        # the model half-seeded if something fails mid-loop, and avoids redundant rollups.
        for comp in components:
            level = skill_levels.get(comp.display_skill.value)
            if not level:
                continue
            # Graded baseline by how far the component sits from the measured level:
            #  >=1 band below -> 0.90, at level -> 0.80, 1 above -> 0.25, >=2 above -> 0.08.
            diff = scoring.cefr_rank(level) - scoring.cefr_rank(comp.cefr_level.value)
            initial = 0.90 if diff >= 1 else 0.80 if diff == 0 else 0.25 if diff == -1 else 0.08
            await self.process_event(
                LearningEvent(
                    student_id=student_id, language_id=language_id, component_code=comp.code,
                    correct=diff >= 0, source="placement", evidence_weight=PLACEMENT_EVIDENCE_WEIGHT,
                    initial_mastery=initial,
                ),
                commit=False, sync_cefr=False,
            )
            processed += 1
        # Do NOT roll the seeded mastery up into the headline CEFR. The placement exam already wrote
        # the authoritative per-skill levels; deriving from the seed here would OVERWRITE them — and a
        # cautious seed can derive below threshold and silently DOWNGRADE the level the exam measured.
        # Seeding only populates the component model.
        await self.db.commit()
        return processed

    # ---- read ------------------------------------------------------------------------
    async def get_due_reviews(self, *, student_id: int, language_id: int, limit: int = 20) -> list[ComponentMastery]:
        now = datetime.now(timezone.utc)
        rows = (
            await self.db.execute(
                select(ComponentMastery)
                .where(
                    ComponentMastery.student_id == student_id,
                    ComponentMastery.language_id == language_id,
                    ComponentMastery.next_review_at.isnot(None),
                    ComponentMastery.next_review_at <= now,
                )
                .order_by(ComponentMastery.next_review_at)
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)

    async def get_component_profile(self, *, student_id: int, language_id: int) -> list[dict]:
        rows = (
            await self.db.execute(
                select(ComponentMastery, KnowledgeComponent)
                .join(KnowledgeComponent, KnowledgeComponent.id == ComponentMastery.component_id)
                .where(
                    ComponentMastery.student_id == student_id,
                    ComponentMastery.language_id == language_id,
                )
            )
        ).all()
        now = datetime.now(timezone.utc)
        return [
            {
                "code": comp.code,
                "skill": comp.display_skill.value,
                "category": comp.category,
                "cefr_level": comp.cefr_level.value,
                "p_mastery": round(self._decayed(cm, now), 3),
                "confidence": round(cm.confidence or 0.0, 3),
                "evidence_count": cm.evidence_count,
                "next_review_at": cm.next_review_at,
            }
            for cm, comp in rows
        ]

    async def get_skill_confidence(self, *, student_id: int, language_id: int) -> dict[str, float]:
        rows = (
            await self.db.execute(
                select(ComponentMastery, KnowledgeComponent)
                .join(KnowledgeComponent, KnowledgeComponent.id == ComponentMastery.component_id)
                .where(
                    ComponentMastery.student_id == student_id,
                    ComponentMastery.language_id == language_id,
                )
            )
        ).all()
        agg: dict[str, list[float]] = {}
        for cm, comp in rows:
            agg.setdefault(comp.display_skill.value, []).append(cm.confidence or 0.0)
        return {skill: round(sum(v) / len(v), 3) for skill, v in agg.items() if v}
