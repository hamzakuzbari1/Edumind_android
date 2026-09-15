package com.rork.eduspark.data.remote.gamification

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
internal data class GamificationProfileDto(
    val level: Int = 1,
    @SerialName("total_xp") val totalXp: Int = 0,
    @SerialName("xp_to_next_level") val xpToNextLevel: Int = 0,
    @SerialName("xp_in_level") val xpInLevel: Int = 0,
    @SerialName("xp_for_level") val xpForLevel: Int = 0,
    @SerialName("progress_percent") val progressPercent: Int = 0,
    @SerialName("is_max_level") val isMaxLevel: Boolean = false,
    @SerialName("current_streak") val currentStreak: Int = 0,
    @SerialName("longest_streak") val longestStreak: Int = 0,
    @SerialName("streak_display") val streakDisplay: String = "",
    val achievements: List<AchievementDto> = emptyList(),
    @SerialName("achievement_count") val achievementCount: Int = 0,
    val badges: List<BadgeDto> = emptyList(),
    @SerialName("xp_rules") val xpRules: List<XpRuleDto> = emptyList(),
    @SerialName("recent_activity") val recentActivity: List<XpActivityDto> = emptyList(),
)

@Serializable
internal data class AchievementDto(
    @SerialName("achievement_key") val achievementKey: String,
    val icon: String = "",
    val title: String = "",
    val description: String = "",
    @SerialName("unlocked_at") val unlockedAt: String? = null,
)

@Serializable
internal data class BadgeDto(
    @SerialName("achievement_key") val achievementKey: String,
    val icon: String = "",
    val title: String = "",
    val description: String = "",
    val unlocked: Boolean = false,
    @SerialName("unlocked_at") val unlockedAt: String? = null,
)

@Serializable
internal data class XpRuleDto(
    val category: String = "",
    val label: String = "",
    val xp: Int = 0,
)

@Serializable
internal data class XpActivityDto(
    val label: String = "",
    val xp: Int = 0,
    @SerialName("occurred_at") val occurredAt: String? = null,
    val kind: String = "xp",
)
