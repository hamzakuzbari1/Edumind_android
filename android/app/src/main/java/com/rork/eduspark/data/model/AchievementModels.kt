package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-15 · Achievements.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit §2: "Achievements / XP — Implemented." Deliberately just badges tied to real
 * product mechanics already in this app (streaks, lessons, quizzes, course progress) — no
 * leaderboard, coins, gems, or social ranking exists in the product definition, so none are
 * modelled here.
 */

enum class AchievementStatus { Earned, Locked }

/** What the five example categories in the Screen Inventory map to — icon selection only, not a new backend concept. */
enum class AchievementKind { Streak, LessonCompletion, QuizPerformance, StudyConsistency, CourseProgress }

/** How close a locked achievement is — always a concrete count, never a vague "almost there". */
data class AchievementProgress(
    val current: Int,
    val target: Int,
)

data class Achievement(
    val id: String,
    val kind: AchievementKind,
    val title: String,
    val description: String,
    val status: AchievementStatus,
    /** Present while [status] is [AchievementStatus.Locked] — what exactly remains. */
    val progress: AchievementProgress? = null,
    /** Present while [status] is [AchievementStatus.Earned] — pre-formatted, same convention as [LearningPath.lastUpdatedLabel]. */
    val earnedDateLabel: String? = null,
)
