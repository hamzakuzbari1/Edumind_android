package com.rork.eduspark.ui.screens.auth

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.isolateBidi
import com.rork.eduspark.core.format.maskEmail
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.OtpInput
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-09 · Two-Factor Verify
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deliberately unmistakable next to A-08: a full-bleed Basalt security band (always dark,
 * regardless of the app's own light/dark theme — that constancy is what makes it read as a
 * distinct security surface rather than a themed screen) replaces the centred envelope tile,
 * the header is start-aligned instead of centred, and the destination is a **masked email
 * address**.
 *
 * That last point is a deliberate correction from the PDF's masked-phone mockup: the
 * verified backend's second factor is email OTP (Source Audit §3), not SMS. Building toward
 * a phone number here would be inventing a channel the platform does not have.
 */
@Composable
fun TwoFactorScreen(
    email: String,
    onBack: () -> Unit,
    onAuthenticated: (SessionUser) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TwoFactorViewModel = koinViewModel(parameters = { parametersOf(email) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val focusManager = LocalFocusManager.current

    BackHandler { onBack() }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TwoFactorEvent.Verified -> onAuthenticated(event.user)
            }
        }
    }

    val fieldsEnabled = state.phase != TwoFactorPhase.Verifying && state.phase != TwoFactorPhase.Success
    val isError = state.phase is TwoFactorPhase.Invalid

    AuthScaffold(
        modifier = modifier,
        headerBand = { SecurityBand(onBack = onBack) },
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .verticalScroll(rememberScrollState()),
        ) {
            Spacer(modifier = Modifier.height(Spacing.section))

            Text(
                text = stringResource(R.string.a09_title),
                style = EduTheme.typography.titleLg,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                text = stringResource(R.string.a09_body, maskEmail(email).isolateBidi()),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textMuted,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xxs),
            )

            Spacer(modifier = Modifier.height(Spacing.section))

            OtpInput(
                value = state.code,
                onValueChange = viewModel::onCodeChange,
                contentDescription = stringResource(R.string.a11y_a09_otp),
                isError = isError,
                enabled = fieldsEnabled,
            )

            TrustDeviceRow(
                checked = state.trustDevice,
                onCheckedChange = viewModel::onTrustDeviceChange,
                enabled = fieldsEnabled,
                modifier = Modifier.padding(top = Spacing.md),
            )

            AuthErrorRegion {
                when (val phase = state.phase) {
                    TwoFactorPhase.Verifying ->
                        AuthProgressRow(stringResource(R.string.a09_confirming))

                    is TwoFactorPhase.Invalid -> AuthMessageSurface(
                        icon = Icons.Filled.ErrorOutline,
                        accent = EduTheme.colors.danger,
                    ) {
                        Text(
                            text = pluralStringResource(
                                R.plurals.a09_error_invalid_code_attempts,
                                phase.attemptsRemaining,
                                phase.attemptsRemaining,
                            ),
                            style = EduTheme.typography.caption,
                            color = EduTheme.colors.textPrimary,
                        )
                    }

                    TwoFactorPhase.Success -> AuthMessageSurface(
                        icon = Icons.Filled.CheckCircle,
                        accent = EduTheme.colors.success,
                    ) {
                        Text(
                            text = stringResource(R.string.a09_success_title),
                            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                            color = EduTheme.colors.textPrimary,
                        )
                        Text(
                            text = stringResource(R.string.a09_success_body),
                            style = EduTheme.typography.caption,
                            color = EduTheme.colors.textMuted,
                        )
                    }

                    TwoFactorPhase.Idle -> Unit
                }
            }

            PrimaryButton(
                text = stringResource(
                    if (state.phase == TwoFactorPhase.Verifying) R.string.a09_confirming else R.string.a09_confirm
                ),
                onClick = {
                    focusManager.clearFocus()
                    viewModel.submit()
                },
                enabled = state.canSubmit,
                isLoading = state.phase == TwoFactorPhase.Verifying,
                modifier = Modifier.fillMaxWidth(),
            )

            if (state.phase != TwoFactorPhase.Success) {
                TwoFactorResendRow(
                    canResend = state.canResend,
                    resendCapReached = state.resendCapReached,
                    cooldownSeconds = state.resendCooldownSeconds,
                    resendCount = state.resendCount,
                    onResend = viewModel::resend,
                    modifier = Modifier.padding(top = Spacing.md),
                )
            }

            Spacer(modifier = Modifier.height(Spacing.section))
        }
    }
}

