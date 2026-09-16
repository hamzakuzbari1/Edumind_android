package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.AvailableCourse
import com.rork.eduspark.data.model.CourseSubscription
import com.rork.eduspark.data.model.Money
import com.rork.eduspark.data.model.PaymentMethod
import com.rork.eduspark.data.model.PaymentRequest
import com.rork.eduspark.data.model.PaymentStatus
import com.rork.eduspark.data.model.PendingPayment
import com.rork.eduspark.data.model.PurchaseAccess
import com.rork.eduspark.data.model.SubscriptionStatus
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.auth.AuthApi
import com.rork.eduspark.data.remote.auth.ForgotPasswordRequestDto
import com.rork.eduspark.data.remote.auth.LoginRequestDto
import com.rork.eduspark.data.remote.auth.LoginResponseDto
import com.rork.eduspark.data.remote.auth.LogoutRequestDto
import com.rork.eduspark.data.remote.auth.OkResponseDto
import com.rork.eduspark.data.remote.auth.RefreshTokenRequestDto
import com.rork.eduspark.data.remote.auth.RegisterRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorRequestDto
import com.rork.eduspark.data.remote.auth.ResendTwoFactorResponseDto
import com.rork.eduspark.data.remote.auth.ResetPasswordRequestDto
import com.rork.eduspark.data.remote.auth.TokenResponseDto
import com.rork.eduspark.data.remote.auth.UserDto
import com.rork.eduspark.data.remote.auth.VerifyEmailRequestDto
import com.rork.eduspark.data.remote.auth.VerifyTwoFactorRequestDto
import com.rork.eduspark.data.remote.learning.LessonProgressUpdateDto
import com.rork.eduspark.data.remote.learning.StudentLearningApi
import com.rork.eduspark.data.remote.learning.SubscribeCourseOutDto
import com.rork.eduspark.data.remote.learning.SubscribeCourseRequestDto
import com.rork.eduspark.data.remote.learning.SubscriptionCourseDto
import com.rork.eduspark.data.remote.learning.SubscriptionsCatalogDto
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs

class RemoteSubscriptionRepositoryTest {
    @Test
    fun catalogMapsNumericCourseIdsAndSplitsActiveFromAvailable() = runBlocking {
        val fixture = fixture(
            catalog = catalog(
                course(id = 12, title = "الرياضيات", status = "active", unlocked = true, days = 40),
                course(id = 15, title = "الفيزياء", status = "expiring_soon", unlocked = true, days = 5),
                course(id = 18, title = "الكيمياء", status = "pending", unlocked = false, price = 25_000f),
            ),
        )

        val subscriptions = assertIs<AppResult.Success<List<CourseSubscription>>>(
            fixture.subscriptions.getSubscriptions(),
        ).data
        val available = assertIs<AppResult.Success<List<AvailableCourse>>>(
            fixture.subscriptions.getAvailableCourses(),
        ).data

        assertEquals(listOf("12", "15"), subscriptions.map { it.courseId })
        assertEquals(SubscriptionStatus.Active, subscriptions[0].status)
        assertEquals(SubscriptionStatus.ExpiringSoon, subscriptions[1].status)
        assertEquals("18", available.single().courseId)
        assertEquals(Money(25_000, "SYP"), available.single().price)

        val methods = assertIs<AppResult.Success<List<PaymentMethod>>>(
            fixture.payments.getPaymentMethods(),
        ).data
        assertEquals(listOf("card", "transfer", "wallet", "cash"), methods.map { it.id })
    }

    @Test
    fun mockStyleStringIdsAreRejectedBeforeSubscribe() = runBlocking {
        val fixture = fixture()
        val result = fixture.payments.submitPayment(
            PaymentRequest(
                courseId = "math",
                courseTitle = "الرياضيات",
                amount = Money(1, "SYP"),
                methodId = "cash",
                methodName = "نقداً",
            ),
        )
        assertIs<AppResult.Failure>(result)
        assertEquals(AppError.Domain("invalid_course_id"), result.error)
    }

