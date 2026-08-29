package com.rork.eduspark.ui.screens.auth

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.MailOutline
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.input.PasswordField
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-04 · Login — the first branded surface with a form on it.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The structural decision that makes this screen work is the **single error region**: one
 * fixed slot below the remember-me row where every failure speaks. Wrong password, locked
 * account, no connection, unverified address — all of them render in the same place at the
 * same reserved height, so the form never jumps under the user's thumb mid-attempt. Fields
 * still turn red for inline validation, but they never grow a message of their own.
 *
 * Login also carries the language toggle, because locale is chosen *before* authentication
 * (Design System §6.8) and a user who cannot read the interface must be able to fix that
 * without an account.
 */
@Composable
fun LoginScreen(
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
    onAuthenticated: (UserRole) -> Unit,
    onTwoFactorRequired: (String) -> Unit,
    onVerifyEmail: (String) -> Unit,
    onForgotPassword: () -> Unit,
    onCreateAccount: () -> Unit,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    viewModel: LoginViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val focusManager = LocalFocusManager.current

    BackHandler(enabled = onBack != null) { onBack?.invoke() }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is LoginEvent.Authenticated -> onAuthenticated(event.role)
                is LoginEvent.TwoFactorRequired -> onTwoFactorRequired(event.email)
                is LoginEvent.VerifyEmailRequested -> onVerifyEmail(event.email)
            }
        }
    }

    AuthScaffold(
        modifier = modifier,
        onBack = onBack,
        bottomBlock = {
            AuthLanguageToggle(
                current = locale,
                onSelect = onSelectLocale,
                note = stringResource(R.string.a04_language_restart_note),
            )
        },
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .verticalScroll(rememberScrollState()),
        ) {
            Spacer(modifier = Modifier.height(Spacing.section))

            BrandWordmark(size = WordmarkSize.Compact)

            Spacer(modifier = Modifier.height(Spacing.lg))

            EduTextField(
                value = state.email,
                onValueChange = viewModel::onEmailChange,
                label = stringResource(R.string.a04_email_label),
                placeholder = stringResource(R.string.a04_email_placeholder),
                errorText = state.emailError?.let { stringResource(it) },
                // The message belongs to the single region below, not under the field.
                showErrorText = false,
                labelPlacement = FieldLabelPlacement.Above,
                keyboardType = KeyboardType.Email,
                imeAction = ImeAction.Next,
                enabled = !state.isSubmitting,
            )

            Spacer(modifier = Modifier.height(Spacing.md))

            PasswordField(
                value = state.password,
                onValueChange = viewModel::onPasswordChange,
                label = stringResource(R.string.a04_password_label),
                placeholder = stringResource(R.string.a04_password_placeholder),
                errorText = state.passwordError?.let { stringResource(it) },
                showErrorText = false,
                labelPlacement = FieldLabelPlacement.Above,
                revealAsText = true,
                imeAction = ImeAction.Done,
                onImeAction = {
                    focusManager.clearFocus()
                    viewModel.submit()
                },
            )

            Spacer(modifier = Modifier.height(Spacing.xs))

            RememberAndForgotRow(
                rememberMe = state.rememberMe,
                onRememberMeChange = viewModel::onRememberMeChange,
                onForgotPassword = onForgotPassword,
            )

            // ── THE SINGLE ERROR REGION ──────────────────────────────────
            // Shared with A-05…A-07 so every auth form fails in the same place, the same way.
            AuthErrorRegion {
                when {
                    state.isSubmitting -> AuthProgressRow(stringResource(R.string.a04_validating))

                    state.message != null -> LoginMessageCard(
                        message = state.message!!,
                        isOnline = state.isOnline,
                        onResendVerification = viewModel::onResendVerification,
                        onChangeEmail = viewModel::clearEmail,
                        onResetPassword = onForgotPassword,
                        onRetry = {
                            focusManager.clearFocus()
                            viewModel.submit()
                        },
                    )
                }
            }

            PrimaryButton(
                text = stringResource(
                    if (state.isSubmitting) R.string.a04_submitting else R.string.a04_submit
                ),
                onClick = {
                    focusManager.clearFocus()
                    viewModel.submit()
                },
                enabled = state.canSubmit,
                isLoading = state.isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            )

            AuthFooterPrompt(
                question = stringResource(R.string.a04_no_account),
                actionLabel = stringResource(R.string.a04_create_account),
                onAction = onCreateAccount,
                modifier = Modifier.padding(top = Spacing.xxs),
            )

            Spacer(modifier = Modifier.height(Spacing.section))
        }
    }
}

