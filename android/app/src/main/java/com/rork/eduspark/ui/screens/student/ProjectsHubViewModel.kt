package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.ProjectDifficulty
import com.rork.eduspark.data.model.ProjectMedium
import com.rork.eduspark.data.model.ProjectMode
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-01 · Projects Hub.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Combines [ProjectRepository.getActiveProjects] and [ProjectRepository.getCatalog] into one
 * load, the same "one fetch, one Content" shape [AchievementViewModel] already uses.
 * [ProjectRepository.activeProjects] is additionally collected as a hot flow so starting a
 * project from PJ-02 and returning here shows it in My Projects immediately, no manual reload.
 *
 * Discover filtering ([DiscoverFilters]) is deliberately local-only — no repository call, no
 * remote query, matching the "local MOCK filtering, no search backend" boundary for this
 * slice. Filtering itself lives in [ProjectsHubScreen] as pure functions over already-loaded
 * data, not here, since it never needs to survive process death or be shared with another screen.
 */
data class ProjectsHubScreenData(
    val activeProjects: List<ActiveProject>,
    val catalog: List<Project>,
)

data class DiscoverFilters(
    val subjectId: String? = null,
    val difficulty: ProjectDifficulty? = null,
    val durationLabel: String? = null,
    val mode: ProjectMode? = null,
    val medium: ProjectMedium? = null,
)

data class ProjectsHubUiState(
    val result: UiState<ProjectsHubScreenData> = UiState.Loading,
    val filters: DiscoverFilters = DiscoverFilters(),
    val isOnline: Boolean = true,
)

class ProjectsHubViewModel(
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ProjectsHubUiState())
    val state: StateFlow<ProjectsHubUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            projectRepository.activeProjects.collect { active ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(activeProjects = active)))
                }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val activeResult = projectRepository.getActiveProjects()
            val catalogResult = projectRepository.getCatalog()
            if (activeResult is AppResult.Success && catalogResult is AppResult.Success) {
                _state.update {
                    it.copy(result = UiState.Content(ProjectsHubScreenData(activeResult.data, catalogResult.data)))
                }
            } else {
                val error = (activeResult as? AppResult.Failure)?.error
                    ?: (catalogResult as? AppResult.Failure)?.error
                    ?: AppError.Unknown
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }

    fun toggleSubjectFilter(subjectId: String) {
        _state.update { it.copy(filters = it.filters.copy(subjectId = if (it.filters.subjectId == subjectId) null else subjectId)) }
    }

    fun toggleDifficultyFilter(difficulty: ProjectDifficulty) {
        _state.update { it.copy(filters = it.filters.copy(difficulty = if (it.filters.difficulty == difficulty) null else difficulty)) }
    }

    fun toggleDurationFilter(durationLabel: String) {
        _state.update { it.copy(filters = it.filters.copy(durationLabel = if (it.filters.durationLabel == durationLabel) null else durationLabel)) }
    }

    fun toggleModeFilter(mode: ProjectMode) {
        _state.update { it.copy(filters = it.filters.copy(mode = if (it.filters.mode == mode) null else mode)) }
    }

    fun toggleMediumFilter(medium: ProjectMedium) {
        _state.update { it.copy(filters = it.filters.copy(medium = if (it.filters.medium == medium) null else medium)) }
    }

    fun clearFilters() = _state.update { it.copy(filters = DiscoverFilters()) }
}
