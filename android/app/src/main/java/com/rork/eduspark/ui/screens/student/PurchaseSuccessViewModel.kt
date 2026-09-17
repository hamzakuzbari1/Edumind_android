package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.PaymentStatus
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.PaymentRepository
import com.rork.eduspark.data.repository.SubscriptionRepository
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
 * Shows a payment whose status is already [PaymentStatus.Verified]. Backend access is
 * authoritative — this screen refreshes subscriptions and learning entitlement, and never
 * calls subscribe a second time. Mock-only [PaymentRepository.activateAccess] remains for
 * the seeded local fixture that is verified but not yet locally activated.
 */
data class PurchaseSuccessUiState(
    val result: UiState<PendingPayment> = UiState.Loading,
    val justActivated: Boolean = false,
    val isOnline: Boolean = true,
)

class PurchaseSuccessViewModel(
    private val courseId: String,
    private val paymentRepository: PaymentRepository,
    private val subscriptionRepository: SubscriptionRepository,
    private val learningRepository: LearningRepository,
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
                        _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                        return@launch
                    }
                    var justActivated = access.confirmedThisSession
                    if (!access.isActivated && !access.confirmedThisSession) {
                        when (val activation = paymentRepository.activateAccess(courseId)) {
                            is AppResult.Success -> justActivated = true
                            is AppResult.Failure -> {
                                _state.update { it.copy(result = UiState.Failure(activation.error)) }
                                return@launch
                            }
                        }
                    }
                    refreshEntitlements()
                    _state.update {
                        it.copy(result = UiState.Content(access.payment), justActivated = justActivated)
                    }
                }
            }
        }
    }

    private suspend fun refreshEntitlements() {
        subscriptionRepository.getSubscriptions()
        learningRepository.getStudentCourses()
        learningRepository.getPath(courseId)
    }
}
