package com.rork.eduspark.ui.screens.teacher

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.TeacherCriterionReview
import com.rork.eduspark.data.model.TeacherProjectSubmission
import com.rork.eduspark.data.repository.TeacherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-18 · Review Detail — submission, rubric, AI pre-review, teacher finalization.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Opening a submission (via [load]) is what moves a still-[com.rork.eduspark.data.model.ProjectReviewStatus.AwaitingReview]
 * row to [com.rork.eduspark.data.model.ProjectReviewStatus.InReview] — [TeacherRepository.getReviewSubmission]'s
 * own side effect, not something this ViewModel decides separately. Every criterion score this
 * screen shows the teacher editing is [TeacherCriterionReview.teacherScore] — [aiSuggestedScore]
 * never changes; [com.rork.eduspark.data.model.TeacherProjectSubmission.finalScore] is read
 * straight off the loaded submission, always derived server-side, never recomputed here.
 */
data class TeacherReviewDetailUiState(
    val result: UiState<TeacherProjectSubmission> = UiState.Loading,
    val isOnline: Boolean = true,

    val feedbackDraft: String = "",
    val privateCommentDraft: String = "",
    val hasUnsavedFeedback: Boolean = false,
    val isSavingFeedback: Boolean = false,

    val editingCriterionId: String? = null,
    val scoreDraftText: String = "",
    val scoreDraftError: Boolean = false,

    val showFinalizeConfirm: Boolean = false,
    val isFinalizing: Boolean = false,
    val finalizeError: Boolean = false,
)

class TeacherReviewDetailViewModel(
    private val submissionId: String,
    private val teacherRepository: TeacherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TeacherReviewDetailUiState())
    val state: StateFlow<TeacherReviewDetailUiState> = _state.asStateFlow()

    private var draftsSeeded = false

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
            when (val result = teacherRepository.getReviewSubmission(submissionId)) {
                is AppResult.Success -> {
                    val submission = result.data
                    _state.update { current ->
                        val withDrafts = if (!draftsSeeded) {
                            draftsSeeded = true
                            current.copy(feedbackDraft = submission.teacherFeedback, privateCommentDraft = submission.teacherPrivateComment)
                        } else current
                        withDrafts.copy(result = UiState.Content(submission))
                    }
                }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    private fun currentSubmission(): TeacherProjectSubmission? = (_state.value.result as? UiState.Content)?.data

    // ── Criterion scoring ────────────────────────────────────────────────────────────────────

    fun openScoreEditor(criterion: TeacherCriterionReview) = _state.update {
        it.copy(editingCriterionId = criterion.criterionId, scoreDraftText = (criterion.teacherScore ?: criterion.aiSuggestedScore).toString(), scoreDraftError = false)
    }

    fun updateScoreDraftText(value: String) = _state.update { it.copy(scoreDraftText = value, scoreDraftError = false) }

    fun dismissScoreEditor() = _state.update { it.copy(editingCriterionId = null, scoreDraftError = false) }

    fun confirmScore() {
        val draft = _state.value
        val criterionId = draft.editingCriterionId ?: return
        val submission = currentSubmission() ?: return
        val criterion = submission.criteria.firstOrNull { it.criterionId == criterionId } ?: return
        val score = draft.scoreDraftText.toIntOrNull()
        if (score == null || score < 0 || score > criterion.maxScore) {
            _state.update { it.copy(scoreDraftError = true) }
            return
        }
        viewModelScope.launch {
            teacherRepository.saveCriterionOverride(submissionId, criterionId, score)
            _state.update { it.copy(editingCriterionId = null) }
            load()
        }
    }

    /** "Confirm as-is" — accepts the AI suggestion for this one criterion without opening the score editor. */
    fun acceptAiSuggestion(criterion: TeacherCriterionReview) {
        viewModelScope.launch {
            teacherRepository.saveCriterionOverride(submissionId, criterion.criterionId, criterion.aiSuggestedScore)
            load()
        }
    }

    // ── Feedback ─────────────────────────────────────────────────────────────────────────────

    fun updateFeedbackDraft(value: String) = _state.update { it.copy(feedbackDraft = value, hasUnsavedFeedback = true) }
    fun updatePrivateCommentDraft(value: String) = _state.update { it.copy(privateCommentDraft = value, hasUnsavedFeedback = true) }

    /** Pre-fills the feedback draft from the AI's suggested wording — still an explicit Save away from becoming the teacher's own final feedback, and immediately editable, never locked as AI text. */
    fun useAiSuggestedFeedback() {
        val submission = currentSubmission() ?: return
        _state.update { it.copy(feedbackDraft = submission.aiSuggestedFeedback, hasUnsavedFeedback = true) }
    }

    fun saveFeedback() {
        val draft = _state.value
        _state.update { it.copy(isSavingFeedback = true) }
        viewModelScope.launch {
            teacherRepository.saveReviewFeedback(submissionId, draft.feedbackDraft, draft.privateCommentDraft)
            _state.update { it.copy(hasUnsavedFeedback = false, isSavingFeedback = false) }
            load()
        }
    }

    // ── Finalize ─────────────────────────────────────────────────────────────────────────────

    fun requestFinalize() = _state.update { it.copy(showFinalizeConfirm = true) }
    fun dismissFinalizeConfirm() = _state.update { it.copy(showFinalizeConfirm = false) }

    fun confirmFinalize() {
        _state.update { it.copy(showFinalizeConfirm = false, isFinalizing = true, finalizeError = false) }
        viewModelScope.launch {
            when (teacherRepository.finalizeReview(submissionId)) {
                is AppResult.Success -> {
                    _state.update { it.copy(isFinalizing = false) }
                    load()
                }
                is AppResult.Failure -> _state.update { it.copy(isFinalizing = false, finalizeError = true) }
            }
        }
    }
}
