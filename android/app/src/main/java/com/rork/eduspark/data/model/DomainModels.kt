package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * CLIENT DOMAIN MODELS — not API DTOs.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * These describe what the *UI* needs. They deliberately do NOT mirror any FastAPI
 * response shape, because we have not seen the generated client yet and inventing a
 * response structure would be worse than having none.
 *
 * When the real client arrives, each repository gains a mapper (DTO → these models) and
 * nothing in the UI layer changes. That is the whole point of the seam.
 *
 * Backend status is recorded per concept below, taken from the verified Source Audit.
 */

/** Source Audit §2 — the platform has exactly these three account types (plus a minimal admin). */
enum class UserRole { Student, Teacher, Parent }

/**
 * The signed-in user.
 *
 * Tokens stay in the secure session store and never enter the UI-facing user model.
 */
data class SessionUser(
    val id: String,
    val displayName: String,
    val email: String,
    val role: UserRole,
    val isEmailVerified: Boolean,
    val requiresTwoFactor: Boolean,
    val hasCompletedOnboarding: Boolean,
    val onboardingStep: StudentOnboardingStep? = null,
    val grade: Int? = null,
)

/**
 * Non-secret presentation metadata for a pending email-OTP login challenge.
 *
 * The challenge token itself remains inside the repository and is never placed in Compose
 * state, navigation arguments, logs, or saved instance state.
 */
data class TwoFactorChallengeInfo(
    val email: String,
    val maskedEmail: String?,
    val expiresInSeconds: Int?,
    val resendAvailableInSeconds: Int?,
)

/** Lesson lifecycle — Source Audit §6: `draft → processing → processed | error`. */
enum class LessonStatus {
    Draft,
    Processing,
    Processed,
    Error,

    /** Client-side only: processed, but the student has no paid access to the course. */
    LockedByEntitlement,

    /** Client-side only: paid and processed, but a prerequisite step isn't done yet. */
    LockedSequential,
}

/** Why a [LearningStep] is locked — ST-02's "locked rows say what unlocks them". */
sealed interface LockedReason {
    /** "Locked — finish {title} to open." [LessonStatus.LockedSequential] only. */
    data class RequiresStep(val stepTitle: String) : LockedReason

    /** "Locked — opens after {count} lessons." Used for milestone/test beads. [LessonStatus.LockedSequential] only. */
    data class RequiresStepCount(val count: Int) : LockedReason

    /** The step is processed but the student has no paid access — [LessonStatus.LockedByEntitlement]. */
    data object RequiresEntitlement : LockedReason
}

/** Which media a lesson bundles — ST-02's per-row icon row (PDF · VIDEO · AUDIO). */
enum class LessonMediaType { Pdf, Video, Audio }

/**
 * A step on the Progress Spine.
 *
 * One model serves course lessons, language-path units and project milestones, because
 * the spine is deliberately the same object in all three places.
 */
data class LearningStep(
    val id: String,
    val title: String,
    val subtitle: String?,
    val status: LessonStatus,
    val isCurrent: Boolean,
    val isCompleted: Boolean,
    val durationMinutes: Int = 0,
    val mediaTypes: Set<LessonMediaType> = emptySet(),
    /** Set when [isCompleted] — the XP the student already banked for this step. */
    val xpEarned: Int? = null,
    /** Set when [isCurrent] and partially watched/read. */
    val minutesLeft: Int? = null,
    /** Set only when [status] is [LessonStatus.LockedSequential]. */
    val lockedReason: LockedReason? = null,
    /** A milestone bead (e.g. a unit test) reads slightly differently from a plain lesson. */
    val isMilestone: Boolean = false,
)

/** Canonical backend course unit/chapter. "Chapter" is only a display synonym. */
data class LearningUnit(
    val id: String?,
    val title: String,
    val subtitle: String? = null,
    val progress: Float = 0f,
    val completedLessonCount: Int = 0,
    val totalLessonCount: Int = 0,
    val steps: List<LearningStep> = emptyList(),
)

/** A learning path — a course, a language unit, or a project milestone board. */
data class LearningPath(
    val id: String,
    val title: String,
    val subtitle: String,
    val progress: Float,
    val steps: List<LearningStep>,
    val teacherName: String = "",
    val quizCount: Int = 0,
    /** False shows ST-02's "not published yet" state instead of the lesson list. */
    val isPublished: Boolean = true,
    /** False shows ST-02's whole-course locked/paywall state instead of the lesson list.
     *  Checked only when [isPublished] is true — a draft course has no entitlement question
     *  yet, since nobody has access to it regardless of payment. */
    val isEntitled: Boolean = true,
    /** Pre-formatted, e.g. "updated today" — a real backend would send a timestamp the
     *  client formats; this mock slice keeps the label as-is rather than modelling one. */
    val lastUpdatedLabel: String = "",
    /** The header stat line ("5 of 8 lessons") — independent of how many [steps] this
     *  particular fixture bothers to model in full; a real course can have more lessons
     *  than are useful to hand-write for every locked/completed/current state combination. */
    val completedLessonCount: Int = 0,
    val totalLessonCount: Int = 0,
    val units: List<LearningUnit> = emptyList(),
)

