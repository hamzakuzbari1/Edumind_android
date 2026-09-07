package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.ProjectMode
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-03 · Milestone Board.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [ProjectRepository.activeProjects] is the single source of the whole board — the Progress
 * Spine renders straight from [ActiveProject.milestones], never a separately-tracked manual
 * percentage (see [ActiveProject]'s own doc comment). This screen is only ever reached for a
 * project the student has already started; if [projectId] has no [ActiveProject] this loads
 * as an honest [com.rork.eduspark.core.result.AppError.NotFound] rather than fabricating a board.
 *
 * A task tap now opens PJ-04 directly — a plain navigation callback the screen owns, not a
 * repository/ViewModel concern. [projectMode] is exposed so the screen can show its one
 * contextual PJ-08 "Team Workspace" action for [ProjectMode.Team] projects only — never a
 * second copy of [com.rork.eduspark.data.model.Project.mode] tracked independently.
 */
data class MilestoneBoardScreenData(
    val projectTitle: String,
    val projectMode: ProjectMode,
    val activeProject: ActiveProject,
)

data class MilestoneBoardUiState(
    val result: UiState<MilestoneBoardScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    /** Null means "use the current milestone" — set explicitly once the student taps a bead to expand/collapse it. */
    val expandedMilestoneId: String? = null,
)

class MilestoneBoardViewModel(
    private val projectId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(MilestoneBoardUiState())
    val state: StateFlow<MilestoneBoardUiState> = _state.asStateFlow()

    private var projectTitle: String? = null
    private var projectMode: ProjectMode? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            projectRepository.activeProjects.collect { active ->
                val title = projectTitle ?: return@collect
                val mode = projectMode ?: return@collect
                val current = active.firstOrNull { it.projectId == projectId } ?: return@collect
                _state.update { it.copy(result = UiState.Content(MilestoneBoardScreenData(title, mode, current))) }
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
                projectMode = projectResult.data.mode
                _state.update {
                    it.copy(
                        result = UiState.Content(MilestoneBoardScreenData(projectResult.data.title, projectResult.data.mode, active)),
                        expandedMilestoneId = it.expandedMilestoneId ?: active.currentMilestone?.id,
                    )
                }
            } else {
                val error = (projectResult as? AppResult.Failure)?.error ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }

    fun toggleMilestoneExpanded(milestoneId: String) {
        _state.update { it.copy(expandedMilestoneId = if (it.expandedMilestoneId == milestoneId) null else milestoneId) }
    }
}
