package com.rork.eduspark.ui.screens.messaging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.launch

sealed interface TeacherContactEvent {
    data class OpenThread(val threadId: String) : TeacherContactEvent
}

class TeacherContactViewModel(
    private val authRepository: AuthRepository,
    private val messagingRepository: MessagingRepository,
) : ViewModel() {

    private val _events = Channel<TeacherContactEvent>(Channel.BUFFERED)
    val events: Flow<TeacherContactEvent> = _events.receiveAsFlow()

    fun openCourseTeacherThread() {
        viewModelScope.launch {
            val session = authRepository.session.first() ?: return@launch
            val viewerId = session.messagingParticipantIdOrNull() ?: return@launch
            val viewerRole = session.messagingRoleOrNull() ?: return@launch
            val contacts = messagingRepository.getPermittedContacts(viewerId, viewerRole)
            val teacher = (contacts as? AppResult.Success)
                ?.data
                ?.firstOrNull { it.role == MessageParticipantRole.Teacher }
                ?: return@launch
            val thread = messagingRepository.openOrCreateThread(viewerId, viewerRole, teacher.id)
            val threadId = (thread as? AppResult.Success)?.data?.id ?: return@launch
            _events.send(TeacherContactEvent.OpenThread(threadId))
        }
    }
}
