package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.SubjectProgress
import com.rork.eduspark.data.model.PlannerRecommendation
import com.rork.eduspark.data.model.RoutineSlot
import com.rork.eduspark.data.model.WeekPlan
import com.rork.eduspark.data.repository.ExamRepository
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
 * ST-10 · Planner.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Collects [PlannerRepository.weekPlan] continuously rather than fetching once — a change
 * ST-11's chat accepts is written straight into that hot flow, and this screen's backstack
 * entry (and its ViewModel) stay alive the whole time ST-11 is pushed on top of it, so a
 * plain re-fetch on return would either be redundant or, worse, race the flow update. One
 * source of truth avoids both.
 */
data class PlannerUiState(
    val result: UiState<WeekPlan> = UiState.Loading,
    val isOnline: Boolean = true,
    val isRegenerating: Boolean = false,
    /** ST-14's confirmed count, reflected here only — no new planner feature reads from it yet. */
    val upcomingExamCount: Int = 0,
    /** Test-2SY's subject-strength analysis, derived from the same [SubjectProgress] data ST-01
     *  already shows — reused here rather than a second progress model. */
    val subjects: List<SubjectProgress> = emptyList(),
    /** Test-2SY's streak-context on the planner — the same streak ST-01/ST-15 already track. */
    val streakDays: Int = 0,
    val recommendations: List<PlannerRecommendation> = emptyList(),
    val routineSlots: List<RoutineSlot> = emptyList(),
)

class PlannerViewModel(
    private val plannerRepository: PlannerRepository,
    private val examRepository: ExamRepository,
    private val learningRepository: LearningRepository,
    private val routineRepository: RoutineRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(PlannerUiState())
    val state: StateFlow<PlannerUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            plannerRepository.weekPlan.collect { plan ->
                if (plan != null) _state.update { it.copy(result = UiState.Content(plan)) }
            }
        }
        viewModelScope.launch {
            examRepository.examSchedule.collect { schedule ->
                _state.update { it.copy(upcomingExamCount = schedule?.entries?.size ?: 0) }
            }
        }
        viewModelScope.launch {
            plannerRepository.recommendations.collect { recommendations ->
                _state.update { it.copy(recommendations = recommendations) }
            }
        }
        viewModelScope.launch {
            routineRepository.routineProfile.collect { routine ->
                _state.update { it.copy(routineSlots = routine?.slots.orEmpty()) }
            }
        }
        viewModelScope.launch {
            val home = learningRepository.getStudentHome()
            if (home is AppResult.Success) {
                _state.update { it.copy(subjects = home.data.subjects, streakDays = home.data.streakDays) }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val result = plannerRepository.loadWeekPlan()) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun regenerateWeek() {
        if (_state.value.isRegenerating) return
        _state.update { it.copy(isRegenerating = true) }
        viewModelScope.launch {
            plannerRepository.regenerateWeek()
            _state.update { it.copy(isRegenerating = false) }
        }
    }

    fun toggleSessionCompletion(sessionId: String) {
        viewModelScope.launch { plannerRepository.toggleSessionCompletion(sessionId) }
    }

    fun applyRecommendation(recommendationId: String) {
        viewModelScope.launch { plannerRepository.applyRecommendation(recommendationId) }
    }

    fun ignoreRecommendation(recommendationId: String) {
        viewModelScope.launch { plannerRepository.dismissRecommendation(recommendationId) }
    }
}
