package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.CourseOffer
import com.rork.eduspark.data.model.SubscriptionStatus
import com.rork.eduspark.data.repository.PaymentRepository
import com.rork.eduspark.data.repository.SubscriptionRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-17 · Course Paywall Sheet.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [SubscriptionRepository.getSubscriptions] is checked first, not [PaymentRepository] alone —
 * a course with an existing [SubscriptionStatus.Active] subscription must never reach the
 * offer/price path at all, which is what actually stops a duplicate purchase (rather than a
 * UI-only guard the screen could route around). [SubscriptionStatus.ExpiringSoon]/[SubscriptionStatus.Expired]
 * both fall through to the normal offer — renewing before or after expiry is still one flow.
 */
sealed interface PaywallContent {
    data class Offer(val offer: CourseOffer) : PaywallContent
    data class AlreadySubscribed(val courseTitle: String) : PaywallContent
}

data class PaywallUiState(
    val result: UiState<PaywallContent> = UiState.Loading,
    val isOnline: Boolean = true,
)

class PaywallViewModel(
    private val courseId: String,
    private val subscriptionRepository: SubscriptionRepository,
    private val paymentRepository: PaymentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(PaywallUiState())
    val state: StateFlow<PaywallUiState> = _state.asStateFlow()

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
            val subscriptionsResult = subscriptionRepository.getSubscriptions()
            val active = (subscriptionsResult as? AppResult.Success)?.data
                ?.firstOrNull { it.courseId == courseId && it.status == SubscriptionStatus.Active }
            if (active != null) {
                _state.update { it.copy(result = UiState.Content(PaywallContent.AlreadySubscribed(active.courseTitle))) }
                return@launch
            }

            when (val offerResult = paymentRepository.getCourseOffer(courseId)) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(PaywallContent.Offer(offerResult.data))) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(offerResult.error)) }
            }
        }
    }
}
