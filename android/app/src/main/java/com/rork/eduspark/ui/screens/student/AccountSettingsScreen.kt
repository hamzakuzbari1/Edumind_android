package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Badge
import androidx.compose.material.icons.filled.DeleteForever
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.OtpInput
import com.rork.eduspark.ui.components.input.PasswordField
import com.rork.eduspark.ui.components.input.PasswordStrengthMeter
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.OfflineBanner
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-23 · Settings — Account.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A settings list, not one giant form — each row opens its own small sheet. See
 * [AccountSettingsViewModel]'s own doc comment for exactly which boundaries (email/password/
 * delete) are mock-local vs. backed by [com.rork.eduspark.data.repository.ProfileRepository].
 */
@Composable
fun AccountSettingsScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: AccountSettingsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val colors = EduTheme.colors

    EduScaffold(title = stringResource(R.string.st23_title), onBack = onBack, modifier = modifier) { _ ->
        Column(modifier = Modifier.fillMaxSize()) {
            OfflineBanner(visible = !state.isOnline)
            LazyColumn(
                contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
                modifier = Modifier.fillMaxSize(),
            ) {
                item {
                    SectionHeader(title = stringResource(R.string.st23_profile_section))
                    ListRow(
                        title = stringResource(R.string.st23_name_row),
                        supporting = state.displayName,
                        leading = Icons.Filled.Badge,
                        showChevron = true,
                        onClick = viewModel::openNameSheet,
                    )
                }
                item {
                    SectionHeader(title = stringResource(R.string.st23_login_section))
                    ListRow(
                        title = stringResource(R.string.st23_email_row),
                        supporting = state.email,
                        leading = Icons.Filled.Email,
                        showChevron = true,
                        onClick = viewModel::openEmailChange,
                    )
                    ListRow(
                        title = stringResource(R.string.st23_password_row),
                        supporting = stringResource(R.string.st23_password_masked),
                        leading = Icons.Filled.Lock,
                        showChevron = true,
                        onClick = viewModel::openPasswordChange,
                    )
                }
                item {
                    SectionHeader(title = stringResource(R.string.st23_danger_section))
                    ListRow(
                        title = stringResource(R.string.st23_delete_account_row),
                        leading = Icons.Filled.DeleteForever,
                        leadingTint = colors.danger,
                        showChevron = true,
                        onClick = viewModel::requestDeleteAccount,
                    )
                }
            }
        }
    }

    if (state.showNameSheet) {
        NameEditSheet(
            initialName = state.displayName,
            isSaving = state.isSavingName,
            onDismiss = viewModel::dismissNameSheet,
            onSave = viewModel::saveName,
        )
    }

    state.emailChange?.let { emailChange ->
        EmailChangeSheet(
            state = emailChange,
            onDismiss = viewModel::dismissEmailChange,
            onEmailChange = viewModel::updateNewEmail,
            onSubmitEmail = viewModel::submitNewEmail,
            onCodeChange = viewModel::updateEmailChangeCode,
            onConfirmCode = viewModel::confirmEmailChange,
        )
    }

    state.passwordChange?.let { passwordChange ->
        PasswordChangeSheet(
            state = passwordChange,
            onDismiss = viewModel::dismissPasswordChange,
            onCurrentChange = viewModel::updateCurrentPassword,
            onNewChange = viewModel::updateNewPassword,
            onConfirmChange = viewModel::updateConfirmPassword,
            onSubmit = viewModel::submitPasswordChange,
        )
    }

    when (state.deleteAccount) {
        DeleteAccountPhase.Confirming -> ConfirmDialog(
            title = stringResource(R.string.st23_delete_confirm_title),
            body = stringResource(R.string.st23_delete_confirm_body),
            confirmLabel = stringResource(R.string.st23_delete_confirm_action),
            onConfirm = viewModel::confirmDeleteAccount,
            onDismiss = viewModel::cancelDeleteAccount,
            isDestructive = true,
        )
        DeleteAccountPhase.Confirmed -> ConfirmDialog(
            title = stringResource(R.string.st23_delete_done_title),
            body = stringResource(R.string.st23_delete_done_body),
            confirmLabel = stringResource(R.string.common_close),
            onConfirm = viewModel::cancelDeleteAccount,
            onDismiss = viewModel::cancelDeleteAccount,
        )
        null -> Unit
    }
}

@Composable
private fun SheetContainer(content: @Composable () -> Unit) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface, RoundedCornerShape(Radius.lg))
            .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.lg))
            .padding(Spacing.card),
        content = { content() },
    )
}

