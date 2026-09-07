package com.rork.eduspark.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.repository.AuthRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
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
 * A-08 · Verify Email — state and the six approved states.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reached from two places, both already wired: A-05/06/07 Register on success, and A-04
 * Login's "Resend link" action on an unverified address. Only the first actually leaves the
 * user signed in — Source Audit §3 confirms the platform does not require verification to
 * log in, so the login path never created a session in the first place. [onVerified] reflects
 * that honestly: it reports whatever role the current session actually holds, or none.
 *
 * The attempts counter and the expiry it leads to are **client-side UX state**, not a
 * backend contract — `verifyEmail` only ever reports valid or invalid. Nothing here invents
 * a server-side attempts field.
 */
sealed interface VerifyEmailPhase {
    data object Idle : VerifyEmailPhase
    data object Verifying : VerifyEmailPhase
    data class Invalid(val attemptsRemaining: Int) : VerifyEmailPhase
    data object Expired : VerifyEmailPhase
    data object Success : VerifyEmailPhase
}

data class VerifyEmailUiState(
    val email: String,
    val code: String = "",
    val phase: VerifyEmailPhase = VerifyEmailPhase.Idle,
    val resendCooldownSeconds: Int = 0,
    val isOnline: Boolean = true,
) {
    val canSubmit: Boolean
        get() = code.length == OTP_LENGTH &&
            phase != VerifyEmailPhase.Verifying &&
            phase != VerifyEmailPhase.Success

    val canResend: Boolean
        get() = resendCooldownSeconds == 0 &&
            phase != VerifyEmailPhase.Verifying &&
            phase != VerifyEmailPhase.Success
}

/** One-shot outcome. [user] is null when this verification never had a session behind it. */
sealed interface VerifyEmailEvent {
    data class Verified(val user: SessionUser?) : VerifyEmailEvent
}

class VerifyEmailViewModel(
    email: String,
    private val authRepository: AuthRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(VerifyEmailUiState(email = email))
    val state: StateFlow<VerifyEmailUiState> = _state.asStateFlow()

    private val _events = Channel<VerifyEmailEvent>(Channel.BUFFERED)
    val events: Flow<VerifyEmailEvent> = _events.receiveAsFlow()

    /** Resets on every fresh code (initial send or resend) — never persisted server-side. */
    private var attemptsRemaining = MAX_ATTEMPTS
    private var cooldownJob: kotlinx.coroutines.Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online ->
                _state.update { it.copy(isOnline = online) }
            }
        }
        // The code arriving at A-08 was already sent by whichever screen navigated here
        // (register success, or login's "resend link"), so the resend control starts cool.
        startCooldown()
    }

    fun onCodeChange(value: String) {
        val current = _state.value
        if (current.phase == VerifyEmailPhase.Verifying || current.phase == VerifyEmailPhase.Success) return
        _state.update { it.copy(code = value, phase = VerifyEmailPhase.Idle) }
    }

    fun submit() {
        val current = _state.value
        if (!current.canSubmit) return

        _state.update { it.copy(phase = VerifyEmailPhase.Verifying) }

        viewModelScope.launch {
            when (val result = authRepository.verifyEmail(current.code)) {
                is AppResult.Success -> {
                    _state.update { it.copy(phase = VerifyEmailPhase.Success) }
                    // Let the success state render for a beat before leaving it — the PDF
                    // treats it as its own screen, not an instant redirect.
                    delay(SUCCESS_HOLD_MS)
                    val user = authRepository.session.first()
                    _events.send(VerifyEmailEvent.Verified(user))
                }

                is AppResult.Failure -> {
                    attemptsRemaining = (attemptsRemaining - 1).coerceAtLeast(0)
                    _state.update {
                        it.copy(
                            code = "",
                            phase = if (attemptsRemaining == 0) {
                                VerifyEmailPhase.Expired
                            } else {
                                VerifyEmailPhase.Invalid(attemptsRemaining)
                            },
                        )
                    }
                }
            }
        }
    }

    /** Also the Expired phase's "send a new code" action — same call, same reset. */
    fun resend() {
        if (!_state.value.canResend) return

        viewModelScope.launch {
            authRepository.resendEmailCode()
            attemptsRemaining = MAX_ATTEMPTS
            _state.update { it.copy(code = "", phase = VerifyEmailPhase.Idle) }
            startCooldown()
        }
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

    private companion object {
        const val MAX_ATTEMPTS = 3
        const val RESEND_COOLDOWN_SECONDS = 60
        const val SUCCESS_HOLD_MS = 900L
    }
}

private const val OTP_LENGTH = 6
