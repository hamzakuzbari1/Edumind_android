package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.AnalyticsPeriod
import com.rork.eduspark.data.model.StudentMonitoringStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository
import kotlin.math.roundToInt
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
 * TC-15 · Teacher Analytics — PDF page 22.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Compact "what needs attention" landing. Every figure is derived from the existing
 * [TeacherRepository] roster / quiz-attempt / analytics snapshot — no second analytics
 * store, and no invented metrics (subscription expiry is omitted because Teacher mock
 * state does not carry it).
 */
data class TeacherAnalyticsInsight(
    val courseId: String,
    val subjectTitle: String,
    val completionPercent: Int,
)

data class TeacherAnalyticsQuizAttention(
    val quizId: String,
    val quizTitle: String,
    val pendingCount: Int,
)

data class TeacherAnalyticsInactiveAttention(
    val courseId: String,
    val subjectTitle: String,
    val inactiveCount: Int,
    val firstStudentId: String?,
)

data class TeacherAnalyticsScreenData(
    val engagementCounts: List<Int>,
    val insight: TeacherAnalyticsInsight?,
    val quizAttention: TeacherAnalyticsQuizAttention?,
    val inactiveAttention: TeacherAnalyticsInactiveAttention?,
)

data class TeacherAnalyticsUiState(
    val result: UiState<TeacherAnalyticsScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
)

sealed interface TeacherAnalyticsEvent {
    data class OpenCourse(val courseId: String) : TeacherAnalyticsEvent
    data class OpenQuizResults(val quizId: String) : TeacherAnalyticsEvent
    data class OpenStudentDetail(val studentId: String) : TeacherAnalyticsEvent
}

class TeacherAnalyticsViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherAnalyticsUiState())
    val state: StateFlow<TeacherAnalyticsUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherAnalyticsEvent>(Channel.BUFFERED)
    val events: Flow<TeacherAnalyticsEvent> = _events.receiveAsFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    fun onOpenCourse(courseId: String) = viewModelScope.launch {
        _events.send(TeacherAnalyticsEvent.OpenCourse(courseId))
    }

    fun onOpenQuizResults(quizId: String) = viewModelScope.launch {
        _events.send(TeacherAnalyticsEvent.OpenQuizResults(quizId))
    }

    fun onOpenStudentDetail(studentId: String) = viewModelScope.launch {
        _events.send(TeacherAnalyticsEvent.OpenStudentDetail(studentId))
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
            val students = (teacherRepository.getStudents(teacherId) as? AppResult.Success)?.data.orEmpty()
            val quizzes = (teacherRepository.getQuizzes(teacherId) as? AppResult.Success)?.data.orEmpty()
            val snapshotResult = teacherRepository.getAnalyticsSnapshot(
                teacherId,
                courseId = null,
                period = AnalyticsPeriod.SevenDays,
            )
            if (snapshotResult !is AppResult.Success) {
                _state.update { it.copy(result = UiState.Failure((snapshotResult as AppResult.Failure).error)) }
                return@launch
            }

            val insight = weakestCourseInsight(courses, students)
            val quizAttention = quizzes.map { quiz ->
                val attempts = (teacherRepository.getQuizAttempts(quiz.id) as? AppResult.Success)?.data.orEmpty()
                TeacherAnalyticsQuizAttention(
                    quizId = quiz.id,
                    quizTitle = quiz.title,
                    pendingCount = attempts.sumOf { it.pendingEssayCount },
                )
            }.filter { it.pendingCount > 0 }.maxByOrNull { it.pendingCount }

            val inactiveByCourse = students
                .filter { it.status == StudentMonitoringStatus.Inactive }
                .groupBy { it.courseId }
            val inactiveAttention = inactiveByCourse.maxByOrNull { it.value.size }?.let { (courseId, group) ->
                val course = courses.firstOrNull { it.id == courseId }
                TeacherAnalyticsInactiveAttention(
                    courseId = courseId,
                    subjectTitle = courseSubjectTitle(course?.title ?: group.first().courseTitle),
                    inactiveCount = group.size,
                    firstStudentId = group.firstOrNull()?.studentId,
                )
            }

            _state.update {
                it.copy(
                    result = UiState.Content(
                        TeacherAnalyticsScreenData(
                            engagementCounts = snapshotResult.data.engagement.map { point -> point.activeCount },
                            insight = insight,
                            quizAttention = quizAttention,
                            inactiveAttention = inactiveAttention,
                        )
                    )
                )
            }
        }
    }

    private fun weakestCourseInsight(
        courses: List<TeacherCourseSummary>,
        students: List<TeacherStudentSummary>,
    ): TeacherAnalyticsInsight? {
        return courses.mapNotNull { course ->
            val roster = students.filter { it.courseId == course.id }
            if (roster.isEmpty()) return@mapNotNull null
            val completionPercent = (roster.map { it.progressPercent }.average() * 100).roundToInt()
            TeacherAnalyticsInsight(
                courseId = course.id,
                subjectTitle = courseSubjectTitle(course.title),
                completionPercent = completionPercent,
            )
        }.minWithOrNull(compareBy<TeacherAnalyticsInsight> { it.completionPercent }.thenBy { it.subjectTitle })
    }

    private fun courseSubjectTitle(courseTitle: String): String {
        val separators = listOf("—", "–", "-")
        val cut = separators.firstOrNull { courseTitle.contains(it) }?.let { courseTitle.substringBefore(it).trim() }
        return cut?.takeIf { it.isNotBlank() } ?: courseTitle
    }
}
