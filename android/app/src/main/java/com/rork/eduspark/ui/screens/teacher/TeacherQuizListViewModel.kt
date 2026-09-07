package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizAttemptStatus
import com.rork.eduspark.data.model.TeacherQuizStatus
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
 * TC-10 · Quizzes list — PDF page 14.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Filters, attempt/average, and pending-essay counts are derived from the same
 * [TeacherRepository.getQuizzes] / [TeacherRepository.getQuizAttempts] already used here.
 */
data class TeacherQuizRow(
    val quiz: TeacherQuiz,
    val hasResults: Boolean,
    val attemptsCount: Int = 0,
    val submittedCount: Int = 0,
    val averagePercent: Int? = null,
    val pendingEssayCount: Int = 0,
)

data class TeacherQuizListUiState(
    val result: UiState<List<TeacherQuizRow>> = UiState.Loading,
    val isOnline: Boolean = true,
    val isCreating: Boolean = false,
    val statusFilter: TeacherQuizStatus? = null,
    val courses: List<TeacherCourseSummary> = emptyList(),
    val showCoursePicker: Boolean = false,
    val pendingEssayCount: Int = 0,
    val pendingQuizId: String? = null,
)

sealed interface TeacherQuizListEvent {
    data class OpenEditor(val quizId: String) : TeacherQuizListEvent
}

class TeacherQuizListViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherQuizListUiState())
    val state: StateFlow<TeacherQuizListUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherQuizListEvent>(Channel.BUFFERED)
    val events: Flow<TeacherQuizListEvent> = _events.receiveAsFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    fun selectStatusFilter(status: TeacherQuizStatus?) = _state.update { it.copy(statusFilter = status) }

    fun onAddTapped() {
        val courses = _state.value.courses
        when {
            courses.isEmpty() -> return
            courses.size == 1 -> createQuiz(courses.first().id)
            else -> _state.update { it.copy(showCoursePicker = !it.showCoursePicker) }
        }
    }

    fun pickCourse(courseId: String) {
        _state.update { it.copy(showCoursePicker = false) }
        createQuiz(courseId)
    }

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
            val courses = (teacherRepository.getCourses(teacherId) as? AppResult.Success)?.data.orEmpty()
            when (val result = teacherRepository.getQuizzes(teacherId)) {
                is AppResult.Success -> {
                    val rows = result.data.map { quiz ->
                        val attempts = (teacherRepository.getQuizAttempts(quiz.id) as? AppResult.Success)?.data.orEmpty()
                        val submitted = attempts.filter { it.status == TeacherQuizAttemptStatus.Completed }
                        val scored = submitted.filter { !it.hasPendingEssay }
                        val average = if (quiz.totalPoints > 0 && scored.isNotEmpty()) {
                            scored.mapNotNull { it.scorePercent(quiz) }.average().toInt()
                        } else {
                            null
                        }
                        TeacherQuizRow(
                            quiz = quiz,
                            hasResults = quiz.status == TeacherQuizStatus.Published && attempts.isNotEmpty(),
                            attemptsCount = attempts.size,
                            submittedCount = submitted.size,
                            averagePercent = average,
                            pendingEssayCount = attempts.sumOf { it.pendingEssayCount },
                        )
                    }
                    val mostPending = rows.maxByOrNull { it.pendingEssayCount }
                    _state.update {
                        it.copy(
                            result = UiState.Content(rows),
                            courses = courses,
                            pendingEssayCount = rows.sumOf { row -> row.pendingEssayCount },
                            pendingQuizId = mostPending?.takeIf { row -> row.pendingEssayCount > 0 }?.quiz?.id,
                        )
                    }
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error), courses = courses) }
            }
        }
    }

    fun createQuiz(courseId: String) {
        if (_state.value.isCreating) return
        _state.update { it.copy(isCreating = true) }
        viewModelScope.launch {
            when (val result = teacherRepository.createQuiz(courseId)) {
                is AppResult.Success -> {
                    _state.update { it.copy(isCreating = false) }
                    _events.send(TeacherQuizListEvent.OpenEditor(result.data.id))
                }
                is AppResult.Failure -> _state.update { it.copy(isCreating = false) }
            }
        }
    }
}
