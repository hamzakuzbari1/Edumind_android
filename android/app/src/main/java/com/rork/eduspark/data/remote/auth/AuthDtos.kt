package com.rork.eduspark.data.remote.auth

import com.rork.eduspark.core.session.StoredSession
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class RegisterRequestDto(
    val name: String,
    val email: String,
    val password: String,
    val role: String,
    @SerialName("device_name") val deviceName: String? = null,
)

@Serializable
data class LoginRequestDto(
    val email: String,
    val password: String,
    @SerialName("viewer_mode") val viewerMode: String? = null,
    @SerialName("device_name") val deviceName: String? = null,
)

@Serializable
data class RefreshTokenRequestDto(
    @SerialName("refresh_token") val refreshToken: String,
)

@Serializable
data class LogoutRequestDto(
    @SerialName("refresh_token") val refreshToken: String? = null,
)

@Serializable
data class VerifyTwoFactorRequestDto(
    @SerialName("challenge_token") val challengeToken: String,
    val code: String,
)

@Serializable
data class ResendTwoFactorRequestDto(
    @SerialName("challenge_token") val challengeToken: String,
)

@Serializable
data class VerifyEmailRequestDto(val token: String)

@Serializable
data class ForgotPasswordRequestDto(val email: String)

@Serializable
data class ResetPasswordRequestDto(
    val token: String,
    @SerialName("new_password") val newPassword: String,
    @SerialName("confirm_password") val confirmPassword: String,
)

@Serializable
data class UserDto(
    val id: Int,
    val name: String,
    val email: String,
    val role: String,
    @SerialName("email_verified") val emailVerified: Boolean = false,
    @SerialName("onboarding_complete") val onboardingComplete: Boolean = false,
    @SerialName("teacher_setup_complete") val teacherSetupComplete: Boolean = false,
    @SerialName("onboarding_step") val onboardingStep: String? = null,
    val grade: Int? = null,
)

@Serializable
data class TokenResponseDto(
    @SerialName("access_token") val accessToken: String,
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("session_id") val sessionId: Int? = null,
    @SerialName("token_type") val tokenType: String = "bearer",
    val user: UserDto,
)

@Serializable
data class LoginResponseDto(
    @SerialName("requires_2fa") val requiresTwoFactor: Boolean = false,
    @SerialName("access_token") val accessToken: String? = null,
    @SerialName("refresh_token") val refreshToken: String? = null,
    @SerialName("session_id") val sessionId: Int? = null,
    @SerialName("token_type") val tokenType: String = "bearer",
    val user: UserDto? = null,
    @SerialName("challenge_token") val challengeToken: String? = null,
    @SerialName("expires_in_seconds") val expiresInSeconds: Int? = null,
    @SerialName("masked_email") val maskedEmail: String? = null,
    @SerialName("resend_available_in_seconds") val resendAvailableInSeconds: Int? = null,
)

@Serializable
data class ResendTwoFactorResponseDto(
    val ok: Boolean = true,
    @SerialName("expires_in_seconds") val expiresInSeconds: Int? = null,
    @SerialName("resend_available_in_seconds") val resendAvailableInSeconds: Int? = null,
)

@Serializable
data class OkResponseDto(val ok: Boolean = true)

internal fun UserDto.toDomain(): SessionUser {
    val mappedRole = when (role.lowercase()) {
        "student" -> UserRole.Student
        "teacher" -> UserRole.Teacher
        "parent" -> UserRole.Parent
        else -> throw UnknownRoleException(role)
    }
    val setupComplete = when (mappedRole) {
        UserRole.Student -> onboardingComplete
        UserRole.Teacher -> teacherSetupComplete
        UserRole.Parent -> true
    }
    return SessionUser(
        id = id.toString(),
        displayName = name,
        email = email,
        role = mappedRole,
        isEmailVerified = emailVerified,
        requiresTwoFactor = false,
        hasCompletedOnboarding = setupComplete,
        onboardingStep = if (mappedRole == UserRole.Student) onboardingStep.toOnboardingStep() else null,
        grade = if (mappedRole == UserRole.Student) grade else null,
    )
}

private fun String?.toOnboardingStep(): com.rork.eduspark.data.model.StudentOnboardingStep? =
    when (this?.lowercase()) {
        "grade" -> com.rork.eduspark.data.model.StudentOnboardingStep.Grade
        "subjects" -> com.rork.eduspark.data.model.StudentOnboardingStep.Subjects
        "teachers" -> com.rork.eduspark.data.model.StudentOnboardingStep.Teachers
        "complete" -> com.rork.eduspark.data.model.StudentOnboardingStep.Complete
        else -> null
    }

internal fun TokenResponseDto.toStoredSession(): StoredSession = StoredSession(
    accessToken = accessToken,
    refreshToken = requireNotNull(refreshToken),
    sessionId = requireNotNull(sessionId),
    userId = user.id.toString(),
)

internal fun LoginResponseDto.toTokenResponse(): TokenResponseDto = TokenResponseDto(
    accessToken = requireNotNull(accessToken),
    refreshToken = requireNotNull(refreshToken),
    sessionId = requireNotNull(sessionId),
    tokenType = tokenType,
    user = requireNotNull(user),
)

internal class UnknownRoleException(role: String) :
    IllegalArgumentException("Unsupported backend role: $role")
