package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.RedeemedVoucher
import com.rork.eduspark.data.model.VoucherStatus
import com.rork.eduspark.data.model.VoucherValidationResult
import com.rork.eduspark.data.repository.VoucherRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-21 · Voucher Redeem.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Enter → [validate] (read-only preview) → [redeem] (commits). [redeem] is only ever called
 * once [phase] is [VoucherPhase.Validated] with [VoucherValidationResult.status] Valid, and
 * [VoucherRepository.redeemVoucher] is itself idempotent per code, so retrying or re-entering
 * an already-redeemed code never duplicates access.
 */
sealed interface VoucherPhase {
    data object Input : VoucherPhase
    data class Validated(val result: VoucherValidationResult) : VoucherPhase
    data class Redeemed(val redeemed: RedeemedVoucher) : VoucherPhase
}

data class VoucherUiState(
    val code: String = "",
    val phase: VoucherPhase = VoucherPhase.Input,
    val isValidating: Boolean = false,
    val isRedeeming: Boolean = false,
    val error: AppError? = null,
    val isOnline: Boolean = true,
)

class VoucherRedeemViewModel(
    private val voucherRepository: VoucherRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(VoucherUiState())
    val state: StateFlow<VoucherUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
    }

    /** Editing the code after a validation result invalidates that result — it was for the old text. */
    fun updateCode(value: String) {
        _state.update { it.copy(code = value, phase = VoucherPhase.Input, error = null) }
    }

    fun validate() {
        val code = _state.value.code.trim()
        if (code.isEmpty() || _state.value.isValidating) return
        _state.update { it.copy(isValidating = true, error = null) }
        viewModelScope.launch {
            when (val result = voucherRepository.validateVoucher(code)) {
                is AppResult.Success -> _state.update {
                    it.copy(isValidating = false, phase = VoucherPhase.Validated(result.data))
                }
                is AppResult.Failure -> _state.update { it.copy(isValidating = false, error = result.error) }
            }
        }
    }

    fun redeem() {
        val validated = _state.value.phase as? VoucherPhase.Validated ?: return
        if (validated.result.status != VoucherStatus.Valid || _state.value.isRedeeming) return
        _state.update { it.copy(isRedeeming = true, error = null) }
        viewModelScope.launch {
            when (val result = voucherRepository.redeemVoucher(_state.value.code.trim())) {
                is AppResult.Success -> _state.update { it.copy(isRedeeming = false, phase = VoucherPhase.Redeemed(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(isRedeeming = false, error = result.error) }
            }
        }
    }

    /** Redeemed → start over for a second code, e.g. redeeming for a sibling. */
    fun startOver() {
        _state.update { VoucherUiState(isOnline = it.isOnline) }
    }
}
