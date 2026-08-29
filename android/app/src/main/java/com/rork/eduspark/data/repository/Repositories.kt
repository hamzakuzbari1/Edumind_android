package com.rork.eduspark.data.repository

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.data.model.LearningPath
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole
import kotlinx.coroutines.flow.Flow

/**
 * ══════════════════════════════════════════════════════════════════════════
 * REPOSITORY CONTRACTS — the swap point for the real FastAPI client.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Every contract below describes a capability the **existing backend already has**,
 * verified against the Source Audit. Nothing here invents an endpoint, a field name or a
 * response shape; method names describe intent, not routes.
 *
 * Today these are fulfilled by the isolated mock implementations in
 * `data/repository/mock`. When the generated client lands, a `Remote…Repository`
 * implements the same interface, Koin binds it instead, and no ViewModel or composable
 * changes at all.
 *
 * Features with **no backend** (Projects, push, real payments, offline sync endpoints)
 * deliberately have no contract yet. They get one when the backend does — see
 * [FeatureAvailability].
 */

/**
 * Auth — Source Audit §3.
 *
 * Capabilities that exist: register (student|teacher|parent), login, logout (revokes the
 * server session), `/auth/me`, password reset, email verification, email-OTP 2FA.
 *
 * Capability that does NOT exist: **token refresh**. There is no `refresh()` on this
 * interface on purpose. Every consumer must treat expiry as "sign in again".
 */
interface AuthRepository {

    /** Emits the current session, or null when signed out. */
    val session: Flow<SessionUser?>

    suspend fun signIn(email: String, password: String): AppResult<SignInOutcome>

    suspend fun register(
        name: String,
        email: String,
        password: String,
        role: UserRole,
    ): AppResult<SessionUser>

    /** Email verification exists on the backend but is NOT enforced at login. */
    suspend fun verifyEmail(code: String): AppResult<Unit>

    suspend fun resendEmailCode(): AppResult<Unit>

    /** Email OTP only — the platform returns 501 for TOTP. */
    suspend fun verifyTwoFactor(code: String, trustDevice: Boolean): AppResult<SessionUser>

    suspend fun requestPasswordReset(email: String): AppResult<Unit>

    suspend fun resetPassword(token: String, newPassword: String): AppResult<Unit>

    /** Revokes the session server-side and clears local credentials. */
    suspend fun signOut()
}

/** What login can lead to. Mirrors the real branching of A-04. */
sealed interface SignInOutcome {
    data class Authenticated(val user: SessionUser) : SignInOutcome

    /** Backend reports the address is unverified → route to A-08. */
    data class EmailVerificationRequired(val email: String) : SignInOutcome

    /** Backend requires the email OTP second factor → route to A-09. */
    data class TwoFactorRequired(val email: String) : SignInOutcome
}

/**
 * Learning paths — courses and their lessons.
 *
 * Backend equivalents exist (student dashboard, course detail, lesson list) and are
 * marked READY in the Source Audit's mobile reuse map. Students only ever see
 * **processed** lessons on **paid** courses; the entitlement gate is a server decision,
 * never re-implemented on the client.
 */
interface LearningRepository {
    suspend fun getPath(pathId: String): AppResult<LearningPath>
    suspend fun getGamification(): AppResult<GamificationSnapshot>
}

/**
 * Single source of truth for "does this part of the product have a backend yet".
 *
 * Screens read this instead of hard-coding assumptions, so a pending feature can present
 * an honest state rather than a fabricated one, and flipping it on later is one edit.
 */
object FeatureAvailability {
    /** Projects module (PJ-01…PJ-12) — no endpoints, no tables. Mock data only. */
    const val PROJECTS_BACKEND_READY = false

    /** Push notifications — in-app only today; no FCM/APNs registration exists. */
    const val PUSH_BACKEND_READY = false

    /** Real payment rails — only a demo checkout exists. */
    const val PAYMENTS_BACKEND_READY = false

    /** Offline bootstrap/push sync endpoints — planned, not built. */
    const val SYNC_ENDPOINTS_READY = false

    /** Token refresh — no endpoint exists; 401 always means re-login. */
    const val TOKEN_REFRESH_READY = false
}
