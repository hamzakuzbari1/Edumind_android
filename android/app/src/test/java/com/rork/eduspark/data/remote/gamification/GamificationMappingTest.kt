package com.rork.eduspark.data.remote.gamification

import com.rork.eduspark.data.model.AchievementKind
import com.rork.eduspark.data.model.AchievementStatus
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

class GamificationMappingTest {
    @Test
    fun snapshotMapsXpLevelAndStreaks() {
        val snapshot = GamificationProfileDto(
            level = 3,
            totalXp = 420,
            xpToNextLevel = 80,
            xpForLevel = 500,
            progressPercent = 40,
            currentStreak = 5,
            longestStreak = 12,
        ).toSnapshot()

        assertEquals(3, snapshot.level)
        assertEquals(420, snapshot.xp)
        assertEquals(0.4f, snapshot.progressToNextLevel)
        assertEquals(5, snapshot.streakDays)
        assertEquals(12, snapshot.longestStreakDays)
        assertEquals(500, snapshot.xpForNextLevel)
    }

    @Test
    fun badgesPreferCatalogAndMapLockedAndEarned() {
        val profile = GamificationProfileDto(
            badges = listOf(
                BadgeDto(
                    achievementKey = "first_lesson",
                    title = "أول درس",
                    description = "أكملت أول درس دراسي",
                    unlocked = true,
                    unlockedAt = "2026-03-01T12:00:00Z",
                ),
                BadgeDto(
                    achievementKey = "streak_30",
                    title = "سلسلة 30 يوماً",
                    description = "درست 30 يوماً متتالياً",
                    unlocked = false,
                ),
            ),
            achievements = listOf(
                AchievementDto(achievementKey = "first_lesson", title = "أول درس"),
            ),
        )

        val items = profile.toAchievementList()
        assertEquals(2, items.size)
        assertEquals(AchievementStatus.Earned, items[0].status)
        assertEquals(AchievementKind.LessonCompletion, items[0].kind)
        assertEquals("2026-03-01", items[0].earnedDateLabel)
        assertEquals(AchievementStatus.Locked, items[1].status)
        assertEquals(AchievementKind.Streak, items[1].kind)
        assertNull(items[1].progress)
        assertNull(items[1].earnedDateLabel)
    }

    @Test
    fun emptyBadgesFallBackToUnlockedAchievementsOrEmpty() {
        assertTrue(
            GamificationProfileDto().toAchievementList().isEmpty(),
        )
        val onlyUnlocked = GamificationProfileDto(
            achievements = listOf(
                AchievementDto(
                    achievementKey = "average_score_95",
                    title = "متوسط 95%",
                    unlockedAt = "2026-01-15",
                ),
            ),
        ).toAchievementList()
        assertEquals(1, onlyUnlocked.size)
        assertEquals(AchievementKind.QuizPerformance, onlyUnlocked.single().kind)
        assertEquals(AchievementStatus.Earned, onlyUnlocked.single().status)
    }
}
