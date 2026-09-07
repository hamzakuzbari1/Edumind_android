package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.CommitmentSchedule
import com.rork.eduspark.data.model.RoutineBuildStep
import com.rork.eduspark.data.model.RoutineBuilderAnswers
import com.rork.eduspark.data.model.RoutineDraft
import com.rork.eduspark.data.model.RoutineProfile
import com.rork.eduspark.data.model.StudyTimeOfDay
import com.rork.eduspark.data.model.Weekday
import com.rork.eduspark.data.repository.RoutineRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-12 · Routine Builder.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One screen, six questions plus a review step — not six routes with a graph-scoped shared
 * ViewModel like onboarding's SO-01…SO-05. There is nowhere else in the app that needs to
 * reach an in-progress routine setup, so the extra graph-scoping machinery [OnboardingViewModel]
 * needs would only add ceremony here; a single regular ViewModel with local question-index
 * paging (same idea as SO-04's own five-questions-one-screen design) is enough.
 *
 * Deterministic mock only: [RoutineRepository.confirmRoutine] runs a rule-based builder over
 * these six answers, not an LLM call — matching Source Audit's own "smart planner generate"
 * fact that the real feature isn't AI either.
 */
data class RoutineBuilderUiState(
    val answers: RoutineBuilderAnswers = RoutineBuilderAnswers(),
    val isOnline: Boolean = true,
    val isConfirming: Boolean = false,
    val confirmFailed: Boolean = false,
    val confirmedRoutine: RoutineProfile? = null,
    val step: RoutineBuildStep = RoutineBuildStep.Onboarding,
    val draft: RoutineDraft? = null,
    val draftInput: String = "",
    val buildFailed: Boolean = false,
    val reviewFailed: Boolean = false,
) {
    val canConfirm: Boolean
        get() = answers.wakeTime != null &&
            answers.schoolHoursId != null &&
            answers.energyPattern != null &&
            answers.sleepTime != null
}

class RoutineBuilderViewModel(
    private val routineRepository: RoutineRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(RoutineBuilderUiState())
    val state: StateFlow<RoutineBuilderUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            routineRepository.routineDraft.collect { draft -> _state.update { it.copy(draft = draft) } }
        }
    }

    fun setWakeTime(time: String) = _state.update { it.copy(answers = it.answers.copy(wakeTime = time)) }

    fun setSchoolHours(presetId: String) = _state.update { it.copy(answers = it.answers.copy(schoolHoursId = presetId)) }

    fun toggleCommitment(id: String) {
        _state.update {
            val next = if (id in it.answers.commitmentIds) it.answers.commitmentIds - id else it.answers.commitmentIds + id
            it.copy(answers = it.answers.copy(commitmentIds = next))
        }
    }

    /** Approved design's nested commitment detail card (RoutineBuilder.dc.html) — days/time
     *  are additive to the plain [toggleCommitment] chip selection, never required to confirm. */
    fun toggleCommitmentDay(commitmentId: String, day: Weekday) = updateCommitmentSchedule(commitmentId) { current ->
        val days = if (day in current.days) current.days - day else current.days + day
        current.copy(days = days)
    }

    fun setCommitmentStartTime(commitmentId: String, time: String) = updateCommitmentSchedule(commitmentId) { it.copy(startTime = time) }

    fun setCommitmentEndTime(commitmentId: String, time: String) = updateCommitmentSchedule(commitmentId) { it.copy(endTime = time) }

    private fun updateCommitmentSchedule(commitmentId: String, transform: (CommitmentSchedule) -> CommitmentSchedule) {
        _state.update {
            val current = it.answers.commitmentSchedules[commitmentId] ?: CommitmentSchedule()
            val updated = it.answers.commitmentSchedules + (commitmentId to transform(current))
            it.copy(answers = it.answers.copy(commitmentSchedules = updated))
        }
    }

    fun toggleStudyWindow(id: String) {
        _state.update {
            val next = if (id in it.answers.studyWindowIds) it.answers.studyWindowIds - id else it.answers.studyWindowIds + id
            it.copy(answers = it.answers.copy(studyWindowIds = next))
        }
    }

    fun setEnergyPattern(pattern: StudyTimeOfDay) = _state.update { it.copy(answers = it.answers.copy(energyPattern = pattern)) }

    fun setSleepTime(time: String) = _state.update { it.copy(answers = it.answers.copy(sleepTime = time)) }

    fun confirmRoutine() {
        startAiBuild()
    }

    fun startAiBuild() {
        if (_state.value.isConfirming || !_state.value.canConfirm) return
        _state.update { it.copy(isConfirming = true, confirmFailed = false, buildFailed = false) }
        viewModelScope.launch {
            when (val result = routineRepository.startRoutineAiBuild(_state.value.answers)) {
                is AppResult.Success -> _state.update { it.copy(isConfirming = false, draft = result.data, step = RoutineBuildStep.AiBuild) }
                is AppResult.Failure -> _state.update { it.copy(isConfirming = false, confirmFailed = true, buildFailed = true) }
            }
        }
    }

    fun confirmDraftDay(day: Weekday) {
        viewModelScope.launch {
            routineRepository.confirmRoutineDraftDay(day)
        }
    }

    fun updateDraftInput(input: String) = _state.update { it.copy(draftInput = input) }

    fun sendDraftAdjustment() {
        val message = _state.value.draftInput.trim()
        if (message.isBlank()) return
        _state.update { it.copy(draftInput = "") }
        viewModelScope.launch { routineRepository.adjustRoutineDraft(message) }
    }

    fun reviewDraft() {
        if (_state.value.draft?.readyForReview != true) return
        _state.update { it.copy(reviewFailed = false) }
        viewModelScope.launch {
            when (routineRepository.reviewRoutineDraft()) {
                is AppResult.Success -> _state.update { it.copy(step = RoutineBuildStep.SuggestionReview) }
                is AppResult.Failure -> _state.update { it.copy(reviewFailed = true) }
            }
        }
    }

    fun setSuggestion(suggestionId: String, accepted: Boolean?) {
        viewModelScope.launch { routineRepository.setRoutineSuggestion(suggestionId, accepted) }
    }

    fun editDraft() = _state.update { it.copy(step = RoutineBuildStep.AiBuild) }

    fun returnToOnboarding() = _state.update { it.copy(step = RoutineBuildStep.Onboarding, isConfirming = false) }

    fun finalizeRoutine() {
        if (_state.value.isConfirming) return
        _state.update { it.copy(isConfirming = true, confirmFailed = false) }
        viewModelScope.launch {
            when (val result = routineRepository.finalizeRoutineDraft()) {
                is AppResult.Success -> _state.update {
                    it.copy(
                        isConfirming = false,
                        confirmedRoutine = result.data,
                        step = RoutineBuildStep.FinalWeek,
                    )
                }
                is AppResult.Failure -> _state.update { it.copy(isConfirming = false, confirmFailed = true) }
            }
        }
    }
}
