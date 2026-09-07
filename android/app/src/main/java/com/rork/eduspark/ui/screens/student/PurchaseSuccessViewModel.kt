package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.PaymentStatus
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.repository.PaymentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-20 · Purchase Success.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Semantically distinct from ST-19: this screen only ever shows a payment whose status is
 * already [PaymentStatus.Verified] — a [PaymentStatus.Pending] one (or none at all) is treated
 * as [com.rork.eduspark.core.result.AppError.NotFound], the same "safe failure, no fake
 * success" boundary [PaywallViewModel] uses for an unknown course. [PaymentRepository.activateAccess]
 * is only ever called once verification is already confirmed, and is idempotent itself, so
 * revisiting this screen for an already-activated course never re-grants or duplicates access.
 */
data class PurchaseSuccessUiState(
    val result: UiState<PendingPayment> = UiState.Loading,
    val justActivated: Boolean = false,
    val isOnline: Boolean = true,
)

class PurchaseSuccessViewModel(
    private val courseId: String,
    private val paymentRepository: PaymentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(PurchaseSuccessUiState())
    val state: StateFlow<PurchaseSuccessUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val accessResult = paymentRepository.getPurchaseAccess(courseId)) {
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(accessResult.error)) }
                is AppResult.Success -> {
                    val access = accessResult.data
                    if (access == null || access.payment.status != PaymentStatus.Verified) {
                        // Nothing here fakes success for a Pending (or missing) payment.
                        _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                        return@launch
                    }
                    if (access.isActivated) {
                        _state.update { it.copy(result = UiState.Content(access.payment), justActivated = false) }
                        return@launch
                    }
                    when (val activation = paymentRepository.activateAccess(courseId)) {
                        is AppResult.Success -> _state.update { it.copy(result = UiState.Content(access.payment), justActivated = true) }
                        is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(activation.error)) }
                    }
                }
            }
        }
    }
}
