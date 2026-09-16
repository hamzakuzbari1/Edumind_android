package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-17 · Course Paywall / ST-18 · Payment Method Select / ST-19 · Payment Pending /
 * ST-20 · Purchase Success.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * `PAYMENT_MODE = "direct"` (see [com.rork.eduspark.di.PaymentMode]) — no card form, no
 * payment SDK, no gateway. [PaymentStatus.Verified] is the *only* addition ST-20 needed —
 * nothing in this build ever produces it automatically; it exists purely as the minimum mock
 * state required to represent "a future backend/admin flow already verified this," which is
 * why [com.rork.eduspark.data.repository.mock.MockPaymentRepository] seeds it as fixture data
 * rather than any code path promoting [PaymentStatus.Pending] into it.
 * [CourseSubscription] is never touched by anything here; see its own doc comment.
 */

/** Structured money — never string-formatted arithmetic. Every fixture in this slice is USD. */
data class Money(val amount: Int, val currencyCode: String = "USD")

/**
 * What buying/renewing [courseId] gets the student — built from the same course/subscription
 * data ST-02/ST-16 already expose, not a second copy of course identity.
 */
data class CourseOffer(
    val courseId: String,
    val courseTitle: String,
    val teacherName: String,
    val accessSummary: String,
    val accessPeriodLabel: String,
    val price: Money,
    /** True when this offer renews an existing (expiring/expired) [CourseSubscription] rather than starting a new one. */
    val isRenewal: Boolean,
)

/** One direct-payment option. No SDK, no gateway id — just a name and a human instruction. */
data class PaymentMethod(
    val id: String,
    val name: String,
    val instruction: String,
)

/**
 * [Draft]/[Submitting] only ever live in a ViewModel's own UI state, never in
 * [PendingPayment.status] — a [PendingPayment] is not created until submission succeeds, so a
 * failed attempt never has one lying around to accidentally duplicate on retry. [Verified] is
 * ST-20's only addition — see this file's own doc comment for why nothing here ever produces
 * it from [Pending] automatically.
 */
enum class PaymentStatus { Draft, Submitting, Pending, Verified, Failed }

data class PaymentRequest(
    val courseId: String,
    val courseTitle: String,
    val amount: Money,
    val methodId: String,
    val methodName: String,
    val teacherName: String? = null,
)

/** The one mock reference record ST-19 shows — pending until a future backend/admin flow verifies it. */
data class PendingPayment(
    val referenceId: String,
    val courseId: String,
    val courseTitle: String,
    val amount: Money,
    val methodName: String,
    val status: PaymentStatus,
    val submittedAtLabel: String,
    /** ST-20's approved teacher-identity row (PurchaseSuccess.dc.html) — null hides that row rather than fabricating a name. */
    val teacherName: String? = null,
)

/**
 * ST-20. [payment] is only ever meaningful here when its status is [PaymentStatus.Verified] —
 * callers must check that themselves; this record does not re-assert it. [isActivated]
 * is backend/catalog access, not a local grant. [confirmedThisSession] is true when this
 * process already received a verified/unlocked subscribe response — ST-20 then shows success
 * without calling subscribe again.
 */
data class PurchaseAccess(
    val payment: PendingPayment,
    val isActivated: Boolean,
    val confirmedThisSession: Boolean = false,
)
