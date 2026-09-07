package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.model.SubmissionAttachment
import com.rork.eduspark.data.model.SubmissionDraft
import com.rork.eduspark.data.model.SubmissionType
import com.rork.eduspark.data.repository.ProjectRepository
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
 * PJ-05 · Submission Composer.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * No CameraX, no gallery picker, no file provider, no upload networking —
 * [addMockAttachment] just appends a deterministic [SubmissionAttachment] record, the same
 * "honest MOCK boundary" convention ST-14's capture flow already established. Draft
 * persistence goes through [ProjectRepository.saveDraft]/[getDraft] — local, session-scoped,
 * survives leaving and returning to this screen. [submit] is only ever meaningful once
 * [SubmissionDraft.hasContent], and [ProjectRepository.submitTask] is itself idempotent, so a
 * retry after [ComposerPhase.Failed] can never create a duplicate submission.
 */
data class SubmissionComposerScreenData(
    val task: ProjectTask,
    val draft: SubmissionDraft,
)

enum class ComposerPhase { Idle, SavingDraft, Submitting, Failed }

sealed interface SubmissionComposerEvent {
    data object Submitted : SubmissionComposerEvent
}

data class SubmissionComposerUiState(
    val result: UiState<SubmissionComposerScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val phase: ComposerPhase = ComposerPhase.Idle,
    val showValidationError: Boolean = false,
)

class SubmissionComposerViewModel(
    private val projectId: String,
    private val taskId: String,
    private val projectRepository: ProjectRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(SubmissionComposerUiState())
    val state: StateFlow<SubmissionComposerUiState> = _state.asStateFlow()

    private val _events = Channel<SubmissionComposerEvent>(Channel.BUFFERED)
    val events: Flow<SubmissionComposerEvent> = _events.receiveAsFlow()

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
            val taskResult = projectRepository.getTask(projectId, taskId)
            val draftResult = projectRepository.getDraft(projectId, taskId)
            if (taskResult is AppResult.Success && draftResult is AppResult.Success) {
                _state.update {
                    it.copy(result = UiState.Content(SubmissionComposerScreenData(taskResult.data, draftResult.data)))
                }
            } else {
                val error = (taskResult as? AppResult.Failure)?.error
                    ?: (draftResult as? AppResult.Failure)?.error
                    ?: AppError.Unknown
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }

    fun updateReflection(text: String) = updateDraft { it.copy(writtenReflection = text) }

    fun updateLink(text: String) = updateDraft { it.copy(link = text) }

    fun addMockAttachment(type: SubmissionType) {
        updateDraft { draft ->
            val index = draft.attachments.count { it.type == type } + 1
            val label = when (type) {
                SubmissionType.Photo -> "IMG_%03d.jpg".format(index)
                SubmissionType.File -> "document_$index.pdf"
                else -> return@updateDraft draft
            }
            draft.copy(attachments = draft.attachments + SubmissionAttachment(id = "${taskId}-att-${type.name}-$index", type = type, label = label))
        }
    }

    fun removeAttachment(attachmentId: String) = updateDraft { draft ->
        draft.copy(attachments = draft.attachments.filterNot { it.id == attachmentId })
    }

    private fun updateDraft(transform: (SubmissionDraft) -> SubmissionDraft) {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        _state.update {
            it.copy(result = UiState.Content(data.copy(draft = transform(data.draft))), showValidationError = false)
        }
    }

    fun saveDraft() {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        if (_state.value.phase == ComposerPhase.SavingDraft || _state.value.phase == ComposerPhase.Submitting) return
        _state.update { it.copy(phase = ComposerPhase.SavingDraft) }
        viewModelScope.launch {
            projectRepository.saveDraft(data.draft)
            _state.update { it.copy(phase = ComposerPhase.Idle) }
        }
    }

    fun submit() {
        val data = (_state.value.result as? UiState.Content)?.data ?: return
        if (_state.value.phase == ComposerPhase.Submitting) return
        if (!data.draft.hasContent) {
            _state.update { it.copy(showValidationError = true) }
            return
        }
        _state.update { it.copy(phase = ComposerPhase.Submitting, showValidationError = false) }
        viewModelScope.launch {
            projectRepository.saveDraft(data.draft)
            when (projectRepository.submitTask(projectId, taskId)) {
                is AppResult.Success -> {
                    _state.update { it.copy(phase = ComposerPhase.Idle) }
                    _events.send(SubmissionComposerEvent.Submitted)
                }
                is AppResult.Failure -> _state.update { it.copy(phase = ComposerPhase.Failed) }
            }
        }
    }
}
