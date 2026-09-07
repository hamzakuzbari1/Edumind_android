package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.LessonProcessingOverallStatus
import com.rork.eduspark.data.model.TeacherLessonProcessingState
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-06 · Lesson Processing Status.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [TeacherLessonProcessingState] is read from, and every mutation ([retryProcessing],
 * [startTicking]'s own [TeacherRepository.advanceLessonProcessing] calls) written straight
 * back to, [TeacherRepository] — this ViewModel keeps no independent copy of "is this lesson
 * done processing," see [TeacherLessonProcessingState.overallStatus]'s own doc comment for why
 * that decision lives in exactly one place. [startTicking] is the same "ViewModel just drives
 * the clock, repository remembers the state" shape [TeacherLessonUploadViewModel] already uses
 * for TC-05's progress — reopening this screen for the same lesson always resumes from
 * whatever stage the repository is actually at, never restarts.
 */
data class TeacherLessonProcessingScreenData(
    val lessonTitle: String,
    val courseTitle: String,
    val contentType: LessonContentType,
)

data class TeacherLessonProcessingUiState(
    val result: UiState<TeacherLessonProcessingScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val processing: TeacherLessonProcessingState? = null,
    val isRetrying: Boolean = false,
)

class TeacherLessonProcessingViewModel(
    private val courseId: String,
    private val lessonId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherLessonProcessingUiState())
    val state: StateFlow<TeacherLessonProcessingUiState> = _state.asStateFlow()

    private var tickingJob: Job? = null

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
            val lessonResult = teacherRepository.getLesson(courseId, lessonId)
            val courseResult = teacherRepository.getCourse(courseId)
            val processingResult = teacherRepository.getLessonProcessingState(lessonId)
            if (lessonResult !is AppResult.Success || courseResult !is AppResult.Success || processingResult !is AppResult.Success) {
                val error = (lessonResult as? AppResult.Failure)?.error
                    ?: (courseResult as? AppResult.Failure)?.error
                    ?: (processingResult as? AppResult.Failure)?.error
                    ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }

            _state.update {
                it.copy(
                    result = UiState.Content(
                        TeacherLessonProcessingScreenData(
                            lessonTitle = lessonResult.data.title,
                            courseTitle = courseResult.data.title,
                            contentType = lessonResult.data.contentType,
                        )
                    ),
                    processing = processingResult.data,
                )
            }
            if (processingResult.data.overallStatus == LessonProcessingOverallStatus.Running) {
                startTicking()
            }
        }
    }

    fun retryProcessing() {
        if (_state.value.isRetrying) return
        _state.update { it.copy(isRetrying = true) }
        viewModelScope.launch {
            when (val result = teacherRepository.retryLessonProcessing(lessonId)) {
                is AppResult.Success -> {
                    _state.update { it.copy(processing = result.data, isRetrying = false) }
                    startTicking()
                }
                is AppResult.Failure -> _state.update { it.copy(isRetrying = false) }
            }
        }
    }

    private fun startTicking() {
        tickingJob?.cancel()
        tickingJob = viewModelScope.launch {
            while (isActive) {
                val current = _state.value.processing ?: break
                if (current.overallStatus != LessonProcessingOverallStatus.Running) break
                delay(TICK_DELAY_MS)
                when (val result = teacherRepository.advanceLessonProcessing(lessonId)) {
                    is AppResult.Success -> {
                        _state.update { it.copy(processing = result.data) }
                        if (result.data.overallStatus != LessonProcessingOverallStatus.Running) break
                    }
                    is AppResult.Failure -> break
                }
            }
        }
    }

    override fun onCleared() {
        tickingJob?.cancel()
        super.onCleared()
    }

    private companion object {
        const val TICK_DELAY_MS = 900L
    }
}
