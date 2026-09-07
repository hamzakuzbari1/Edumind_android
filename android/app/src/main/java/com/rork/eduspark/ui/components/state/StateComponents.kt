package com.rork.eduspark.ui.components.state

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Inbox
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.SearchOff
import androidx.compose.material.icons.filled.SystemUpdateAlt
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import com.rork.eduspark.R
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.ui.EmptyReason
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-14 · Global States Kit
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Designed once, together, so every screen in the app is consistent. Screens never
 * hand-roll an error or an empty view — they hand a [UiState] to [ScreenStateHost].
 *
 * Copy rules (Design System §9): errors say what happened and what to do — no apologies,
 * no "oops". Empty states are invitations with exactly one action, never a shrug.
 */

/**
 * Renders the correct state for [state] and delegates the loaded case to [content].
 *
 * This is the component that makes "every screen ships four states" structurally true
 * rather than a convention people forget under deadline.
 *
 * @param isOffline drives the persistent banner above cached content.
 */
@Composable
fun <T> ScreenStateHost(
    state: UiState<T>,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
    isOffline: Boolean = false,
    loading: @Composable () -> Unit = { DefaultLoadingState() },
    empty: @Composable (EmptyReason) -> Unit = { reason -> DefaultEmptyState(reason, onRetry) },
    onSessionExpired: (() -> Unit)? = null,
    content: @Composable (T) -> Unit,
) {
    Column(modifier = modifier.fillMaxSize()) {
        OfflineBanner(visible = isOffline || (state as? UiState.Content)?.isStale == true)

        when (state) {
            is UiState.Loading -> loading()

            is UiState.Content -> content(state.data)

            is UiState.Empty -> empty(state.reason)

            is UiState.Failure -> ErrorState(
                error = state.error,
                onRetry = onRetry,
                onSessionExpired = onSessionExpired,
            )
        }
    }
}

/**
 * Offline banner — a persistent, non-dismissible strip. It is a live region so TalkBack
 * announces the connection change instead of leaving the user guessing.
 */
@Composable
fun OfflineBanner(
    visible: Boolean,
    modifier: Modifier = Modifier,
) {
    AnimatedVisibility(
        visible = visible,
        enter = fadeIn() + expandVertically(),
        exit = fadeOut() + shrinkVertically(),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = modifier
                .fillMaxWidth()
                .background(EduTheme.colors.neutralAlpha100)
                .padding(horizontal = Spacing.gutter, vertical = Spacing.xs)
                .semantics { liveRegion = LiveRegionMode.Polite },
        ) {
            Icon(
                imageVector = Icons.Filled.CloudOff,
                contentDescription = null,
                tint = EduTheme.colors.warning,
                modifier = Modifier.size(Sizing.icon),
            )
            Column {
                Text(
                    text = stringResource(R.string.state_offline_title),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.state_offline_cached),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
            }
        }
    }
}

/**
 * The shared empty/error/permission layout: brand headline, plain explanation, one action.
 * Never more than two actions — the second is always the escape hatch.
 */
@Composable
fun MessageState(
    icon: ImageVector,
    title: String,
    body: String,
    modifier: Modifier = Modifier,
    iconTint: Color = EduTheme.colors.textSecondary,
    primaryActionLabel: String? = null,
    onPrimaryAction: (() -> Unit)? = null,
    secondaryActionLabel: String? = null,
    onSecondaryAction: (() -> Unit)? = null,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm, Alignment.CenterVertically),
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.section)
            .semantics { liveRegion = LiveRegionMode.Polite },
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = iconTint,
            modifier = Modifier.size(Sizing.stateIcon),
        )
        Text(
            // Empty-state headlines are a brand moment — Plex, per Design System §4.
            text = title,
            style = EduTheme.typography.brandTitle,
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Center,
        )
        Text(
            text = body,
            style = EduTheme.typography.body,
            color = EduTheme.colors.textSecondary,
            textAlign = TextAlign.Center,
        )
        if (primaryActionLabel != null && onPrimaryAction != null) {
            PrimaryButton(
                text = primaryActionLabel,
                onClick = onPrimaryAction,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
        if (secondaryActionLabel != null && onSecondaryAction != null) {
            SecondaryButton(text = secondaryActionLabel, onClick = onSecondaryAction)
        }
    }
}

@Composable
fun DefaultEmptyState(
    reason: EmptyReason,
    onAction: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    when (reason) {
        EmptyReason.NoContent -> MessageState(
            icon = Icons.Filled.Inbox,
            title = stringResource(R.string.state_empty_default_title),
            body = stringResource(R.string.state_empty_default_body),
            modifier = modifier,
        )

        EmptyReason.NoResults -> MessageState(
            icon = Icons.Filled.SearchOff,
            title = stringResource(R.string.state_empty_default_title),
            body = stringResource(R.string.state_empty_default_body),
            primaryActionLabel = onAction?.let { stringResource(R.string.common_clear) },
            onPrimaryAction = onAction,
            modifier = modifier,
        )
    }
}

