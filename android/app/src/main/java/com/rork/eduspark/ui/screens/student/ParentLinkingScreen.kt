package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.PersonRemove
import androidx.compose.material.icons.filled.SupervisorAccount
import androidx.compose.material3.Icon
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LinkedParent
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import kotlinx.coroutines.launch
import org.koin.androidx.compose.koinViewModel

@Composable
fun ParentLinkingScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentLinkingViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    val clipboard = LocalClipboardManager.current
    val scope = rememberCoroutineScope()
    val copiedMessage = stringResource(R.string.st_parent_link_copied)

    EduScaffold(
        title = stringResource(R.string.st_parent_link_title),
        onBack = onBack,
        snackbarHostState = snackbarHostState,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLinkingSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentLinkingContent(
                data = data,
                onCopyCode = {
                    clipboard.setText(AnnotatedString(data.profile.parentLinkCode))
                    scope.launch { snackbarHostState.showSnackbar(copiedMessage) }
                },
                onRevokeParent = viewModel::requestRevokeParent,
            )
        }
    }

    val parentId = state.pendingRevokeParentId
    if (parentId != null) {
        val parentName = (state.result as? UiState.Content)?.data?.linkedParents
            ?.firstOrNull { it.id == parentId }?.name.orEmpty()
        ConfirmDialog(
            title = stringResource(R.string.st22_revoke_parent_title),
            body = stringResource(R.string.st22_revoke_parent_body, parentName),
            confirmLabel = stringResource(R.string.st22_revoke_confirm),
            onConfirm = viewModel::confirmRevokeParent,
            onDismiss = viewModel::cancelRevokeParent,
            isDestructive = true,
        )
    }
}

@Composable
private fun ParentLinkingContent(
    data: ParentLinkingData,
    onCopyCode: () -> Unit,
    onRevokeParent: (String) -> Unit,
) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.28f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(Sizing.avatar)
                            .background(colors.primaryContainer, CircleShape),
                    ) {
                        Icon(Icons.Filled.SupervisorAccount, contentDescription = null, tint = colors.primary)
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = stringResource(R.string.st_parent_link_code_label),
                            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                            color = colors.primary,
                        )
                        Text(
                            text = data.profile.parentLinkCode,
                            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.textPrimary,
                        )
                    }
                    EduIconButton(
                        icon = Icons.Filled.ContentCopy,
                        contentDescription = stringResource(R.string.st_parent_link_copy),
                        onClick = onCopyCode,
                    )
                }
                Text(
                    text = stringResource(R.string.st_parent_link_help),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                PrimaryButton(
                    text = stringResource(R.string.st_parent_link_copy),
                    onClick = onCopyCode,
                    leadingIcon = Icons.Filled.ContentCopy,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            }
            Spacer(modifier = Modifier.height(Spacing.section))
        }

        item { SectionHeader(title = stringResource(R.string.st_parent_link_linked_section)) }
        if (data.linkedParents.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.SupervisorAccount,
                    title = stringResource(R.string.st22_no_parents_title),
                    body = stringResource(R.string.st_parent_link_empty_body),
                )
            }
        } else {
            items(data.linkedParents, key = { it.id }) { parent ->
                LinkedParentAccessCard(parent = parent, onRevoke = { onRevokeParent(parent.id) })
                Spacer(modifier = Modifier.height(Spacing.sm))
            }
        }
    }
}

@Composable
private fun LinkedParentAccessCard(parent: LinkedParent, onRevoke: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.neutralAlpha100, CircleShape),
            ) {
                Icon(Icons.Filled.SupervisorAccount, contentDescription = null, tint = colors.textSecondary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(parent.name, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                Text(
                    text = stringResource(R.string.st22_parent_relationship_format, parent.relationship, parent.email),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
            EduIconButton(
                icon = Icons.Filled.PersonRemove,
                contentDescription = stringResource(R.string.st22_revoke_parent_action),
                tint = colors.danger,
                onClick = onRevoke,
            )
        }
    }
}

@Composable
private fun ParentLinkingSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
    }
}
