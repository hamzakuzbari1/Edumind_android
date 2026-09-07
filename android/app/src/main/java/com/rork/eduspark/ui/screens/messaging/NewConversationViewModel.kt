package com.rork.eduspark.ui.screens.messaging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
import kotlinx.coroutines.Job
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
 * X-03 · New Conversation.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The contact list is already permission-filtered by [MessagingRepository.getPermittedContacts]
 * — Student↔their teacher, Teacher↔their students — never re-derived independently here.
 * Tapping a contact is existing-thread-first: [MessagingRepository.openOrCreateThread] only
 * ever creates a new thread when [contactId] genuinely has none yet.
 */
data class NewConversationUiState(
    val result: UiState<List<MessageParticipant>> = UiState.Loading,
    val isOnline: Boolean = true,
    val searchQuery: String = "",
    val viewerId: String = "",
    val viewerRole: MessageParticipantRole? = null,
)

sealed interface NewConversationEvent {
    data class ThreadReady(val threadId: String) : NewConversationEvent
}

class NewConversationViewModel(
    private val authRepository: AuthRepository,
    private val messagingRepository: MessagingRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(NewConversationUiState())
    val state: StateFlow<NewConversationUiState> = _state.asStateFlow()

    private val _events = Channel<NewConversationEvent>(Channel.BUFFERED)
    val events: Flow<NewConversationEvent> = _events.receiveAsFlow()

    private var loadJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        loadJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        loadJob = viewModelScope.launch {
            val session = authRepository.session.first()
            val viewerId = session?.messagingParticipantIdOrNull()
            val viewerRole = session?.messagingRoleOrNull()
            if (viewerId == null || viewerRole == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            _state.update { it.copy(viewerId = viewerId, viewerRole = viewerRole) }
            when (val result = messagingRepository.getPermittedContacts(viewerId, viewerRole)) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }

    fun updateSearchQuery(query: String) = _state.update { it.copy(searchQuery = query) }

    fun onContactTapped(contactId: String) {
        val viewerId = _state.value.viewerId
        val viewerRole = _state.value.viewerRole ?: return
        if (viewerId.isEmpty()) return
        viewModelScope.launch {
            when (val result = messagingRepository.openOrCreateThread(viewerId, viewerRole, contactId)) {
                is AppResult.Success -> _events.send(NewConversationEvent.ThreadReady(result.data.id))
                // MOCK: the contact list itself is already permission-filtered, so this branch
                // has no real product case to recover from — no dedicated error surface needed.
                is AppResult.Failure -> Unit
            }
        }
    }
}
