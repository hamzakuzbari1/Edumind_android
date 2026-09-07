package com.rork.eduspark.ui.screens.auth

import androidx.annotation.StringRes
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.repository.AuthRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-11 · Reset Password — reached by deep link.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [email] is context, not a credential: when the deep link (or the in-app hand-off from
 * A-10) carries it, the screen can honestly say *whose* account it is resetting, per the
 * PDF ("New password — for reem@mail.com"). When it doesn't — a bare external link with only
 * a token — the screen falls back to generic copy rather than fabricating an address.
 *
 * A blank [token] is treated as already-expired at construction time, so an app opened
 * straight at this screen with no usable token lands on the non-dead-end expired state
 * immediately instead of a form that can only fail.
 */
sealed interface ResetPasswordPhase {
    data object Input : ResetPasswordPhase
    data object Submitting : ResetPasswordPhase
    data object Success : ResetPasswordPhase
    data object ExpiredLink : ResetPasswordPhase
}

sealed interface ResetPasswordMessage {
    data object Offline : ResetPasswordMessage
    data object ServerProblem : ResetPasswordMessage
    data object Unknown : ResetPasswordMessage
}

data class ResetPasswordUiState(
    val email: String,
    val newPassword: String = "",
    val confirmPassword: String = "",
    @param:StringRes val passwordError: Int? = null,
    @param:StringRes val confirmError: Int? = null,
    val phase: ResetPasswordPhase = ResetPasswordPhase.Input,
    val message: ResetPasswordMessage? = null,
    /** Set once "Send a new link" has actually fired, so the expired state doesn't dead-end. */
    val linkResent: Boolean = false,
    val isOnline: Boolean = true,
) {
    val canSubmit: Boolean get() = phase == ResetPasswordPhase.Input
    val emailKnown: Boolean get() = email.isNotBlank()
}

/** [Completed] routes to Login — resetting a password never returns a session (Source Audit §3). */
sealed interface ResetPasswordEvent {
    data object Completed : ResetPasswordEvent
}

class ResetPasswordViewModel(
    private val token: String,
    email: String,
    private val authRepository: AuthRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(
        ResetPasswordUiState(
            email = email,
            phase = if (token.isBlank()) ResetPasswordPhase.ExpiredLink else ResetPasswordPhase.Input,
        )
    )
    val state: StateFlow<ResetPasswordUiState> = _state.asStateFlow()

    private val _events = Channel<ResetPasswordEvent>(Channel.BUFFERED)
    val events: Flow<ResetPasswordEvent> = _events.receiveAsFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online ->
                _state.update { it.copy(isOnline = online) }
            }
        }
    }

    fun onNewPasswordChange(value: String) {
        _state.update { it.copy(newPassword = value, passwordError = null, message = null) }
    }

    fun onConfirmPasswordChange(value: String) {
        _state.update { it.copy(confirmPassword = value, confirmError = null, message = null) }
    }

    fun submit() {
        val current = _state.value
        if (!current.canSubmit) return

        val passwordError = newPasswordErrorOf(current.newPassword)
        val confirmError = passwordConfirmationErrorOf(current.newPassword, current.confirmPassword)
        if (passwordError != null || confirmError != null) {
            _state.update { it.copy(passwordError = passwordError, confirmError = confirmError) }
            return
        }

        _state.update { it.copy(phase = ResetPasswordPhase.Submitting, message = null) }

        viewModelScope.launch {
            when (val result = authRepository.resetPassword(token, current.newPassword)) {
                is AppResult.Success -> {
                    _state.update { it.copy(phase = ResetPasswordPhase.Success) }
                    delay(SUCCESS_HOLD_MS)
                    _events.send(ResetPasswordEvent.Completed)
                }

                is AppResult.Failure -> {
                    val error = result.error
                    if (error is AppError.Domain && error.code == "expired_link") {
                        _state.update { it.copy(phase = ResetPasswordPhase.ExpiredLink) }
                    } else {
                        _state.update {
                            it.copy(phase = ResetPasswordPhase.Input, message = messageFor(error))
                        }
                    }
                }
            }
        }
    }

    /**
     * The expired-link escape hatch when the address is known. When it isn't, the screen
     * routes to A-10 instead of calling this — see [ResetPasswordUiState.emailKnown].
     */
    fun requestNewLink() {
        val email = _state.value.email
        if (email.isBlank()) return
        viewModelScope.launch {
            authRepository.requestPasswordReset(email)
            _state.update { it.copy(linkResent = true) }
        }
    }

    private fun messageFor(error: AppError): ResetPasswordMessage = when (error) {
        AppError.Offline, AppError.Network -> ResetPasswordMessage.Offline
        AppError.Server -> ResetPasswordMessage.ServerProblem
        else -> ResetPasswordMessage.Unknown
    }

    private companion object {
        const val SUCCESS_HOLD_MS = 900L
    }
}
