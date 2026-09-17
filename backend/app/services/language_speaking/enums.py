"""Canonical Speaking skill enums (S0) — single source of truth for all speaking packages."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class OfficialSpeakingCEFR(StrEnum):
    """Official speaking CEFR band — only Official Promotion may advance this at runtime."""

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class SpeakingGoal(StrEnum):
    """Personal learning goal — influences selection, generation, coach, and SPA."""

    general_english = "general_english"
    travel = "travel"
    ielts = "ielts"
    business = "business"
    academic = "academic"
    job_interview = "job_interview"
    daily_communication = "daily_communication"


class SpeakingCoachPersonality(StrEnum):
    """Coach tone wrapper — pedagogical advice unchanged; rendering only."""

    friendly_teacher = "friendly_teacher"
    strict_teacher = "strict_teacher"
    ielts_coach = "ielts_coach"
    business_mentor = "business_mentor"
    academic_tutor = "academic_tutor"
    conversation_partner = "conversation_partner"


class SpeakingTaskType(StrEnum):
    """High-level speaking task shapes."""

    monologue = "monologue"
    dialogue = "dialogue"
    role_play = "role_play"
    shadowing = "shadowing"
    pronunciation_drill = "pronunciation_drill"
    picture_description = "picture_description"
    interview = "interview"


class SpeakingSkillType(StrEnum):
    """Node types in the Speaking Skill Dependency Graph (S1+)."""

    phoneme = "phoneme"
    pronunciation_pattern = "pronunciation_pattern"
    word = "word"
    phrase = "phrase"
    grammar_structure = "grammar_structure"
    vocabulary_function = "vocabulary_function"
    speaking_function = "speaking_function"
    fluency_skill = "fluency_skill"
    prosody_skill = "prosody_skill"
    interaction_skill = "interaction_skill"
    conversation_skill = "conversation_skill"
    task_skill = "task_skill"


class SpeakingAudioSource(StrEnum):
    """How audio entered the session."""

    browser_recording = "browser_recording"
    file_upload = "file_upload"
    streaming_chunk = "streaming_chunk"  # future LiveKit path


class SpeakingSessionProcessingState(StrEnum):
    """Audio session processing lifecycle — no educational scoring here."""

    created = "created"
    audio_received = "audio_received"
    transcribing = "transcribing"
    extracting_features = "extracting_features"
    evidence_ready = "evidence_ready"
    evaluating = "evaluating"
    complete = "complete"
    failed = "failed"


class SpeakingConversationState(StrEnum):
    """Turn-level conversation interaction state."""

    awaiting_student = "awaiting_student"
    student_speaking = "student_speaking"
    processing = "processing"
    coach_responding = "coach_responding"
    micro_drill = "micro_drill"
    completed = "completed"


class SpeakingLessonLifecycle(StrEnum):
    """Lesson session lifecycle."""

    not_started = "not_started"
    mission_viewed = "mission_viewed"
    in_conversation = "in_conversation"
    revising = "revising"
    completed = "completed"


class SpeakingLearningStage(IntEnum):
    """Persistent learning stage (1–3). Stage engine owns transitions."""

    foundation = 1
    developing = 2
    advanced = 3


class SpeakingMissionKind(StrEnum):
    """Educational phase / purpose of a speaking mission (S10.1 taxonomy — dimension A).

    This enum represents ONLY educational purpose/phase. It is strictly orthogonal to:
    - SpeakingExecutionMode (HOW a mission executes)
    - SpeakingEvidenceIntent (WHY evidence is collected)

    Deliberately excluded (S10.1 correction):
    - execution modalities (controlled_speaking / recorded_speaking / live_conversation)
      now live only in SpeakingExecutionMode.
    - `retry` is a runtime flow/outcome decision (SpeakingMissionOutcome), never an
      educational phase, so it is not a mission kind.

    Note on `transfer` vs `retention_review` overlap with evidence intents:
    - `transfer` (kind) = educational purpose "apply the target skill in a changed
      task/context". `SpeakingEvidenceIntent.transfer` = "evidence is eligible for
      transfer evaluation". A transfer mission carries transfer evidence intent, but the
      two dimensions remain distinct concepts (purpose vs evidence eligibility).
    - `retention_review` (kind) = educational purpose "revisit a prior skill later".
      `SpeakingEvidenceIntent.retention` = "evidence is delayed-retention evidence".
    """

    teaching = "teaching"
    noticing = "noticing"
    guided_practice = "guided_practice"
    speak = "speak"
    feedback = "feedback"
    transfer = "transfer"
    retention_review = "retention_review"


class SpeakingExecutionMode(StrEnum):
    """How a mission is executed at runtime (S10 taxonomy — dimension B).

    Owns execution modality. Independent from mission kind: e.g. a `speak` kind may run
    as a `recorded_response` or a `live_evi_conversation`.
    """

    study = "study"  # no student audio — teaching / noticing / feedback reading
    controlled_response = "controlled_response"  # scaffolded speaking with frames
    recorded_response = "recorded_response"  # free recorded speech (S4 pipeline)
    live_evi_conversation = "live_evi_conversation"  # Alex / Hume EVI live turn
    review = "review"  # spaced review surface


class SpeakingEvidenceIntent(StrEnum):
    """Why a mission collects speaking evidence (S10 taxonomy — dimension C).

    `none` means the mission is teaching/review content and must NOT be treated as skill
    evidence. Evidence application to S2 remains owned by the S8 knowledge bridge.
    """

    none = "none"  # teaching / review content — not evidence
    formative = "formative"  # low-stakes practice evidence
    summative = "summative"  # primary skill evidence
    transfer = "transfer"  # transfer-context evidence
    retention = "retention"  # delayed retention evidence


class SpeakingTeachingBlockKind(StrEnum):
    """Typed teaching-block families (S10). Teaching content, never evidence by default."""

    explanation = "explanation"
    example = "example"
    contrast = "contrast"
    noticing_cue = "noticing_cue"
    scaffold = "scaffold"
    guided_prompt = "guided_prompt"
    misconception_correction = "misconception_correction"


class InterruptionDecision(StrEnum):
    """Canonical interruption policy output (S11+)."""

    none = "none"
    wait_until_finish = "wait_until_finish"
    clarify_meaning = "clarify_meaning"
    micro_drill_now = "micro_drill_now"
    save_for_revision = "save_for_revision"


class PromotionStatus(StrEnum):
    """Promotion readiness band — never mutates official CEFR."""

    not_ready = "not_ready"
    almost_ready = "almost_ready"
    ready = "ready"
    blocked = "blocked"
