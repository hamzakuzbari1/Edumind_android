package com.rork.eduspark.ui.screens.auth

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.MailOutline
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.isolateBidi
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.OtpInput
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-08 · Verify Email
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reached from A-05/06/07 Register on success, and from A-04 Login's "Resend link" action on
 * an unverified address. Same shell as the rest of the funnel (`AuthScaffold`,
 * `AuthErrorRegion`, `AuthMessageSurface`), a centred envelope mark instead of the wordmark,
 * and the six states the design calls for: idle, verifying, invalid (with attempts
 * remaining), expired, cooldown (layered on top of any of the above via the resend row), and
 * success.
 */
@Composable
fun VerifyEmailScreen(
    email: String,
    onBack: () -> Unit,
    onVerified: (SessionUser?) -> Unit,
    onChangeEmail: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: VerifyEmailViewModel = koinViewModel(parameters = { parametersOf(email) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val focusManager = LocalFocusManager.current

    BackHandler { onBack() }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is VerifyEmailEvent.Verified -> onVerified(event.user)
            }
        }
    }

    val fieldsEnabled = state.phase != VerifyEmailPhase.Verifying && state.phase != VerifyEmailPhase.Success
    val isError = state.phase is VerifyEmailPhase.Invalid || state.phase == VerifyEmailPhase.Expired

    AuthScaffold(
        modifier = modifier,
        onBack = onBack,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .verticalScroll(rememberScrollState()),
        ) {
            Spacer(modifier = Modifier.height(Spacing.section))

            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                AuthIconMark(icon = Icons.Filled.MailOutline)
            }

            Text(
                text = stringResource(R.string.a08_title),
                style = EduTheme.typography.titleLg,
                color = EduTheme.colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
            Text(
                text = stringResource(R.string.a08_body, email.isolateBidi()),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xxs),
            )

            Spacer(modifier = Modifier.height(Spacing.section))

            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                OtpInput(
                    value = state.code,
                    onValueChange = viewModel::onCodeChange,
                    contentDescription = stringResource(R.string.a11y_a08_otp),
                    isError = isError,
                    enabled = fieldsEnabled,
                )
            }

            if (state.phase == VerifyEmailPhase.Idle) {
                Text(
                    text = stringResource(R.string.a08_code_hint),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.sm),
                )
            }

            AuthErrorRegion {
                when (val phase = state.phase) {
                    VerifyEmailPhase.Verifying ->
                        AuthProgressRow(stringResource(R.string.a08_verifying))

                    is VerifyEmailPhase.Invalid -> AuthMessageSurface(
                        icon = Icons.Filled.ErrorOutline,
                        accent = EduTheme.colors.danger,
                    ) {
                        Text(
                            text = pluralStringResource(
                                R.plurals.a08_error_invalid_code_attempts,
                                phase.attemptsRemaining,
                                phase.attemptsRemaining,
                            ),
                            style = EduTheme.typography.caption,
                            color = EduTheme.colors.textPrimary,
                        )
                    }

                    VerifyEmailPhase.Expired -> AuthMessageSurface(
                        icon = Icons.Filled.Schedule,
                        accent = EduTheme.colors.warning,
                    ) {
                        Text(
                            text = stringResource(R.string.a08_error_expired),
                            style = EduTheme.typography.caption,
                            color = EduTheme.colors.textPrimary,
                        )
                        SecondaryButton(
                            text = stringResource(R.string.a08_action_send_new_code),
                            onClick = viewModel::resend,
                            modifier = Modifier.padding(top = Spacing.xs),
                        )
                    }

                    VerifyEmailPhase.Success -> AuthMessageSurface(
                        icon = Icons.Filled.CheckCircle,
                        accent = EduTheme.colors.success,
                    ) {
                        Text(
                            text = stringResource(R.string.a08_success_title),
                            style = EduTheme.typography.caption.copy(
                                fontWeight = androidx.compose.ui.text.font.FontWeight.SemiBold
                            ),
                            color = EduTheme.colors.textPrimary,
                        )
                        Text(
                            text = stringResource(R.string.a08_success_body),
                            style = EduTheme.typography.caption,
                            color = EduTheme.colors.textMuted,
                        )
                    }

                    VerifyEmailPhase.Idle -> Unit
                }
            }

            PrimaryButton(
                text = stringResource(
                    if (state.phase == VerifyEmailPhase.Verifying) {
                        R.string.a08_verifying
                    } else {
                        R.string.a08_verify
                    }
                ),
                onClick = {
                    focusManager.clearFocus()
                    viewModel.submit()
                },
                enabled = state.canSubmit,
                isLoading = state.phase == VerifyEmailPhase.Verifying,
                modifier = Modifier.fillMaxWidth(),
            )

            if (state.phase != VerifyEmailPhase.Success) {
                ResendRow(
                    canResend = state.canResend,
                    cooldownSeconds = state.resendCooldownSeconds,
                    onResend = viewModel::resend,
                    modifier = Modifier.padding(top = Spacing.md),
                )

                ChangeEmailRow(
                    onChangeEmail = onChangeEmail,
                    modifier = Modifier.padding(top = Spacing.section),
                )
            }

            Spacer(modifier = Modifier.height(Spacing.section))
        }
    }
}

@Composable
private fun ResendRow(
    canResend: Boolean,
    cooldownSeconds: Int,
    onResend: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
        modifier = modifier.fillMaxWidth(),
    ) {
        if (canResend) {
            Text(
                text = stringResource(R.string.a08_resend_prompt),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textMuted,
            )
            GhostButton(text = stringResource(R.string.a08_resend_action), onClick = onResend)
        } else {
            Text(
                text = stringResource(R.string.a08_resend_cooldown, numeral(formatCooldown(cooldownSeconds))),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
            )
        }
    }
}

@Composable
private fun ChangeEmailRow(
    onChangeEmail: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier.fillMaxWidth(),
    ) {
        Text(
            text = stringResource(R.string.a08_change_email_prompt),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = stringResource(R.string.a08_change_email_hint),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
            )
            GhostButton(text = stringResource(R.string.a08_change_email_action), onClick = onChangeEmail)
        }
    }
}

/** "00:42" — mm:ss, run through [numeral] so it honours the Arabic-Indic setting too. */
private fun formatCooldown(totalSeconds: Int): String {
    val minutes = totalSeconds / 60
    val seconds = totalSeconds % 60
    return "%02d:%02d".format(minutes, seconds)
}
