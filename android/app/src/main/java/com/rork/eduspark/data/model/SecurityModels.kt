package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-24 · Settings — Security.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit: the platform's only second factor is email OTP — [SecuritySettings] has no
 * TOTP/authenticator-app concept, and enabling it reuses the exact same deterministic mock
 * code every A-08/A-09 email-OTP flow already accepts (see [com.rork.eduspark.data.repository.mock.MockSecurityRepository]'s
 * own doc comment). This is deliberately independent of [com.rork.eduspark.data.repository.AuthRepository.verifyTwoFactor],
 * which verifies a *login attempt*, not an account setting.
 */
data class SecuritySettings(
    val twoFactorEnabled: Boolean,
)

/** ST-24. One signed-in device/browser. [isCurrentDevice] sessions never offer a revoke action of their own. */
data class ActiveSession(
    val id: String,
    val deviceLabel: String,
    val isCurrentDevice: Boolean,
    val lastSeenLabel: String,
)
