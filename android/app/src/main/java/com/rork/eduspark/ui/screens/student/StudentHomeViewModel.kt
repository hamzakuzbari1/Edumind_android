package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.model.PlannerItem
import com.rork.eduspark.data.model.PlannerRecommendation
import com.rork.eduspark.data.model.RoutineSlot
import com.rork.eduspark.data.model.RoutineSlotStatus
import com.rork.eduspark.data.model.SessionStatus
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.data.model.StudentHomeSnapshot
import com.rork.eduspark.data.repository.AchievementRepository
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.PlannerRepository
import com.rork.eduspark.data.repository.RoutineRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-01 · Student Home.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A successful fetch is always [UiState.Content] — the PDF's "first day" layout is not a
 * different fetch outcome, it's the *same* snapshot with [StudentHomeSnapshot.continueItem]
 * null, and the screen decides which layout that calls for. Only a genuine fetch failure
 * (never happened yet, or the network dropped before anything loaded) is [UiState.Failure].
 *
 * Pull-to-refresh re-fetches without clearing the currently-shown content first, so the
 * screen never flashes to a skeleton on a manual refresh — only [isRefreshing] toggles,
 * which drives the pull-to-refresh spinner.
 */
data class StudentHomeUiState(
    val result: UiState<StudentHomeSnapshot> = UiState.Loading,
    val isOnline: Boolean = true,
    val isRefreshing: Boolean = false,
    val courses: List<StudentCourseSummary> = emptyList(),
    val todayPlannerItems: List<PlannerItem> = emptyList(),
    val todayRoutineSlots: List<RoutineSlot> = emptyList(),
    val plannerRecommendations: List<PlannerRecommendation> = emptyList(),
    /** ST-01's achievements-preview row (Test-2SY's `HomeAchievementsSection`). A separate,
     *  independently-failable fetch — losing this row is not worth failing the whole screen over. */
    val achievements: List<Achievement> = emptyList(),
)

class StudentHomeViewModel(
    private val learningRepository: LearningRepository,
    private val achievementRepository: AchievementRepository,
    private val plannerRepository: PlannerRepository,
    private val routineRepository: RoutineRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(StudentHomeUiState())
    val state: StateFlow<StudentHomeUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            plannerRepository.weekPlan.collect { plan ->
                val todayItems = plan?.sessions
                    ?.filter { it.day == plan.today && it.status != SessionStatus.Completed }
                    ?.sortedBy { it.startTime }
                    ?.map { session ->
                        PlannerItem(
                            time = session.startTime,
                            title = session.title,
                            durationMinutes = session.durationMinutes,
                        )
                    }
                    .orEmpty()
                _state.update { it.copy(todayPlannerItems = todayItems) }
            }
        }
        viewModelScope.launch {
            plannerRepository.recommendations.collect { recommendations ->
                _state.update { it.copy(plannerRecommendations = recommendations) }
            }
        }
        viewModelScope.launch {
            routineRepository.routineProfile.collect { profile ->
                val todaySlots = profile?.slots
                    ?.filter { it.day == profile.today && it.status == RoutineSlotStatus.Upcoming }
                    ?.sortedBy { it.startTime }
                    .orEmpty()
                _state.update { it.copy(todayRoutineSlots = todaySlots) }
            }
        }
        // Same hot-flow shape PlannerViewModel already collects exam schedule through — a
        // lesson completed on ST-03 updates the continue card/subject progress here without
        // the student having to leave Home and come back. Silent (no Loading flash).
        viewModelScope.launch {
            learningRepository.completedLessonIds.collect { fetch() }
        }
        load()
    }

    fun retry() = load()

    fun refresh() {
        if (_state.value.isRefreshing) return
        _state.update { it.copy(isRefreshing = true) }
        viewModelScope.launch {
            fetch()
            _state.update { it.copy(isRefreshing = false) }
        }
    }

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch { fetch() }
    }

    private suspend fun fetch() {
        when (val result = learningRepository.getStudentHome()) {
            is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
            is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
        }
        val coursesResult = learningRepository.getStudentCourses()
        if (coursesResult is AppResult.Success) {
            _state.update { it.copy(courses = coursesResult.data) }
        }
        val achievementsResult = achievementRepository.getAchievements()
        if (achievementsResult is AppResult.Success) {
            _state.update { it.copy(achievements = achievementsResult.data) }
        }
        plannerRepository.loadWeekPlan()
        routineRepository.loadRoutine()
    }
}
