package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-21 · Voucher Redeem.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Its own entitlement rail, deliberately independent of [PendingPayment]/[PaymentStatus] —
 * a voucher grants a course directly, with no submission-then-verification step to reconcile.
 * No discount/cash-value concept exists here; a voucher only ever grants course access.
 */
enum class VoucherStatus { Valid, Invalid, Expired, AlreadyUsed }

/**
 * The result of checking a code before redeeming it. [courseId]/[courseTitle]/[accessPeriodLabel]
 * are only ever set when [status] is [VoucherStatus.Valid] — nothing about what a rejected code
 * would have granted is ever exposed, so an invalid attempt can't leak hints about other codes.
 */
data class VoucherValidationResult(
    val status: VoucherStatus,
    val courseId: String? = null,
    val courseTitle: String? = null,
    val accessPeriodLabel: String? = null,
)

/** What redeeming a valid code actually grants — shown on ST-21's confirmed state. */
data class RedeemedVoucher(
    val code: String,
    val courseId: String,
    val courseTitle: String,
    val accessPeriodLabel: String,
)
