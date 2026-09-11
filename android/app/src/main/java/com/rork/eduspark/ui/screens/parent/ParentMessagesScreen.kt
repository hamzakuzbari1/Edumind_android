package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.MessageAttachmentType
import com.rork.eduspark.data.model.MessagingChatMessage
import com.rork.eduspark.data.model.MessageThread
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.ui.components.input.SearchField
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.screens.messaging.parentRelativeMessageTimeLabel
import com.rork.eduspark.ui.screens.messaging.rememberMessageRelativeNowMillis
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun ParentMessagesScreen(
    onOpenLinkStudent: () -> Unit,
    onOpenThread: (threadId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentMessagesViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val nowMillis = rememberMessageRelativeNowMillis()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is ParentMessagesEvent.OpenThread -> onOpenThread(event.threadId)
            }
        }
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { ParentMessagesSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        ParentMessagesContent(
            data = data,
            searchQuery = state.searchQuery,
            onSearchChange = viewModel::updateSearchQuery,
            onOpenLinkStudent = onOpenLinkStudent,
            onThreadTap = viewModel::onThreadTapped,
            nowMillis = nowMillis,
        )
    }
}

@Composable
private fun ParentMessagesContent(
    data: ParentMessagesData,
    searchQuery: String,
    onSearchChange: (String) -> Unit,
    onOpenLinkStudent: () -> Unit,
    onThreadTap: (String) -> Unit,
    nowMillis: Long,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentMessagesEmptyState(onOpenLinkStudent = onOpenLinkStudent)
        return
    }

    val selectedStudent = data.linkedStudents.first()
    val filtered = data.threads.filter { thread ->
        val teacher = thread.otherParticipant(data.viewerId)
        val preview = thread.lastMessage?.body.orEmpty()
        searchQuery.isBlank() ||
            teacher.displayName.contains(searchQuery, ignoreCase = true) ||
            teacher.contextLabel.contains(searchQuery, ignoreCase = true) ||
            preview.contains(searchQuery, ignoreCase = true)
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            ParentLinkedStudentCard(student = selectedStudent)
        }
        item {
            SearchField(
                value = searchQuery,
                onValueChange = onSearchChange,
                placeholder = stringResource(R.string.pr12_search_hint),
            )
        }
        item {
            SectionHeader(title = stringResource(R.string.pr12_conversations_section))
        }

        when {
            data.threads.isEmpty() -> item {
                ParentMessagesNoThreadsState()
            }

            filtered.isEmpty() -> item {
                ParentMessagesSearchEmptyState()
            }

            else -> items(filtered, key = { it.id }) { thread ->
                ParentConversationRow(
                    thread = thread,
                    viewerId = data.viewerId,
                    student = selectedStudent,
                    nowMillis = nowMillis,
                    onClick = { onThreadTap(thread.id) },
                )
            }
        }
        item { Spacer(modifier = Modifier.height(Spacing.section)) }
    }
}

@Composable
private fun ParentMessagesEmptyState(onOpenLinkStudent: () -> Unit) {
    MessageState(
        icon = Icons.Filled.Link,
        title = stringResource(R.string.pr12_empty_title),
        body = stringResource(R.string.pr12_empty_body),
        primaryActionLabel = stringResource(R.string.pr02_empty_action),
        onPrimaryAction = onOpenLinkStudent,
        modifier = Modifier.fillMaxSize(),
    )
}

@Composable
private fun ParentMessagesNoThreadsState() {
    MessageState(
        icon = Icons.Filled.Forum,
        title = stringResource(R.string.pr12_no_threads_title),
        body = stringResource(R.string.pr12_no_threads_body),
        modifier = Modifier.height(320.dp),
    )
}

@Composable
private fun ParentMessagesSearchEmptyState() {
    MessageState(
        icon = Icons.Filled.Forum,
        title = stringResource(R.string.pr12_search_empty_title),
        body = stringResource(R.string.pr12_search_empty_body),
        modifier = Modifier.height(320.dp),
    )
}

@Composable
private fun ParentConversationRow(
    thread: MessageThread,
    viewerId: String,
    student: ParentLinkedStudent,
    nowMillis: Long,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val teacher = thread.otherParticipant(viewerId)
    val unread = thread.unreadCountFor(viewerId)
    val last = thread.lastMessage
    val voiceLabel = stringResource(R.string.x01_voice_message_preview)
    val preview = last?.let { parentMessagePreview(it, voiceLabel) }.orEmpty()
    val timeLabel = last?.let { parentRelativeMessageTimeLabel(it, nowMillis) }.orEmpty()
    val rowLabel = stringResource(
        R.string.pr12_thread_row_a11y,
        teacher.displayName,
        teacher.contextLabel,
        timeLabel,
    )

    EduCard(onClick = onClick, onClickLabel = rowLabel) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(
                    text = teacher.avatarInitial,
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.primary,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        text = teacher.displayName,
                        style = EduTheme.typography.body.copy(
                            fontWeight = if (unread > 0) FontWeight.ExtraBold else FontWeight.SemiBold,
                        ),
                        color = colors.textPrimary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    if (last != null) {
                        Text(
                            text = timeLabel,
                            style = EduTheme.typography.caption,
                            color = if (unread > 0) colors.primary else colors.textSecondary,
                        )
                    }
                }
                if (teacher.contextLabel.isNotBlank()) {
                    Text(
                        text = teacher.contextLabel,
                        style = EduTheme.typography.caption,
                        color = colors.primary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Text(
                    text = stringResource(R.string.pr12_for_student, student.displayName),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.padding(top = Spacing.xxs),
                ) {
                    if (last?.body.isNullOrBlank() && last?.attachment?.type == MessageAttachmentType.Voice) {
                        Icon(
                            imageVector = Icons.Filled.Mic,
                            contentDescription = null,
                            tint = colors.textSecondary,
                            modifier = Modifier.size(Sizing.iconSm),
                        )
                    }
                    Text(
                        text = preview,
                        style = EduTheme.typography.caption,
                        color = if (unread > 0) colors.textPrimary else colors.textSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    if (unread > 0) {
                        ParentUnreadBadge(unread = unread)
                    } else {
                        StatusPill(
                            label = stringResource(R.string.x02_role_teacher),
                            contentColor = colors.textSecondary,
                            containerColor = colors.neutralAlpha100,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ParentUnreadBadge(unread: Int) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .defaultMinSize(minWidth = Sizing.iconSm, minHeight = Sizing.iconSm)
            .background(EduTheme.colors.primary, RoundedCornerShape(Radius.pill))
            .padding(horizontal = 5.dp, vertical = 1.dp),
    ) {
        Text(
            text = numeral(if (unread > 9) 9 else unread),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.onPrimary,
        )
    }
}

private fun parentMessagePreview(message: MessagingChatMessage, voiceLabel: String): String {
    if (message.body.isNotBlank()) return message.body
    val attachment = message.attachment ?: return ""
    return if (attachment.type == MessageAttachmentType.Voice) voiceLabel else attachment.label
}

@Composable
private fun ParentMessagesSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonListItem()
        repeat(3) { SkeletonCard() }
    }
}
