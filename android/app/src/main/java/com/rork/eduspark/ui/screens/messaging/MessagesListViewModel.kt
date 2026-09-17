package com.rork.eduspark.ui.screens.messaging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.MessageThread
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
 * X-01 · Messages List.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reads the SAME canonical [MessagingRepository.threads] hot flow X-02/X-03 and the TopBar
 * badge ([MessagesBadgeViewModel]) all read — never a separate fixture. Filtering to "my own"
 * threads and sorting by recency happen once here, the content composable does search
 * filtering only, the same "repository row set filtered in the composable" shape
 * [com.rork.eduspark.ui.screens.teacher.TeacherStudentsScreen] already established.
 */
enum class MessagesListCategory { Students, Parents }

data class MessagesListUiState(
    val result: UiState<List<MessageThread>> = UiState.Loading,
    val isOnline: Boolean = true,
    val searchQuery: String = "",
    val viewerId: String = "",
    val viewerRole: MessageParticipantRole? = null,
    val category: MessagesListCategory = MessagesListCategory.Students,
)

sealed interface MessagesListEvent {
    data class OpenThread(val threadId: String) : MessagesListEvent
    data object OpenNewConversation : MessagesListEvent
}

class MessagesListViewModel(
    private val authRepository: AuthRepository,
    private val messagingRepository: MessagingRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(MessagesListUiState())
    val state: StateFlow<MessagesListUiState> = _state.asStateFlow()

    private val _events = Channel<MessagesListEvent>(Channel.BUFFERED)
    val events: Flow<MessagesListEvent> = _events.receiveAsFlow()

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
            if (viewerId == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            _state.update { it.copy(viewerId = viewerId, viewerRole = viewerRole) }
            messagingRepository.getThreads()
            messagingRepository.threads.collect { all ->
                val mine = all.filter { it.involves(viewerId) }
                    .sortedByDescending { it.lastMessage?.sentAtMillis ?: 0L }
                _state.update { it.copy(result = UiState.Content(mine)) }
            }
        }
    }

    fun updateSearchQuery(query: String) = _state.update { it.copy(searchQuery = query) }

    fun selectCategory(category: MessagesListCategory) = _state.update { it.copy(category = category) }

    fun onThreadTapped(threadId: String) =
        viewModelScope.launch { _events.send(MessagesListEvent.OpenThread(threadId)) }

    fun onNewConversationTapped() =
        viewModelScope.launch { _events.send(MessagesListEvent.OpenNewConversation) }
}
