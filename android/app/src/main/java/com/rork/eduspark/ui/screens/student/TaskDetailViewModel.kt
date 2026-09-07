package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-04 · Task Detail.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reads through [ProjectRepository.activeProjects] (already-cached, local — no fake remote
 * loading dependency, per this slice's offline requirement) for the task/milestone, plus
 * [ProjectRepository.getProject] once for the project title. [startTask] is the only call
 * that mutates anything, and only moves [com.rork.eduspark.data.model.TaskWorkflowStatus.NotStarted]
 * to [com.rork.eduspark.data.model.TaskWorkflowStatus.InProgress] — opening this screen alone
 * never does. Hints reveal one at a time via [revealedHintIds], never all at once.
 */
data class TaskDetailScreenData(
    val projectTitle: String,
    val milestoneTitle: String,
    val task: ProjectTask,
)

data class TaskDetailUiState(
    val result: UiState<TaskDetailScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val revealedHintIds: Set<String> = emptySet(),
    val isStarting: Boolean = false,
)

class TaskDetailViewModel(
    private val projectId: String,
    private val taskId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TaskDetailUiState())
    val state: StateFlow<TaskDetailUiState> = _state.asStateFlow()

    private var projectTitle: String? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            projectRepository.activeProjects.collect { activeList ->
                val title = projectTitle ?: return@collect
                val active = activeList.firstOrNull { it.projectId == projectId } ?: return@collect
                val milestone = active.milestones.firstOrNull { m -> m.tasks.any { it.id == taskId } } ?: return@collect
                val task = milestone.tasks.firstOrNull { it.id == taskId } ?: return@collect
                _state.update { it.copy(result = UiState.Content(TaskDetailScreenData(title, milestone.title, task))) }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val projectResult = projectRepository.getProject(projectId)
            val activeResult = projectRepository.getActiveProjects()
            val milestoneAndTask = (activeResult as? AppResult.Success)?.data
                ?.firstOrNull { it.projectId == projectId }
                ?.milestones
                ?.firstOrNull { m -> m.tasks.any { it.id == taskId } }
                ?.let { milestone -> milestone to milestone.tasks.first { it.id == taskId } }

            if (projectResult is AppResult.Success && milestoneAndTask != null) {
                val (milestone, task) = milestoneAndTask
                projectTitle = projectResult.data.title
                _state.update { it.copy(result = UiState.Content(TaskDetailScreenData(projectResult.data.title, milestone.title, task))) }
            } else {
                val error = (projectResult as? AppResult.Failure)?.error ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }

    fun revealNextHint() {
        val task = (_state.value.result as? UiState.Content)?.data?.task ?: return
        val nextHint = task.hints.firstOrNull { it.id !in _state.value.revealedHintIds } ?: return
        _state.update { it.copy(revealedHintIds = it.revealedHintIds + nextHint.id) }
    }

    fun startTask() {
        if (_state.value.isStarting) return
        _state.update { it.copy(isStarting = true) }
        viewModelScope.launch {
            projectRepository.startTaskWork(projectId, taskId)
            // Reflected by the activeProjects flow collector above.
            _state.update { it.copy(isStarting = false) }
        }
    }
}
