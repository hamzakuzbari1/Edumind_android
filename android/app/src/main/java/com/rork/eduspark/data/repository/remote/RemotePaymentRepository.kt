package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.CourseOffer
import com.rork.eduspark.data.model.Money
import com.rork.eduspark.data.model.PaymentMethod
import com.rork.eduspark.data.model.PaymentRequest
import com.rork.eduspark.data.model.PaymentStatus
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.model.PurchaseAccess
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.learning.StudentLearningApi
import com.rork.eduspark.data.remote.learning.SubscribeCourseRequestDto
import com.rork.eduspark.data.remote.learning.SubscriptionCourseDto
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.PaymentRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal class RemotePaymentRepository(
    private val api: StudentLearningApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : PaymentRepository {

    private val _pendingPayment = MutableStateFlow<PendingPayment?>(null)
    override val pendingPayment: Flow<PendingPayment?> = _pendingPayment.asStateFlow()

    private val _verifiedUnactivatedPayment = MutableStateFlow<PendingPayment?>(null)
    override val verifiedUnactivatedPayment: Flow<PendingPayment?> = _verifiedUnactivatedPayment.asStateFlow()

    override suspend fun getCourseOffer(courseId: String): AppResult<CourseOffer> {
        val course = when (val catalog = catalogCourse(courseId)) {
            is AppResult.Success -> catalog.data ?: return AppResult.Failure(AppError.NotFound)
            is AppResult.Failure -> return catalog
        }
        val (isRenewal, price, _) = course.toCourseOfferFields()
        return AppResult.Success(
            CourseOffer(
                courseId = course.id.toString(),
                courseTitle = course.title,
                teacherName = course.teacherName,
                accessSummary = course.subscriptionBenefits.ifBlank {
                    if (isRenewal) {
                        "جدد اشتراكك لمتابعة دروس ${course.title} دون انقطاع."
                    } else {
                        "اشترك للوصول الكامل إلى دروس ${course.title}."
                    }
                },
                accessPeriodLabel = "مدة الاشتراك",
                price = price,
                isRenewal = isRenewal,
            ),
        )
    }

    override suspend fun getPaymentMethods(): AppResult<List<PaymentMethod>> =
        AppResult.Success(DIRECT_METHODS)

    override suspend fun submitPayment(request: PaymentRequest): AppResult<PendingPayment> {
        val numericCourseId = request.courseId.toPositiveIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val method = DIRECT_METHODS.firstOrNull { it.id == request.methodId }?.id
            ?: return AppResult.Failure(AppError.NotFound)
        val existing = _pendingPayment.value
        if (
            existing != null &&
            existing.courseId == request.courseId &&
            existing.methodName == request.methodName &&
            existing.status == PaymentStatus.Pending
        ) {
            return AppResult.Success(existing)
        }
        return when (
            val response = authorizedRequest {
                api.subscribeCourse(it, SubscribeCourseRequestDto(courseId = numericCourseId, method = method))
            }
        ) {
            is ApiCallResult.Success -> {
                if (!response.value.ok) {
                    return AppResult.Failure(AppError.Domain("payment_request_rejected"))
                }
                val unlocked = response.value.unlocked
                val pending = PendingPayment(
                    referenceId = response.value.reference,
                    courseId = request.courseId,
                    courseTitle = request.courseTitle,
                    amount = request.amount,
                    methodName = request.methodName,
                    status = if (unlocked) PaymentStatus.Verified else PaymentStatus.Pending,
                    submittedAtLabel = "الآن",
                    teacherName = request.teacherName,
                )
                _pendingPayment.value = pending
                AppResult.Success(pending)
            }
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getPurchaseAccess(courseId: String): AppResult<PurchaseAccess?> {
        val course = when (val catalog = catalogCourse(courseId)) {
            is AppResult.Success -> catalog.data
            is AppResult.Failure -> return catalog
        }
        val sessionPayment = _pendingPayment.value?.takeIf { it.courseId == courseId }
        if (sessionPayment != null) {
            val verified = sessionPayment.status == PaymentStatus.Verified || course?.unlocked == true
            val payment = sessionPayment.copy(
                status = if (verified) PaymentStatus.Verified else sessionPayment.status,
                teacherName = sessionPayment.teacherName ?: course?.teacherName,
            )
            return AppResult.Success(
                PurchaseAccess(
                    payment = payment,
                    isActivated = course?.unlocked == true,
                    confirmedThisSession = sessionPayment.status == PaymentStatus.Verified,
                ),
            )
        }
        if (course?.unlocked == true) {
            return AppResult.Success(
                PurchaseAccess(
                    payment = course.toVerifiedPayment(),
                    isActivated = true,
                    confirmedThisSession = false,
                ),
            )
        }
        return AppResult.Success(null)
    }

    override suspend fun activateAccess(courseId: String): AppResult<Unit> {
        val access = when (val result = getPurchaseAccess(courseId)) {
            is AppResult.Success -> result.data
            is AppResult.Failure -> return result
        }
        return if (access?.isActivated == true || access?.payment?.status == PaymentStatus.Verified) {
            AppResult.Success(Unit)
        } else {
            AppResult.Failure(AppError.Domain("access_not_active"))
        }
    }

    private suspend fun catalogCourse(courseId: String): AppResult<SubscriptionCourseDto?> =
        when (val response = authorizedRequest(api::subscriptionsCatalog)) {
            is ApiCallResult.Success -> AppResult.Success(
                response.value.courses.firstOrNull { it.id.toString() == courseId },
            )
            else -> AppResult.Failure(handleFailure(response))
        }

    private suspend fun <T> authorizedRequest(
        call: suspend (String) -> ApiCallResult<T>,
    ): ApiCallResult<T> {
        val stored = tokenStore.read() ?: return ApiCallResult.HttpFailure(401)
        val first = call(stored.accessToken)
        if (first !is ApiCallResult.HttpFailure || first.statusCode != 401) return first
        return when (val refreshed = refreshCoordinator.refreshAfterUnauthorized(stored.accessToken)) {
            is AppResult.Success -> call(refreshed.data.accessToken)
            is AppResult.Failure -> ApiCallResult.HttpFailure(401)
        }
    }

    private suspend fun handleFailure(response: ApiCallResult<*>): AppError {
        val error = when (response) {
            ApiCallResult.NetworkFailure -> AppError.Network
            ApiCallResult.InvalidResponse -> AppError.Unknown
            is ApiCallResult.Success -> AppError.Unknown
            is ApiCallResult.HttpFailure -> when (response.statusCode) {
                401 -> AppError.SessionExpired
                403 -> AppError.Forbidden
                404, 410 -> AppError.NotFound
                422 -> AppError.Validation(response.fieldErrors)
                in 500..599 -> AppError.Server
                else -> AppError.Domain(response.detail ?: "payment_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }

    private companion object {
        val DIRECT_METHODS = listOf(
            PaymentMethod(
                id = "card",
                name = "بطاقة",
                instruction = "معرّف دفع تجريبي (card). لا تتم معالجة بطاقة خارجية.",
            ),
            PaymentMethod(
                id = "transfer",
                name = "حوالة",
                instruction = "معرّف دفع تجريبي (transfer). لا تتم معالجة حوالة خارجية.",
            ),
            PaymentMethod(
                id = "wallet",
                name = "محفظة",
                instruction = "معرّف دفع تجريبي (wallet). لا تتم معالجة محفظة خارجية.",
            ),
            PaymentMethod(
                id = "cash",
                name = "نقداً",
                instruction = "معرّف دفع تجريبي (cash). يُسجَّل كطريقة دفع في وضع التطوير.",
            ),
        )
    }
}

private fun SubscriptionCourseDto.toVerifiedPayment() = PendingPayment(
    referenceId = "",
    courseId = id.toString(),
    courseTitle = title,
    amount = Money(price.toInt(), currency.ifBlank { "SYP" }),
    methodName = "",
    status = PaymentStatus.Verified,
    submittedAtLabel = "",
    teacherName = teacherName,
)

private fun String.toPositiveIntOrNull(): Int? = toIntOrNull()?.takeIf { it > 0 }
