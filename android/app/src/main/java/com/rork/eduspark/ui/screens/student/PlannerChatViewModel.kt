package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.PlannerChatMessage
import com.rork.eduspark.data.model.PlannerChatSender
import com.rork.eduspark.data.model.ProposalStatus
import com.rork.eduspark.data.repository.PlannerRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-11 · Planner AI Chat.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Not graph-scoped with [PlannerViewModel] — unlike ST-04/05's tutor pair, ST-10 and ST-11
 * don't need a shared conversation, only shared *data*, and [PlannerRepository.weekPlan]
 * already is that. Accepting a proposal here writes through the repository; ST-10 picks the
 * change up on its own via the flow it's already collecting.
 */
data class PlannerChatUiState(
    val messages: List<PlannerChatMessage> = emptyList(),
    val isSending: Boolean = false,
    val error: AppError? = null,
    val isOnline: Boolean = true,
)

class PlannerChatViewModel(
    private val plannerRepository: PlannerRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(PlannerChatUiState())
    val state: StateFlow<PlannerChatUiState> = _state.asStateFlow()

    private var messageCounter = 0

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
    }

    fun sendMessage(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty() || _state.value.isSending) return
        appendStudentMessage(trimmed)
        _state.update { it.copy(isSending = true, error = null) }
        viewModelScope.launch {
            when (val result = plannerRepository.sendPlannerChatMessage(trimmed)) {
                is AppResult.Success -> {
                    _state.update { it.copy(isSending = false, messages = it.messages + result.data) }
                }
                is AppResult.Failure -> _state.update { it.copy(isSending = false, error = result.error) }
            }
        }
    }

    /**
     * ST-14 entry point from chat — records the student's stated intent as a plain message,
     * with no assistant reply and no repository call. This is *not* [sendMessage]: it never
     * reaches [PlannerRepository.sendPlannerChatMessage], so nothing here parses it into a
     * proposal or fabricates an OCR result — the actual capture/extraction only happens once
     * ST-14 itself is opened.
     */
    fun announceExamCaptureIntent(text: String) = appendStudentMessage(text)

    fun accept(messageId: String, proposalId: String) {
        viewModelScope.launch {
            when (plannerRepository.acceptProposal(proposalId)) {
                is AppResult.Success -> applyProposalStatus(messageId, ProposalStatus.Accepted)
                is AppResult.Failure -> Unit // the diff card simply stays pending; student can retry the tap.
            }
        }
    }

    fun reject(messageId: String, proposalId: String) {
        viewModelScope.launch {
            plannerRepository.rejectProposal(proposalId)
            applyProposalStatus(messageId, ProposalStatus.Rejected)
        }
    }

    private fun applyProposalStatus(messageId: String, status: ProposalStatus) {
        _state.update { state ->
            state.copy(
                messages = state.messages.map { message ->
                    if (message.id == messageId) {
                        message.copy(proposedChange = message.proposedChange?.copy(status = status))
                    } else {
                        message
                    }
                },
            )
        }
    }

    private fun appendStudentMessage(text: String) {
        messageCounter += 1
        val message = PlannerChatMessage(
            id = "student-msg-$messageCounter",
            sender = PlannerChatSender.Student,
            text = text,
        )
        _state.update { it.copy(messages = it.messages + message) }
    }
}
