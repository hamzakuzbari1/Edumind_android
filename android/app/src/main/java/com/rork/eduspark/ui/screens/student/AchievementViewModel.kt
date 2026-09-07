package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.data.repository.AchievementRepository
import com.rork.eduspark.data.repository.LearningRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-15 · Achievements.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The level/XP/streak header comes from [LearningRepository.getGamification] — the exact
 * same call ST-01 already makes — rather than a second gamification fetch or model, so this
 * screen can never show a number that disagrees with Student Home.
 */
data class AchievementScreenData(
    val gamification: GamificationSnapshot,
    val achievements: List<Achievement>,
    val longestStreakDays: Int,
    val recentXp: List<RecentXpActivity>,
    val xpRules: List<XpRule>,
)

data class RecentXpActivity(
    val title: String,
    val detail: String,
    val xp: Int,
)

data class XpRule(
    val title: String,
    val detail: String,
)

data class AchievementUiState(
    val result: UiState<AchievementScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class AchievementViewModel(
    private val achievementRepository: AchievementRepository,
    private val learningRepository: LearningRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(AchievementUiState())
    val state: StateFlow<AchievementUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val gamificationResult = learningRepository.getGamification()
            val achievementsResult = achievementRepository.getAchievements()
            when {
                gamificationResult is AppResult.Success && achievementsResult is AppResult.Success -> {
                    val gamification = gamificationResult.data
                    _state.update {
                        it.copy(
                            result = UiState.Content(
                                AchievementScreenData(
                                    gamification = gamification,
                                    achievements = achievementsResult.data,
                                    longestStreakDays = longestTrueRun(gamification.streakHistory).coerceAtLeast(gamification.streakDays),
                                    recentXp = recentXp(gamification),
                                    xpRules = xpRules(),
                                )
                            )
                        )
                    }
                }
                gamificationResult is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(gamificationResult.error)) }
                achievementsResult is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(achievementsResult.error)) }
            }
        }
    }

    private fun longestTrueRun(history: List<Boolean>): Int {
        var current = 0
        var best = 0
        history.forEach { studied ->
            current = if (studied) current + 1 else 0
            best = maxOf(best, current)
        }
        return best
    }

    private fun recentXp(gamification: GamificationSnapshot): List<RecentXpActivity> = listOf(
        RecentXpActivity("إكمال درس", "المشتقة الثانية", 15),
        RecentXpActivity("نتيجة اختبار", "آخر اختبار: 85%", 45),
        RecentXpActivity("مواظبة", "سلسلة ${gamification.streakDays} أيام", 10),
    )

    private fun xpRules(): List<XpRule> = listOf(
        XpRule("الدروس", "تحصل على نقاط عند إكمال درس ومعالجة محتواه."),
        XpRule("الاختبارات", "الإجابات الصحيحة تضيف نقاطاً حسب عدد الأسئلة."),
        XpRule("المواظبة", "الاستمرار اليومي يحافظ على السلسلة ويدعم تقدم المستوى."),
    )
}
