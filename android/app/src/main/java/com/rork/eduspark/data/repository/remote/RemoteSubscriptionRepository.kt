package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.AvailableCourse
import com.rork.eduspark.data.model.CourseSubscription
import com.rork.eduspark.data.model.Money
import com.rork.eduspark.data.model.SubscriptionStatus
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.learning.StudentLearningApi
import com.rork.eduspark.data.remote.learning.SubscriptionCourseDto
import com.rork.eduspark.data.remote.learning.SubscriptionsCatalogDto
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.SubscriptionRepository
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

internal class RemoteSubscriptionRepository(
    private val api: StudentLearningApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : SubscriptionRepository {

    override suspend fun getSubscriptions(): AppResult<List<CourseSubscription>> =
        requestCatalog { catalog ->
            catalog.courses.mapNotNull { it.toManagedSubscription() }
        }

    override suspend fun getAvailableCourses(): AppResult<List<AvailableCourse>> =
        requestCatalog { catalog ->
            catalog.courses.mapNotNull { it.toAvailableCourse() }
        }

    private suspend fun <T> requestCatalog(
        map: (SubscriptionsCatalogDto) -> T,
    ): AppResult<T> = when (val response = authorizedRequest(api::subscriptionsCatalog)) {
        is ApiCallResult.Success -> AppResult.Success(map(response.value))
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
                else -> AppError.Domain(response.detail ?: "subscription_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

internal fun SubscriptionCourseDto.toManagedSubscription(): CourseSubscription? {
    val status = subscriptionStatus.toSubscriptionStatus() ?: return null
    return CourseSubscription(
        courseId = id.toString(),
        courseTitle = title,
        teacherName = teacherName,
        status = status,
        expiryDateLabel = expiresAt.toExpiryLabel(),
        daysUntilExpiry = if (status == SubscriptionStatus.Expired) null else daysUntilExpiry,
        includedFeatures = includedFeatures(),
    )
}

internal fun SubscriptionCourseDto.toAvailableCourse(): AvailableCourse? {
    if (unlocked || subscriptionStatus.toSubscriptionStatus() != null) return null
    if (subscriptionStatus == "revoked" || subscriptionStatus == "suspended") return null
    return AvailableCourse(
        courseId = id.toString(),
        courseTitle = title,
        teacherName = teacherName,
        priceLabel = "",
        price = Money(price.toInt(), currency.ifBlank { "SYP" }),
        benefits = subscriptionBenefits.splitBenefits(),
        includedFeatures = includedFeatures(),
    )
}

internal fun SubscriptionCourseDto.toCourseOfferFields(): Triple<Boolean, Money, List<String>> {
    val isRenewal = subscriptionStatus.toSubscriptionStatus()
        .let { it == SubscriptionStatus.ExpiringSoon || it == SubscriptionStatus.Expired }
    return Triple(
        isRenewal,
        Money(price.toInt(), currency.ifBlank { "SYP" }),
        includedFeatures(),
    )
}

private fun String.toSubscriptionStatus(): SubscriptionStatus? = when (this) {
    "active" -> SubscriptionStatus.Active
    "expiring_soon" -> SubscriptionStatus.ExpiringSoon
    "expired" -> SubscriptionStatus.Expired
    else -> null
}

private fun SubscriptionCourseDto.includedFeatures(): List<String> = buildList {
    addAll(subscriptionBenefits.splitBenefits())
    if (isEmpty()) {
        if (videoCount > 0) add("دروس")
        if (pdfCount > 0) add("ملفات")
        if (homeworkCount > 0) add("واجبات")
        if (aiLessonCount > 0) add("معلّم ذكي")
    }
}

private fun String.splitBenefits(): List<String> =
    split('،', ',', '•', '\n')
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .take(4)

private fun String?.toExpiryLabel(): String? {
    val raw = this?.trim().orEmpty()
    if (raw.isEmpty()) return null
    val parsed = runCatching { OffsetDateTime.parse(raw) }.getOrNull() ?: return raw.take(10)
    return parsed.format(DateTimeFormatter.ofPattern("d MMM yyyy", Locale("ar")))
}
