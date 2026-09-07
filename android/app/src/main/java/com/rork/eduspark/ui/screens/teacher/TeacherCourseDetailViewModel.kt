package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonProcessingStage
import com.rork.eduspark.data.model.LessonProcessingStageStatus
import com.rork.eduspark.data.model.StudentMonitoringStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonStatus
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
 * TC-04 · Course Detail.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Every lesson status now has a real destination: Processing opens TC-06, Draft opens TC-07
 * the editor, Published opens TC-08 the preview — see [TeacherCourseDetailEvent] for the three
 * one-shot navigation events this emits. [TeacherComingSoonDialog] is no longer used from this
 * screen for a lesson tap; nothing about a lesson's status leaves a fake link anymore.
 *
 * [TeacherLessonRow.activeStage]/[activeStageStatus] are read once, at load time, from
 * [TeacherRepository.getLessonProcessingState] — a snapshot for the row's secondary caption,
 * not a live subscription; TC-06 is where that pipeline actually ticks.
 */
data class TeacherLessonRow(
    val lesson: TeacherLesson,
    val activeStage: LessonProcessingStage? = null,
    val activeStageStatus: LessonProcessingStageStatus? = null,
)

data class TeacherCourseDetailData(
    val course: TeacherCourseSummary,
    val teacherDisplayName: String,
    val lessons: List<TeacherLessonRow>,
    val attentionStudents: List<TeacherStudentSummary> = emptyList(),
    val completionPercent: Int? = null,
)

data class TeacherCourseDetailUiState(
    val result: UiState<TeacherCourseDetailData> = UiState.Loading,
    val isOnline: Boolean = true,
)

sealed interface TeacherCourseDetailEvent {
    data class OpenLessonProcessing(val lessonId: String) : TeacherCourseDetailEvent
    data class OpenLessonEditor(val lessonId: String) : TeacherCourseDetailEvent
    data class OpenLessonPreview(val lessonId: String) : TeacherCourseDetailEvent
}

class TeacherCourseDetailViewModel(
    private val courseId: String,
    private val authRepository: AuthRepository,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherCourseDetailUiState())
    val state: StateFlow<TeacherCourseDetailUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherCourseDetailEvent>(Channel.BUFFERED)
    val events: Flow<TeacherCourseDetailEvent> = _events.receiveAsFlow()

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
            val courseResult = teacherRepository.getCourse(courseId)
            val lessonsResult = teacherRepository.getLessons(courseId)
            val teacherId = authRepository.session.first()?.id
            if (courseResult !is AppResult.Success || lessonsResult !is AppResult.Success || teacherId == null) {
                val error = (courseResult as? AppResult.Failure)?.error
                    ?: (lessonsResult as? AppResult.Failure)?.error
                    ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }

            val setupResult = teacherRepository.getSetupState(teacherId)
            val teacherDisplayName = (setupResult as? AppResult.Success)?.data?.identity?.displayName.orEmpty()

            val rows = lessonsResult.data.map { lesson ->
                if (lesson.status != TeacherLessonStatus.Processing) return@map TeacherLessonRow(lesson)
                val active = (teacherRepository.getLessonProcessingState(lesson.id) as? AppResult.Success)
                    ?.data?.stages?.firstOrNull {
                        it.status == LessonProcessingStageStatus.Running || it.status == LessonProcessingStageStatus.Failed
                    }
                TeacherLessonRow(lesson, active?.stage, active?.status)
            }

            val courseStudents = (teacherRepository.getStudents(teacherId) as? AppResult.Success)
                ?.data
                ?.filter { it.courseId == courseId }
                .orEmpty()
            val attentionStudents = courseStudents
                .filter {
                    it.status == StudentMonitoringStatus.NeedsAttention ||
                        it.status == StudentMonitoringStatus.Inactive
                }
                .take(3)
            val completionPercent = courseStudents
                .takeIf { it.isNotEmpty() }
                ?.map { it.progressPercent }
                ?.average()
                ?.let { (it * 100).roundToInt() }

            _state.update {
                it.copy(
                    result = UiState.Content(
                        TeacherCourseDetailData(
                            course = courseResult.data,
                            teacherDisplayName = teacherDisplayName,
                            lessons = rows,
                            attentionStudents = attentionStudents,
                            completionPercent = completionPercent,
                        )
                    )
                )
            }
        }
    }

    fun onLessonTapped(lesson: TeacherLesson) {
        val event = when (lesson.status) {
            TeacherLessonStatus.Processing -> TeacherCourseDetailEvent.OpenLessonProcessing(lesson.id)
            TeacherLessonStatus.Draft -> TeacherCourseDetailEvent.OpenLessonEditor(lesson.id)
            TeacherLessonStatus.Published -> TeacherCourseDetailEvent.OpenLessonPreview(lesson.id)
        }
        viewModelScope.launch { _events.send(event) }
    }

    /** Reflects the new order immediately (optimistic), then persists — see the TC-04 spec's own "UI updates immediately" requirement. */
    fun reorderLessons(orderedLessonIds: List<String>) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val byId = data.lessons.associateBy { it.lesson.id }
        val reorderedRows = orderedLessonIds.mapIndexedNotNull { index, id ->
            byId[id]?.let { row -> row.copy(lesson = row.lesson.copy(order = index + 1)) }
        }
        _state.update { it.copy(result = UiState.Content(data.copy(lessons = reorderedRows))) }
        viewModelScope.launch { teacherRepository.reorderLessons(courseId, orderedLessonIds) }
    }
}
