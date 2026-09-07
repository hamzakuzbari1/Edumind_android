package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.TeacherCourseStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-03 · Courses List.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Filtering happens entirely in the content composable over the loaded list — never a second
 * repository call — the exact same local-filter shape
 * [com.rork.eduspark.ui.screens.student.ProjectsHubViewModel] already established for PJ-01's
 * Discover filters. Tapping a course opens TC-04 Course Detail directly — [TeacherCoursesScreen]
 * takes the courseId straight to its `onOpenCourse` callback, no ViewModel event needed.
 */
data class TeacherCoursesFilters(
    val subjectId: String? = null,
    val grade: Grade? = null,
    val status: TeacherCourseStatus? = null,
)

data class TeacherCoursesUiState(
    val result: UiState<List<TeacherCourseSummary>> = UiState.Loading,
    val isOnline: Boolean = true,
    val searchQuery: String = "",
    val filters: TeacherCoursesFilters = TeacherCoursesFilters(),
)

class TeacherCoursesViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherCoursesUiState())
    val state: StateFlow<TeacherCoursesUiState> = _state.asStateFlow()

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
}
