package com.rork.eduspark.ui.screens.parent

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.MessageThread
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
import com.rork.eduspark.data.repository.ParentRepository
import com.rork.eduspark.data.repository.parentMessagingTeacherIdsByStudent
import com.rork.eduspark.ui.screens.messaging.messagingParticipantIdOrNull
import com.rork.eduspark.ui.screens.messaging.messagingRoleOrNull
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ParentMessagesData(
    val linkedStudents: List<ParentLinkedStudent>,
    val threads: List<MessageThread>,
    val viewerId: String,
)

data class ParentMessagesUiState(
    val result: UiState<ParentMessagesData> = UiState.Loading,
    val isOnline: Boolean = true,
    val searchQuery: String = "",
)

sealed interface ParentMessagesEvent {
    data class OpenThread(val threadId: String) : ParentMessagesEvent
}

class ParentMessagesViewModel(
    private val authRepository: AuthRepository,
    private val parentRepository: ParentRepository,
    private val messagingRepository: MessagingRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ParentMessagesUiState())
    val state: StateFlow<ParentMessagesUiState> = _state.asStateFlow()

    private val _events = Channel<ParentMessagesEvent>(Channel.BUFFERED)
    val events: Flow<ParentMessagesEvent> = _events.receiveAsFlow()

    private var loadJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    fun updateSearchQuery(query: String) = _state.update { it.copy(searchQuery = query) }

    fun onThreadTapped(threadId: String) {
        viewModelScope.launch { _events.send(ParentMessagesEvent.OpenThread(threadId)) }
    }

    private fun load() {
        loadJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        loadJob = viewModelScope.launch {
            combine(authRepository.session, parentRepository.linkedStudents, messagingRepository.threads) { session, linkedStudents, threads ->
                val viewerId = session?.messagingParticipantIdOrNull()
                val viewerRole = session?.messagingRoleOrNull()
                ParentMessagesBoundary(viewerId, viewerRole, linkedStudents, threads)
            }.collect { boundary ->
                val viewerId = boundary.viewerId
                val data = if (viewerId == null || boundary.viewerRole != MessageParticipantRole.Parent) {
                    null
                } else {
                    val allowedTeacherIdsByStudent =
                        parentRepository.parentMessagingTeacherIdsByStudent(boundary.linkedStudents)
                    ParentMessagesData(
                        linkedStudents = boundary.linkedStudents,
                        threads = allowedParentThreads(
                            viewerId = viewerId,
                            allowedTeacherIdsByStudent = allowedTeacherIdsByStudent,
                            threads = boundary.threads,
                        ),
                        viewerId = viewerId,
                    )
                }
                _state.update {
                    it.copy(result = data?.let { messagesData -> UiState.Content(messagesData) } ?: UiState.Failure(AppError.NotFound))
                }
            }
        }
    }

    private fun allowedParentThreads(
        viewerId: String,
        allowedTeacherIdsByStudent: Map<String, Set<String>>,
        threads: List<MessageThread>,
    ): List<MessageThread> {
        if (allowedTeacherIdsByStudent.isEmpty()) return emptyList()

        return threads
            .filter { thread ->
                val relatedStudentId = thread.studentParticipant.relatedStudentId
                thread.involves(viewerId) &&
                    thread.studentParticipant.id == viewerId &&
                    thread.studentParticipant.role == MessageParticipantRole.Parent &&
                    relatedStudentId != null &&
                    thread.teacherParticipant.id in allowedTeacherIdsByStudent[relatedStudentId].orEmpty()
            }
            .sortedByDescending { it.lastMessage?.sentAtMillis ?: 0L }
    }
}

private data class ParentMessagesBoundary(
    val viewerId: String?,
    val viewerRole: MessageParticipantRole?,
    val linkedStudents: List<ParentLinkedStudent>,
    val threads: List<MessageThread>,
)