    @Test
    fun cashSubscribePersistsRemoteReferenceAndUnlocksFromBackend() = runBlocking {
        val fixture = fixture(
            catalog = catalog(course(id = 15, title = "الفيزياء", status = "expiring_soon", unlocked = true, days = 4)),
            subscribe = ApiCallResult.Success(
                SubscribeCourseOutDto(ok = true, courseId = 15, reference = "SUB-ABC123", unlocked = true),
            ),
        )

        val pending = assertIs<AppResult.Success<PendingPayment>>(
            fixture.payments.submitPayment(
                PaymentRequest(
                    courseId = "15",
                    courseTitle = "الفيزياء",
                    amount = Money(20_000, "SYP"),
                    methodId = "cash",
                    methodName = "نقداً",
                ),
            ),
        ).data

        assertEquals("SUB-ABC123", pending.referenceId)
        assertEquals(PaymentStatus.Verified, pending.status)
        assertEquals(15, fixture.learning.lastSubscribe?.courseId)
        assertEquals("cash", fixture.learning.lastSubscribe?.method)

        val access = assertIs<AppResult.Success<PurchaseAccess?>>(
            fixture.payments.getPurchaseAccess("15"),
        ).data
        requireNotNull(access)
        assertEquals(PaymentStatus.Verified, access.payment.status)
        assertEquals(true, access.isActivated)
        assertEquals(true, access.confirmedThisSession)
        assertEquals(null, fixture.payments.verifiedUnactivatedPayment.first())
        assertEquals(1, fixture.learning.subscribeCallCount)

        val activation = fixture.payments.activateAccess("15")
        assertIs<AppResult.Success<Unit>>(activation)
        assertEquals(1, fixture.learning.subscribeCallCount)
    }

    @Test
    fun genuinePendingDoesNotAutoSucceed() = runBlocking {
        val fixture = fixture(
            catalog = catalog(course(id = 18, title = "الكيمياء", status = "pending", unlocked = false, price = 25_000f)),
            subscribe = ApiCallResult.Success(
                SubscribeCourseOutDto(ok = true, courseId = 18, reference = "SUB-PENDING", unlocked = false),
            ),
        )

        val pending = assertIs<AppResult.Success<PendingPayment>>(
            fixture.payments.submitPayment(cashRequest("18", "الكيمياء")),
        ).data
        assertEquals(PaymentStatus.Pending, pending.status)

        val access = assertIs<AppResult.Success<PurchaseAccess?>>(
            fixture.payments.getPurchaseAccess("18"),
        ).data
        requireNotNull(access)
        assertEquals(PaymentStatus.Pending, access.payment.status)
        assertEquals(false, access.isActivated)
        assertEquals(false, access.confirmedThisSession)
    }

    @Test
    fun failedSubscribeRemainsRetryable() = runBlocking {
        val fixture = fixture(
            catalog = catalog(course(id = 18, title = "الكيمياء", status = "pending", unlocked = false)),
            subscribe = ApiCallResult.HttpFailure(500),
        )

        val first = fixture.payments.submitPayment(cashRequest("18", "الكيمياء"))
        assertIs<AppResult.Failure>(first)
        assertEquals(AppError.Server, first.error)
        assertEquals(1, fixture.learning.subscribeCallCount)

        fixture.learning.subscribe = ApiCallResult.Success(
            SubscribeCourseOutDto(ok = true, courseId = 18, reference = "SUB-RETRY", unlocked = true),
        )
        val second = assertIs<AppResult.Success<PendingPayment>>(
            fixture.payments.submitPayment(cashRequest("18", "الكيمياء")),
        ).data
        assertEquals(PaymentStatus.Verified, second.status)
        assertEquals(2, fixture.learning.subscribeCallCount)
    }

    @Test
    fun activateAccessNeverCallsSubscribe() = runBlocking {
        val fixture = fixture(
            catalog = catalog(course(id = 12, title = "الرياضيات", status = "active", unlocked = true, days = 40)),
        )
        val before = fixture.learning.subscribeCallCount
        val result = fixture.payments.activateAccess("12")
        assertIs<AppResult.Success<Unit>>(result)
        assertEquals(before, fixture.learning.subscribeCallCount)
    }

    @Test
    fun reloadUsesBackendCatalogInsteadOfSessionMemory() = runBlocking {
        val unlockedCatalog = catalog(
            course(id = 18, title = "الكيمياء", status = "active", unlocked = true, days = 90, price = 25_000f),
        )
        val fixture = fixture(catalog = unlockedCatalog)

        val access = assertIs<AppResult.Success<PurchaseAccess?>>(
            fixture.payments.getPurchaseAccess("18"),
        ).data
        requireNotNull(access)
        assertEquals(PaymentStatus.Verified, access.payment.status)
        assertEquals(true, access.isActivated)
        assertEquals(false, access.confirmedThisSession)
        assertEquals("18", access.payment.courseId)
        assertEquals(0, fixture.learning.subscribeCallCount)
        assertEquals(null, fixture.payments.verifiedUnactivatedPayment.first())
    }