/**
 * Remember-me and forgot-password share one row: a state toggle on the leading edge and an
 * escape hatch on the trailing edge. In Arabic that puts the checkbox on the right without
 * a single direction check.
 */
@Composable
private fun RememberAndForgotRow(
    rememberMe: Boolean,
    onRememberMeChange: (Boolean) -> Unit,
    onForgotPassword: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val label = stringResource(R.string.a04_remember_me)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
            // The row owns the click so the label is part of the 48dp target, not just the box.
            modifier = Modifier.eduClickable(
                role = androidx.compose.ui.semantics.Role.Checkbox,
                onClickLabel = label,
            ) { onRememberMeChange(!rememberMe) },
        ) {
            Checkbox(
                checked = rememberMe,
                onCheckedChange = null,
                colors = CheckboxDefaults.colors(
                    checkedColor = EduTheme.colors.zaytoun,
                    checkmarkColor = EduTheme.colors.onZaytoun,
                    uncheckedColor = EduTheme.colors.border,
                ),
            )
            Text(
                text = label,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
            )
        }

        Spacer(modifier = Modifier.weight(1f))

        GhostButton(
            text = stringResource(R.string.a04_forgot_password),
            onClick = onForgotPassword,
        )
    }
}

/**
 * Every failure and notice renders through [AuthMessageSurface], which is what keeps the
 * six branches visually consistent instead of six ad-hoc treatments.
 */
@Composable
private fun LoginMessageCard(
    message: LoginMessage,
    isOnline: Boolean,
    onResendVerification: (String) -> Unit,
    onChangeEmail: () -> Unit,
    onResetPassword: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors

    when (message) {
        is LoginMessage.WrongCredentials -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = colors.danger,
            modifier = modifier,
        ) {
            Text(
                text = message.attemptsRemaining?.let { remaining ->
                    pluralStringResource(
                        R.plurals.a04_error_credentials_attempts,
                        remaining,
                        remaining,
                    )
                } ?: stringResource(R.string.a04_error_credentials),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
        }

        is LoginMessage.AccountLocked -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = colors.danger,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(R.string.a04_error_locked),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
            // Rendered only when the server actually tells us when the lock lifts.
            if (message.unlockAt != null) {
                Text(
                    text = stringResource(
                        R.string.a04_error_locked_unlocks,
                        numeral(message.unlockAt),
                    ),
                    style = EduTheme.typography.mono,
                    color = colors.textMuted,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            SecondaryButton(
                text = stringResource(R.string.a04_forgot_password),
                onClick = onResetPassword,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }

        // Offline never replays the attempt by itself. The form keeps what was typed, the
        // card explains the situation, and signing in stays a deliberate press.
        LoginMessage.Offline -> AuthMessageSurface(
            icon = Icons.Filled.WifiOff,
            accent = colors.warning,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(
                    if (isOnline) R.string.a04_offline_back_online else R.string.a04_error_offline
                ),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
            if (isOnline) {
                SecondaryButton(
                    text = stringResource(R.string.common_retry),
                    onClick = onRetry,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }

        is LoginMessage.EmailNotVerified -> AuthMessageSurface(
            // Not an error: the platform lets unverified users sign in, so this is a notice.
            icon = Icons.Filled.MailOutline,
            accent = colors.zaytoun,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(R.string.a04_notice_unverified, message.email),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            ) {
                PrimaryButton(
                    text = stringResource(R.string.a04_action_resend_link),
                    onClick = { onResendVerification(message.email) },
                    modifier = Modifier.weight(1f),
                )
                SecondaryButton(
                    text = stringResource(R.string.a04_action_change_email),
                    onClick = onChangeEmail,
                    modifier = Modifier.weight(1f),
                )
            }
        }

        LoginMessage.ServerProblem -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = colors.danger,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(R.string.state_error_server_body),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
        }

        LoginMessage.Unknown -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = colors.danger,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(R.string.state_error_unknown_body),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
        }
    }
}
