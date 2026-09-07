package com.rork.eduspark.ui.screens.auth

import androidx.annotation.StringRes
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.repository.AuthRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-10 · Forgot Password
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Two phases, not six states like A-08/A-09: [ForgotPasswordPhase.Input] is the email form,
 * [ForgotPasswordPhase.Sent] is the confirmation. The confirmation deliberately never
 * confirms an account exists for the address — Source Audit-consistent: the backend does not
 * expose that, and this client does not invent the distinction either.
 */
sealed interface ForgotPasswordPhase {
    data object Input : ForgotPasswordPhase
    data object Sent : ForgotPasswordPhase
}

/** Reuses the same failure vocabulary as A-04/A-08 rather than inventing a fourth. */
sealed interface ForgotPasswordMessage {
    data object Offline : ForgotPasswordMessage
    data object ServerProblem : ForgotPasswordMessage
    data object Unknown : ForgotPasswordMessage
}

data class ForgotPasswordUiState(
    val email: String = "",
    @param:StringRes val emailError: Int? = null,
    val phase: ForgotPasswordPhase = ForgotPasswordPhase.Input,
    val isSubmitting: Boolean = false,
    val message: ForgotPasswordMessage? = null,
    val resendCooldownSeconds: Int = 0,
    val isOnline: Boolean = true,
) {
    val canSubmit: Boolean get() = !isSubmitting
    val canResend: Boolean get() = !isSubmitting && resendCooldownSeconds == 0
}

class ForgotPasswordViewModel(
    private val authRepository: AuthRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ForgotPasswordUiState())
    val state: StateFlow<ForgotPasswordUiState> = _state.asStateFlow()

    private var cooldownJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online ->
                _state.update { it.copy(isOnline = online) }
            }
        }
    }

    fun onEmailChange(value: String) {
        _state.update { it.copy(email = value, emailError = null, message = null) }
    }

    fun submit() {
        val current = _state.value
        if (!current.canSubmit) return

        val emailError = emailErrorOf(current.email)
        if (emailError != null) {
            _state.update { it.copy(emailError = emailError, message = null) }
            return
        }

        _state.update { it.copy(isSubmitting = true, message = null) }

        viewModelScope.launch {
            when (val result = authRepository.requestPasswordReset(current.email.trim())) {
                is AppResult.Success -> {
                    _state.update { it.copy(isSubmitting = false, phase = ForgotPasswordPhase.Sent) }
                    startCooldown()
                }

                is AppResult.Failure -> _state.update {
                    it.copy(isSubmitting = false, message = messageFor(result.error))
                }
            }
        }
    }

    fun resend() {
        val current = _state.value
        if (!current.canResend) return

        _state.update { it.copy(isSubmitting = true) }
        viewModelScope.launch {
            authRepository.requestPasswordReset(current.email.trim())
            _state.update { it.copy(isSubmitting = false) }
            startCooldown()
        }
    }

    /** "Wrong address? Try another email" — back to the form, the typed address kept. */
    fun editEmail() {
        _state.update { it.copy(phase = ForgotPasswordPhase.Input, message = null) }
    }

    private fun startCooldown() {
        cooldownJob?.cancel()
        cooldownJob = viewModelScope.launch {
            _state.update { it.copy(resendCooldownSeconds = RESEND_COOLDOWN_SECONDS) }
            while (_state.value.resendCooldownSeconds > 0) {
                delay(1_000)
                _state.update {
                    it.copy(resendCooldownSeconds = (it.resendCooldownSeconds - 1).coerceAtLeast(0))
                }
            }
        }
    }

    private fun messageFor(error: AppError): ForgotPasswordMessage = when (error) {
        AppError.Offline, AppError.Network -> ForgotPasswordMessage.Offline
        AppError.Server -> ForgotPasswordMessage.ServerProblem
        else -> ForgotPasswordMessage.Unknown
    }

    private companion object {
        const val RESEND_COOLDOWN_SECONDS = 60
    }
}
