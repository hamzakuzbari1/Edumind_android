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
 * Note what is absent: no refresh token is modelled, because the backend has no refresh
 * endpoint. A 401 ends the session — that is a product fact, not an oversight.
 */
data class SessionUser(
    val id: String,
    val displayName: String,
    val email: String,
    val role: UserRole,
    val isEmailVerified: Boolean,
    val requiresTwoFactor: Boolean,
    val hasCompletedOnboarding: Boolean,
)

/** Lesson lifecycle — Source Audit §6: `draft → processing → processed | error`. */
enum class LessonStatus {
    Draft,
    Processing,
    Processed,
    Error,

    /** Client-side only: processed, but the student has no paid access to the course. */
    LockedByEntitlement,
}

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
)

/** A learning path — a course, a language unit, or a project milestone board. */
data class LearningPath(
    val id: String,
    val title: String,
    val subtitle: String,
    val progress: Float,
    val steps: List<LearningStep>,
)

/**
 * Gamification snapshot. Backend: `GET /student/gamification` exists and is implemented.
 */
data class GamificationSnapshot(
    val level: Int,
    val xp: Int,
    val progressToNextLevel: Float,
    val streakDays: Int,
)
