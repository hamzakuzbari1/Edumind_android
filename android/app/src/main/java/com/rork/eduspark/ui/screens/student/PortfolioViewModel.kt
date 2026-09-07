package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.isFullyCompleted
import com.rork.eduspark.data.repository.ProfileRepository
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-10 · Project Portfolio.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A public-artifact showcase, not a second My Projects — only [ActiveProject.isFullyCompleted]
 * instances ever appear here, never an in-progress one shown as if it were finished. Reuses
 * [ProjectRepository.getActiveProjects]/[ProjectRepository.getCatalog] verbatim (no new
 * listing endpoint) and [ProfileRepository.getProfile] for the header identity — deliberately
 * only [com.rork.eduspark.data.model.StudentProfile.displayName]/`avatarInitial`; grade,
 * school and linked parents are never read here, since this screen is designed to be shown to
 * a parent, teacher, or university interviewer and has no reason to expose account internals.
 */
data class PortfolioEntry(
    val project: Project,
    val active: ActiveProject,
)

data class PortfolioScreenData(
    val displayName: String,
    val avatarInitial: String,
    val entries: List<PortfolioEntry>,
    val skillsSummary: List<String>,
)

data class PortfolioUiState(
    val result: UiState<PortfolioScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class PortfolioViewModel(
    private val projectRepository: ProjectRepository,
    private val profileRepository: ProfileRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(PortfolioUiState())
    val state: StateFlow<PortfolioUiState> = _state.asStateFlow()

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
            val profileResult = profileRepository.getProfile()
            val catalogResult = projectRepository.getCatalog()
            val activeResult = projectRepository.getActiveProjects()

            if (profileResult !is AppResult.Success || catalogResult !is AppResult.Success || activeResult !is AppResult.Success) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }

            val entries = activeResult.data
                .filter { it.isFullyCompleted }
                .mapNotNull { active ->
                    catalogResult.data.firstOrNull { it.id == active.projectId }?.let { PortfolioEntry(it, active) }
                }
            val skillsSummary = entries.flatMap { it.project.skills }.distinct()

            _state.update {
                it.copy(
                    result = UiState.Content(
                        PortfolioScreenData(
                            displayName = profileResult.data.displayName,
                            avatarInitial = profileResult.data.avatarInitial,
                            entries = entries,
                            skillsSummary = skillsSummary,
                        )
                    )
                )
            }
        }
    }
}
