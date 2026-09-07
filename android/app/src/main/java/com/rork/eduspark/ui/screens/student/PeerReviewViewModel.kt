package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.PeerReviewDraft
import com.rork.eduspark.data.model.PeerSubmissionPreview
import com.rork.eduspark.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-07 · Peer Review.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deterministic MOCK — one fixed anonymized assignment ([ProjectRepository.getPeerReviewAssignment]),
 * the same rubric shape PJ-06 uses, no real peer network. [isToneAcceptable] is a small fixed
 * hostile-phrase scan, never a real LLM call — it only blocks language hostile toward the
 * person being reviewed, never ordinary constructive criticism of the work itself.
 * [submit] is guarded to be idempotent client-side too — see
 * [ProjectRepository.submitPeerReview]'s own doc comment for the repository-side guarantee a
 * repeated tap can never create a second review.
 */
data class PeerReviewScreenData(
    val assignment: PeerSubmissionPreview,
    val draft: PeerReviewDraft,
)

enum class PeerReviewPhase { Idle, Submitting, Submitted }

data class PeerReviewUiState(
    val result: UiState<PeerReviewScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val phase: PeerReviewPhase = PeerReviewPhase.Idle,
    val showToneWarning: Boolean = false,
    val showValidationError: Boolean = false,
)

class PeerReviewViewModel(
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(PeerReviewUiState())
    val state: StateFlow<PeerReviewUiState> = _state.asStateFlow()

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
            val assignmentResult = projectRepository.getPeerReviewAssignment()
            if (assignmentResult !is AppResult.Success) {
                _state.update { it.copy(result = UiState.Failure((assignmentResult as AppResult.Failure).error)) }
                return@launch
            }
            val taskId = assignmentResult.data.taskId
            val draft = (projectRepository.getPeerReviewDraft(taskId) as? AppResult.Success)?.data
                ?: PeerReviewDraft(taskId = taskId)
            _state.update { it.copy(result = UiState.Content(PeerReviewScreenData(assignmentResult.data, draft))) }
        }
    }

    fun setScore(criterionId: String, score: Int) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val updated = data.draft.copy(scores = data.draft.scores + (criterionId to score))
        _state.update { it.copy(result = UiState.Content(data.copy(draft = updated)), showValidationError = false) }
        persistDraft(updated)
    }

    fun updateComment(text: String) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val updated = data.draft.copy(comment = text)
        _state.update {
            it.copy(result = UiState.Content(data.copy(draft = updated)), showToneWarning = false, showValidationError = false)
        }
        persistDraft(updated)
    }

    private fun persistDraft(draft: PeerReviewDraft) {
        viewModelScope.launch { projectRepository.savePeerReviewDraft(draft) }
    }

    fun submit() {
        if (_state.value.phase != PeerReviewPhase.Idle) return
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        val draft = data.draft

        val allScored = data.assignment.criteria.all { draft.scores.containsKey(it.id) }
        val commentLongEnough = draft.comment.trim().length >= MIN_COMMENT_LENGTH
        if (!allScored || !commentLongEnough) {
            _state.update { it.copy(showValidationError = true) }
            return
        }
        if (!isToneAcceptable(draft.comment)) {
            _state.update { it.copy(showToneWarning = true) }
            return
        }

        _state.update { it.copy(phase = PeerReviewPhase.Submitting, showValidationError = false, showToneWarning = false) }
        viewModelScope.launch {
            when (val result = projectRepository.submitPeerReview(draft)) {
                is AppResult.Success -> _state.update { it.copy(phase = PeerReviewPhase.Submitted) }
                is AppResult.Failure -> _state.update { it.copy(phase = PeerReviewPhase.Idle) }
            }
        }
    }

    companion object {
        const val MIN_COMMENT_LENGTH = 20

        /**
         * Deterministic MOCK tone check — a small fixed hostile-phrase scan, never a real LLM
         * call. Every phrase here is directed at the PERSON ("you're stupid", "I hate you"),
         * never at the work — a comment like "الأسلاك غير مرتبة" (the wiring is messy) must
         * never be flagged, since that is exactly the constructive criticism PJ-07 exists to
         * collect.
         */
        private val HOSTILE_PHRASES = listOf(
            "غبي", "أحمق", "حقير", "أكرهك", "لا قيمة لك",
            "stupid", "idiot", "moron", "hate you", "worthless",
        )

        fun isToneAcceptable(comment: String): Boolean {
            val normalized = comment.lowercase()
            return HOSTILE_PHRASES.none { normalized.contains(it.lowercase()) }
        }
    }
}
