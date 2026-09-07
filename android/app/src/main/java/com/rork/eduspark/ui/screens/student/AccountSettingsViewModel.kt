package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.ProfileRepository
import com.rork.eduspark.ui.components.input.PASSWORD_MIN_LENGTH
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-23 · Settings — Account.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Name/avatar edits go through [ProfileRepository.updateProfile] — the same call ST-22's
 * sheet makes, read-modify-write so grade/school (not shown here) are preserved untouched.
 *
 * Email change, password change and delete-account are all local, ViewModel-owned mock state
 * rather than new repository methods, because nothing else in the app needs to read "pending
 * email" or "password" — [displayEmail][AccountSettingsUiState.email] only updates *after*
 * [EmailChangeState] reaches its OTP step and the deterministic code matches, never before
 * (see [confirmEmailChange]). [DeleteAccountPhase.Confirmed] is a terminal UI state, not a
 * call to [AuthRepository.signOut] — this build has no existing "what happens after sign-out"
 * navigation path to route into, so modelling deletion any deeper than an honest confirmed
 * state would be inventing an untested side effect, which the boundaries for this slice rule out.
 */
enum class EmailChangeStep { EnterEmail, Verify }

data class EmailChangeState(
    val step: EmailChangeStep = EmailChangeStep.EnterEmail,
    val newEmail: String = "",
    val code: String = "",
    val isSubmitting: Boolean = false,
    val isInvalidCode: Boolean = false,
)

data class PasswordChangeState(
    val currentPassword: String = "",
    val newPassword: String = "",
    val confirmPassword: String = "",
    val isSubmitting: Boolean = false,
    val isComplete: Boolean = false,
    val validationFailed: Boolean = false,
)

enum class DeleteAccountPhase { Confirming, Confirmed }

data class AccountSettingsUiState(
    val isLoading: Boolean = true,
    val displayName: String = "",
    val avatarInitial: String = "",
    val email: String = "",
    val isOnline: Boolean = true,
    val showNameSheet: Boolean = false,
    val isSavingName: Boolean = false,
    val emailChange: EmailChangeState? = null,
    val passwordChange: PasswordChangeState? = null,
    val deleteAccount: DeleteAccountPhase? = null,
)

class AccountSettingsViewModel(
    private val profileRepository: ProfileRepository,
    private val authRepository: AuthRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(AccountSettingsUiState())
    val state: StateFlow<AccountSettingsUiState> = _state.asStateFlow()

    private var hasLocalEmailOverride = false

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            profileRepository.profile.collect { profile ->
                _state.update { it.copy(displayName = profile.displayName, avatarInitial = profile.avatarInitial) }
            }
        }
        viewModelScope.launch {
            authRepository.session.collect { session ->
                if (session != null && !hasLocalEmailOverride) {
                    _state.update { it.copy(email = session.email) }
                }
                _state.update { it.copy(isLoading = false) }
            }
        }
    }

    // ── Name / avatar ────────────────────────────────────────────────────
    fun openNameSheet() = _state.update { it.copy(showNameSheet = true) }
    fun dismissNameSheet() = _state.update { it.copy(showNameSheet = false) }

    fun saveName(newName: String) {
        if (_state.value.isSavingName || newName.isBlank()) return
        _state.update { it.copy(isSavingName = true) }
        viewModelScope.launch {
            val currentProfile = (profileRepository.getProfile() as? AppResult.Success)?.data
            if (currentProfile == null) {
                _state.update { it.copy(isSavingName = false) }
                return@launch
            }
            when (profileRepository.updateProfile(newName, currentProfile.grade, currentProfile.school)) {
                is AppResult.Success -> _state.update { it.copy(isSavingName = false, showNameSheet = false) }
                is AppResult.Failure -> _state.update { it.copy(isSavingName = false) }
            }
        }
    }

    // ── Email change — enter new email → verify → done, never earlier ─────
    fun openEmailChange() = _state.update { it.copy(emailChange = EmailChangeState()) }
    fun dismissEmailChange() = _state.update { it.copy(emailChange = null) }

    fun updateNewEmail(value: String) {
        _state.update { it.copy(emailChange = it.emailChange?.copy(newEmail = value)) }
    }

    fun submitNewEmail() {
        val current = _state.value.emailChange ?: return
        if (current.step != EmailChangeStep.EnterEmail || current.newEmail.isBlank() || current.isSubmitting) return
        _state.update { it.copy(emailChange = current.copy(isSubmitting = true)) }
        viewModelScope.launch {
            delay(MOCK_DELAY_MS)
            _state.update {
                it.copy(emailChange = it.emailChange?.copy(step = EmailChangeStep.Verify, isSubmitting = false, code = ""))
            }
        }
    }

    fun updateEmailChangeCode(value: String) {
        _state.update { it.copy(emailChange = it.emailChange?.copy(code = value, isInvalidCode = false)) }
    }

    fun confirmEmailChange() {
        val current = _state.value.emailChange ?: return
        if (current.step != EmailChangeStep.Verify || current.isSubmitting) return
        _state.update { it.copy(emailChange = current.copy(isSubmitting = true)) }
        viewModelScope.launch {
            delay(MOCK_DELAY_MS)
            if (current.code != EMAIL_OTP_CODE) {
                _state.update { it.copy(emailChange = it.emailChange?.copy(isSubmitting = false, isInvalidCode = true)) }
                return@launch
            }
            hasLocalEmailOverride = true
            _state.update { it.copy(email = current.newEmail, emailChange = null) }
        }
    }

    // ── Password change — MOCK completion only ─────────────────────────────
    fun openPasswordChange() = _state.update { it.copy(passwordChange = PasswordChangeState()) }
    fun dismissPasswordChange() = _state.update { it.copy(passwordChange = null) }

    fun updateCurrentPassword(value: String) {
        _state.update { it.copy(passwordChange = it.passwordChange?.copy(currentPassword = value, validationFailed = false)) }
    }

    fun updateNewPassword(value: String) {
        _state.update { it.copy(passwordChange = it.passwordChange?.copy(newPassword = value, validationFailed = false)) }
    }

    fun updateConfirmPassword(value: String) {
        _state.update { it.copy(passwordChange = it.passwordChange?.copy(confirmPassword = value, validationFailed = false)) }
    }

    fun submitPasswordChange() {
        val current = _state.value.passwordChange ?: return
        if (current.isSubmitting) return
        val isValid = current.currentPassword.isNotBlank() &&
            current.newPassword.length >= PASSWORD_MIN_LENGTH &&
            current.newPassword == current.confirmPassword
        if (!isValid) {
            _state.update { it.copy(passwordChange = current.copy(validationFailed = true)) }
            return
        }
        _state.update { it.copy(passwordChange = current.copy(isSubmitting = true)) }
        viewModelScope.launch {
            delay(MOCK_DELAY_MS)
            _state.update { it.copy(passwordChange = it.passwordChange?.copy(isSubmitting = false, isComplete = true)) }
        }
    }

    // ── Delete account — destructive, explicit confirmation ────────────────
    fun requestDeleteAccount() = _state.update { it.copy(deleteAccount = DeleteAccountPhase.Confirming) }
    fun cancelDeleteAccount() = _state.update { it.copy(deleteAccount = null) }
    fun confirmDeleteAccount() = _state.update { it.copy(deleteAccount = DeleteAccountPhase.Confirmed) }

    private companion object {
        const val MOCK_DELAY_MS = 400L
        const val EMAIL_OTP_CODE = "123456"
    }
}
