package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.CourseOffer
import com.rork.eduspark.data.model.PaymentMethod
import com.rork.eduspark.data.repository.PaymentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-18 · Payment Method Select.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Read-only, like ST-17 — this screen never calls [PaymentRepository.submitPayment] itself.
 * Continue only carries the chosen [PaymentMethod.id] forward to ST-19, which is the screen
 * that actually owns the submitting/pending/failed lifecycle (see [PaymentPendingViewModel]).
 */
data class PaymentMethodScreenData(
    val offer: CourseOffer,
    val methods: List<PaymentMethod>,
)

data class PaymentMethodUiState(
    val result: UiState<PaymentMethodScreenData> = UiState.Loading,
    val selectedMethodId: String? = null,
    val isOnline: Boolean = true,
)

class PaymentMethodViewModel(
    private val courseId: String,
    private val paymentRepository: PaymentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(PaymentMethodUiState())
    val state: StateFlow<PaymentMethodUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    fun selectMethod(methodId: String) {
        _state.update { it.copy(selectedMethodId = methodId) }
    }

    private fun load() {
        _state.update { it.copy(result = UiState.Loading) }
        viewModelScope.launch {
            val offerResult = paymentRepository.getCourseOffer(courseId)
            val methodsResult = paymentRepository.getPaymentMethods()
            if (offerResult is AppResult.Success && methodsResult is AppResult.Success) {
                _state.update {
                    it.copy(result = UiState.Content(PaymentMethodScreenData(offerResult.data, methodsResult.data)))
                }
            } else {
                val error = (offerResult as? AppResult.Failure)?.error
                    ?: (methodsResult as? AppResult.Failure)?.error
                    ?: AppError.Unknown
                _state.update { it.copy(result = UiState.Failure(error)) }
            }
        }
    }
}
