package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.ProjectReflection
import com.rork.eduspark.data.model.isFullyCompleted
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-10 · Project Showcase Detail.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [reflections] reuses [ProjectRepository.getReflection] per milestone — the exact same PJ-09
 * repository state, never a second copy fetched or stored here. Only [milestoneTitles] are
 * shown for the milestone summary, never a per-task/submission dump (the Screen Inventory's
 * "do not dump every internal task/submission"). [certificateCode] is null until
 * [ProjectRepository.getCertificateCode] resolves one — this screen never fabricates a
 * certificate entry point for a project that doesn't have one.
 */
data class ShowcaseDetailScreenData(
    val project: Project,
    val active: ActiveProject,
    val reflections: List<ProjectReflection>,
    val certificateCode: String?,
)

data class ShowcaseDetailUiState(
    val result: UiState<ShowcaseDetailScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class ProjectShowcaseDetailViewModel(
    private val projectId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ShowcaseDetailUiState())
    val state: StateFlow<ShowcaseDetailUiState> = _state.asStateFlow()

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
            val projectResult = projectRepository.getProject(projectId)
            val active = (projectRepository.getActiveProjects() as? AppResult.Success)?.data
                ?.firstOrNull { it.projectId == projectId }

            // Only a fully completed project is a showcase artifact — an in-progress project
            // (even one this screen was somehow reached for) never renders here as if finished.
            if (projectResult !is AppResult.Success || active == null || !active.isFullyCompleted) {
                val error = (projectResult as? AppResult.Failure)?.error ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }

            val reflections = active.milestones.mapNotNull { milestone ->
                (projectRepository.getReflection(projectId, milestone.id) as? AppResult.Success)?.data
            }
            val certificateCode = (projectRepository.getCertificateCode(projectId) as? AppResult.Success)?.data

            _state.update {
                it.copy(result = UiState.Content(ShowcaseDetailScreenData(projectResult.data, active, reflections, certificateCode)))
            }
        }
    }
}
