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
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.isolateBidi
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.input.PasswordField
import com.rork.eduspark.ui.components.input.PasswordStrengthMeter
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-11 · Reset Password — reached by deep link.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Same `AuthIconMark` family as A-10, same [PasswordStrengthMeter] as A-05, so the "set a
 * password" moment looks identical whether it's the first one (register) or a replacement
 * one (here) — only the surrounding copy differs.
 *
 * The expired-link state is the one required to never dead-end: it resends directly when the
 * address is known, and falls back to A-10 (via [onNeedEmail]) when it isn't.
 */
@Composable
fun ResetPasswordScreen(
    token: String,
    email: String,
    onBack: () -> Unit,
    onNeedEmail: () -> Unit,
    onCompleted: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ResetPasswordViewModel = koinViewModel(parameters = { parametersOf(token, email) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val focusManager = LocalFocusManager.current

    BackHandler { onBack() }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                ResetPasswordEvent.Completed -> onCompleted()
            }
        }
    }

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
            when (state.phase) {
                ResetPasswordPhase.ExpiredLink -> ResetPasswordExpired(
                    state = state,
                    onSendNewLink = {
                        if (state.emailKnown) viewModel.requestNewLink() else onNeedEmail()
                    },
                    onUseDifferentEmail = onNeedEmail,
                    onLogin = onBack,
                )

                else -> ResetPasswordForm(
                    state = state,
                    onNewPasswordChange = viewModel::onNewPasswordChange,
                    onConfirmPasswordChange = viewModel::onConfirmPasswordChange,
                    onSubmit = {
                        focusManager.clearFocus()
                        viewModel.submit()
                    },
                )
            }
        }
    }
}

@Composable
private fun ResetPasswordForm(
    state: ResetPasswordUiState,
    onNewPasswordChange: (String) -> Unit,
    onConfirmPasswordChange: (String) -> Unit,
    onSubmit: () -> Unit,
) {
    val fieldsEnabled = state.phase == ResetPasswordPhase.Input

    Spacer(modifier = Modifier.height(Spacing.section))

    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        AuthIconMark(icon = Icons.Filled.Key)
    }

    Text(
        text = stringResource(R.string.a11_title),
        style = EduTheme.typography.titleLg,
        color = EduTheme.colors.textPrimary,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
    )
    Text(
        text = if (state.emailKnown) {
            stringResource(R.string.a11_body_for_email, state.email.isolateBidi())
        } else {
            stringResource(R.string.a11_body_generic)
        },
        style = EduTheme.typography.body,
        color = EduTheme.colors.textMuted,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.xxs),
    )

    Spacer(modifier = Modifier.height(Spacing.section))

    PasswordField(
        value = state.newPassword,
        onValueChange = onNewPasswordChange,
        label = stringResource(R.string.a11_new_password_label),
        placeholder = stringResource(R.string.reg_password_placeholder),
        errorText = state.passwordError?.let { stringResource(it) },
        supportingText = stringResource(R.string.reg_password_hint),
        showErrorText = false,
        labelPlacement = FieldLabelPlacement.Above,
        revealAsText = true,
        imeAction = ImeAction.Next,
    )

    PasswordStrengthMeter(password = state.newPassword)

    Spacer(modifier = Modifier.height(Spacing.md))

    PasswordField(
        value = state.confirmPassword,
        onValueChange = onConfirmPasswordChange,
        label = stringResource(R.string.reg_confirm_label),
        placeholder = stringResource(R.string.reg_confirm_placeholder),
        errorText = state.confirmError?.let { stringResource(it) },
        showErrorText = false,
        labelPlacement = FieldLabelPlacement.Above,
        revealAsText = true,
        imeAction = ImeAction.Done,
        onImeAction = onSubmit,
    )

    Text(
        text = stringResource(R.string.a11_signed_out_note),
        style = EduTheme.typography.caption,
        color = EduTheme.colors.textMuted,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
    )

    AuthErrorRegion {
        when (state.phase) {
            ResetPasswordPhase.Submitting -> AuthProgressRow(stringResource(R.string.a11_submitting))

            ResetPasswordPhase.Success -> AuthMessageSurface(
                icon = Icons.Filled.CheckCircle,
                accent = EduTheme.colors.success,
            ) {
                Text(
                    text = stringResource(R.string.a08_success_title),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                    color = EduTheme.colors.textPrimary,
                )
            }

            else -> if (state.message != null) {
                ResetPasswordMessageSurface(message = state.message, isOnline = state.isOnline)
            }
        }
    }

    PrimaryButton(
        text = stringResource(if (fieldsEnabled) R.string.a11_submit else R.string.a11_submitting),
        onClick = onSubmit,
        enabled = state.canSubmit,
        isLoading = state.phase == ResetPasswordPhase.Submitting,
        modifier = Modifier.fillMaxWidth(),
    )

    Spacer(modifier = Modifier.height(Spacing.section))
}

@Composable
private fun ResetPasswordExpired(
    state: ResetPasswordUiState,
    onSendNewLink: () -> Unit,
    onUseDifferentEmail: () -> Unit,
    onLogin: () -> Unit,
) {
    Spacer(modifier = Modifier.height(Spacing.section))

    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        AuthIconMark(icon = Icons.Filled.Schedule)
    }

    Text(
        text = stringResource(R.string.a11_expired_title),
        style = EduTheme.typography.titleLg,
        color = EduTheme.colors.textPrimary,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
    )
    Text(
        text = stringResource(R.string.a11_expired_body) + if (state.emailKnown) {
            " " + stringResource(R.string.a11_expired_resend_known, state.email.isolateBidi())
        } else {
            ""
        },
        style = EduTheme.typography.body,
        color = EduTheme.colors.textMuted,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.xxs),
    )

    Spacer(modifier = Modifier.height(Spacing.section))

    if (state.linkResent) {
        Text(
            text = stringResource(R.string.a11_link_resent, state.email.isolateBidi()),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.success,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
    } else {
        PrimaryButton(
            text = stringResource(R.string.a11_action_send_new_link),
            onClick = onSendNewLink,
            modifier = Modifier.fillMaxWidth(),
        )
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
    ) {
        GhostButton(
            text = stringResource(R.string.a11_action_use_different_email),
            onClick = onUseDifferentEmail,
        )
    }

    AuthFooterPrompt(
        question = stringResource(R.string.a10_remembered),
        actionLabel = stringResource(R.string.a03_login_action),
        onAction = onLogin,
    )

    Spacer(modifier = Modifier.height(Spacing.section))
}

/** Reuses A-04's offline copy and A-14's generic server/unknown copy — no bespoke strings. */
@Composable
private fun ResetPasswordMessageSurface(
    message: ResetPasswordMessage,
    isOnline: Boolean,
) {
    when (message) {
        ResetPasswordMessage.Offline -> AuthMessageSurface(
            icon = Icons.Filled.WifiOff,
            accent = EduTheme.colors.warning,
        ) {
            Text(
                text = stringResource(
                    if (isOnline) R.string.a04_offline_back_online else R.string.a04_error_offline
                ),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textPrimary,
            )
        }

        ResetPasswordMessage.ServerProblem -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = EduTheme.colors.danger,
        ) {
            Text(
                text = stringResource(R.string.state_error_server_body),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textPrimary,
            )
        }

        ResetPasswordMessage.Unknown -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = EduTheme.colors.danger,
        ) {
            Text(
                text = stringResource(R.string.state_error_unknown_body),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textPrimary,
            )
        }
    }
}
