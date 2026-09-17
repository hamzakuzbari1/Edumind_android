package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.RedeemedVoucher
import com.rork.eduspark.data.model.VoucherValidationResult
import com.rork.eduspark.data.repository.VoucherRepository

/**
 * Remote payment/subscription has no voucher contract yet. Blocks mock codes and string
 * course ids instead of wiring [com.rork.eduspark.data.repository.mock.MockVoucherRepository].
 */
internal class UnavailableVoucherRepository : VoucherRepository {
    override val isAvailable: Boolean = false

    override suspend fun validateVoucher(code: String): AppResult<VoucherValidationResult> =
        AppResult.Failure(AppError.Domain("voucher_unavailable"))

    override suspend fun redeemVoucher(code: String): AppResult<RedeemedVoucher> =
        AppResult.Failure(AppError.Domain("voucher_unavailable"))
}