    @Test
    fun renewalAfterVerifiedCallsSubscribeAgain() = runBlocking {
        val fixture = fixture(
            catalog = catalog(course(id = 15, title = "الفيزياء", status = "expiring_soon", unlocked = true, days = 4)),
            subscribe = ApiCallResult.Success(
                SubscribeCourseOutDto(ok = true, courseId = 15, reference = "SUB-RENEW", unlocked = true),
            ),
        )
        assertIs<AppResult.Success<PendingPayment>>(
            fixture.payments.submitPayment(cashRequest("15", "الفيزياء")),
        )
        assertEquals(1, fixture.learning.subscribeCallCount)

        val renewed = assertIs<AppResult.Success<PendingPayment>>(
            fixture.payments.submitPayment(cashRequest("15", "الفيزياء")),
        ).data
        assertEquals(PaymentStatus.Verified, renewed.status)
        assertEquals(2, fixture.learning.subscribeCallCount)

        val subscriptions = assertIs<AppResult.Success<List<CourseSubscription>>>(
            fixture.subscriptions.getSubscriptions(),
        ).data
        assertEquals(SubscriptionStatus.Active, subscriptions.single { it.courseId == "15" }.status)
        assertEquals(90, subscriptions.single { it.courseId == "15" }.daysUntilExpiry)
    }

    @Test
    fun pendingSubmitIsIdempotentPerCourse() = runBlocking {
        val fixture = fixture(
            catalog = catalog(course(id = 18, title = "الكيمياء", status = "pending", unlocked = false)),
            subscribe = ApiCallResult.Success(
                SubscribeCourseOutDto(ok = true, courseId = 18, reference = "SUB-ONCE", unlocked = false),
            ),
        )
        val first = assertIs<AppResult.Success<PendingPayment>>(
            fixture.payments.submitPayment(cashRequest("18", "الكيمياء")),
        ).data
        val second = assertIs<AppResult.Success<PendingPayment>>(
            fixture.payments.submitPayment(cashRequest("18", "الكيمياء")),
        ).data
        assertEquals("SUB-ONCE", first.referenceId)
        assertEquals(first.referenceId, second.referenceId)
        assertEquals(1, fixture.learning.subscribeCallCount)
    }

    @Test
    fun remoteVoucherRejectsMockCodesAndStringCourseIds() = runBlocking {
        val vouchers = UnavailableVoucherRepository()
        assertEquals(false, vouchers.isAvailable)
        val validate = vouchers.validateVoucher("EDU-VALID-001")
        assertIs<AppResult.Failure>(validate)
        assertEquals(AppError.Domain("voucher_unavailable"), validate.error)
        val redeem = vouchers.redeemVoucher("EDU-VALID-001")
        assertIs<AppResult.Failure>(redeem)
        assertEquals(AppError.Domain("voucher_unavailable"), redeem.error)
    }
}

private fun cashRequest(courseId: String, title: String) = PaymentRequest(
    courseId = courseId,
    courseTitle = title,
    amount = Money(20_000, "SYP"),
    methodId = "cash",
    methodName = "نقداً",
    teacherName = "المعلم",
)

private suspend fun fixture(
    catalog: SubscriptionsCatalogDto = catalog(),
    subscribe: ApiCallResult<SubscribeCourseOutDto> = ApiCallResult.InvalidResponse,
): SubscriptionFixture {
    val auth = FakeSubscriptionAuthApi()
    val store = InMemoryTokenStore().apply {
        write(StoredSession("access", "refresh", 7, "42"))
    }
    val authRepository = RemoteAuthRepository(auth, store, AuthRefreshCoordinator(auth, store))
    val api = FakeStudentLearningApi(catalog = catalog, subscribe = subscribe)
    return SubscriptionFixture(
        learning = api,
        subscriptions = RemoteSubscriptionRepository(
            api = api,
            tokenStore = store,
            refreshCoordinator = AuthRefreshCoordinator(auth, store),
            authRepository = authRepository,
        ),
        payments = RemotePaymentRepository(
            api = api,
            tokenStore = store,
            refreshCoordinator = AuthRefreshCoordinator(auth, store),
            authRepository = authRepository,
        ),
    )
}