/**
 * Error state.
 *
 * [AppError.SessionExpired] is treated as a distinct, non-retryable case because the
 * platform has no refresh endpoint — the only correct action is to sign in again.
 */
@Composable
fun ErrorState(
    error: AppError,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
    onSessionExpired: (() -> Unit)? = null,
) {
    val retryLabel = stringResource(R.string.common_retry)

    when (error) {
        AppError.Offline, AppError.Network -> MessageState(
            icon = Icons.Filled.CloudOff,
            title = stringResource(R.string.state_error_network_title),
            body = stringResource(R.string.state_error_network_body),
            iconTint = EduTheme.colors.warning,
            primaryActionLabel = retryLabel,
            onPrimaryAction = onRetry,
            modifier = modifier,
        )

        AppError.SessionExpired -> MessageState(
            icon = Icons.Filled.Lock,
            title = stringResource(R.string.state_error_unauthorized_title),
            body = stringResource(R.string.state_error_unauthorized_body),
            iconTint = EduTheme.colors.warning,
            primaryActionLabel = stringResource(R.string.common_continue),
            onPrimaryAction = onSessionExpired ?: onRetry,
            modifier = modifier,
        )

        AppError.NotFound -> MessageState(
            icon = Icons.Filled.ErrorOutline,
            title = stringResource(R.string.state_error_not_found_title),
            body = stringResource(R.string.state_error_not_found_body),
            modifier = modifier,
        )

        AppError.Forbidden -> MessageState(
            icon = Icons.Filled.Lock,
            title = stringResource(R.string.state_error_not_found_title),
            body = stringResource(R.string.state_error_not_found_body),
            modifier = modifier,
        )

        AppError.Server -> MessageState(
            icon = Icons.Filled.ErrorOutline,
            title = stringResource(R.string.state_error_server_title),
            body = stringResource(R.string.state_error_server_body),
            iconTint = EduTheme.colors.danger,
            primaryActionLabel = retryLabel,
            onPrimaryAction = onRetry,
            modifier = modifier,
        )

        else -> MessageState(
            icon = Icons.Filled.ErrorOutline,
            title = stringResource(R.string.state_error_unknown_title),
            body = stringResource(R.string.state_error_unknown_body),
            iconTint = EduTheme.colors.danger,
            primaryActionLabel = retryLabel,
            onPrimaryAction = onRetry,
            modifier = modifier,
        )
    }
}

/** Hard block for the `direct` (sideloaded) flavour when the client is below minimum version. */
@Composable
fun UpdateRequiredState(
    onDownload: () -> Unit,
    modifier: Modifier = Modifier,
) {
    MessageState(
        icon = Icons.Filled.SystemUpdateAlt,
        title = stringResource(R.string.state_update_required_title),
        body = stringResource(R.string.state_update_required_body),
        iconTint = EduTheme.colors.warning,
        primaryActionLabel = stringResource(R.string.common_continue),
        onPrimaryAction = onDownload,
        modifier = modifier,
    )
}

/** Permission-denied state, distinct from an empty state so the fix is obvious. */
@Composable
fun PermissionDeniedState(
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    MessageState(
        icon = Icons.Filled.Lock,
        title = stringResource(R.string.state_permission_denied_title),
        body = stringResource(R.string.state_permission_denied_body),
        primaryActionLabel = stringResource(R.string.common_continue),
        onPrimaryAction = onOpenSettings,
        modifier = modifier,
    )
}

/**
 * Server-side maintenance window — the last of A-14's named states. Purely informational:
 * no retry action, because a retry cannot fix scheduled maintenance.
 */
@Composable
fun MaintenanceState(modifier: Modifier = Modifier) {
    MessageState(
        icon = Icons.Filled.Build,
        title = stringResource(R.string.state_maintenance_title),
        body = stringResource(R.string.state_maintenance_body),
        iconTint = EduTheme.colors.warning,
        modifier = modifier,
    )
}

/**
 * Default loading state — a skeleton, never a bare spinner, so the screen keeps its
 * shape and does not jump when content arrives.
 */
@Composable
fun DefaultLoadingState(modifier: Modifier = Modifier) {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md)
            .semantics { liveRegion = LiveRegionMode.Polite },
    ) {
        com.rork.eduspark.ui.components.surface.SkeletonCard()
        repeat(4) { com.rork.eduspark.ui.components.surface.SkeletonListItem() }
    }
}

/** Centred inline loader for small regions where a skeleton would be noisier than useful. */
@Composable
fun InlineLoader(modifier: Modifier = Modifier) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .padding(Spacing.section),
    ) {
        androidx.compose.material3.CircularProgressIndicator(
            color = EduTheme.colors.primary,
            strokeWidth = Sizing.hairline * 2,
            modifier = Modifier.size(Sizing.iconLg),
        )
    }
}
