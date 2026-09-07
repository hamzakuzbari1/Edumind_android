package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.AiReviewStatus
import com.rork.eduspark.data.model.QuestionType
import com.rork.eduspark.data.model.QuizOption
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.TeacherQuiz
import com.rork.eduspark.data.model.TeacherQuizQuestion
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-10 · Quiz Builder — create/edit one quiz.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A TEACHER-authored quiz builder — not TC-07's generated-lesson-quiz review. Title/instructions
 * are a local draft until explicit Save (same discipline TC-07's lesson-content section uses);
 * every question-list change (add/edit-save/delete/duplicate/reorder, AI-import acceptance) is
 * a discrete, already-decided action and persists immediately — nothing here keeps quiz content
 * only in this ViewModel, [TeacherRepository] is written to on every one of those actions.
 */
data class TeacherQuizEditorUiState(
    val result: UiState<TeacherQuiz> = UiState.Loading,
    val isOnline: Boolean = true,
    val titleDraft: String = "",
    val instructionsDraft: String = "",
    val durationMinutes: Int? = 15,
    val passMarkDraft: String = "60",
    val singleAttempt: Boolean = true,
    val hasUnsavedMetadata: Boolean = false,
    val isSavingMetadata: Boolean = false,
    val isPublishing: Boolean = false,
    val showPublishBlocked: Boolean = false,
    val expandedQuestionId: String? = null,
    val savingQuestionId: String? = null,
    val showAiImport: Boolean = false,
    val isLoadingAiCandidates: Boolean = false,
    val aiCandidates: List<TeacherQuizQuestion> = emptyList(),
    val aiReviewStatus: Map<String, AiReviewStatus> = emptyMap(),
    val phase: TeacherQuizEditorPhase = TeacherQuizEditorPhase.Setup,
) {
    /** Mirrors [TeacherRepository]'s own publish gate — see [com.rork.eduspark.data.repository.mock.MockTeacherRepository]'s `canPublishQuiz`. Reads the last-SAVED quiz, never the unsaved title/instructions draft — Publish always operates on what the repository actually has. */
    val canPublish: Boolean
        get() {
            val quiz = (result as? UiState.Content)?.data ?: return false
            return quiz.title.isNotBlank() &&
                quiz.questions.isNotEmpty() &&
                quiz.questions.all { it.question.prompt.isNotBlank() } &&
                quiz.questions.all { it.points > 0 } &&
                quiz.questions.all { hasValidCorrectAnswer(it.question) }
        }
}

enum class TeacherQuizEditorPhase { Setup, Questions }

private fun hasValidCorrectAnswer(question: QuizQuestion): Boolean = when (question.type) {
    QuestionType.MultipleChoice, QuestionType.TrueFalse ->
        question.options.size >= 2 && question.options.any { it.id == question.correctAnswer }
    QuestionType.ShortAnswer -> true
    QuestionType.GapFill -> question.correctAnswer.isNotBlank()
}

class TeacherQuizEditorViewModel(
    private val quizId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherQuizEditorUiState())
    val state: StateFlow<TeacherQuizEditorUiState> = _state.asStateFlow()

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
            when (val result = teacherRepository.getQuiz(quizId)) {
                is AppResult.Success -> _state.update {
                    it.copy(
                        result = UiState.Content(result.data),
                        titleDraft = result.data.title,
                        instructionsDraft = result.data.instructions,
                        durationMinutes = result.data.durationMinutes,
                        passMarkDraft = result.data.passMarkPercent.toString(),
                        singleAttempt = result.data.singleAttempt,
                        hasUnsavedMetadata = false,
                    )
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    private fun currentQuiz(): TeacherQuiz? = (_state.value.result as? UiState.Content)?.data

    // ── Metadata ─────────────────────────────────────────────────────────────────────────────
    fun updateTitleDraft(text: String) = _state.update { it.copy(titleDraft = text, hasUnsavedMetadata = true) }
    fun updateInstructionsDraft(text: String) = _state.update { it.copy(instructionsDraft = text, hasUnsavedMetadata = true) }
    fun updateDurationMinutes(minutes: Int?) = _state.update { it.copy(durationMinutes = minutes, hasUnsavedMetadata = true) }
    fun updatePassMarkDraft(text: String) = _state.update { it.copy(passMarkDraft = text.filter { ch -> ch.isDigit() }.take(3), hasUnsavedMetadata = true) }
    fun updateSingleAttempt(enabled: Boolean) = _state.update { it.copy(singleAttempt = enabled, hasUnsavedMetadata = true) }

    fun goToSetup() = _state.update { it.copy(phase = TeacherQuizEditorPhase.Setup) }

    private fun parsedPassMark(): Int = _state.value.passMarkDraft.toIntOrNull()?.coerceIn(0, 100) ?: 60

    private suspend fun persistMetadata(): AppResult<TeacherQuiz> {
        val current = _state.value
        return teacherRepository.saveQuizMetadata(
            quizId = quizId,
            title = current.titleDraft,
            instructions = current.instructionsDraft,
            durationMinutes = current.durationMinutes,
            passMarkPercent = parsedPassMark(),
            singleAttempt = current.singleAttempt,
        )
    }

    fun continueToQuestions() {
        if (_state.value.isSavingMetadata) return
        _state.update { it.copy(isSavingMetadata = true) }
        viewModelScope.launch {
            val result = persistMetadata()
            _state.update {
                if (result is AppResult.Success) {
                    it.copy(
                        result = UiState.Content(result.data),
                        passMarkDraft = result.data.passMarkPercent.toString(),
                        hasUnsavedMetadata = false,
                        isSavingMetadata = false,
                        phase = TeacherQuizEditorPhase.Questions,
                        expandedQuestionId = it.expandedQuestionId
                            ?: result.data.questions.firstOrNull()?.question?.id,
                    )
                } else {
                    it.copy(isSavingMetadata = false)
                }
            }
        }
    }

    fun saveMetadata() {
        if (_state.value.isSavingMetadata) return
        _state.update { it.copy(isSavingMetadata = true) }
        viewModelScope.launch {
            val result = persistMetadata()
            _state.update {
                if (result is AppResult.Success) {
                    it.copy(
                        result = UiState.Content(result.data),
                        passMarkDraft = result.data.passMarkPercent.toString(),
                        hasUnsavedMetadata = false,
                        isSavingMetadata = false,
                    )
                } else {
                    it.copy(isSavingMetadata = false)
                }
            }
        }
    }

    // ── Questions ────────────────────────────────────────────────────────────────────────────
    fun addQuestion(type: QuestionType) {
        val quiz = currentQuiz() ?: return
        val newQuestion = TeacherQuizQuestion(question = blankQuestion(type), points = 1)
        persistQuestions(quiz.questions + newQuestion)
        _state.update { it.copy(expandedQuestionId = newQuestion.question.id) }
    }

    fun selectQuestion(questionId: String) = _state.update { it.copy(expandedQuestionId = questionId) }

    fun toggleExpandedQuestion(questionId: String) = _state.update {
        it.copy(expandedQuestionId = if (it.expandedQuestionId == questionId) null else questionId)
    }

    fun updateQuestionDraft(questionId: String, transform: (QuizQuestion) -> QuizQuestion) {
        val quiz = currentQuiz() ?: return
        val updated = quiz.copy(
            questions = quiz.questions.map { if (it.question.id == questionId) it.copy(question = transform(it.question)) else it },
        )
        _state.update { it.copy(result = UiState.Content(updated)) }
    }

    fun updateQuestionPoints(questionId: String, points: Int) {
        if (points <= 0) return
        val quiz = currentQuiz() ?: return
        val updated = quiz.copy(questions = quiz.questions.map { if (it.question.id == questionId) it.copy(points = points) else it })
        _state.update { it.copy(result = UiState.Content(updated)) }
    }

    fun addOption(questionId: String) = updateQuestionDraft(questionId) { question ->
        val nextId = ('a' + question.options.size).toString()
        question.copy(options = question.options + QuizOption(nextId, ""))
    }

    fun removeOption(questionId: String, optionId: String) = updateQuestionDraft(questionId) { question ->
        if (question.options.size <= 2) return@updateQuestionDraft question
        val remaining = question.options.filterNot { it.id == optionId }
        val correctAnswer = if (question.correctAnswer == optionId) remaining.first().id else question.correctAnswer
        question.copy(options = remaining, correctAnswer = correctAnswer)
    }

    /** Persists whatever is currently in the local draft for [questionId] — same "Save edits" shape TC-07's question editor already uses. */
    fun saveQuestionEdit(questionId: String) {
        val quiz = currentQuiz() ?: return
        if (_state.value.savingQuestionId != null) return
        _state.update { it.copy(savingQuestionId = questionId) }
        viewModelScope.launch {
            val result = teacherRepository.saveQuizQuestions(quizId, quiz.questions)
            _state.update {
                if (result is AppResult.Success) it.copy(result = UiState.Content(result.data), savingQuestionId = null, expandedQuestionId = questionId)
                else it.copy(savingQuestionId = null)
            }
        }
    }

    fun deleteQuestion(questionId: String) {
        val quiz = currentQuiz() ?: return
        persistQuestions(quiz.questions.filterNot { it.question.id == questionId })
    }

    fun duplicateQuestion(questionId: String) {
        val quiz = currentQuiz() ?: return
        val index = quiz.questions.indexOfFirst { it.question.id == questionId }
        if (index == -1) return
        val original = quiz.questions[index]
        val copy = original.copy(question = original.question.copy(id = "${original.question.id}-copy${System.currentTimeMillis()}"))
        val updated = quiz.questions.toMutableList().apply { add(index + 1, copy) }
        persistQuestions(updated)
    }

    /** Reflects the new order immediately (optimistic), then persists — same shape TC-04's drag reorder already uses. Question ids are never regenerated, only reordered. */
    fun reorderQuestions(orderedQuestionIds: List<String>) {
        val quiz = currentQuiz() ?: return
        val byId = quiz.questions.associateBy { it.question.id }
        val reordered = orderedQuestionIds.mapNotNull { byId[it] }
        _state.update { it.copy(result = UiState.Content(quiz.copy(questions = reordered))) }
        viewModelScope.launch { teacherRepository.saveQuizQuestions(quizId, reordered) }
    }

    private fun persistQuestions(questions: List<TeacherQuizQuestion>) {
        val quiz = currentQuiz() ?: return
        _state.update { it.copy(result = UiState.Content(quiz.copy(questions = questions))) }
        viewModelScope.launch {
            val result = teacherRepository.saveQuizQuestions(quizId, questions)
            if (result is AppResult.Success) _state.update { it.copy(result = UiState.Content(result.data)) }
        }
    }

    private fun blankQuestion(type: QuestionType): QuizQuestion {
        val id = "q-${System.currentTimeMillis()}"
        return when (type) {
            QuestionType.MultipleChoice -> QuizQuestion(
                id = id, type = type, prompt = "",
                options = listOf(QuizOption("a", ""), QuizOption("b", ""), QuizOption("c", ""), QuizOption("d", "")),
                correctAnswer = "a", explanation = "",
            )
            QuestionType.TrueFalse -> QuizQuestion(
                id = id, type = type, prompt = "",
                options = listOf(QuizOption("true", "صحيح"), QuizOption("false", "خطأ")),
                correctAnswer = "true", explanation = "",
            )
            QuestionType.ShortAnswer, QuestionType.GapFill -> QuizQuestion(id = id, type = type, prompt = "", correctAnswer = "", explanation = "")
        }
    }

    // ── AI bulk import ───────────────────────────────────────────────────────────────────────
    fun openAiImport() {
        _state.update { it.copy(showAiImport = true) }
        if (_state.value.aiCandidates.isEmpty()) loadAiCandidates()
    }

    private fun loadAiCandidates() {
        _state.update { it.copy(isLoadingAiCandidates = true) }
        viewModelScope.launch {
            val result = teacherRepository.generateAiQuizQuestionCandidates(quizId)
            _state.update {
                if (result is AppResult.Success) {
                    it.copy(
                        isLoadingAiCandidates = false,
                        aiCandidates = result.data,
                        aiReviewStatus = result.data.associate { q -> q.question.id to AiReviewStatus.Unreviewed },
                    )
                } else {
                    it.copy(isLoadingAiCandidates = false)
                }
            }
        }
    }

    fun reviewAiCandidate(questionId: String, status: AiReviewStatus) = _state.update {
        it.copy(aiReviewStatus = it.aiReviewStatus + (questionId to status))
    }

    /** Only [AiReviewStatus.Accepted] candidates are copied in — an unreviewed candidate is discarded exactly like a rejected one, same "Rejected → not added" rule extended to "never reviewed → not added". */
    fun closeAiImport() {
        val quiz = currentQuiz()
        val accepted = _state.value.aiCandidates.filter { _state.value.aiReviewStatus[it.question.id] == AiReviewStatus.Accepted }
        _state.update { it.copy(showAiImport = false, aiCandidates = emptyList(), aiReviewStatus = emptyMap()) }
        if (quiz != null && accepted.isNotEmpty()) {
            persistQuestions(quiz.questions + accepted)
        }
    }

    // ── Publish ──────────────────────────────────────────────────────────────────────────────
    fun publish() {
        if (_state.value.isPublishing) return
        if (!_state.value.canPublish) {
            _state.update { it.copy(showPublishBlocked = true) }
            return
        }
        _state.update { it.copy(isPublishing = true) }
        viewModelScope.launch {
            when (val result = teacherRepository.publishQuiz(quizId)) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data), isPublishing = false) }
                is AppResult.Failure -> _state.update { it.copy(isPublishing = false, showPublishBlocked = true) }
            }
        }
    }

    fun dismissPublishBlocked() = _state.update { it.copy(showPublishBlocked = false) }
}