/**
 * The full-bleed Basalt band — the visual identity this screen must not share with A-08.
 * Content on it is a fixed light-on-dark pair, not the theme's [EduTheme.colors]: the band
 * looks identical in the app's light and dark mode by design, which is exactly what signals
 * "this is a distinct security surface" rather than "this is a themed screen".
 */
@Composable
private fun SecurityBand(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(EduTheme.colors.basalt),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .height(Sizing.topBarHeight)
                .padding(horizontal = Spacing.xs),
        ) {
            EduIconButton(
                icon = Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = stringResource(R.string.a11y_back),
                tint = Color.White,
                onClick = onBack,
            )
            Spacer(modifier = Modifier.width(Spacing.xs))
            Icon(
                imageVector = Icons.Filled.Shield,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(Sizing.icon),
            )
            Spacer(modifier = Modifier.width(Spacing.xxs))
            Text(
                text = stringResource(R.string.a09_security_badge),
                style = EduTheme.typography.caption.copy(letterSpacing = 3.sp, fontWeight = FontWeight.SemiBold),
                color = Color.White,
            )
        }
        Text(
            text = stringResource(R.string.a09_band_label),
            style = EduTheme.typography.caption,
            color = Color.White.copy(alpha = 0.75f),
            modifier = Modifier.padding(start = Spacing.gutter, end = Spacing.gutter, bottom = Spacing.sm),
        )
    }
}

@Composable
private fun TrustDeviceRow(
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    enabled: Boolean,
    modifier: Modifier = Modifier,
) {
    val label = stringResource(R.string.a09_trust_device)

    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
            modifier = Modifier.eduClickable(
                role = androidx.compose.ui.semantics.Role.Checkbox,
                onClickLabel = label,
                enabled = enabled,
            ) { onCheckedChange(!checked) },
        ) {
            Checkbox(
                checked = checked,
                onCheckedChange = null,
                enabled = enabled,
                colors = CheckboxDefaults.colors(
                    checkedColor = EduTheme.colors.zaytoun,
                    checkmarkColor = EduTheme.colors.onZaytoun,
                    uncheckedColor = EduTheme.colors.border,
                ),
            )
            Text(text = label, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary)
        }
        Text(
            text = stringResource(R.string.a09_trust_device_hint),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.padding(start = Sizing.touchTarget),
        )
    }
}

@Composable
private fun TwoFactorResendRow(
    canResend: Boolean,
    resendCapReached: Boolean,
    cooldownSeconds: Int,
    resendCount: Int,
    onResend: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        when {
            resendCapReached -> Text(
                text = stringResource(R.string.a09_resend_cap_reached),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
            )

            canResend -> Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = stringResource(R.string.a08_resend_prompt),
                    style = EduTheme.typography.body,
                    color = EduTheme.colors.textMuted,
                )
                GhostButton(text = stringResource(R.string.a08_resend_action), onClick = onResend)
            }

            else -> Text(
                text = stringResource(R.string.a08_resend_cooldown, numeral(formatCooldown(cooldownSeconds))),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
            )
        }

        Text(
            text = stringResource(R.string.a09_resend_sent_count, resendCount, 3),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

private fun formatCooldown(totalSeconds: Int): String {
    val minutes = totalSeconds / 60
    val seconds = totalSeconds % 60
    return "%02d:%02d".format(minutes, seconds)
}
