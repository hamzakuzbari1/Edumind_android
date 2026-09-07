package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.ProjectMode
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
 * PJ-02 · Project Detail.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The materials checklist ([ProjectDetailScreenData.checkedMaterialIds]) is tracked entirely
 * through [ProjectRepository.getCheckedMaterials]/[setMaterialChecked] — a preparation state
 * independent of [ActiveProject], so ticking a box here can never mark a milestone/task
 * complete (see [ProjectRepository]'s own doc comment).
 *
 * The primary action only ever calls [ProjectRepository.startProject] for
 * [ProjectMode.Solo] — a [ProjectMode.Team] project shows [ProjectDetailUiState.showTeamBoundary]
 * instead, an honest "not available yet" boundary rather than inventing team formation.
 * [startProject] is itself idempotent, so a double-tap here can never create two active
 * instances of the same project.
 */
data class ProjectDetailScreenData(
    val project: Project,
    val activeProject: ActiveProject?,
    val checkedMaterialIds: Set<String>,
)

data class ProjectDetailUiState(
    val result: UiState<ProjectDetailScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val isStarting: Boolean = false,
    val showTeamBoundary: Boolean = false,
)

sealed interface ProjectDetailEvent {
    data class NavigateToMilestoneBoard(val projectId: String) : ProjectDetailEvent
}

class ProjectDetailViewModel(
    private val projectId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ProjectDetailUiState())
    val state: StateFlow<ProjectDetailUiState> = _state.asStateFlow()

    private val _events = Channel<ProjectDetailEvent>(Channel.BUFFERED)
    val events: Flow<ProjectDetailEvent> = _events.receiveAsFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            projectRepository.activeProjects.collect { active ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(activeProject = active.firstOrNull { it.projectId == projectId })))
                }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val projectResult = projectRepository.getProject(projectId)
            if (projectResult !is AppResult.Success) {
                _state.update { it.copy(result = UiState.Failure((projectResult as AppResult.Failure).error)) }
                return@launch
            }
            val active = (projectRepository.getActiveProjects() as? AppResult.Success)?.data
                ?.firstOrNull { it.projectId == projectId }
            val checked = (projectRepository.getCheckedMaterials(projectId) as? AppResult.Success)?.data ?: emptySet()
            _state.update {
                it.copy(result = UiState.Content(ProjectDetailScreenData(projectResult.data, active, checked)))
            }
        }
    }

    fun toggleMaterial(materialId: String, checked: Boolean) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val updated = if (checked) data.checkedMaterialIds + materialId else data.checkedMaterialIds - materialId
        _state.update { it.copy(result = UiState.Content(data.copy(checkedMaterialIds = updated))) }
        viewModelScope.launch { projectRepository.setMaterialChecked(projectId, materialId, checked) }
    }

    /** Continue (already active), Start (solo, not started), or the team boundary — the screen decides which label to show; this decides what tapping it does. */
    fun onPrimaryAction() {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        if (data.activeProject != null) {
            viewModelScope.launch { _events.send(ProjectDetailEvent.NavigateToMilestoneBoard(projectId)) }
            return
        }
        when (data.project.mode) {
            ProjectMode.Solo -> startProject()
            ProjectMode.Team -> _state.update { it.copy(showTeamBoundary = true) }
        }
    }

    fun dismissTeamBoundary() = _state.update { it.copy(showTeamBoundary = false) }

    private fun startProject() {
        if (_state.value.isStarting) return
        _state.update { it.copy(isStarting = true) }
        viewModelScope.launch {
            when (val result = projectRepository.startProject(projectId)) {
                is AppResult.Success -> {
                    _state.update { it.copy(isStarting = false) }
                    _events.send(ProjectDetailEvent.NavigateToMilestoneBoard(projectId))
                }
                is AppResult.Failure -> _state.update { it.copy(isStarting = false) }
            }
        }
    }
}
