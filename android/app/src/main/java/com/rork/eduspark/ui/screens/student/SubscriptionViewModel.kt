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
 * Read-only — there is no accept/reject/complete-style mutation here, unlike Planner/Routine.
 * Renew/Subscribe now navigate into ST-17 (see [com.rork.eduspark.ui.screens.student.CoursePaywallScreen]);
 * nothing in this ViewModel ever flips a subscription to Active — that boundary lives entirely
 * in ST-17/18/19's own PaymentRepository, never here. [verifiedPurchase] is ST-20's own entry
 * point — [PaymentRepository.verifiedUnactivatedPayment] is collected, not fetched once, so the
 * "confirmed access" banner disappears the moment ST-20 activates it, with no extra reload.
 */
data class SubscriptionUiState(
    val result: UiState<List<CourseSubscription>> = UiState.Loading,
    val availableCourses: List<AvailableCourse> = emptyList(),
    val verifiedPurchase: PendingPayment? = null,
    val isOnline: Boolean = true,
)

class SubscriptionViewModel(
    private val subscriptionRepository: SubscriptionRepository,
    paymentRepository: PaymentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(SubscriptionUiState())
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

    fun retry() = load()

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            when (val result = subscriptionRepository.getSubscriptions()) {
                is AppResult.Success -> _state.update { it.copy(result = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(result = UiState.Failure(result.error)) }
            }
            when (val available = subscriptionRepository.getAvailableCourses()) {
                // Non-critical: the "add a course" section simply stays empty on failure.
                is AppResult.Success -> _state.update { it.copy(availableCourses = available.data) }
                is AppResult.Failure -> Unit
            }
        }
    }
}
