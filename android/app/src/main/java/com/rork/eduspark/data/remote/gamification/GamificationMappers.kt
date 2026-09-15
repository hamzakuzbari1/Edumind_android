package com.rork.eduspark.data.remote.gamification

import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.model.AchievementKind
import com.rork.eduspark.data.model.AchievementStatus
import com.rork.eduspark.data.model.GamificationSnapshot

internal fun GamificationProfileDto.toSnapshot(): GamificationSnapshot = GamificationSnapshot(
    level = level.coerceAtLeast(1),
    xp = totalXp.coerceAtLeast(0),
    progressToNextLevel = (progressPercent.coerceIn(0, 100) / 100f),
    streakDays = currentStreak.coerceAtLeast(0),
    xpForNextLevel = when {
        xpForLevel > 0 -> xpForLevel
        xpToNextLevel > 0 -> totalXp + xpToNextLevel
        else -> 0
    },
    longestStreakDays = longestStreak.coerceAtLeast(0),
)

/**
 * Prefer the badge catalog (earned + locked). Fall back to unlocked achievements only when
 * the catalog is empty so an empty backend still yields a safe empty list for the UI.
 */
internal fun GamificationProfileDto.toAchievementList(): List<Achievement> {
    if (badges.isNotEmpty()) return badges.map(BadgeDto::toDomain)
    return achievements.map(AchievementDto::toDomain)
}

internal fun BadgeDto.toDomain(): Achievement = Achievement(
    id = achievementKey,
    kind = achievementKindFor(achievementKey),
    title = title.ifBlank { achievementKey },
    description = description,
    status = if (unlocked) AchievementStatus.Earned else AchievementStatus.Locked,
    progress = null,
    earnedDateLabel = if (unlocked) formatUnlockedAt(unlockedAt) else null,
)

internal fun AchievementDto.toDomain(): Achievement = Achievement(
    id = achievementKey,
    kind = achievementKindFor(achievementKey),
    title = title.ifBlank { achievementKey },
    description = description,
    status = AchievementStatus.Earned,
    progress = null,
    earnedDateLabel = formatUnlockedAt(unlockedAt),
)

internal fun achievementKindFor(key: String): AchievementKind {
    val normalized = key.lowercase()
    return when {
        "streak" in normalized -> AchievementKind.Streak
        "quiz" in normalized || "score" in normalized || "perfect" in normalized ->
            AchievementKind.QuizPerformance
        "course" in normalized -> AchievementKind.CourseProgress
        "lesson" in normalized -> AchievementKind.LessonCompletion
        else -> AchievementKind.StudyConsistency
    }
}

internal fun formatUnlockedAt(raw: String?): String? {
    val value = raw?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    // Keep a short, stable label without inventing relative-time localization.
    return value.take(10)
}
