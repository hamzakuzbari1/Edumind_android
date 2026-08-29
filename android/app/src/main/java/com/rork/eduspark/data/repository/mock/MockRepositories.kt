package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.data.model.LearningPath
import com.rork.eduspark.data.model.LearningStep
import com.rork.eduspark.data.model.LessonStatus
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.SignInOutcome
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ISOLATED MOCK REPOSITORIES — development only.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * These exist so screens can be built and reviewed before the FastAPI client is wired.
 * They are intentionally quarantined in this package so that deleting the package is a
 * complete removal — no mock data leaks into models, ViewModels or composables.
 *
 * They deliberately reproduce the platform's *real* behaviours rather than a happy path:
 *  • latency you can feel (the AI tutor genuinely takes 5–30s and does not stream),
 *  • the branching login outcomes (unverified email, email-OTP 2FA),
 *  • failure cases, so error and offline states are exercised during development.
 *
 * They do NOT invent endpoints, field names or response envelopes.
 */

/** Deterministic latencies so the four states are visible while building screens. */
private object MockLatency {
    const val FAST_MS = 400L
    const val LIST_MS = 700L
}

class MockAuthRepository(
    private val tokenStore: SecureTokenStore,
) : AuthRepository {

    private val _session = MutableStateFlow<SessionUser?>(null)
    override val session: Flow<SessionUser?> = _session.asStateFlow()

    /**
     * Fixture accounts. The local part of the address selects the outcome, so every
     * branch of A-04 Login can be walked by hand on a device without a backend:
     *   student@… / teacher@… / parent@…  → straight in
     *   unverified@…                      → A-08 Verify Email
     *   twofactor@…                       → A-09 Two-Factor Verify
     *   locked@…                          → forbidden
     *   offline@…                         → offline error
     */
    override suspend fun signIn(email: String, password: String): AppResult<SignInOutcome> {
        delay(MockLatency.FAST_MS)

        if (password.isBlank()) {
            return AppResult.Failure(AppError.Validation(mapOf("password" to "required")))
        }

        val local = email.substringBefore('@').lowercase()
        return when {
            local.startsWith("offline") -> AppResult.Failure(AppError.Offline)
            local.startsWith("locked") -> AppResult.Failure(AppError.Forbidden)
            local.startsWith("unverified") ->
                AppResult.Success(SignInOutcome.EmailVerificationRequired(email))

            local.startsWith("twofactor") ->
                AppResult.Success(SignInOutcome.TwoFactorRequired(email))

            password.length < 6 ->
                AppResult.Failure(AppError.Domain("invalid_credentials"))

            else -> {
                val user = fixtureUser(email, roleFor(local))
                persist(user)
                AppResult.Success(SignInOutcome.Authenticated(user))
            }
        }
    }

    override suspend fun register(
        name: String,
        email: String,
        password: String,
        role: UserRole,
    ): AppResult<SessionUser> {
        delay(MockLatency.FAST_MS)
        if (email.contains("taken")) {
            return AppResult.Failure(AppError.Validation(mapOf("email" to "already_registered")))
        }
        val user = fixtureUser(email, role).copy(
            displayName = name,
            isEmailVerified = false,
            hasCompletedOnboarding = false,
        )
        persist(user)
        return AppResult.Success(user)
    }

    override suspend fun verifyEmail(code: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        if (code != VALID_CODE) return AppResult.Failure(AppError.Domain("invalid_code"))
        _session.value = _session.value?.copy(isEmailVerified = true)
        return AppResult.Success(Unit)
    }

    override suspend fun resendEmailCode(): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(Unit)
    }

    override suspend fun verifyTwoFactor(code: String, trustDevice: Boolean): AppResult<SessionUser> {
        delay(MockLatency.FAST_MS)
        if (code != VALID_CODE) return AppResult.Failure(AppError.Domain("invalid_code"))
        val user = fixtureUser("student@edumind.sy", UserRole.Student)
        persist(user)
        return AppResult.Success(user)
    }

    override suspend fun requestPasswordReset(email: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(Unit)
    }

    override suspend fun resetPassword(token: String, newPassword: String): AppResult<Unit> {
        delay(MockLatency.FAST_MS)
        if (token.isBlank()) return AppResult.Failure(AppError.Domain("expired_link"))
        return AppResult.Success(Unit)
    }

    override suspend fun signOut() {
        tokenStore.clear()
        _session.value = null
    }

    private suspend fun persist(user: SessionUser) {
        tokenStore.write(
            StoredSession(
                accessToken = "mock-access-token",
                sessionId = "mock-session",
                userId = user.id,
            )
        )
        _session.value = user
    }

    private fun roleFor(localPart: String): UserRole = when {
        localPart.startsWith("teacher") -> UserRole.Teacher
        localPart.startsWith("parent") -> UserRole.Parent
        else -> UserRole.Student
    }

    private fun fixtureUser(email: String, role: UserRole) = SessionUser(
        id = "mock-${role.name.lowercase()}",
        displayName = email.substringBefore('@'),
        email = email,
        role = role,
        isEmailVerified = true,
        requiresTwoFactor = false,
        hasCompletedOnboarding = true,
    )

    private companion object {
        const val VALID_CODE = "123456"
    }
}

/**
 * Learning fixtures used to exercise the Progress Spine while screens are being built.
 * Titles are intentionally mixed-direction ("درس Python الأول") to keep bidirectional
 * text shaping honest during development.
 */
class MockLearningRepository : LearningRepository {

    override suspend fun getPath(pathId: String): AppResult<LearningPath> {
        delay(MockLatency.LIST_MS)
        return AppResult.Success(
            LearningPath(
                id = pathId,
                title = "الرياضيات — البكالوريا",
                subtitle = "الوحدة الثانية",
                progress = 0.45f,
                steps = listOf(
                    step("1", "المتتاليات العددية", "18 دقيقة", LessonStatus.Processed, completed = true),
                    step("2", "النهايات والاتصال", "24 دقيقة", LessonStatus.Processed, completed = true),
                    step("3", "الاشتقاق وتطبيقاته", "31 دقيقة", LessonStatus.Processed, current = true),
                    step("4", "درس Python الأول", "قيد المعالجة", LessonStatus.Processing),
                    step("5", "التكامل", "مقفل", LessonStatus.LockedByEntitlement),
                ),
            )
        )
    }

    override suspend fun getGamification(): AppResult<GamificationSnapshot> {
        delay(MockLatency.FAST_MS)
        return AppResult.Success(
            GamificationSnapshot(level = 7, xp = 1240, progressToNextLevel = 0.62f, streakDays = 11)
        )
    }

    private fun step(
        id: String,
        title: String,
        subtitle: String,
        status: LessonStatus,
        completed: Boolean = false,
        current: Boolean = false,
    ) = LearningStep(
        id = id,
        title = title,
        subtitle = subtitle,
        status = status,
        isCurrent = current,
        isCompleted = completed,
    )
}
