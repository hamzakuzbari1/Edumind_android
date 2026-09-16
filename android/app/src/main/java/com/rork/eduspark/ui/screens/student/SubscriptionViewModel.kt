package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.AvailableCourse
import com.rork.eduspark.data.model.CourseSubscription
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.repository.PaymentRepository
import com.rork.eduspark.data.repository.SubscriptionRepository
import com.rork.eduspark.data.repository.VoucherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-16 · Subscriptions.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Read-only — renew/subscribe navigate into ST-17. Access after a remote payment comes from
 * GET /subscriptions on refresh, not from [PaymentRepository.verifiedUnactivatedPayment].
 * That banner remains mock-only. Voucher entry is hidden when no backend contract exists.
 */
data class SubscriptionUiState(
    val result: UiState<List<CourseSubscription>> = UiState.Loading,
    val availableCourses: List<AvailableCourse> = emptyList(),
    val verifiedPurchase: PendingPayment? = null,
    val voucherEntryEnabled: Boolean = false,
    val isOnline: Boolean = true,
)

class SubscriptionViewModel(
    private val subscriptionRepository: SubscriptionRepository,
    paymentRepository: PaymentRepository,
    voucherRepository: VoucherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(
        SubscriptionUiState(voucherEntryEnabled = voucherRepository.isAvailable),
    )
    val state: StateFlow<SubscriptionUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            paymentRepository.verifiedUnactivatedPayment.collect { payment ->
                _state.update { it.copy(verifiedPurchase = payment) }
            }
        }
        load()
    }

    fun retry() = load(showLoading = true)

    fun refresh() = load(showLoading = false)

    private fun load(showLoading: Boolean = true) {
        if (showLoading) {
            _state.update { it.copy(result = UiState.Loading) }
        }
        viewModelScope.launch {
            when (val result = subscriptionRepository.getSubscriptions()) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
            when (val available = subscriptionRepository.getAvailableCourses()) {
                is AppResult.Success -> _state.update { it.copy(availableCourses = available.data) }
                is AppResult.Failure -> Unit
            }
        }
    }
}
