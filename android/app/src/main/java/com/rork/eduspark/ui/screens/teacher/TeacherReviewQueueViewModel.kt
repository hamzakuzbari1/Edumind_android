package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectReviewStatus
import com.rork.eduspark.data.model.TeacherProjectSubmission
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-18 · Project Review Queue.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reached from TC-17 (a link on the project list, and any project card's own context) —
 * never a separate TC number. Rows still needing attention ([ProjectReviewStatus.AwaitingReview]/
 * [ProjectReviewStatus.InReview]) sort before already-[ProjectReviewStatus.Reviewed] ones, the
 * one ordering decision this ViewModel makes; every other field is read straight from
 * [TeacherRepository.getReviewQueue] — never a re-derived number.
 */
data class TeacherReviewQueueUiState(
    val result: UiState<List<TeacherProjectSubmission>> = UiState.Loading,
    val isOnline: Boolean = true,
)

sealed interface TeacherReviewQueueEvent {
    data class OpenDetail(val submissionId: String) : TeacherReviewQueueEvent
}

class TeacherReviewQueueViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherReviewQueueUiState())
    val state: StateFlow<TeacherReviewQueueUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherReviewQueueEvent>(Channel.BUFFERED)
    val events: Flow<TeacherReviewQueueEvent> = _events.receiveAsFlow()

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
            val teacherId = authRepository.session.first()?.id
            if (teacherId == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            when (val result = teacherRepository.getReviewQueue(teacherId)) {
                is AppResult.Success -> {
                    val sorted = result.data.sortedBy { it.reviewStatus == ProjectReviewStatus.Reviewed }
                    _state.update { it.copy(result = UiState.Content(sorted)) }
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun onSubmissionTapped(submissionId: String) = viewModelScope.launch { _events.send(TeacherReviewQueueEvent.OpenDetail(submissionId)) }
}
