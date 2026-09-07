package com.rork.eduspark.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.CertificateVerification
import com.rork.eduspark.data.repository.CertificateRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-12 · Certificate Verification — public, no session.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deliberately depends on nothing but [CertificateRepository] and connectivity — no
 * [com.rork.eduspark.data.repository.AuthRepository], because this screen must render
 * correctly for a reader who has never opened the app and never will.
 *
 * Fits [UiState] exactly (loading / content / failure — never "empty", a certificate either
 * verifies or it doesn't), so it renders through the existing A-14 [com.rork.eduspark.ui
 * .components.state.ScreenStateHost] rather than a bespoke state machine.
 */
data class CertificateVerifyUiState(
    val result: UiState<CertificateVerification> = UiState.Loading,
    val isOnline: Boolean = true,
)

class CertificateVerifyViewModel(
    private val code: String,
    private val certificateRepository: CertificateRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(CertificateVerifyUiState())
    val state: StateFlow<CertificateVerifyUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online ->
                _state.update { it.copy(isOnline = online) }
            }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val result = certificateRepository.verify(code)) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
        }
    }
}
