package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.FeedbackMode
import com.rork.eduspark.data.model.Quiz
import com.rork.eduspark.data.model.QuizAnswer
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.repository.QuizRepository
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
 * ST-06 · Quiz Runner / ST-08 · Remedial Quiz / ST-09 · Manual Quiz Runner — one shell.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The same [Quiz] fetched here can be an AI lesson quiz, a teacher manual quiz, or a
 * remedial subset — [Quiz.origin] and [Quiz.isRemedial] are read by the screen to change
 * copy, marking and framing; nothing here branches on which screen ID a build called it.
 *
 * Every mutation (answer, question index, reset) is written straight through to
 * [QuizRepository], which is the actual owner of "resume where I left off" — this
 * ViewModel only mirrors that state for the UI to render.
 */
data class QuizRunnerUiState(
    val result: UiState<Quiz> = UiState.Loading,
    val isOnline: Boolean = true,
    val currentIndex: Int = 0,
    /** questionId → last saved response, restored from the repository on load. */
    val answers: Map<String, String> = emptyMap(),
    /** In-progress response for the current question, not yet confirmed via Next/Submit. */
    val draftResponse: String = "",
    val showValidation: Boolean = false,
    /** Immediate-feedback mode only: the question id whose just-confirmed answer is showing correct/incorrect. */
    val revealedFeedbackFor: String? = null,
    val hintRevealed: Boolean = false,
    val timeRemainingSeconds: Int? = null,
    val isSubmitting: Boolean = false,
    val submitError: AppError? = null,
    val submittedResult: QuizResult? = null,
)

class QuizRunnerViewModel(
    private val quizId: String,
    private val quizRepository: QuizRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(QuizRunnerUiState())
    val state: StateFlow<QuizRunnerUiState> = _state.asStateFlow()

    private var timerJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        timerJob?.cancel()
        viewModelScope.launch {
            when (val result = quizRepository.getQuiz(quizId)) {
                is AppResult.Success -> {
                    val quiz = result.data
                    val attempt = quizRepository.getAttempt(quizId)
                    val answers = attempt.answers.mapValues { (_, answer) -> answer.response }
                    val currentQuestion = quiz.questions.getOrNull(attempt.currentQuestionIndex)
                    var submittedResult: QuizResult? = null
                    if (attempt.isCompleted) {
                        submittedResult = (quizRepository.getResult(quizId) as? AppResult.Success)?.data
                    }
                    _state.update {
                        it.copy(
                            result = UiState.Content(quiz),
                            currentIndex = attempt.currentQuestionIndex,
                            answers = answers,
                            draftResponse = currentQuestion?.let { q -> answers[q.id] }.orEmpty(),
                            timeRemainingSeconds = quiz.timerSeconds,
                            submittedResult = submittedResult,
                        )
                    }
                    if (quiz.timerSeconds != null && !attempt.isCompleted) startTimer()
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    private fun startTimer() {
        timerJob = viewModelScope.launch {
            while (isActive) {
                delay(1000L)
                val remaining = _state.value.timeRemainingSeconds ?: break
                if (remaining <= 0) break
                _state.update { it.copy(timeRemainingSeconds = remaining - 1) }
            }
        }
    }

    fun updateDraft(response: String) = _state.update { it.copy(draftResponse = response, showValidation = false) }

    /** MC/T-F selection and free-text entry both funnel here. */
    fun selectOption(optionId: String) = updateDraft(optionId)

    /** Immediate mode's "Continue" tap, after feedback for the just-answered question was shown. */
    fun continueAfterFeedback() {
        _state.update { it.copy(revealedFeedbackFor = null) }
        advance()
    }

    fun next() {
        val quiz = currentQuiz() ?: return
        val question = quiz.questions.getOrNull(_state.value.currentIndex) ?: return
        val response = _state.value.draftResponse.trim()
        if (response.isEmpty()) {
            _state.update { it.copy(showValidation = true) }
            return
        }

        val updatedAttempt = quizRepository.saveAnswer(quizId, QuizAnswer(question.id, response))
        _state.update {
            it.copy(
                answers = updatedAttempt.answers.mapValues { (_, a) -> a.response },
                showValidation = false,
            )
        }

        if (quiz.feedbackMode == FeedbackMode.Immediate) {
            _state.update { it.copy(revealedFeedbackFor = question.id) }
        } else {
            advance()
        }
    }

    fun previous() {
        val quiz = currentQuiz() ?: return
        val newIndex = (_state.value.currentIndex - 1).coerceAtLeast(0)
        moveTo(quiz, newIndex)
    }

    private fun advance() {
        val quiz = currentQuiz() ?: return
        val isLast = _state.value.currentIndex == quiz.questions.lastIndex
        if (isLast) {
            submit()
        } else {
            moveTo(quiz, _state.value.currentIndex + 1)
        }
    }

    private fun moveTo(quiz: Quiz, index: Int) {
        quizRepository.goToQuestion(quizId, index)
        val question = quiz.questions[index]
        _state.update {
            it.copy(
                currentIndex = index,
                draftResponse = it.answers[question.id].orEmpty(),
                revealedFeedbackFor = null,
                showValidation = false,
                hintRevealed = false,
            )
        }
    }

    fun revealHint() = _state.update { it.copy(hintRevealed = true) }

    fun submit() {
        if (_state.value.isSubmitting) return
        _state.update { it.copy(isSubmitting = true, submitError = null) }
        viewModelScope.launch {
            when (val result = quizRepository.submitQuiz(quizId)) {
                is AppResult.Success -> {
                    timerJob?.cancel()
                    _state.update { it.copy(isSubmitting = false, submittedResult = result.data) }
                }
                is AppResult.Failure -> _state.update { it.copy(isSubmitting = false, submitError = result.error) }
            }
        }
    }

    /** ST-08's retry — same question set, blank slate. */
    fun retryAttempt() {
        quizRepository.resetAttempt(quizId)
        timerJob?.cancel()
        val quiz = currentQuiz()
        _state.update {
            it.copy(
                currentIndex = 0,
                answers = emptyMap(),
                draftResponse = "",
                revealedFeedbackFor = null,
                showValidation = false,
                hintRevealed = false,
                submittedResult = null,
                submitError = null,
                timeRemainingSeconds = quiz?.timerSeconds,
            )
        }
        if (quiz?.timerSeconds != null) startTimer()
    }

    private fun currentQuiz(): Quiz? = (_state.value.result as? UiState.Content)?.data

    override fun onCleared() {
        timerJob?.cancel()
    }
}
