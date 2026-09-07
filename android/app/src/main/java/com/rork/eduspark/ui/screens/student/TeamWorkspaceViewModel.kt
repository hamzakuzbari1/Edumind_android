package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.model.ProjectTeam
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-08 · Team Workspace.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [tasks] is read straight from [com.rork.eduspark.data.model.ActiveProject.milestones] —
 * the exact same [ProjectTask] list PJ-01/PJ-03 render from — never a second copy; only the
 * assignee mapping ([ProjectTeam.taskAssignments]) is workspace-specific state. Self-assign
 * only: [assignToMe]/[unassignMine] can only ever change the current student's own claim (see
 * [ProjectRepository.assignTaskToSelf]'s own doc comment) — there is no reassign-someone-else
 * affordance in this slice. [sendMessage] appends locally the moment the mock repository
 * accepts it — no WebSocket, no real-time delivery to anyone else, state is session-local only.
 */
data class TeamWorkspaceScreenData(
    val projectTitle: String,
    val team: ProjectTeam,
    val tasks: List<ProjectTask>,
)

enum class TeamWorkspaceTab { Overview, Chat }

data class TeamWorkspaceUiState(
    val result: UiState<TeamWorkspaceScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val tab: TeamWorkspaceTab = TeamWorkspaceTab.Overview,
    val isSendingMessage: Boolean = false,
)

class TeamWorkspaceViewModel(
    private val projectId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeamWorkspaceUiState())
    val state: StateFlow<TeamWorkspaceUiState> = _state.asStateFlow()

    private var projectTitle: String? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            projectRepository.activeProjects.collect { active ->
                val title = projectTitle ?: return@collect
                val current = active.firstOrNull { it.projectId == projectId } ?: return@collect
                refreshTeam(title, current.milestones.flatMap { it.tasks })
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val projectResult = projectRepository.getProject(projectId)
            val active = (projectRepository.getActiveProjects() as? AppResult.Success)?.data
                ?.firstOrNull { it.projectId == projectId }

            if (projectResult is AppResult.Success && active != null) {
                projectTitle = projectResult.data.title
                refreshTeam(projectResult.data.title, active.milestones.flatMap { it.tasks })
            } else {
                val error = (projectResult as? AppResult.Failure)?.error ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }

    private fun refreshTeam(title: String, tasks: List<ProjectTask>) {
        viewModelScope.launch {
            val teamResult = projectRepository.getTeam(projectId)
            if (teamResult is AppResult.Success) {
                _state.update { it.copy(result = UiState.Content(TeamWorkspaceScreenData(title, teamResult.data, tasks))) }
            }
        }
    }

    fun selectTab(tab: TeamWorkspaceTab) = _state.update { it.copy(tab = tab) }

    fun assignToMe(taskId: String) {
        viewModelScope.launch {
            projectRepository.assignTaskToSelf(projectId, taskId)
            reloadTeamOnly()
        }
    }

    fun unassignMine(taskId: String) {
        viewModelScope.launch {
            projectRepository.unassignOwnTask(projectId, taskId)
            reloadTeamOnly()
        }
    }

    private fun reloadTeamOnly() {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        viewModelScope.launch {
            val teamResult = projectRepository.getTeam(projectId)
            if (teamResult is AppResult.Success) {
                _state.update { it.copy(result = UiState.Content(data.copy(team = teamResult.data))) }
            }
        }
    }

    fun sendMessage(text: String) {
        if (text.isBlank() || _state.value.isSendingMessage) return
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        _state.update { it.copy(isSendingMessage = true) }
        viewModelScope.launch {
            when (val result = projectRepository.sendTeamMessage(projectId, text)) {
                is AppResult.Success -> {
                    val updatedTeam = data.team.copy(messages = data.team.messages + result.data)
                    _state.update { it.copy(result = UiState.Content(data.copy(team = updatedTeam)), isSendingMessage = false) }
                }
                is AppResult.Failure -> _state.update { it.copy(isSendingMessage = false) }
            }
        }
    }
}
