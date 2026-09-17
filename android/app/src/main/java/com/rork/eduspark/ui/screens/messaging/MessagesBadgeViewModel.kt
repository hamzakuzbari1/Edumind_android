package com.rork.eduspark.ui.screens.messaging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch

/**
 * Drives the Messages TopBar badge on both the Student and Teacher root shells — the same
 * canonical [MessagingRepository.threads] X-01 itself reads, never a separately counted
 * number. A Parent session (no messaging surface yet) always reads 0.
 */
class MessagesBadgeViewModel(
    private val authRepository: AuthRepository,
    private val messagingRepository: MessagingRepository,
) : ViewModel() {

    private val _unreadCount = MutableStateFlow(0)
    val unreadCount: StateFlow<Int> = _unreadCount.asStateFlow()

    init {
        viewModelScope.launch { messagingRepository.getThreads() }
        viewModelScope.launch {
            combine(authRepository.session, messagingRepository.threads) { session, threads ->
                val viewerId = session?.messagingParticipantIdOrNull() ?: return@combine 0
                threads.filter { it.involves(viewerId) }.sumOf { it.unreadCountFor(viewerId) }
            }.collect { count -> _unreadCount.value = count }
        }
    }
}
