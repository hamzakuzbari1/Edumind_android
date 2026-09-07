package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.PaymentRequest
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.repository.PaymentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-19 · Payment Pending.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Owns the submit call ST-18 deliberately did not make — [submit] resolves the same
 * [CourseOffer][com.rork.eduspark.data.model.CourseOffer]/[PaymentMethod][com.rork.eduspark.data.model.PaymentMethod]
 * ST-18 already showed (by [courseId]/[methodId], not a duplicated repository field) and calls
 * [PaymentRepository.submitPayment]. That call is idempotent per course (see its own doc
 * comment), so calling [submit] again — on [retry], or because this ViewModel was simply
 * recreated by returning to ST-19 later — can never create a second pending transaction; the
 * repository just hands back the same [PendingPayment] it already has.
 */
enum class PaymentPendingPhase { Submitting, Pending, Failed }

data class PaymentPendingUiState(
    val phase: PaymentPendingPhase = PaymentPendingPhase.Submitting,
    val pending: PendingPayment? = null,
    val error: AppError? = null,
    val isOnline: Boolean = true,
)

class PaymentPendingViewModel(
    private val courseId: String,
    private val methodId: String,
    private val paymentRepository: PaymentRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(PaymentPendingUiState())
    val state: StateFlow<PaymentPendingUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            paymentRepository.pendingPayment.collect { pending ->
                if (pending != null && pending.courseId == courseId) {
                    _state.update { it.copy(phase = PaymentPendingPhase.Pending, pending = pending) }
                }
            }
        }
        submit()
    }

    fun retry() = submit()

    private fun submit() {
        _state.update { it.copy(phase = PaymentPendingPhase.Submitting, error = null) }
        viewModelScope.launch {
            val offerResult = paymentRepository.getCourseOffer(courseId)
            val methodsResult = paymentRepository.getPaymentMethods()
            if (offerResult !is AppResult.Success || methodsResult !is AppResult.Success) {
                val error = (offerResult as? AppResult.Failure)?.error
                    ?: (methodsResult as? AppResult.Failure)?.error
                    ?: AppError.Unknown
                _state.update { it.copy(phase = PaymentPendingPhase.Failed, error = error) }
                return@launch
            }
            val method = methodsResult.data.firstOrNull { it.id == methodId }
            if (method == null) {
                _state.update { it.copy(phase = PaymentPendingPhase.Failed, error = AppError.Unknown) }
                return@launch
            }

            val request = PaymentRequest(
                courseId = courseId,
                courseTitle = offerResult.data.courseTitle,
                amount = offerResult.data.price,
                methodId = method.id,
                methodName = method.name,
            )
            when (val result = paymentRepository.submitPayment(request)) {
                // Success is reflected by the flow collector above — same convention as
                // PlannerViewModel's own loadWeekPlan() call.
                is AppResult.Success -> Unit
                is AppResult.Failure -> _state.update { it.copy(phase = PaymentPendingPhase.Failed, error = result.error) }
            }
        }
    }
}
