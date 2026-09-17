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

    fun openCourseTeacherThread(courseId: String) {
        viewModelScope.launch {
            authRepository.session.first() ?: return@launch
            val thread = messagingRepository.openCourseTeacherThread(courseId)
            val threadId = (thread as? AppResult.Success)?.data?.id ?: return@launch
            _events.send(TeacherContactEvent.OpenThread(threadId))
        }
    }
}
