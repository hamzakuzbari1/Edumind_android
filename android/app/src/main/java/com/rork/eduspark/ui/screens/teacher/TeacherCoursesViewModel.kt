package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.TeacherCourseCreateRequest
import com.rork.eduspark.data.model.TeacherCourseFormSubject
import com.rork.eduspark.data.model.TeacherCourseStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
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
 * TC-03 · Courses List.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Filtering happens entirely in the content composable over the loaded list — never a second
 * repository call. Create uses the existing teacher Course APIs, then reloads this list.
 */
data class TeacherCoursesFilters(
    val subjectId: String? = null,
    val grade: Grade? = null,
    val status: TeacherCourseStatus? = null,
)

data class TeacherCourseCreateUiState(
    val visible: Boolean = false,
    val title: String = "",
    val description: String = "",
    val grade: Grade = Grade.Baccalaureate,
    val subjectId: String? = null,
    val subjects: List<TeacherCourseFormSubject> = emptyList(),
    val published: Boolean = true,
    val subjectsLoading: Boolean = false,
    val isSubmitting: Boolean = false,
    val showValidationError: Boolean = false,
    val error: AppError? = null,
)

data class TeacherCoursesUiState(
    val result: UiState<List<TeacherCourseSummary>> = UiState.Loading,
    val isOnline: Boolean = true,
    val searchQuery: String = "",
    val filters: TeacherCoursesFilters = TeacherCoursesFilters(),
    val create: TeacherCourseCreateUiState = TeacherCourseCreateUiState(),
)

sealed interface TeacherCoursesEvent {
    data class OpenCourse(val courseId: String) : TeacherCoursesEvent
}

class TeacherCoursesViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherCoursesUiState())
    val state: StateFlow<TeacherCoursesUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherCoursesEvent>(Channel.BUFFERED)
    val events: Flow<TeacherCoursesEvent> = _events.receiveAsFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        if (_state.value.result !is UiState.Content) {
            _state.update { it.copy(result = UiState.Loading) }
        }
        viewModelScope.launch {
            val teacherId = authRepository.session.first()?.id
            if (teacherId == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            when (val result = teacherRepository.getCourses(teacherId)) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun updateSearchQuery(query: String) = _state.update { it.copy(searchQuery = query) }

    fun toggleSubjectFilter(subjectId: String) = _state.update {
        it.copy(filters = it.filters.copy(subjectId = if (it.filters.subjectId == subjectId) null else subjectId))
    }

    fun toggleGradeFilter(grade: Grade) = _state.update {
        it.copy(filters = it.filters.copy(grade = if (it.filters.grade == grade) null else grade))
    }

    fun toggleStatusFilter(status: TeacherCourseStatus) = _state.update {
        it.copy(filters = it.filters.copy(status = if (it.filters.status == status) null else status))
    }

    fun selectStatus(status: TeacherCourseStatus?) = _state.update {
        it.copy(filters = TeacherCoursesFilters(status = status))
    }

    fun clearFilters() = _state.update { it.copy(searchQuery = "", filters = TeacherCoursesFilters()) }

    fun openCreateDialog() {
        _state.update {
            it.copy(create = TeacherCourseCreateUiState(visible = true, grade = Grade.Baccalaureate, published = true))
        }
        loadFormSubjects(Grade.Baccalaureate)
    }

    fun dismissCreateDialog() {
        if (_state.value.create.isSubmitting) return
        _state.update { it.copy(create = TeacherCourseCreateUiState()) }
    }

    fun updateCreateTitle(title: String) = _state.update {
        it.copy(create = it.create.copy(title = title, showValidationError = false, error = null))
    }

    fun updateCreateDescription(description: String) = _state.update {
        it.copy(create = it.create.copy(description = description, error = null))
    }

    fun updateCreatePublished(published: Boolean) = _state.update {
        it.copy(create = it.create.copy(published = published))
    }

    fun selectCreateGrade(grade: Grade) {
        _state.update {
            it.copy(create = it.create.copy(grade = grade, subjectId = null, showValidationError = false, error = null))
        }
        loadFormSubjects(grade)
    }

    fun selectCreateSubject(subjectId: String) = _state.update {
        it.copy(create = it.create.copy(subjectId = subjectId, showValidationError = false, error = null))
    }

    fun submitCreate() {
        val form = _state.value.create
        if (form.isSubmitting) return
        val title = form.title.trim()
        val subject = form.subjects.firstOrNull { it.id == form.subjectId }
        if (title.length < 2 || subject == null) {
            _state.update { it.copy(create = form.copy(showValidationError = true)) }
            return
        }
        _state.update { it.copy(create = form.copy(isSubmitting = true, error = null, showValidationError = false)) }
        viewModelScope.launch {
            when (
                val result = teacherRepository.createCourse(
                    TeacherCourseCreateRequest(
                        title = title,
                        subjectId = subject.id,
                        subjectTitle = subject.name,
                        grade = form.grade,
                        description = form.description.trim().takeIf { it.isNotEmpty() },
                        published = form.published,
                    ),
                )
            ) {
                is AppResult.Success -> {
                    _state.update { it.copy(create = TeacherCourseCreateUiState()) }
                    load()
                    _events.send(TeacherCoursesEvent.OpenCourse(result.data.id))
                }
                is AppResult.Failure -> _state.update {
                    it.copy(create = it.create.copy(isSubmitting = false, error = result.error))
                }
            }
        }
    }

    private fun loadFormSubjects(grade: Grade) {
        _state.update { it.copy(create = it.create.copy(subjectsLoading = true, subjects = emptyList())) }
        viewModelScope.launch {
            when (val result = teacherRepository.getCourseFormSubjects(grade)) {
                is AppResult.Success -> {
                    val math = result.data.firstOrNull { subject ->
                        subject.name.contains("رياض", ignoreCase = true) ||
                            subject.name.contains("math", ignoreCase = true)
                    }
                    _state.update { state ->
                        val selected = state.create.subjectId
                            ?.takeIf { id -> result.data.any { it.id == id } }
                            ?: math?.id
                            ?: result.data.firstOrNull()?.id
                        state.copy(
                            create = state.create.copy(
                                subjects = result.data,
                                subjectId = selected,
                                subjectsLoading = false,
                            ),
                        )
                    }
                }
                is AppResult.Failure -> _state.update {
                    it.copy(create = it.create.copy(subjectsLoading = false, error = result.error, subjects = emptyList()))
                }
            }
        }
    }
}
