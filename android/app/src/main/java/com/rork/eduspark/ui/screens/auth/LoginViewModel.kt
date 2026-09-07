package com.rork.eduspark.ui.screens.auth

import androidx.annotation.StringRes
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.R
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.SignInOutcome
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-04 · Login — state, validation and the five failure branches.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Everything the screen can say lives in [LoginMessage], and the screen renders exactly one
 * of them in one fixed region. That is the whole reason the layout never jumps between an
 * idle form and a failed attempt.
 *
 * Two fields are deliberately nullable — [LoginMessage.WrongCredentials.attemptsRemaining]
 * and [LoginMessage.AccountLocked.unlockAt]. The approved design shows both ("2 attempts
 * left", "Unlocks 09:56"), but the backend exposes neither today, so they are wired through
 * and passed as null rather than fabricated on the client. The moment the API returns them,
 * one mapping line lights the richer copy up; until then the honest sentence is shown.
 */
sealed interface LoginMessage {

    /** Wrong email/password. [attemptsRemaining] comes from the server when it offers it. */
    data class WrongCredentials(val attemptsRemaining: Int?) : LoginMessage

    /** Server refused the account. [unlockAt] is a pre-formatted clock time when known. */
    data class AccountLocked(val unlockAt: String?) : LoginMessage

    /**
     * No connection.
     *
     * The typed values stay in the form so nothing has to be retyped, but the attempt is
     * **not** replayed automatically: credentials are never queued, stored or re-sent
     * without the user pressing the button again. When the network comes back the card
     * says so and offers an explicit retry.
     */
    data object Offline : LoginMessage

    /**
     * The address has not been verified. Note the Source Audit: verification is **not**
     * enforced at login by the platform, so this is presented as a notice, not an error.
     */
    data class EmailNotVerified(val email: String) : LoginMessage

    data object ServerProblem : LoginMessage

    data object Unknown : LoginMessage
}

data class LoginUiState(
    val email: String = "",
    val password: String = "",
    val rememberMe: Boolean = false,
    @param:StringRes val emailError: Int? = null,
    @param:StringRes val passwordError: Int? = null,
    val isSubmitting: Boolean = false,
    val message: LoginMessage? = null,
    /** Drives the offline card's copy: "you're back online, try again". */
    val isOnline: Boolean = true,
) {
    /** The primary action stays enabled and validates on press — never a dead grey button. */
    val canSubmit: Boolean get() = !isSubmitting
}

/**
 * One-shot navigation results. Kept out of the state so they cannot replay on rotation.
 *
 * [Authenticated] carries the whole [SessionUser], not just the role — the caller needs
 * `hasCompletedOnboarding` to route a student correctly (Student Core vs. SO-01…SO-05).
 */
sealed interface LoginEvent {
    data class Authenticated(val user: SessionUser) : LoginEvent
    data class TwoFactorRequired(val email: String) : LoginEvent
    data class VerifyEmailRequested(val email: String) : LoginEvent
}

class LoginViewModel(
    private val authRepository: AuthRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    private val _events = Channel<LoginEvent>(Channel.BUFFERED)
    val events: Flow<LoginEvent> = _events.receiveAsFlow()

    init {
        // Connectivity is *observed*, never acted on: it only changes what the offline card
        // says. A login attempt happens when — and only when — the user asks for one.
        viewModelScope.launch {
            connectivity.isOnline.collect { online ->
                _state.update { it.copy(isOnline = online) }
            }
        }
    }

    fun onEmailChange(value: String) {
        _state.update { it.copy(email = value, emailError = null, message = null) }
    }

    fun onPasswordChange(value: String) {
        _state.update { it.copy(password = value, passwordError = null, message = null) }
    }

    fun onRememberMeChange(value: Boolean) {
        _state.update { it.copy(rememberMe = value) }
    }

    /** Clears the address so the user can sign in as someone else (the "change email" action). */
    fun clearEmail() {
        _state.update { it.copy(email = "", message = null, emailError = null) }
    }

    fun submit() {
        val current = _state.value
        if (current.isSubmitting) return

        val emailError = emailErrorOf(current.email)
        val passwordError = if (current.password.isBlank()) {
            R.string.a04_error_password_required
        } else {
            null
        }

        if (emailError != null || passwordError != null) {
            // Inline validation marks the offending fields; the sentence still speaks in
            // the single region, so there is only ever one place to read a failure.
            _state.update {
                it.copy(
                    emailError = emailError,
                    passwordError = passwordError,
                    message = null,
                )
            }
            return
        }

        _state.update { it.copy(isSubmitting = true, message = null) }

        viewModelScope.launch {
            when (val result = authRepository.signIn(current.email.trim(), current.password)) {
                is AppResult.Success -> {
                    _state.update { it.copy(isSubmitting = false) }
                    handleOutcome(result.data)
                }

                is AppResult.Failure -> _state.update {
                    // The email and password stay exactly as typed — an offline failure must
                    // never cost the user their input.
                    it.copy(isSubmitting = false, message = messageFor(result.error))
                }
            }
        }
    }

    private suspend fun handleOutcome(outcome: SignInOutcome) {
        when (outcome) {
            is SignInOutcome.Authenticated ->
                _events.send(LoginEvent.Authenticated(outcome.user))

            is SignInOutcome.TwoFactorRequired ->
                _events.send(LoginEvent.TwoFactorRequired(outcome.email))

            is SignInOutcome.EmailVerificationRequired ->
                // Shown in place rather than pushed, because the platform lets an unverified
                // user sign in. The notice offers the route to A-08 instead of forcing it.
                _state.update { it.copy(message = LoginMessage.EmailNotVerified(outcome.email)) }
        }
    }

    /** Called by the "resend link" action on the unverified notice. */
    fun onResendVerification(email: String) {
        viewModelScope.launch { _events.send(LoginEvent.VerifyEmailRequested(email)) }
    }

    private fun messageFor(error: AppError): LoginMessage = when (error) {
        AppError.Offline, AppError.Network -> LoginMessage.Offline
        AppError.Forbidden -> LoginMessage.AccountLocked(unlockAt = null)
        AppError.SessionExpired -> LoginMessage.WrongCredentials(attemptsRemaining = null)
        AppError.Server -> LoginMessage.ServerProblem
        is AppError.Domain -> LoginMessage.WrongCredentials(attemptsRemaining = null)
        is AppError.Validation -> LoginMessage.WrongCredentials(attemptsRemaining = null)
        else -> LoginMessage.Unknown
    }

}