@Composable
private fun NameEditSheet(initialName: String, isSaving: Boolean, onDismiss: () -> Unit, onSave: (String) -> Unit) {
    var name by remember { mutableStateOf(initialName) }
    Dialog(onDismissRequest = onDismiss) {
        SheetContainer {
            Text(stringResource(R.string.st23_name_sheet_title), style = EduTheme.typography.titleLg, color = EduTheme.colors.textPrimary)
            EduTextField(
                value = name,
                onValueChange = { name = it },
                label = stringResource(R.string.st23_name_row),
                modifier = Modifier.padding(top = Spacing.md),
            )
            PrimaryButton(
                text = stringResource(R.string.common_save),
                onClick = { onSave(name) },
                enabled = name.isNotBlank(),
                isLoading = isSaving,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
            )
            SecondaryButton(
                text = stringResource(R.string.common_cancel),
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun EmailChangeSheet(
    state: EmailChangeState,
    onDismiss: () -> Unit,
    onEmailChange: (String) -> Unit,
    onSubmitEmail: () -> Unit,
    onCodeChange: (String) -> Unit,
    onConfirmCode: () -> Unit,
) {
    val colors = EduTheme.colors
    Dialog(onDismissRequest = onDismiss) {
        SheetContainer {
            when (state.step) {
                EmailChangeStep.EnterEmail -> {
                    Text(stringResource(R.string.st23_email_sheet_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)
                    Text(
                        stringResource(R.string.st23_email_sheet_body),
                        style = EduTheme.typography.body,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                    EduTextField(
                        value = state.newEmail,
                        onValueChange = onEmailChange,
                        label = stringResource(R.string.st23_email_new_label),
                        keyboardType = KeyboardType.Email,
                        modifier = Modifier.padding(top = Spacing.md),
                    )
                    PrimaryButton(
                        text = stringResource(R.string.st23_email_send_code),
                        onClick = onSubmitEmail,
                        enabled = state.newEmail.isNotBlank(),
                        isLoading = state.isSubmitting,
                        modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
                    )
                }
                EmailChangeStep.Verify -> {
                    Text(stringResource(R.string.st23_email_verify_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)
                    Text(
                        stringResource(R.string.st23_email_verify_body, state.newEmail),
                        style = EduTheme.typography.body,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
                    )
                    OtpInput(
                        value = state.code,
                        onValueChange = onCodeChange,
                        contentDescription = stringResource(R.string.st23_email_verify_title),
                        isError = state.isInvalidCode,
                    )
                    if (state.isInvalidCode) {
                        Text(
                            stringResource(R.string.st23_email_invalid_code),
                            style = EduTheme.typography.caption,
                            color = colors.danger,
                            modifier = Modifier.padding(top = Spacing.xs),
                        )
                    }
                    PrimaryButton(
                        text = stringResource(R.string.st23_email_confirm),
                        onClick = onConfirmCode,
                        enabled = state.code.length == 6,
                        isLoading = state.isSubmitting,
                        modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
                    )
                }
            }
            SecondaryButton(
                text = stringResource(R.string.common_cancel),
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth().padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun PasswordChangeSheet(
    state: PasswordChangeState,
    onDismiss: () -> Unit,
    onCurrentChange: (String) -> Unit,
    onNewChange: (String) -> Unit,
    onConfirmChange: (String) -> Unit,
    onSubmit: () -> Unit,
) {
    val colors = EduTheme.colors
    Dialog(onDismissRequest = onDismiss) {
        SheetContainer {
            if (state.isComplete) {
                Text(stringResource(R.string.st23_password_done_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)
                Text(
                    stringResource(R.string.st23_password_done_body),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                PrimaryButton(
                    text = stringResource(R.string.common_close),
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
                )
            } else {
                Text(stringResource(R.string.st23_password_sheet_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)
                PasswordField(
                    value = state.currentPassword,
                    onValueChange = onCurrentChange,
                    label = stringResource(R.string.st23_password_current_label),
                    modifier = Modifier.padding(top = Spacing.md),
                )
                PasswordField(
                    value = state.newPassword,
                    onValueChange = onNewChange,
                    label = stringResource(R.string.st23_password_new_label),
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                PasswordStrengthMeter(password = state.newPassword, modifier = Modifier.padding(top = Spacing.xs))
                PasswordField(
                    value = state.confirmPassword,
                    onValueChange = onConfirmChange,
                    label = stringResource(R.string.st23_password_confirm_label),
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                if (state.validationFailed) {
                    Text(
                        stringResource(R.string.st23_password_validation_error),
                        style = EduTheme.typography.caption,
                        color = colors.danger,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                }
                PrimaryButton(
                    text = stringResource(R.string.st23_password_submit),
                    onClick = onSubmit,
                    isLoading = state.isSubmitting,
                    modifier = Modifier.fillMaxWidth().padding(top = Spacing.md),
                )
                SecondaryButton(
                    text = stringResource(R.string.common_cancel),
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth().padding(top = Spacing.xs),
                )
            }
        }
    }
}
