package com.rork.eduspark.ui.screens.auth

import android.content.Intent
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
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.isolateBidi
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-10 · Forgot Password
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Two phases in one screen, same shell as A-08 (`AuthScaffold`, `AuthIconMark`,
 * `AuthErrorRegion`, `AuthMessageSurface`): the input form, then the confirmation. The
 * confirmation copy is careful never to say an account exists for the address — the backend
 * doesn't expose that distinction, and this screen doesn't invent one either.
 */
@Composable
fun ForgotPasswordScreen(
    onBack: () -> Unit,
    onLogin: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ForgotPasswordViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val focusManager = LocalFocusManager.current

    BackHandler { onBack() }

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
                ForgotPasswordPhase.Input -> ForgotPasswordInput(
                    state = state,
                    onEmailChange = viewModel::onEmailChange,
                    onSubmit = {
                        focusManager.clearFocus()
                        viewModel.submit()
                    },
                    onLogin = onLogin,
                )

                ForgotPasswordPhase.Sent -> ForgotPasswordSent(
                    state = state,
                    onResend = viewModel::resend,
                    onEditEmail = viewModel::editEmail,
                )
            }
        }
    }
}

@Composable
private fun ForgotPasswordInput(
    state: ForgotPasswordUiState,
    onEmailChange: (String) -> Unit,
    onSubmit: () -> Unit,
    onLogin: () -> Unit,
) {
    Spacer(modifier = Modifier.height(Spacing.section))

    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        AuthIconMark(icon = Icons.Filled.Key)
    }

    Text(
        text = stringResource(R.string.a10_title),
        style = EduTheme.typography.titleLg,
        color = EduTheme.colors.textPrimary,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
    )
    Text(
        text = stringResource(R.string.a10_body),
        style = EduTheme.typography.body,
        color = EduTheme.colors.textMuted,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.xxs),
    )

    Spacer(modifier = Modifier.height(Spacing.section))

    EduTextField(
        value = state.email,
        onValueChange = onEmailChange,
        label = stringResource(R.string.a04_email_label),
        placeholder = stringResource(R.string.a04_email_placeholder),
        errorText = state.emailError?.let { stringResource(it) },
        showErrorText = false,
        labelPlacement = FieldLabelPlacement.Above,
        keyboardType = KeyboardType.Email,
        imeAction = ImeAction.Done,
        enabled = !state.isSubmitting,
    )

    AuthErrorRegion {
        when {
            state.isSubmitting -> AuthProgressRow(stringResource(R.string.a10_submitting))

            state.message != null -> ForgotPasswordMessageSurface(message = state.message, isOnline = state.isOnline)
        }
    }

    PrimaryButton(
        text = stringResource(if (state.isSubmitting) R.string.a10_submitting else R.string.a10_submit),
        onClick = onSubmit,
        enabled = state.canSubmit,
        isLoading = state.isSubmitting,
        modifier = Modifier.fillMaxWidth(),
    )

    AuthFooterPrompt(
        question = stringResource(R.string.a10_remembered),
        actionLabel = stringResource(R.string.a03_login_action),
        onAction = onLogin,
        modifier = Modifier.padding(top = Spacing.xxs),
    )

    Spacer(modifier = Modifier.height(Spacing.section))
}

@Composable
private fun ForgotPasswordSent(
    state: ForgotPasswordUiState,
    onResend: () -> Unit,
    onEditEmail: () -> Unit,
) {
    val context = LocalContext.current

    Spacer(modifier = Modifier.height(Spacing.section))

    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        AuthIconMark(icon = Icons.Filled.CheckCircle)
    }

    Text(
        text = stringResource(R.string.a08_title),
        style = EduTheme.typography.titleLg,
        color = EduTheme.colors.textPrimary,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
    )
    Text(
        text = stringResource(R.string.a10_sent_body, state.email.trim().isolateBidi()),
        style = EduTheme.typography.body,
        color = EduTheme.colors.textMuted,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.xxs),
    )

    Spacer(modifier = Modifier.height(Spacing.md))

    Text(
        text = stringResource(R.string.a10_sent_spam_hint),
        style = EduTheme.typography.caption,
        color = EduTheme.colors.textMuted,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth(),
    )
    Text(
        text = stringResource(R.string.a10_sent_validity),
        style = EduTheme.typography.caption,
        color = EduTheme.colors.textMuted,
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.xxs),
    )

    SecondaryButton(
        text = stringResource(R.string.a10_open_mail_app),
        onClick = {
            val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_APP_EMAIL)
            runCatching { context.startActivity(intent) }
        },
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.section),
    )

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
    ) {
        if (state.canResend) {
            Text(
                text = stringResource(R.string.a08_resend_prompt),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textMuted,
            )
            GhostButton(text = stringResource(R.string.a08_resend_action), onClick = onResend)
        } else {
            Text(
                text = stringResource(R.string.a08_resend_cooldown, numeral(formatCooldownForForgotPassword(state.resendCooldownSeconds))),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
            )
        }
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.xs),
    ) {
        Text(
            text = stringResource(R.string.a08_change_email_prompt),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
        )
        GhostButton(text = stringResource(R.string.a10_try_another_email_action), onClick = onEditEmail)
    }

    Spacer(modifier = Modifier.height(Spacing.section))
}

/** Reuses A-04's offline copy and A-14's generic server/unknown copy — no bespoke strings. */
@Composable
private fun ForgotPasswordMessageSurface(
    message: ForgotPasswordMessage,
    isOnline: Boolean,
) {
    when (message) {
        ForgotPasswordMessage.Offline -> AuthMessageSurface(
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

        ForgotPasswordMessage.ServerProblem -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = EduTheme.colors.danger,
        ) {
            Text(
                text = stringResource(R.string.state_error_server_body),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textPrimary,
            )
        }

        ForgotPasswordMessage.Unknown -> AuthMessageSurface(
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

private fun formatCooldownForForgotPassword(totalSeconds: Int): String {
    val minutes = totalSeconds / 60
    val seconds = totalSeconds % 60
    return "%02d:%02d".format(minutes, seconds)
}
