package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectReview
import com.rork.eduspark.data.model.ProjectSubmission
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-06 · AI Review & Rubric.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [ProjectRepository.getReview] is a deterministic MOCK fixture lookup, not a live AI call —
 * calling it here is what flips the task's [com.rork.eduspark.data.model.TaskWorkflowStatus.Reviewed]
 * (and [com.rork.eduspark.data.model.ProjectTaskStatus.Completed] if [ProjectReview.isAcceptable]),
 * so revisiting this screen never re-runs a "new" review or re-accepts anything — the same
 * fixture record comes back every time. [beginResubmission] only ever routes
 * [com.rork.eduspark.data.model.TaskWorkflowStatus.Reviewed] back to
 * [com.rork.eduspark.data.model.TaskWorkflowStatus.InProgress]; it never resubmits by itself.
 */
data class ProjectReviewScreenData(
    val task: ProjectTask,
    val submission: ProjectSubmission,
    val review: ProjectReview,
)

sealed interface ProjectReviewEvent {
    data object NavigateToComposer : ProjectReviewEvent
}

data class ProjectReviewUiState(
    val result: UiState<ProjectReviewScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val isStartingResubmission: Boolean = false,
)

class ProjectReviewViewModel(
    private val projectId: String,
    private val taskId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ProjectReviewUiState())
    val state: StateFlow<ProjectReviewUiState> = _state.asStateFlow()

    private val _events = Channel<ProjectReviewEvent>(Channel.BUFFERED)
    val events: Flow<ProjectReviewEvent> = _events.receiveAsFlow()

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
            val taskResult = projectRepository.getTask(projectId, taskId)
            val submissionResult = projectRepository.getSubmission(taskId)
            val submission = (submissionResult as? AppResult.Success)?.data
            if (taskResult !is AppResult.Success || submission == null) {
                val error = (taskResult as? AppResult.Failure)?.error ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }
            when (val reviewResult = projectRepository.getReview(projectId, taskId)) {
                is AppResult.Success -> _state.update {
                    it.copy(result = UiState.Content(ProjectReviewScreenData(taskResult.data, submission, reviewResult.data)))
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(reviewResult.error)) }
            }
        }
    }

    fun beginResubmission() {
        if (_state.value.isStartingResubmission) return
        _state.update { it.copy(isStartingResubmission = true) }
        viewModelScope.launch {
            projectRepository.beginResubmission(projectId, taskId)
            _state.update { it.copy(isStartingResubmission = false) }
            _events.send(ProjectReviewEvent.NavigateToComposer)
        }
    }
}
