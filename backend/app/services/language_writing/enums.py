"""Canonical Writing skill enums (W0) — single source of truth for all writing packages."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class OfficialWritingCEFR(StrEnum):
    """Official writing CEFR band — only Official Promotion may advance this at runtime."""

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class WritingArc(StrEnum):
    """Layer 2 — macro writing skill curriculum arc (W1 canonical)."""

    sentence_building = "sentence_building"
    paragraph_writing = "paragraph_writing"
    narrative_writing = "narrative_writing"
    opinion_writing = "opinion_writing"
    formal_writing = "formal_writing"
    professional_writing = "professional_writing"
    academic_writing = "academic_writing"


class WritingGoal(StrEnum):
    """Personal learning goal — influences selection, generation, coach, and WPA."""

    general_english = "general_english"
    travel = "travel"
    ielts = "ielts"
    business = "business"
    academic = "academic"
    job_interview = "job_interview"
    daily_communication = "daily_communication"
    creative_writing = "creative_writing"


class WritingCoachPersonality(StrEnum):
    """Coach tone wrapper — pedagogical advice unchanged; rendering only."""

    friendly_teacher = "friendly_teacher"
    strict_teacher = "strict_teacher"
    ielts_coach = "ielts_coach"
    business_mentor = "business_mentor"
    creative_writing_coach = "creative_writing_coach"
    academic_tutor = "academic_tutor"
    young_learner_coach = "young_learner_coach"


class WritingFeedbackStyle(StrEnum):
    """Goal-driven feedback tone — coach applies over identical evaluation facts."""

    supportive = "supportive"
    direct = "direct"
    exam_focused = "exam_focused"
    professional = "professional"
    creative = "creative"
    concise = "concise"
    scaffolded = "scaffolded"


class WritingPromotionStyle(StrEnum):
    """Goal-driven WPA / promotion framing — official CEFR unchanged."""

    gradual = "gradual"
    exam_gate = "exam_gate"
    portfolio_milestone = "portfolio_milestone"
    competency_checklist = "competency_checklist"
    interview_readiness = "interview_readiness"


class WritingMissionStyle(StrEnum):
    """How missions are framed for a learning goal."""

    everyday_scenario = "everyday_scenario"
    travel_scenario = "travel_scenario"
    business_brief = "business_brief"
    exam_task = "exam_task"
    academic_task = "academic_task"
    interview_prep = "interview_prep"
    creative_prompt = "creative_prompt"
    quick_message = "quick_message"


class WritingRevisionStyle(StrEnum):
    """How the coach guides revision for a learning goal."""

    gentle_scaffold = "gentle_scaffold"
    one_priority_per_turn = "one_priority_per_turn"
    iterative_polish = "iterative_polish"
    exam_rigor = "exam_rigor"
    creative_craft = "creative_craft"
    concise_pass = "concise_pass"


class WritingCoachTone(StrEnum):
    """Preferred coach communication tone for a goal — personality stays fixed; tone adapts within it."""

    warm = "warm"
    direct = "direct"
    professional = "professional"
    exam_calibrated = "exam_calibrated"
    creative = "creative"
    patient = "patient"
    energetic = "energetic"


class ContextComplexity(IntEnum):
    """Real-world rhetorical demand within the same Official CEFR band (1–5)."""

    familiar = 1
    everyday = 2
    mild_problem = 3
    real_world_stakes = 4
    multi_constraint = 5


class LexisCategory(StrEnum):
    """Vocabulary category for balanced lexis progression."""

    core = "core"
    topic = "topic"
    academic = "academic"
    business = "business"
    collocations = "collocations"
    common_phrases = "common_phrases"
    idioms = "idioms"


class GrammarState(StrEnum):
    """Grammar structure mastery state."""

    unknown = "unknown"
    learning = "learning"
    practicing = "practicing"
    mastered = "mastered"


class LexisState(StrEnum):
    """Lemma mastery state within a vocabulary category."""

    unknown = "unknown"
    learning = "learning"
    practicing = "practicing"
    mastered = "mastered"


class WritingLessonLifecycle(StrEnum):
    """Lesson session lifecycle including revision loop."""

    not_started = "not_started"
    mission_viewed = "mission_viewed"
    drafting = "drafting"
    draft_submitted = "draft_submitted"
    coach_ready = "coach_ready"
    revising = "revising"
    draft_resubmitted = "draft_resubmitted"
    completed = "completed"


class WritingRevisionStatus(StrEnum):
    """Status of a single draft revision turn."""

    pending_coach = "pending_coach"
    coach_ready = "coach_ready"
    awaiting_rewrite = "awaiting_rewrite"
    approved = "approved"


class PromotionStatus(StrEnum):
    """Writing Promotion Assessment (WPA) session status."""

    not_eligible = "not_eligible"
    eligible = "eligible"
    in_progress = "in_progress"
    passed = "passed"
    failed = "failed"
    promoted = "promoted"


class ChainTopology(StrEnum):
    """Knowledge chain graph shape — v1 catalog is linear only."""

    linear = "linear"
    # Future: branched = "branched"  — reserved for graph branching extension


class ExpectedWritingOutput(StrEnum):
    """Canonical expected student writing product for a chain node."""

    paragraph = "paragraph"
    essay = "essay"
    email = "email"
    report = "report"
    story = "story"
    dialogue = "dialogue"
    review = "review"
    summary = "summary"
    article = "article"
    message = "message"


class WritingTopicId(StrEnum):
    """Canonical Topic Universe identifiers (W1 v1 — 20 topics)."""

    travel = "travel"
    education = "education"
    business = "business"
    technology = "technology"
    health = "health"
    family = "family"
    work = "work"
    shopping = "shopping"
    environment = "environment"
    science = "science"
    entertainment = "entertainment"
    culture = "culture"
    history = "history"
    food = "food"
    sports = "sports"
    daily_life = "daily_life"
    communication = "communication"
    services = "services"
    housing = "housing"
    society = "society"
