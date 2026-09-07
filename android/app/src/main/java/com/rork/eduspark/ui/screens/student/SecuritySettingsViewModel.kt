package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ActiveSession
import com.rork.eduspark.data.repository.SecurityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-24 · Settings — Security.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Enabling 2FA reuses the email-OTP *concept* every A-08/A-09 flow already uses (send a code,
 * enter it, [SecurityRepository.confirmEnableTwoFactor] checks the same deterministic mock
 * code) — deliberately not [com.rork.eduspark.data.repository.AuthRepository.verifyTwoFactor],
 * which verifies a login attempt, not an account setting. Disabling needs no re-verification;
 * the screen's own confirmation is the gate. [pendingRevokeSessionId]/[pendingRevokeAll] both
 * exist so a revoke never fires without the student explicitly confirming it first.
 */
data class TwoFactorEnableState(
    val code: String = "",
    val isSubmitting: Boolean = false,
    val isInvalidCode: Boolean = false,
)

data class SecurityScreenData(
    val twoFactorEnabled: Boolean,
    val sessions: List<ActiveSession>,
)

data class SecuritySettingsUiState(
    val result: UiState<SecurityScreenData> = UiState.Loading,
    val isOnline: Boolean = true,
    val isStartingTwoFactor: Boolean = false,
    val twoFactorEnableFlow: TwoFactorEnableState? = null,
    val pendingDisableTwoFactor: Boolean = false,
    val isTogglingTwoFactor: Boolean = false,
    val pendingRevokeSessionId: String? = null,
    val pendingRevokeAll: Boolean = false,
    val isRevoking: Boolean = false,
)

class SecuritySettingsViewModel(
    private val securityRepository: SecurityRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(SecuritySettingsUiState())
    val state: StateFlow<SecuritySettingsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            securityRepository.securitySettings.collect { settings ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(twoFactorEnabled = settings.twoFactorEnabled)))
                }
            }
        }
        viewModelScope.launch {
            securityRepository.activeSessions.collect { sessions ->
                _state.update { current ->
                    val data = (current.result as? UiState.Content)?.data ?: return@update current
                    current.copy(result = UiState.Content(data.copy(sessions = sessions)))
                }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val settingsResult = securityRepository.getSecuritySettings()
            val sessionsResult = securityRepository.getActiveSessions()
            if (settingsResult is AppResult.Success && sessionsResult is AppResult.Success) {
                _state.update {
                    it.copy(result = UiState.Content(SecurityScreenData(settingsResult.data.twoFactorEnabled, sessionsResult.data)))
                }
            } else {
                val error = (settingsResult as? AppResult.Failure)?.error
                    ?: (sessionsResult as? AppResult.Failure)?.error
                    ?: AppError.Unknown
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }

    // ── 2FA enable — request code → enter code, never enabled before that succeeds ─────
    fun startEnableTwoFactor() {
        if (_state.value.isStartingTwoFactor) return
        _state.update { it.copy(isStartingTwoFactor = true) }
        viewModelScope.launch {
            securityRepository.requestEnableTwoFactor()
            _state.update { it.copy(isStartingTwoFactor = false, twoFactorEnableFlow = TwoFactorEnableState()) }
        }
    }

    fun cancelEnableTwoFactor() = _state.update { it.copy(twoFactorEnableFlow = null) }

    fun updateTwoFactorCode(value: String) {
        _state.update { it.copy(twoFactorEnableFlow = it.twoFactorEnableFlow?.copy(code = value, isInvalidCode = false)) }
    }

    fun confirmEnableTwoFactor() {
        val flow = _state.value.twoFactorEnableFlow ?: return
        if (flow.isSubmitting) return
        _state.update { it.copy(twoFactorEnableFlow = flow.copy(isSubmitting = true)) }
        viewModelScope.launch {
            when (securityRepository.confirmEnableTwoFactor(flow.code)) {
                // Reflected by the securitySettings flow collector above.
                is AppResult.Success -> _state.update { it.copy(twoFactorEnableFlow = null) }
                is AppResult.Failure -> _state.update {
                    it.copy(twoFactorEnableFlow = it.twoFactorEnableFlow?.copy(isSubmitting = false, isInvalidCode = true))
                }
            }
        }
    }

    // ── 2FA disable — confirmation only, no re-verification needed ─────────
    fun requestDisableTwoFactor() = _state.update { it.copy(pendingDisableTwoFactor = true) }
    fun cancelDisableTwoFactor() = _state.update { it.copy(pendingDisableTwoFactor = false) }

    fun confirmDisableTwoFactor() {
        if (_state.value.isTogglingTwoFactor) return
        _state.update { it.copy(isTogglingTwoFactor = true) }
        viewModelScope.launch {
            securityRepository.disableTwoFactor()
            _state.update { it.copy(isTogglingTwoFactor = false, pendingDisableTwoFactor = false) }
        }
    }

    // ── Sessions ─────────────────────────────────────────────────────────
    fun requestRevokeSession(sessionId: String) = _state.update { it.copy(pendingRevokeSessionId = sessionId) }
    fun cancelRevokeSession() = _state.update { it.copy(pendingRevokeSessionId = null) }

    fun confirmRevokeSession() {
        val sessionId = _state.value.pendingRevokeSessionId ?: return
        _state.update { it.copy(isRevoking = true) }
        viewModelScope.launch {
            securityRepository.revokeSession(sessionId)
            _state.update { it.copy(isRevoking = false, pendingRevokeSessionId = null) }
        }
    }

    fun requestRevokeAll() = _state.update { it.copy(pendingRevokeAll = true) }
    fun cancelRevokeAll() = _state.update { it.copy(pendingRevokeAll = false) }

    fun confirmRevokeAll() {
        _state.update { it.copy(isRevoking = true) }
        viewModelScope.launch {
            securityRepository.revokeAllOtherSessions()
            _state.update { it.copy(isRevoking = false, pendingRevokeAll = false) }
        }
    }
}