private data class SubscriptionFixture(
    val learning: FakeStudentLearningApi,
    val subscriptions: RemoteSubscriptionRepository,
    val payments: RemotePaymentRepository,
)

private fun catalog(vararg courses: SubscriptionCourseDto) = SubscriptionsCatalogDto(
    grade = 12,
    courses = courses.toList(),
    unlockedCount = courses.count { it.unlocked },
    availableCount = courses.size,
)

private fun course(
    id: Int,
    title: String,
    status: String,
    unlocked: Boolean,
    days: Int? = null,
    price: Float = 20_000f,
) = SubscriptionCourseDto(
    id = id,
    title = title,
    subjectName = title,
    teacherName = "المعلم",
    grade = 12,
    price = price,
    currency = "SYP",
    unlocked = unlocked,
    subscriptionStatus = status,
    daysUntilExpiry = days,
    subscriptionBenefits = "دروس، ملفات",
)

private class FakeStudentLearningApi(
    var catalog: SubscriptionsCatalogDto,
    var subscribe: ApiCallResult<SubscribeCourseOutDto>,
) : StudentLearningApi {
    var lastSubscribe: SubscribeCourseRequestDto? = null
    var subscribeCallCount: Int = 0

    override suspend fun dashboard(accessToken: String) = ApiCallResult.InvalidResponse
    override suspend fun course(accessToken: String, courseId: Int) = ApiCallResult.InvalidResponse
    override suspend fun units(accessToken: String, courseId: Int) = ApiCallResult.InvalidResponse
    override suspend fun resume(accessToken: String, courseId: Int) = ApiCallResult.InvalidResponse
    override suspend fun lesson(accessToken: String, lessonId: Int) = ApiCallResult.InvalidResponse
    override suspend fun lessonProgress(accessToken: String, lessonId: Int) = ApiCallResult.InvalidResponse
    override suspend fun updateLessonProgress(
        accessToken: String,
        lessonId: Int,
        body: LessonProgressUpdateDto,
    ) = ApiCallResult.InvalidResponse
    override suspend fun verifyCompletion(accessToken: String, lessonId: Int) = ApiCallResult.InvalidResponse
    override suspend fun subscriptionsCatalog(accessToken: String) = ApiCallResult.Success(catalog)
    override suspend fun subscribeCourse(
        accessToken: String,
        body: SubscribeCourseRequestDto,
    ): ApiCallResult<SubscribeCourseOutDto> {
        subscribeCallCount++
        lastSubscribe = body
        val result = subscribe
        if (result is ApiCallResult.Success && result.value.unlocked) {
            catalog = catalog.copy(
                courses = catalog.courses.map { course ->
                    if (course.id == body.courseId) {
                        course.copy(unlocked = true, subscriptionStatus = "active", daysUntilExpiry = 90)
                    } else {
                        course
                    }
                },
            )
        }
        return result
    }
}

private class FakeSubscriptionAuthApi : AuthApi {
    override suspend fun refresh(body: RefreshTokenRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun register(body: RegisterRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun login(body: LoginRequestDto): ApiCallResult<LoginResponseDto> =
        ApiCallResult.InvalidResponse
    override suspend fun me(accessToken: String): ApiCallResult<UserDto> = ApiCallResult.InvalidResponse
    override suspend fun logout(accessToken: String, body: LogoutRequestDto) =
        ApiCallResult.Success(OkResponseDto())
    override suspend fun verifyTwoFactor(body: VerifyTwoFactorRequestDto) = ApiCallResult.InvalidResponse
    override suspend fun resendTwoFactor(
        body: ResendTwoFactorRequestDto,
    ): ApiCallResult<ResendTwoFactorResponseDto> = ApiCallResult.InvalidResponse
    override suspend fun verifyEmail(body: VerifyEmailRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun resendVerification(accessToken: String) = ApiCallResult.Success(OkResponseDto())
    override suspend fun forgotPassword(body: ForgotPasswordRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun resetPassword(body: ResetPasswordRequestDto) = ApiCallResult.Success(OkResponseDto())
    override suspend fun completeStudentOnboarding(accessToken: String) = ApiCallResult.Success(OkResponseDto())
    override suspend fun completeTeacherSetup(accessToken: String) = ApiCallResult.Success(OkResponseDto())
}
