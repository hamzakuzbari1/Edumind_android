package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.data.repository.LearningRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * STUDENT_COURSES tab ("موادي") — course discovery.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Hosts the STUDENT_COURSES tab root — previously a bare [com.rork.eduspark.ui.screens.PlaceholderScreen],
 * so a locked/unsubscribed course (e.g. "biology") had no real path a student could tap
 * through to reach ST-02's locked state; only Student Home's `subjects` list existed, and
 * that is entitled-courses-only by design (ST-01's own doc comment). This is the smallest
 * real course-discovery surface: [LearningRepository.getStudentCourses] alone.
 */
data class StudentCoursesUiState(
    val result: UiState<List<StudentCourseSummary>> = UiState.Loading,
    val isOnline: Boolean = true,
)

class StudentCoursesViewModel(
    private val learningRepository: LearningRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(StudentCoursesUiState())
    val state: StateFlow<StudentCoursesUiState> = _state.asStateFlow()

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
            when (val result = learningRepository.getStudentCourses()) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }
}
