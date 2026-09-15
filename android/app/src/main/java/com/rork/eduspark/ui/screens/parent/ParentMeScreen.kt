package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ActiveSession
import com.rork.eduspark.ui.components.action.DestructiveButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.input.PASSWORD_MIN_LENGTH
import com.rork.eduspark.ui.components.input.PasswordField
import com.rork.eduspark.ui.components.input.PasswordStrengthMeter
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

private enum class ParentAccountSheet { Password, Security }

@Composable
fun ParentMeScreen(
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentMeViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var activeSheet by rememberSaveable { mutableStateOf<ParentAccountSheet?>(null) }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { ParentMeSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        ParentMeContent(
            data = data,
            onOpenLinkStudent = onOpenLinkStudent,
            onOpenPassword = { activeSheet = ParentAccountSheet.Password },
            onOpenSecurity = { activeSheet = ParentAccountSheet.Security },
            onOpenSession = viewModel::openSessionDetails,
        )

        when (activeSheet) {
            ParentAccountSheet.Password -> ParentPasswordDialog(onDismiss = { activeSheet = null })
            ParentAccountSheet.Security -> ParentSecurityDialog(
                data = data,
                onDismiss = { activeSheet = null },
            )
            null -> Unit
        }

        state.selectedSession?.let { session ->
            ParentSessionDetailsDialog(
                session = session,
                onDismiss = viewModel::dismissSessionDetails,
                onEndDemoSession = viewModel::requestEndDemoSession,
            )
        }

        state.pendingEndSession?.let { session ->
            ConfirmDialog(
                title = stringResource(R.string.pr13_session_end_confirm_title),
                body = stringResource(R.string.pr13_session_end_confirm_body, session.deviceLabel),
                confirmLabel = stringResource(R.string.pr13_session_end_action),
                onConfirm = viewModel::confirmEndDemoSession,
                onDismiss = viewModel::cancelEndDemoSession,
                isDestructive = true,
            )
        }
    }
}

@Composable
private fun ParentMeContent(
    data: ParentMeData,
    onOpenLinkStudent: () -> Unit,
    onOpenPassword: () -> Unit,
    onOpenSecurity: () -> Unit,
    onOpenSession: (String) -> Unit,
) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                ) {
                    ParentAvatar(initial = data.account.avatarInitial, modifier = Modifier.size(Sizing.avatarLg))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = data.account.displayName,
                            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.textPrimary,
                        )
                        Text(
                            text = stringResource(R.string.pr13_account_status_parent),
                            style = EduTheme.typography.caption,
                            color = colors.textSecondary,
                        )
                        Text(
                            text = data.account.email,
                            style = EduTheme.typography.caption,
                            color = colors.textTertiary,
                        )
                    }
                }
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pr13_account_security_section))
            EduCard {
                ListRow(
                    title = stringResource(R.string.pr13_password_title),
                    supporting = stringResource(R.string.pr13_password_supporting),
                    leading = Icons.Filled.Key,
                    leadingTint = colors.primary,
                    showChevron = true,
                    onClick = onOpenPassword,
                )
                EduDivider()
                ListRow(
                    title = stringResource(R.string.pr13_verification_title),
                    supporting = stringResource(R.string.pr13_verification_supporting),
                    leading = Icons.Filled.VerifiedUser,
                    leadingTint = colors.accent,
                    trailingContent = {
                        StatusPill(
                            label = stringResource(if (data.twoFactorEnabled) R.string.st24_status_enabled else R.string.st24_status_disabled),
                            contentColor = if (data.twoFactorEnabled) colors.success else colors.textSecondary,
                            containerColor = if (data.twoFactorEnabled) colors.success.copy(alpha = 0.14f) else colors.neutralAlpha100,
                        )
                    },
                    showChevron = true,
                    onClick = onOpenSecurity,
                )
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pr13_devices_section))
            EduCard {
                data.sessions.forEachIndexed { index, session ->
                    ParentSessionRow(
                        session = session,
                        onClick = { onOpenSession(session.id) },
                    )
                    if (index != data.sessions.lastIndex) EduDivider()
                }
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pr13_linked_students_section))
        }

        if (data.linkedStudents.isEmpty()) {
            item {
                EduCard(borderColor = colors.warning.copy(alpha = 0.36f)) {
                    Text(
                        text = stringResource(R.string.pr13_no_students_title),
                        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                    )
                    Text(
                        text = stringResource(R.string.pr13_no_students_body),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
            }
        } else {
            items(data.linkedStudents, key = { it.id }) { student ->
                ParentLinkedStudentCard(student = student)
            }
        }

        item {
            SecondaryButton(
                text = stringResource(R.string.pr13_link_another_student),
                onClick = onOpenLinkStudent,
                leadingIcon = Icons.Filled.Link,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(Spacing.section))
        }
    }
}

