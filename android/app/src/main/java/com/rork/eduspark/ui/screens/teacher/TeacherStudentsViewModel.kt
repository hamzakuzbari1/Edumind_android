package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.StudentMonitoringStatus
import com.rork.eduspark.data.model.TeacherStudentSummary
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
 * TC-12 · Students List.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Filtering happens entirely in the content composable over the one loaded roster — never a
 * second repository call — the exact same local-filter shape [TeacherCoursesViewModel] already
 * established for TC-03. Tapping a student now opens TC-13 · Student Profile
 * ([TeacherStudentsEvent.OpenStudentDetail]) — the only change this slice makes to TC-12; every
 * other list behaviour (search, filters, empty state) is unchanged.
 */
data class TeacherStudentsFilters(
    val courseId: String? = null,
    val grade: Grade? = null,
    val status: StudentMonitoringStatus? = null,
)

data class TeacherStudentsUiState(
    val result: UiState<List<TeacherStudentSummary>> = UiState.Loading,
    val isOnline: Boolean = true,
    val searchQuery: String = "",
    val filters: TeacherStudentsFilters = TeacherStudentsFilters(),
)

sealed interface TeacherStudentsEvent {
    data class OpenStudentDetail(val studentId: String) : TeacherStudentsEvent
}

class TeacherStudentsViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherStudentsUiState())
    val state: StateFlow<TeacherStudentsUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherStudentsEvent>(Channel.BUFFERED)
    val events: Flow<TeacherStudentsEvent> = _events.receiveAsFlow()

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
            when (val result = teacherRepository.getStudents(teacherId)) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun updateSearchQuery(query: String) = _state.update { it.copy(searchQuery = query) }

    fun toggleCourseFilter(courseId: String) = _state.update {
        it.copy(filters = it.filters.copy(courseId = if (it.filters.courseId == courseId) null else courseId))
    }

    fun toggleGradeFilter(grade: Grade) = _state.update {
        it.copy(filters = it.filters.copy(grade = if (it.filters.grade == grade) null else grade))
    }

    fun toggleStatusFilter(status: StudentMonitoringStatus) = _state.update {
        it.copy(filters = it.filters.copy(status = if (it.filters.status == status) null else status))
    }

    fun clearFilters() = _state.update { it.copy(searchQuery = "", filters = TeacherStudentsFilters()) }

    fun onStudentTapped(studentId: String) = viewModelScope.launch { _events.send(TeacherStudentsEvent.OpenStudentDetail(studentId)) }
}
