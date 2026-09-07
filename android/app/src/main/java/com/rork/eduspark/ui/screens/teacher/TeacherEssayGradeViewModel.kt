package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-11 · Essay grading — PDF page 18.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Writes through [TeacherRepository.saveEssayGrade] into the existing attempt's
 * [com.rork.eduspark.data.model.TeacherEssayResponse] — not a second store.
 */
data class TeacherEssayGradeData(
    val quizId: String,
    val studentId: String,
    val studentName: String,
    val questionId: String,
    val questionNumber: Int,
    val questionPrompt: String,
    val studentText: String,
    val maxMark: Int,
    val assignedMark: Int?,
    val feedback: String,
)

data class TeacherEssayGradeUiState(
    val result: UiState<TeacherEssayGradeData> = UiState.Loading,
    val isOnline: Boolean = true,
    val selectedMark: Int? = null,
    val feedbackDraft: String = "",
    val isSaving: Boolean = false,
)

sealed interface TeacherEssayGradeEvent {
    data class OpenNext(val studentId: String, val questionId: String) : TeacherEssayGradeEvent
    data object Done : TeacherEssayGradeEvent
}

class TeacherEssayGradeViewModel(
    private val quizId: String,
    private val studentId: String,
    private val questionId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherEssayGradeUiState())
    val state: StateFlow<TeacherEssayGradeUiState> = _state.asStateFlow()

    private val _events = Channel<TeacherEssayGradeEvent>(Channel.BUFFERED)
    val events: Flow<TeacherEssayGradeEvent> = _events.receiveAsFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    fun selectMark(mark: Int) = _state.update { it.copy(selectedMark = mark) }

    fun updateFeedback(text: String) = _state.update { it.copy(feedbackDraft = text) }

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val quizResult = teacherRepository.getQuiz(quizId)
            val attemptsResult = teacherRepository.getQuizAttempts(quizId)
            if (quizResult !is AppResult.Success || attemptsResult !is AppResult.Success) {
                val error = (quizResult as? AppResult.Failure)?.error
                    ?: (attemptsResult as? AppResult.Failure)?.error
                    ?: AppError.NotFound
                _state.update { it.copy(result = UiState.Failure(error)) }
                return@launch
            }
            val quiz = quizResult.data
            val attempt = attemptsResult.data.firstOrNull { it.studentId == studentId }
            val questionIndex = quiz.questions.indexOfFirst { it.question.id == questionId }
            val question = quiz.questions.getOrNull(questionIndex)
            val essay = attempt?.essayResponses?.get(questionId)
            if (attempt == null || question == null || essay == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            val data = TeacherEssayGradeData(
                quizId = quizId,
                studentId = studentId,
                studentName = attempt.studentName,
                questionId = questionId,
                questionNumber = questionIndex + 1,
                questionPrompt = question.question.prompt,
                studentText = essay.studentText,
                maxMark = question.points,
                assignedMark = essay.assignedMark,
                feedback = essay.teacherFeedback,
            )
            _state.update {
                it.copy(
                    result = UiState.Content(data),
                    selectedMark = essay.assignedMark,
                    feedbackDraft = essay.teacherFeedback,
                )
            }
        }
    }

    fun saveGrade() {
        val mark = _state.value.selectedMark ?: return
        if (_state.value.isSaving) return
        _state.update { it.copy(isSaving = true) }
        viewModelScope.launch {
            when (
                val result = teacherRepository.saveEssayGrade(
                    quizId = quizId,
                    studentId = studentId,
                    questionId = questionId,
                    assignedMark = mark,
                    feedback = _state.value.feedbackDraft,
                )
            ) {
                is AppResult.Success -> {
                    _state.update { it.copy(isSaving = false) }
                    val attempts = (teacherRepository.getQuizAttempts(quizId) as? AppResult.Success)?.data.orEmpty()
                    val next = attempts.firstOrNull { it.hasPendingEssay }
                    val nextQuestionId = next?.firstPendingQuestionId()
                    if (next != null && nextQuestionId != null) {
                        _events.send(TeacherEssayGradeEvent.OpenNext(next.studentId, nextQuestionId))
                    } else {
                        _events.send(TeacherEssayGradeEvent.Done)
                    }
                }
                is AppResult.Failure -> _state.update { it.copy(isSaving = false) }
            }
        }
    }
}
