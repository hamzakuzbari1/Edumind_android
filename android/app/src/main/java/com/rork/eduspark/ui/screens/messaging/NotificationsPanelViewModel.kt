package com.rork.eduspark.ui.screens.messaging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.StudentNotification
import com.rork.eduspark.data.model.StudentNotificationType
import com.rork.eduspark.data.repository.NotificationRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class NotificationsPanelUiState(
    val notifications: List<StudentNotification> = emptyList(),
    val unreadCount: Int = 0,
    val isLoading: Boolean = true,
)

sealed interface NotificationsPanelEvent {
    data class OpenThread(val threadId: String) : NotificationsPanelEvent
    data class OpenCourse(val courseId: String) : NotificationsPanelEvent
    data class OpenPurchaseSuccess(val courseId: String) : NotificationsPanelEvent
}

class NotificationsPanelViewModel(
    private val notificationRepository: NotificationRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(NotificationsPanelUiState())
    val state: StateFlow<NotificationsPanelUiState> = _state.asStateFlow()

    private val _events = Channel<NotificationsPanelEvent>(Channel.BUFFERED)
    val events: Flow<NotificationsPanelEvent> = _events.receiveAsFlow()

    init {
        viewModelScope.launch {
            notificationRepository.notifications.collect { notifications ->
                val sorted = notifications.sortedByDescending { it.createdAtMillis }
                _state.update {
                    it.copy(
                        notifications = sorted,
                        unreadCount = sorted.count { notification -> !notification.isRead },
                        isLoading = false,
                    )
                }
            }
        }
    }

    fun markAllRead() {
        viewModelScope.launch { notificationRepository.markAllRead() }
    }

    fun openNotification(notification: StudentNotification) {
        viewModelScope.launch {
            val marked = notificationRepository.markRead(notification.id)
            val resolved = (marked as? AppResult.Success)?.data ?: notification
            when {
                resolved.type == StudentNotificationType.InternalMessage && resolved.threadId != null ->
                    _events.send(NotificationsPanelEvent.OpenThread(resolved.threadId))
                resolved.type == StudentNotificationType.PaymentStatus && resolved.courseId != null ->
                    _events.send(NotificationsPanelEvent.OpenPurchaseSuccess(resolved.courseId))
                resolved.type == StudentNotificationType.LessonUpdate && resolved.courseId != null ->
                    _events.send(NotificationsPanelEvent.OpenCourse(resolved.courseId))
            }
        }
    }
}