@Composable
private fun ParentSessionDetailsDialog(
    session: ActiveSession,
    onDismiss: () -> Unit,
    onEndDemoSession: () -> Unit,
) {
    val colors = EduTheme.colors
    Dialog(onDismissRequest = onDismiss) {
        ParentAccountDialogContainer {
            Text(
                text = stringResource(R.string.pr13_session_details_title),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
            )
            Text(
                text = stringResource(R.string.pr13_session_details_body),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
            EduCard(
                containerColor = colors.neutralAlpha100,
                borderColor = colors.neutralAlpha100,
                modifier = Modifier.padding(top = Spacing.md),
            ) {
                ListRow(
                    title = stringResource(R.string.pr13_session_device_title),
                    supporting = session.deviceLabel,
                    leading = if (session.isCurrentDevice) Icons.Filled.PhoneAndroid else Icons.Filled.Computer,
                    leadingTint = if (session.isCurrentDevice) colors.success else colors.primary,
                )
                EduDivider()
                ListRow(
                    title = stringResource(R.string.pr13_session_status_title),
                    supporting = if (session.isCurrentDevice) {
                        stringResource(R.string.pr13_session_status_current)
                    } else {
                        session.lastSeenLabel
                    },
                    leading = Icons.Filled.VerifiedUser,
                    leadingTint = colors.accent,
                    trailingContent = {
                        if (session.isCurrentDevice) {
                            StatusPill(
                                label = stringResource(R.string.st24_current_device),
                                contentColor = colors.success,
                                containerColor = colors.success.copy(alpha = 0.14f),
                            )
                        }
                    },
                )
            }
            if (session.isCurrentDevice) {
                PrimaryButton(
                    text = stringResource(R.string.common_close),
                    onClick = onDismiss,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            } else {
                DestructiveButton(
                    text = stringResource(R.string.pr13_session_end_action),
                    onClick = onEndDemoSession,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
                SecondaryButton(
                    text = stringResource(R.string.common_cancel),
                    onClick = onDismiss,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
            }
        }
    }
}

@Composable
private fun ParentPasswordDialog(onDismiss: () -> Unit) {
    val colors = EduTheme.colors
    var currentPassword by rememberSaveable { mutableStateOf("") }
    var newPassword by rememberSaveable { mutableStateOf("") }
    var confirmPassword by rememberSaveable { mutableStateOf("") }
    var validationFailed by rememberSaveable { mutableStateOf(false) }
    var isComplete by rememberSaveable { mutableStateOf(false) }

    Dialog(onDismissRequest = onDismiss) {
        ParentAccountDialogContainer {
            if (isComplete) {
                Text(
                    text = stringResource(R.string.pr13_password_done_title),
                    style = EduTheme.typography.titleLg,
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.pr13_password_done_body),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                PrimaryButton(
                    text = stringResource(R.string.common_close),
                    onClick = onDismiss,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            } else {
                Text(
                    text = stringResource(R.string.pr13_password_sheet_title),
                    style = EduTheme.typography.titleLg,
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.pr13_password_sheet_body),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                PasswordField(
                    value = currentPassword,
                    onValueChange = {
                        currentPassword = it
                        validationFailed = false
                    },
                    label = stringResource(R.string.st23_password_current_label),
                    modifier = Modifier.padding(top = Spacing.md),
                )
                PasswordField(
                    value = newPassword,
                    onValueChange = {
                        newPassword = it
                        validationFailed = false
                    },
                    label = stringResource(R.string.st23_password_new_label),
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                PasswordStrengthMeter(
                    password = newPassword,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
                PasswordField(
                    value = confirmPassword,
                    onValueChange = {
                        confirmPassword = it
                        validationFailed = false
                    },
                    label = stringResource(R.string.st23_password_confirm_label),
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                if (validationFailed) {
                    Text(
                        text = stringResource(R.string.st23_password_validation_error),
                        style = EduTheme.typography.caption,
                        color = colors.danger,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                }
                PrimaryButton(
                    text = stringResource(R.string.pr13_password_mock_submit),
                    onClick = {
                        val isValid = currentPassword.isNotBlank() &&
                            newPassword.length >= PASSWORD_MIN_LENGTH &&
                            newPassword == confirmPassword
                        if (isValid) {
                            isComplete = true
                        } else {
                            validationFailed = true
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
                SecondaryButton(
                    text = stringResource(R.string.common_cancel),
                    onClick = onDismiss,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
            }
        }
    }
}

@Composable
private fun ParentSecurityDialog(
    data: ParentMeData,
    onDismiss: () -> Unit,
) {
    val colors = EduTheme.colors
    val otherSessions = data.sessions.count { !it.isCurrentDevice }

    Dialog(onDismissRequest = onDismiss) {
        ParentAccountDialogContainer {
            Text(
                text = stringResource(R.string.pr13_security_sheet_title),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
            )
            Text(
                text = stringResource(R.string.pr13_security_sheet_body),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
            EduCard(
                containerColor = colors.neutralAlpha100,
                borderColor = colors.neutralAlpha100,
                modifier = Modifier.padding(top = Spacing.md),
            ) {
                ListRow(
                    title = stringResource(R.string.pr13_security_email_title),
                    supporting = data.account.email,
                    leading = Icons.Filled.VerifiedUser,
                    leadingTint = colors.primary,
                )
                EduDivider()
                ListRow(
                    title = stringResource(R.string.pr13_security_two_factor_title),
                    supporting = stringResource(R.string.pr13_security_two_factor_body),
                    leading = Icons.Filled.Key,
                    leadingTint = colors.accent,
                    trailingContent = {
                        StatusPill(
                            label = stringResource(if (data.twoFactorEnabled) R.string.st24_status_enabled else R.string.st24_status_disabled),
                            contentColor = if (data.twoFactorEnabled) colors.success else colors.textSecondary,
                            containerColor = if (data.twoFactorEnabled) colors.success.copy(alpha = 0.14f) else colors.neutralAlpha100,
                        )
                    },
                )
                EduDivider()
                ListRow(
                    title = stringResource(R.string.pr13_security_sessions_title),
                    supporting = stringResource(R.string.pr13_security_sessions_body, otherSessions),
                    leading = Icons.Filled.Computer,
                    leadingTint = colors.success,
                )
            }
            PrimaryButton(
                text = stringResource(R.string.common_close),
                onClick = onDismiss,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
        }
    }
}

@Composable
private fun ParentAccountDialogContainer(content: @Composable () -> Unit) {
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
private fun ParentSessionRow(
    session: ActiveSession,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    ListRow(
        title = session.deviceLabel,
        supporting = session.lastSeenLabel,
        leading = if (session.isCurrentDevice) Icons.Filled.PhoneAndroid else Icons.Filled.Computer,
        leadingTint = if (session.isCurrentDevice) colors.success else colors.primary,
        trailingContent = {
            if (session.isCurrentDevice) {
                StatusPill(
                    label = stringResource(R.string.st24_current_device),
                    contentColor = colors.success,
                    containerColor = colors.success.copy(alpha = 0.14f),
                )
            }
        },
        showChevron = !session.isCurrentDevice,
        onClick = onClick,
    )
}

@Composable
private fun ParentMeSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        repeat(2) { SkeletonListItem() }
    }
}
