package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.TeacherProject
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
 * TC-17 · Project Authoring — the Teacher "Projects" tab's real content.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The minimum project-management root this slice's own brief calls for: list, Create, Edit,
 * and an entry into TC-18's review queue — still part of TC-17, no separate screen number.
 * "Add project" is grouped per course, the exact same shape TC-10's own quiz list already uses
 * for "Add quiz" (see [TeacherQuizListScreen]'s own doc comment) rather than a new course-picker
 * dialog.
 */
data class TeacherProjectsUiState(
    val result: UiState<List<TeacherProject>> = UiState.Loading,
    val isOnline: Boolean = true,
)

sealed interface TeacherProjectsEvent {
    data class OpenEditor(val projectId: String) : TeacherProjectsEvent
    data object OpenReviewQueue : TeacherProjectsEvent
}

class TeacherProjectsViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherProjectsUiState())
    val state: StateFlow<TeacherProjectsUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherProjectsEvent>(Channel.BUFFERED)
    val events: Flow<TeacherProjectsEvent> = _events.receiveAsFlow()

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
            when (val result = teacherRepository.getTeacherProjects(teacherId)) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun createProject(courseId: String) = viewModelScope.launch {
        when (val result = teacherRepository.createTeacherProject(courseId)) {
            is AppResult.Success -> _events.send(TeacherProjectsEvent.OpenEditor(result.data.id))
            is AppResult.Failure -> Unit
        }
    }

    fun onProjectTapped(projectId: String) = viewModelScope.launch { _events.send(TeacherProjectsEvent.OpenEditor(projectId)) }

    fun onReviewQueueTapped() = viewModelScope.launch { _events.send(TeacherProjectsEvent.OpenReviewQueue) }
}