/**
 * STUDENT_COURSES tab ("موادي") — one row per course the student's grade offers, entitled or
 * not. A lighter projection of [LearningPath], not a duplicate of it: this tab's cards need
 * only what a course card shows (identity, teacher, progress-or-lock state), never the full
 * step list ST-02 loads separately when the student actually opens one.
 */
data class StudentCourseSummary(
    val courseId: String,
    val title: String,
    val teacherName: String,
    val progress: Float,
    val currentLabel: String,
    val isEntitled: Boolean,
    val isPublished: Boolean,
    val completedLessonCount: Int = 0,
    val totalLessonCount: Int = 0,
)

/**
 * Test-2SY's `SubjectCatalogCard` distinguishes `locked` / `ready` / `active` / `done` — this
 * app's own [StudentCourseSummary] already carries everything needed to derive the same four
 * states (plus "coming soon" for an unpublished draft), so this is a pure derived property, not
 * a new stored field.
 */
enum class CourseCardState { ComingSoon, Locked, Ready, InProgress, Completed }

fun StudentCourseSummary.cardState(): CourseCardState = when {
    !isPublished -> CourseCardState.ComingSoon
    !isEntitled -> CourseCardState.Locked
    progress >= 1f -> CourseCardState.Completed
    progress > 0f -> CourseCardState.InProgress
    else -> CourseCardState.Ready
}

/**
 * Gamification snapshot. Backend: `GET /student/gamification` exists and is implemented.
 *
 * [xpForNextLevel] and [streakHistory] exist only for ST-15 Achievements' richer header (the
 * next-level bar needs an absolute target, not just a fraction; the heatmap needs day-by-day
 * data) — both default to values consistent with ST-01's existing snapshot, so this stays the
 * *one* gamification model rather than a second one duplicating level/xp/streak.
 */
data class GamificationSnapshot(
    val level: Int,
    val xp: Int,
    val progressToNextLevel: Float,
    val streakDays: Int,
    val xpForNextLevel: Int = 0,
    /** Most recent day last — true means the student studied that day. Empty where unused (ST-01 doesn't read it). */
    val streakHistory: List<Boolean> = emptyList(),
    /** Backend longest streak when available; ST-15 falls back to [streakHistory] / [streakDays]. */
    val longestStreakDays: Int = 0,
)

/**
 * ST-03 — one lesson's playable content, built from the [LearningStep] the student tapped
 * on ST-02. A separate model from [LearningStep] because the player needs detail the spine
 * row never renders (page count, per-lesson quiz availability), not because the underlying
 * concept differs.
 */
data class LessonDetail(
    val id: String,
    val courseId: String,
    val courseTitle: String,
    val teacherName: String,
    val title: String,
    val status: LessonStatus,
    val mediaTypes: Set<LessonMediaType>,
    val durationMinutes: Int,
    /** PDF lessons only — the mock page count the reader surface paginates through. */
    val pageCount: Int = 0,
    val lessonIndex: Int = 0,
    val lessonTotal: Int = 0,
    val isCompleted: Boolean = false,
    val videoProgress: Float = 0f,
    val pdfProgress: Float = 0f,
    val pdfOpened: Boolean = false,
    /** Null when this lesson has no AI-generated comprehension quiz — ST-03's Take Quiz stays hidden. */
    val quizId: String? = null,
    /** Approved design's "الأفكار الأساسية" card (LessonPlayer.dc.html) — a short numbered
     *  summary of the lesson's core points. Empty hides the card entirely. */
    val keyIdeas: List<String> = emptyList(),
)

/**
 * A-12 Certificate Verification — Source Audit §5: "public certificate verify" exists on
 * the backend and needs no session. [isValid] false covers both "not found" and "revoked";
 * the client does not need to tell those apart, only the server does.
 *
 * PJ-11 reuses this exact model/repository for project certificates rather than a parallel
 * verification type — [levelOrProjectName] already reads generically enough to hold either a
 * language level or a completed project's title, and [skills] is the one minimal optional
 * field added for it (empty for the existing language-certificate fixture, so nothing about
 * A-12's own rendering changes).
 */
data class CertificateVerification(
    val isValid: Boolean,
    val holderName: String,
    val certificateTitle: String,
    val levelOrProjectName: String,
    val issueDate: String,
    val issuingTeacher: String,
    val skills: List<String> = emptyList(),
)
