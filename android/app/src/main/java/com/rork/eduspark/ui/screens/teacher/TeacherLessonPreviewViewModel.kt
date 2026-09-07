package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.AiReviewStatus
import com.rork.eduspark.data.model.TeacherGeneratedQuestion
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonChunk
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-08 · Lesson Preview.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Read-only by construction: this ViewModel exposes no mutator at all, only [retry]. It filters
 * to [AiReviewStatus.Accepted] questions here, in the ViewModel, rather than trusting the
 * screen to remember to skip Rejected ones — see [TeacherLessonPreviewScreenData]'s own doc
 * comment for why a Rejected question is excluded by construction, not merely hidden by UI.
 */
data class TeacherLessonPreviewScreenData(
    val lesson: TeacherLesson,
    val courseTitle: String,
    val chunks: List<TeacherLessonChunk>,
    /** Already filtered to [AiReviewStatus.Accepted] — TC-08 never has to re-check review state itself. */
    val approvedQuestions: List<TeacherGeneratedQuestion>,
)

data class TeacherLessonPreviewUiState(
    val result: UiState<TeacherLessonPreviewScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
)

class TeacherLessonPreviewViewModel(
    private val courseId: String,
    private val lessonId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherLessonPreviewUiState())
    val state: StateFlow<TeacherLessonPreviewUiState> = _state.asStateFlow()

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
            val lessonResult = teacherRepository.getLesson(courseId, lessonId)
            val courseResult = teacherRepository.getCourse(courseId)
            val editorResult = teacherRepository.getLessonEditorState(courseId, lessonId)
            if (lessonResult !is AppResult.Success || courseResult !is AppResult.Success || editorResult !is AppResult.Success) {
                val error = (lessonResult as? AppResult.Failure)?.error
                    ?: (courseResult as? AppResult.Failure)?.error
                    ?: (editorResult as? AppResult.Failure)?.error
                    ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }
            _state.update {
                it.copy(
                    result = UiState.Content(
                        TeacherLessonPreviewScreenData(
                            lesson = lessonResult.data,
                            courseTitle = courseResult.data.title,
                            chunks = editorResult.data.chunks.sortedBy { chunk -> chunk.order },
                            approvedQuestions = editorResult.data.generatedQuestions.filter { it.reviewStatus == AiReviewStatus.Accepted },
                        )
                    )
                )
            }
        }
    }
}
