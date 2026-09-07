package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.StudentMonitoringStatus
import com.rork.eduspark.data.model.TeacherDashboardSummary
import com.rork.eduspark.data.model.TeacherWorkItem
import com.rork.eduspark.data.model.TeacherWorkItemKind
import com.rork.eduspark.data.model.VoiceProfileStatus
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
 * TC-02 · Teacher Dashboard.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * "Today's number that matters first, then a work queue" — not a chart dashboard (charts are
 * TC-15, not this slice). [teacherId] is resolved once via [AuthRepository.session] the same
 * one-shot way [SplashViewModel]/[com.rork.eduspark.ui.screens.auth.VerifyEmailViewModel]
 * already read it, then handed to [TeacherRepository] — no cross-repository dependency, the
 * ViewModel is where the two repositories meet. Most work items in this slice still have no
 * built destination, so tapping one shows [TeacherComingSoonDialog] rather than a fake link —
 * see that composable's own doc comment. The one exception is a
 * [TeacherWorkItemKind.LessonProcessingFailed] item that names a real lesson
 * ([TeacherWorkItem.courseId]/[TeacherWorkItem.lessonId] both non-null): that one opens TC-06
 * directly, via [TeacherDashboardEvent.OpenLessonProcessing].
 *
 * [voiceProfileStatus] backs the small TC-09 link this dashboard carries — see
 * [com.rork.eduspark.ui.screens.teacher.TeacherDashboardScreen]'s own doc comment for why TC-09
 * is reached from here rather than a sixth bottom-nav tab.
 */
data class TeacherDashboardScreenData(
    val teacherDisplayName: String,
    val summary: TeacherDashboardSummary,
    val voiceProfileStatus: VoiceProfileStatus,
    val quizCount: Int,
    val inactiveStudentCount: Int = 0,
    val inactiveStudentContext: String = "",
)

data class TeacherDashboardUiState(
    val result: UiState<TeacherDashboardScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val showComingSoon: Boolean = false,
)

sealed interface TeacherDashboardEvent {
    data class OpenLessonProcessing(val courseId: String, val lessonId: String) : TeacherDashboardEvent
    data object OpenVoiceProfile : TeacherDashboardEvent
    data object OpenQuizzes : TeacherDashboardEvent
    data object OpenGrades : TeacherDashboardEvent
    data object OpenAnalytics : TeacherDashboardEvent
    data object OpenCourses : TeacherDashboardEvent
    data object OpenStudents : TeacherDashboardEvent
    data object OpenMessages : TeacherDashboardEvent
}

class TeacherDashboardViewModel(
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherDashboardUiState())
    val state: StateFlow<TeacherDashboardUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherDashboardEvent>(Channel.BUFFERED)
    val events: Flow<TeacherDashboardEvent> = _events.receiveAsFlow()

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
            val setupResult = teacherRepository.getSetupState(teacherId)
            val dashboardResult = teacherRepository.getDashboard(teacherId)
            val voiceProfileResult = teacherRepository.getVoiceProfile(teacherId)
            val quizzesResult = teacherRepository.getQuizzes(teacherId)
            val studentsResult = teacherRepository.getStudents(teacherId)
            if (setupResult !is AppResult.Success || dashboardResult !is AppResult.Success) {
                val error = (dashboardResult as? AppResult.Failure)?.error
                    ?: (setupResult as? AppResult.Failure)?.error
                    ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }
            _state.update {
                it.copy(
                    result = UiState.Content(
                        TeacherDashboardScreenData(
                            teacherDisplayName = setupResult.data.identity.displayName,
                            summary = dashboardResult.data,
                            voiceProfileStatus = (voiceProfileResult as? AppResult.Success)?.data?.profileStatus ?: VoiceProfileStatus.NotReady,
                            quizCount = (quizzesResult as? AppResult.Success)?.data?.size ?: 0,
                            inactiveStudentCount = (studentsResult as? AppResult.Success)
                                ?.data
                                ?.count { it.status == StudentMonitoringStatus.Inactive }
                                ?: 0,
                            inactiveStudentContext = (studentsResult as? AppResult.Success)
                                ?.data
                                ?.firstOrNull { it.status == StudentMonitoringStatus.Inactive }
                                ?.courseTitle
                                .orEmpty(),
                        )
                    )
                )
            }
        }
    }

    fun onWorkItemTapped(item: TeacherWorkItem) {
        val courseId = item.courseId
        val lessonId = item.lessonId
        viewModelScope.launch {
            when (item.kind) {
                TeacherWorkItemKind.LessonProcessingFailed -> {
                    if (courseId != null && lessonId != null) {
                        _events.send(TeacherDashboardEvent.OpenLessonProcessing(courseId, lessonId))
                    } else {
                        _events.send(TeacherDashboardEvent.OpenCourses)
                    }
                }
                TeacherWorkItemKind.SubmissionAwaitingReview -> _events.send(TeacherDashboardEvent.OpenQuizzes)
                TeacherWorkItemKind.DraftLesson -> _events.send(TeacherDashboardEvent.OpenCourses)
                TeacherWorkItemKind.UnreadMessage -> _events.send(TeacherDashboardEvent.OpenMessages)
            }
        }
    }

    fun onVoiceProfileTapped() = viewModelScope.launch { _events.send(TeacherDashboardEvent.OpenVoiceProfile) }

    fun onQuizzesTapped() = viewModelScope.launch { _events.send(TeacherDashboardEvent.OpenQuizzes) }

    fun onCoursesTapped() = viewModelScope.launch { _events.send(TeacherDashboardEvent.OpenCourses) }

    fun onStudentsTapped() = viewModelScope.launch { _events.send(TeacherDashboardEvent.OpenStudents) }

    fun onMessagesTapped() = viewModelScope.launch { _events.send(TeacherDashboardEvent.OpenMessages) }

    fun onGradesTapped() = viewModelScope.launch { _events.send(TeacherDashboardEvent.OpenGrades) }

    fun onAnalyticsTapped() = viewModelScope.launch { _events.send(TeacherDashboardEvent.OpenAnalytics) }

    fun dismissComingSoon() = _state.update { it.copy(showComingSoon = false) }
}
