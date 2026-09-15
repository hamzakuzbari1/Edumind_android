package com.rork.eduspark.ui.screens.messaging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
import com.rork.eduspark.data.repository.ParentRepository
import com.rork.eduspark.data.repository.parentMessagingTeacherIdsByStudent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch

/**
 * Drives the Messages TopBar badge from the same canonical [MessagingRepository.threads]
 * X-01 itself reads, never a separately counted number. Parent counts are additionally
 * scoped to linked students so the badge matches the Parent tab's permission boundary.
 */
class MessagesBadgeViewModel(
    private val authRepository: AuthRepository,
    private val messagingRepository: MessagingRepository,
    private val parentRepository: ParentRepository,
) : ViewModel() {

    private val _unreadCount = MutableStateFlow(0)
    val unreadCount: StateFlow<Int> = _unreadCount.asStateFlow()

    init {
        viewModelScope.launch {
            combine(authRepository.session, messagingRepository.threads, parentRepository.linkedStudents) { session, threads, linkedStudents ->
                val viewerId = session?.messagingParticipantIdOrNull() ?: return@combine 0
                val viewerRole = session.messagingRoleOrNull()
                val visibleThreads = if (viewerRole == MessageParticipantRole.Parent) {
                    val allowedTeacherIdsByStudent =
                        parentRepository.parentMessagingTeacherIdsByStudent(linkedStudents)
                    threads.filter { thread ->
                        val relatedStudentId = thread.studentParticipant.relatedStudentId
                        thread.involves(viewerId) &&
                            thread.studentParticipant.role == MessageParticipantRole.Parent &&
                            thread.studentParticipant.id == viewerId &&
                            relatedStudentId != null &&
                            thread.teacherParticipant.id in allowedTeacherIdsByStudent[relatedStudentId].orEmpty()
                    }
                } else {
                    threads.filter { it.involves(viewerId) }
                }
                visibleThreads.sumOf { it.unreadCountFor(viewerId) }
            }.collect { count -> _unreadCount.value = count }
        }
    }
}
