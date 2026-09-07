package com.rork.eduspark.ui.screens.messaging

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.MarkChatUnread
import androidx.compose.material.icons.filled.NotificationsNone
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material3.Icon
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.data.model.StudentNotification
import com.rork.eduspark.data.model.StudentNotificationType
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.nav.SheetHandle
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

@Composable
@OptIn(ExperimentalMaterial3Api::class)
fun StudentNotificationsSheet(
    state: NotificationsPanelUiState,
    onDismiss: () -> Unit,
    onMarkAllRead: () -> Unit,
    onNotificationClick: (StudentNotification) -> Unit,
    modifier: Modifier = Modifier,
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = EduTheme.colors.surface,
        dragHandle = null,
        modifier = modifier,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter)
                .padding(bottom = Spacing.section),
        ) {
            SheetHandle(modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.md))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.x04_title),
                        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                        color = EduTheme.colors.textPrimary,
                    )
                    Text(
                        text = stringResource(R.string.x04_subtitle),
                        style = EduTheme.typography.caption,
                        color = EduTheme.colors.textSecondary,
                    )
                }
                if (state.unreadCount > 0) {
                    GhostButton(text = stringResource(R.string.x04_mark_all_read), onClick = onMarkAllRead)
                }
                EduIconButton(
                    icon = Icons.Filled.Close,
                    contentDescription = stringResource(R.string.common_close),
                    onClick = onDismiss,
                )
            }

            Spacer(modifier = Modifier.height(Spacing.md))

            if (state.notifications.isEmpty() && !state.isLoading) {
                MessageState(
                    icon = Icons.Filled.NotificationsNone,
                    title = stringResource(R.string.x04_empty_title),
                    body = stringResource(R.string.x04_empty_body),
                    modifier = Modifier.fillMaxWidth(),
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(bottom = Spacing.sm),
                    verticalArrangement = Arrangement.spacedBy(Spacing.sm),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    items(state.notifications, key = { it.id }) { notification ->
                        NotificationRow(
                            notification = notification,
                            onClick = { onNotificationClick(notification) },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun NotificationRow(
    notification: StudentNotification,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val accent = when (notification.type) {
        StudentNotificationType.InternalMessage -> colors.primary
        StudentNotificationType.PaymentStatus -> colors.success
        StudentNotificationType.LessonUpdate -> colors.highlight
        StudentNotificationType.Achievement -> colors.warning
    }
    EduCard(
        onClick = onClick,
        borderColor = if (notification.isRead) colors.border else accent.copy(alpha = 0.42f),
        contentPadding = PaddingValues(Spacing.sm),
    ) {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(accent.copy(alpha = 0.12f), CircleShape),
            ) {
                Icon(
                    imageVector = notification.type.icon(),
                    contentDescription = null,
                    tint = accent,
                    modifier = Modifier.size(22.dp),
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                ) {
                    Text(
                        text = notification.title,
                        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    if (!notification.isRead) {
                        StatusPill(
                            label = stringResource(R.string.x04_unread),
                            contentColor = accent,
                            containerColor = accent.copy(alpha = 0.12f),
                        )
                    }
                }
                Text(
                    text = notification.body,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Text(
                    text = notification.timestampLabel,
                    style = EduTheme.typography.caption,
                    color = colors.textTertiary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
            if (notification.isRead) {
                Icon(
                    imageVector = Icons.Filled.CheckCircle,
                    contentDescription = null,
                    tint = colors.success,
                    modifier = Modifier.size(18.dp),
                )
            }
        }
    }
}

private fun StudentNotificationType.icon(): ImageVector = when (this) {
    StudentNotificationType.InternalMessage -> Icons.Filled.MarkChatUnread
    StudentNotificationType.PaymentStatus -> Icons.Filled.Payments
    StudentNotificationType.LessonUpdate -> Icons.Filled.AutoStories
    StudentNotificationType.Achievement -> Icons.Filled.EmojiEvents
}
