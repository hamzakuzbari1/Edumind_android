package com.rork.eduspark.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.repository.AuthRepository
import kotlinx.coroutines.Job
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
 * A-09 · Two-Factor Verify — state.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * **Backend reality (Source Audit §3), corrected from the PDF's phone mockup:** the
 * platform's second factor is **email OTP**. There is no SMS channel and TOTP returns 501.
 * The masked destination shown here is therefore a masked *email*, not a phone number — the
 * PDF's visual language (masked destination, distinct security band) is kept, its channel is
 * not.
 *
 * There is no dedicated "resend the 2FA code" endpoint in the verified audit, and this
 * screen does not invent one: it calls the same [AuthRepository.resendEmailCode] seam A-08
 * uses, because both are "re-send the pending email-delivered code" from the client's point
 * of view. `trustDevice` is threaded straight into [AuthRepository.verifyTwoFactor], which
 * already accepts it — nothing new was added to the interface for this screen.
 */
sealed interface TwoFactorPhase {
    data object Idle : TwoFactorPhase
    data object Verifying : TwoFactorPhase
    data class Invalid(val attemptsRemaining: Int) : TwoFactorPhase
    data object Success : TwoFactorPhase
}

data class TwoFactorUiState(
    val email: String,
    val code: String = "",
    val trustDevice: Boolean = false,
    val phase: TwoFactorPhase = TwoFactorPhase.Idle,
    val resendCooldownSeconds: Int = 0,
    /** The initial send counts as 1 of [MAX_RESENDS] — matches the PDF's "Sent 1 of 3". */
    val resendCount: Int = 1,
    val isOnline: Boolean = true,
) {
    /**
     * Once attempts run out, the field stops accepting a submit — nothing here auto-resends
     * on the user's behalf; a fresh code requires the explicit resend action, same principle
     * as offline login never auto-replaying a request.
     */
    val canSubmit: Boolean
        get() = code.length == OTP_LENGTH &&
            phase != TwoFactorPhase.Verifying &&
            phase != TwoFactorPhase.Success &&
            (phase as? TwoFactorPhase.Invalid)?.attemptsRemaining != 0

    val resendCapReached: Boolean get() = resendCount >= MAX_RESENDS

    val canResend: Boolean
        get() = !resendCapReached &&
            resendCooldownSeconds == 0 &&
            phase != TwoFactorPhase.Verifying &&
            phase != TwoFactorPhase.Success
}

sealed interface TwoFactorEvent {
    data class Verified(val user: SessionUser) : TwoFactorEvent
}

class TwoFactorViewModel(
    email: String,
    private val authRepository: AuthRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TwoFactorUiState(email = email))
    val state: StateFlow<TwoFactorUiState> = _state.asStateFlow()

    private val _events = Channel<TwoFactorEvent>(Channel.BUFFERED)
    val events: Flow<TwoFactorEvent> = _events.receiveAsFlow()

    private var attemptsRemaining = MAX_ATTEMPTS
    private var cooldownJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online ->
                _state.update { it.copy(isOnline = online) }
            }
        }
        startCooldown()
    }

    fun onCodeChange(value: String) {
        val current = _state.value
        if (current.phase == TwoFactorPhase.Verifying || current.phase == TwoFactorPhase.Success) return
        _state.update { it.copy(code = value, phase = TwoFactorPhase.Idle) }
    }

    fun onTrustDeviceChange(value: Boolean) {
        _state.update { it.copy(trustDevice = value) }
    }

    fun submit() {
        val current = _state.value
        if (!current.canSubmit) return

        _state.update { it.copy(phase = TwoFactorPhase.Verifying) }

        viewModelScope.launch {
            when (val result = authRepository.verifyTwoFactor(current.code, current.trustDevice)) {
                is AppResult.Success -> {
                    _state.update { it.copy(phase = TwoFactorPhase.Success) }
                    delay(SUCCESS_HOLD_MS)
                    _events.send(TwoFactorEvent.Verified(result.data))
                }

                is AppResult.Failure -> {
                    attemptsRemaining = (attemptsRemaining - 1).coerceAtLeast(0)
                    _state.update {
                        it.copy(code = "", phase = TwoFactorPhase.Invalid(attemptsRemaining))
                    }
                }
            }
        }
    }

    fun resend() {
        if (!_state.value.canResend) return

        viewModelScope.launch {
            authRepository.resendEmailCode()
            attemptsRemaining = MAX_ATTEMPTS
            _state.update {
                it.copy(code = "", phase = TwoFactorPhase.Idle, resendCount = it.resendCount + 1)
            }
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
        const val RESEND_COOLDOWN_SECONDS = 30
        const val SUCCESS_HOLD_MS = 900L
    }
}

private const val OTP_LENGTH = 6

// File-scoped (not in the companion object above) because TwoFactorUiState.resendCapReached
// needs it too, and a private companion member is only visible inside its own class —
// TwoFactorUiState is a separate top-level class, not nested in TwoFactorViewModel.
private const val MAX_RESENDS = 3
