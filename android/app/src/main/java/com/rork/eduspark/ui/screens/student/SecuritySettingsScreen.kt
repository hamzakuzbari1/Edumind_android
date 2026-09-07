package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ActiveSession
import com.rork.eduspark.ui.components.action.DestructiveButton
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.input.OtpInput
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-24 · Settings — Security.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit: email OTP is the only second factor — see [SecuritySettingsViewModel]'s own
 * doc comment for why enabling it here is intentionally not the same call ST-05/A-09's login
 * verification makes. Revoke-one and revoke-all both require an explicit confirmation first.
 */
@Composable
fun SecuritySettingsScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: SecuritySettingsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.st24_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { SecuritySkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            SecurityContent(
                twoFactorEnabled = data.twoFactorEnabled,
                sessions = data.sessions,
                isStartingTwoFactor = state.isStartingTwoFactor,
                onEnableTwoFactor = viewModel::startEnableTwoFactor,
                onDisableTwoFactor = viewModel::requestDisableTwoFactor,
                onRevokeSession = viewModel::requestRevokeSession,
                onRevokeAll = viewModel::requestRevokeAll,
            )
        }
    }

    state.twoFactorEnableFlow?.let { flow ->
        TwoFactorEnableDialog(
            state = flow,
            onCodeChange = viewModel::updateTwoFactorCode,
            onConfirm = viewModel::confirmEnableTwoFactor,
            onDismiss = viewModel::cancelEnableTwoFactor,
        )
    }

    if (state.pendingDisableTwoFactor) {
        ConfirmDialog(
            title = stringResource(R.string.st24_disable_confirm_title),
            body = stringResource(R.string.st24_disable_confirm_body),
            confirmLabel = stringResource(R.string.st24_disable_confirm_action),
            onConfirm = viewModel::confirmDisableTwoFactor,
            onDismiss = viewModel::cancelDisableTwoFactor,
            isDestructive = true,
        )
    }

    if (state.pendingRevokeSessionId != null) {
        ConfirmDialog(
            title = stringResource(R.string.st24_revoke_session_title),
            body = stringResource(R.string.st24_revoke_session_body),
            confirmLabel = stringResource(R.string.st24_revoke_action),
            onConfirm = viewModel::confirmRevokeSession,
            onDismiss = viewModel::cancelRevokeSession,
            isDestructive = true,
        )
    }

    if (state.pendingRevokeAll) {
        ConfirmDialog(
            title = stringResource(R.string.st24_revoke_all_title),
            body = stringResource(R.string.st24_revoke_all_body),
            confirmLabel = stringResource(R.string.st24_revoke_all_action),
            onConfirm = viewModel::confirmRevokeAll,
            onDismiss = viewModel::cancelRevokeAll,
            isDestructive = true,
        )
    }
}

@Composable
private fun SecurityContent(
    twoFactorEnabled: Boolean,
    sessions: List<ActiveSession>,
    isStartingTwoFactor: Boolean,
    onEnableTwoFactor: () -> Unit,
    onDisableTwoFactor: () -> Unit,
    onRevokeSession: (String) -> Unit,
    onRevokeAll: () -> Unit,
) {
    val colors = EduTheme.colors
    val hasOtherSessions = sessions.any { !it.isCurrentDevice }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            SectionHeader(title = stringResource(R.string.st24_two_factor_section))
            EduCard {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            stringResource(R.string.st24_two_factor_row_title),
                            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                            color = colors.textPrimary,
                        )
                        Text(
                            stringResource(R.string.st24_two_factor_row_body),
                            style = EduTheme.typography.caption,
                            color = colors.textSecondary,
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                    }
                    StatusPill(
                        label = stringResource(if (twoFactorEnabled) R.string.st24_status_enabled else R.string.st24_status_disabled),
                        contentColor = if (twoFactorEnabled) colors.success else colors.textSecondary,
                        containerColor = if (twoFactorEnabled) colors.success.copy(alpha = 0.14f) else colors.neutralAlpha100,
                    )
                }
                if (twoFactorEnabled) {
                    SecondaryButton(
                        text = stringResource(R.string.st24_disable_action),
                        onClick = onDisableTwoFactor,
                        modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
                    )
                } else {
                    PrimaryButton(
                        text = stringResource(R.string.st24_enable_action),
                        onClick = onEnableTwoFactor,
                        isLoading = isStartingTwoFactor,
                        modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
                    )
                }
            }
            Spacer(modifier = Modifier.height(Spacing.section))
        }

        item { SectionHeader(title = stringResource(R.string.st24_sessions_section)) }
        items(sessions, key = { it.id }) { session ->
            SessionRow(session = session, onRevoke = { onRevokeSession(session.id) })
            Spacer(modifier = Modifier.height(Spacing.sm))
        }
        if (!hasOtherSessions) {
            item {
                Text(
                    text = stringResource(R.string.st24_no_other_sessions),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(vertical = Spacing.sm),
                )
            }
        } else {
            item {
                DestructiveButton(
                    text = stringResource(R.string.st24_revoke_all_action),
                    onClick = onRevokeAll,
                    modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
                )
            }
        }
    }
}

@Composable
private fun SessionRow(session: ActiveSession, onRevoke: () -> Unit) {
    val colors = EduTheme.colors
    EduCard(borderColor = if (session.isCurrentDevice) colors.primary else colors.border) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Icon(
                imageVector = if (session.isCurrentDevice) Icons.Filled.PhoneAndroid else Icons.Filled.Computer,
                contentDescription = null,
                tint = if (session.isCurrentDevice) colors.primary else colors.textSecondary,
                modifier = Modifier.size(Sizing.icon),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(session.deviceLabel, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                Text(session.lastSeenLabel, style = EduTheme.typography.caption, color = colors.textSecondary)
            }
            if (session.isCurrentDevice) {
                StatusPill(
                    label = stringResource(R.string.st24_current_device),
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
            } else {
                EduIconButton(
                    icon = Icons.Filled.Close,
                    contentDescription = stringResource(R.string.st24_revoke_action),
                    tint = colors.danger,
                    onClick = onRevoke,
                )
            }
        }
    }
}

@Composable
private fun TwoFactorEnableDialog(
    state: TwoFactorEnableState,
    onCodeChange: (String) -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = EduTheme.colors
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.surface, RoundedCornerShape(Radius.lg))
                .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.lg))
                .padding(Spacing.card),
        ) {
            Text(stringResource(R.string.st24_enable_dialog_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)
            Text(
                stringResource(R.string.st24_enable_dialog_body),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
            )
            OtpInput(
                value = state.code,
                onValueChange = onCodeChange,
                contentDescription = stringResource(R.string.st24_enable_dialog_title),
                isError = state.isInvalidCode,
            )
            if (state.isInvalidCode) {
                Text(
                    stringResource(R.string.st24_enable_invalid_code),
                    style = EduTheme.typography.caption,
                    color = colors.danger,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
            PrimaryButton(
                text = stringResource(R.string.st24_enable_confirm_action),
                onClick = onConfirm,
                enabled = state.code.length == 6,
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

@Composable
private fun SecuritySkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        repeat(2) { SkeletonListItem() }
    }
}
