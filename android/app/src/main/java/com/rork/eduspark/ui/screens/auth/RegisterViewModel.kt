package com.rork.eduspark.ui.screens.auth

import androidx.annotation.StringRes
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.R
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.preferences.AppPreferences
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.RegistrationOutcome
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
 * A-05 / A-06 / A-07 · Registration — one form, three roles.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The three screens are deliberately **one** ViewModel parameterised by [role], not three
 * near-identical ones. The Screen Inventory describes them as the same form plus one
 * role-specific block, and the surest way to keep three screens visually and behaviourally
 * identical is for them to be the same screen.
 *
 * What is actually sent when the user registers: **name, email, password, role.** Nothing
 * else. The Source Audit is explicit that the platform registers `teacher | student |
 * parent` and no more, so the teacher's subjects and grades are *not* smuggled into a
 * request field that does not exist. They are kept on the device (see [AppPreferences]) and
 * handed to TC-01 Teacher Setup later, and the screen says so rather than implying the
 * server received them.
 *
 * Failure vocabulary mirrors A-04: everything speaks in one region, so a user who has just
 * filled five fields never has to hunt for what went wrong.
 */
sealed interface RegisterMessage {

    /** A client-side rule the user can fix right now. Carries the sentence to show. */
    data class Invalid(@param:StringRes val messageRes: Int) : RegisterMessage

    /** The address already has an account — the only useful next step is to log in. */
    data object EmailAlreadyRegistered : RegisterMessage

    /**
     * No connection.
     *
     * As on A-04, nothing is queued and nothing is replayed: the form keeps every value the
     * user typed, and creating the account stays an explicit press.
     */
    data object Offline : RegisterMessage

    data object ServerProblem : RegisterMessage

    data object Unknown : RegisterMessage
}

data class RegisterUiState(
    val name: String = "",
    val email: String = "",
    val password: String = "",
    val passwordConfirmation: String = "",
    val acceptedTerms: Boolean = false,

    /** A-07 only — teaching intent, kept on the device. */
    val subjectIds: Set<String> = emptySet(),
    val gradeIds: Set<String> = emptySet(),

    @param:StringRes val nameError: Int? = null,
    @param:StringRes val emailError: Int? = null,
    @param:StringRes val passwordError: Int? = null,
    @param:StringRes val passwordConfirmationError: Int? = null,

    val isSubmitting: Boolean = false,
    val message: RegisterMessage? = null,
    val isOnline: Boolean = true,
) {
    /** Enabled always, validated on press — never a dead grey button the user can't argue with. */
    val canSubmit: Boolean get() = !isSubmitting
}

/** One-shot outcome. Kept off the state so it cannot replay on rotation. */
sealed interface RegisterEvent {
    data class Authenticated(val user: com.rork.eduspark.data.model.SessionUser) : RegisterEvent
    data class EmailVerificationRequired(val email: String) : RegisterEvent
}

class RegisterViewModel(
    val role: UserRole,
    private val authRepository: AuthRepository,
    private val preferences: AppPreferences,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(RegisterUiState())
    val state: StateFlow<RegisterUiState> = _state.asStateFlow()

    private val _events = Channel<RegisterEvent>(Channel.BUFFERED)
    val events: Flow<RegisterEvent> = _events.receiveAsFlow()

    init {
        // Observed only to change what the offline card says. Never to resubmit anything.
        viewModelScope.launch {
            connectivity.isOnline.collect { online ->
                _state.update { it.copy(isOnline = online) }
            }
        }
    }

    fun onNameChange(value: String) {
        _state.update { it.copy(name = value, nameError = null, message = null) }
    }

    fun onEmailChange(value: String) {
        _state.update { it.copy(email = value, emailError = null, message = null) }
    }

    fun onPasswordChange(value: String) {
        _state.update {
            it.copy(
                password = value,
                passwordError = null,
                // Retyping the password invalidates a previous mismatch verdict.
                passwordConfirmationError = null,
                message = null,
            )
        }
    }

    fun onPasswordConfirmationChange(value: String) {
        _state.update {
            it.copy(passwordConfirmation = value, passwordConfirmationError = null, message = null)
        }
    }

    fun onAcceptTermsChange(accepted: Boolean) {
        _state.update { it.copy(acceptedTerms = accepted, message = null) }
    }

    fun toggleSubject(id: String) {
        _state.update { it.copy(subjectIds = it.subjectIds.toggled(id), message = null) }
    }

    fun toggleGrade(id: String) {
        _state.update { it.copy(gradeIds = it.gradeIds.toggled(id), message = null) }
    }

    fun submit() {
        val current = _state.value
        if (current.isSubmitting) return

        val nameError = fullNameErrorOf(current.name)
        val emailError = emailErrorOf(current.email)
        val passwordError = newPasswordErrorOf(current.password)
        val confirmationError = passwordConfirmationErrorOf(
            password = current.password,
            confirmation = current.passwordConfirmation,
        )

        // Rules that belong to no single field, in the order the eye meets them.
        val formError: Int? = when {
            role == UserRole.Teacher && current.subjectIds.isEmpty() ->
                R.string.a07_error_subject_required

            role == UserRole.Teacher && current.gradeIds.isEmpty() ->
                R.string.a07_error_grade_required

            !current.acceptedTerms -> R.string.reg_error_terms_required
            else -> null
        }

        // Every offending field turns red, but only the first problem is spoken, in the one
        // region — five stacked red sentences is noise, not help.
        val firstProblem = nameError ?: emailError ?: passwordError ?: confirmationError ?: formError
        if (firstProblem != null) {
            _state.update {
                it.copy(
                    nameError = nameError,
                    emailError = emailError,
                    passwordError = passwordError,
                    passwordConfirmationError = confirmationError,
                    message = RegisterMessage.Invalid(firstProblem),
                )
            }
            return
        }

        _state.update { it.copy(isSubmitting = true, message = null) }

        viewModelScope.launch {
            val result = authRepository.register(
                name = current.name.trim(),
                email = current.email.trim(),
                password = current.password,
                role = role,
            )

            when (result) {
                is AppResult.Success -> {
                    if (role == UserRole.Teacher) {
                        // Local draft only — TC-01 reads it so nothing is asked twice.
                        preferences.setTeacherIntent(current.subjectIds, current.gradeIds)
                    }
                    _state.update { it.copy(isSubmitting = false) }
                    when (val outcome = result.data) {
                        is RegistrationOutcome.Authenticated ->
                            _events.send(RegisterEvent.Authenticated(outcome.user))
                        is RegistrationOutcome.EmailVerificationRequired ->
                            _events.send(RegisterEvent.EmailVerificationRequired(outcome.email))
                    }
                }

                // Values are left untouched: a failed attempt must never cost typed input.
                is AppResult.Failure -> _state.update {
                    it.copy(isSubmitting = false, message = messageFor(result.error))
                }
            }
        }
    }

    private fun messageFor(error: AppError): RegisterMessage = when (error) {
        AppError.Offline, AppError.Network -> RegisterMessage.Offline
        AppError.Server -> RegisterMessage.ServerProblem
        is AppError.Validation ->
            if (error.fieldErrors.containsKey("email")) {
                RegisterMessage.EmailAlreadyRegistered
            } else {
                RegisterMessage.Unknown
            }

        else -> RegisterMessage.Unknown
    }

    private fun Set<String>.toggled(id: String): Set<String> =
        if (contains(id)) this - id else this + id
}
