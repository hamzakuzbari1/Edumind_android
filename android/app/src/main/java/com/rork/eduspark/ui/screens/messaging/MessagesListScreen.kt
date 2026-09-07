package com.rork.eduspark.ui.screens.messaging

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.MessagingChatMessage
import com.rork.eduspark.data.model.MessageAttachmentType
import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.MessageThread
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.SearchField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * X-01 · Messages List.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Student inbox rows stay the original [EduCard] treatment. Teacher rows are a flatter
 * scan list — same [MessagingRepository] threads, same unread counts, category filter only.
 */
@Composable
fun MessagesListScreen(
    onBack: () -> Unit,
    onOpenThread: (threadId: String) -> Unit,
    onOpenNewConversation: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: MessagesListViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is MessagesListEvent.OpenThread -> onOpenThread(event.threadId)
                MessagesListEvent.OpenNewConversation -> onOpenNewConversation()
            }
        }
    }

    EduScaffold(
        title = stringResource(R.string.x01_title),
        onBack = onBack,
        actions = {
            EduIconButton(
                icon = Icons.Filled.Add,
                contentDescription = stringResource(R.string.x01_new_conversation),
                onClick = viewModel::onNewConversationTapped,
            )
        },
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { MessagesListSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { threads ->
            MessagesListContent(
                threads = threads,
                viewerId = state.viewerId,
                viewerIsTeacher = state.viewerRole == MessageParticipantRole.Teacher,
                category = state.category,
                searchQuery = state.searchQuery,
                onCategoryChange = viewModel::selectCategory,
                onSearchChange = viewModel::updateSearchQuery,
                onThreadTap = viewModel::onThreadTapped,
                onStartConversation = viewModel::onNewConversationTapped,
            )
        }
    }
}

@Composable
private fun MessagesListContent(
    threads: List<MessageThread>,
    viewerId: String,
    viewerIsTeacher: Boolean,
    category: MessagesListCategory,
    searchQuery: String,
    onCategoryChange: (MessagesListCategory) -> Unit,
    onSearchChange: (String) -> Unit,
    onThreadTap: (String) -> Unit,
    onStartConversation: () -> Unit,
) {
    val categorized = if (viewerIsTeacher) {
        threads.filter { thread ->
            val role = thread.otherParticipant(viewerId).role
            when (category) {
                MessagesListCategory.Students -> role == MessageParticipantRole.Student
                MessagesListCategory.Parents -> role == MessageParticipantRole.Parent
            }
        }
    } else {
        threads
    }
    val filtered = categorized.filter { thread ->
        val other = thread.otherParticipant(viewerId)
        searchQuery.isBlank() ||
            other.displayName.contains(searchQuery, ignoreCase = true) ||
            other.contextLabel.contains(searchQuery, ignoreCase = true) ||
            (thread.lastMessage?.body?.contains(searchQuery, ignoreCase = true) == true)
    }

    LazyColumn(
        contentPadding = PaddingValues(bottom = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            SearchField(
                value = searchQuery,
                onValueChange = onSearchChange,
                placeholder = if (viewerIsTeacher) {
                    stringResource(R.string.tc12_search_hint)
                } else {
                    stringResource(R.string.common_search_hint)
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = Spacing.gutter)
                    .padding(top = Spacing.md, bottom = Spacing.sm),
            )
        }

        if (viewerIsTeacher) {
            item {
                MessagesCategoryTabs(
                    selected = category,
                    onSelect = onCategoryChange,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = Spacing.gutter)
                        .padding(bottom = Spacing.sm),
                )
            }
        }

        if (!viewerIsTeacher && threads.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Forum,
                    title = stringResource(R.string.x01_empty_title),
                    body = stringResource(R.string.x01_empty_body),
                    primaryActionLabel = stringResource(R.string.x01_new_conversation),
                    onPrimaryAction = onStartConversation,
                )
            }
        } else if (categorized.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Forum,
                    title = if (viewerIsTeacher && category == MessagesListCategory.Parents) {
                        stringResource(R.string.x01_empty_parents)
                    } else if (viewerIsTeacher) {
                        stringResource(R.string.x01_empty_students)
                    } else {
                        stringResource(R.string.x01_empty_title)
                    },
                    body = stringResource(R.string.x01_empty_body),
                    primaryActionLabel = stringResource(R.string.x01_new_conversation),
                    onPrimaryAction = onStartConversation,
                )
            }
        } else if (filtered.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Forum,
                    title = if (viewerIsTeacher) {
                        stringResource(R.string.x01_teacher_search_empty)
                    } else {
                        stringResource(R.string.x01_search_empty_title)
                    },
                    body = stringResource(R.string.x01_search_empty_body),
                )
            }
        } else if (viewerIsTeacher) {
            itemsIndexed(filtered, key = { _, thread -> thread.id }) { index, thread ->
                TeacherConversationRow(
                    thread = thread,
                    viewerId = viewerId,
                    onClick = { onThreadTap(thread.id) },
                )
                if (index < filtered.lastIndex) {
                    EduDivider(modifier = Modifier.padding(start = Spacing.gutter + Sizing.avatar + Spacing.sm, end = Spacing.gutter))
                }
            }
        } else {
            itemsIndexed(filtered, key = { _, thread -> thread.id }) { _, thread ->
                ThreadRow(
                    thread = thread,
                    viewerId = viewerId,
                    onClick = { onThreadTap(thread.id) },
                    modifier = Modifier.padding(horizontal = Spacing.gutter),
                )
            }
        }
    }
}

@Composable
private fun MessagesCategoryTabs(
    selected: MessagesListCategory,
    onSelect: (MessagesListCategory) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    val selectedLabel = stringResource(R.string.a11y_selected)

    Row(
        modifier = modifier
            .height(Sizing.touchTarget)
            .background(colors.neutralAlpha100, shape)
            .padding(Spacing.xxs),
    ) {
        MessagesListCategory.entries.forEach { option ->
            val isSelected = option == selected
            val label = when (option) {
                MessagesListCategory.Students -> stringResource(R.string.tab_teacher_students)
                MessagesListCategory.Parents -> stringResource(R.string.x01_category_parents)
            }
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .background(if (isSelected) colors.primaryContainer else Color.Transparent, shape)
                    .eduClickable(role = Role.Tab, onClick = { onSelect(option) })
                    .semantics {
                        this.selected = isSelected
                        if (isSelected) stateDescription = selectedLabel
                    },
            ) {
                Text(
                    text = label,
                    style = EduTheme.typography.caption.copy(
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Medium,
                    ),
                    color = if (isSelected) colors.primary else colors.textSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}

@Composable
private fun TeacherConversationRow(
    thread: MessageThread,
    viewerId: String,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val other = thread.otherParticipant(viewerId)
    val unread = thread.unreadCountFor(viewerId)
    val last = thread.lastMessage
    val voiceLabel = stringResource(R.string.x01_voice_message_preview)
    val preview = last?.let { previewFor(it, voiceLabel) }.orEmpty()
    val relationship = parentRelationshipLabel(other)
    val isVoicePreview = last?.body.isNullOrBlank() && last?.attachment?.type == MessageAttachmentType.Voice

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .eduClickable(onClick = onClick)
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .padding(horizontal = Spacing.gutter, vertical = Spacing.xs),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(Sizing.avatar)
                .background(colors.primaryContainer, CircleShape),
        ) {
            Text(
                other.avatarInitial,
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.Bold),
                color = colors.primary,
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = other.displayName,
                    style = EduTheme.typography.body.copy(
                        fontWeight = if (unread > 0) FontWeight.ExtraBold else FontWeight.Bold,
                    ),
                    color = colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                if (last != null) {
                    Text(
                        last.sentAtLabel,
                        style = EduTheme.typography.caption,
                        color = if (unread > 0) colors.primary else colors.textSecondary,
                        modifier = Modifier.padding(start = Spacing.xs),
                    )
                }
            }
            if (relationship != null) {
                Text(
                    text = relationship,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier.padding(top = Spacing.xxs),
            ) {
                if (isVoicePreview) {
                    Icon(
                        Icons.Filled.Mic,
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
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .defaultMinSize(minWidth = Sizing.iconSm, minHeight = Sizing.iconSm)
                            .background(colors.primary, CircleShape)
                            .padding(horizontal = 5.dp, vertical = 1.dp),
                    ) {
                        Text(
                            numeral(if (unread > 9) 9 else unread),
                            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                            color = colors.onPrimary,
                        )
                    }
                }
            }
        }
    }
}

private fun parentRelationshipLabel(other: MessageParticipant): String? {
    if (other.role != MessageParticipantRole.Parent) return null
    val label = other.contextLabel.substringBefore(" · ").ifBlank { other.contextLabel }
    return label.ifBlank { null }
}

@Composable
private fun ThreadRow(
    thread: MessageThread,
    viewerId: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val other = thread.otherParticipant(viewerId)
    val unread = thread.unreadCountFor(viewerId)
    val last = thread.lastMessage

    EduCard(onClick = onClick, modifier = modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(other.avatarInitial, style = EduTheme.typography.title, color = colors.primary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
                        Text(
                            text = other.displayName,
                            style = EduTheme.typography.body.copy(fontWeight = if (unread > 0) FontWeight.Bold else FontWeight.SemiBold),
                            color = colors.textPrimary,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f, fill = false),
                        )
                        if (other.role == MessageParticipantRole.Teacher) {
                            Text(
                                text = stringResource(R.string.x02_role_teacher),
                                style = EduTheme.typography.caption,
                                color = colors.primary,
                                modifier = Modifier
                                    .padding(start = Spacing.xxs)
                                    .background(colors.primaryContainer, RoundedCornerShape(Radius.pill))
                                    .padding(horizontal = Spacing.xs, vertical = 1.dp),
                            )
                        }
                    }
                    if (last != null) {
                        Text(last.sentAtLabel, style = EduTheme.typography.caption, color = colors.textSecondary)
                    }
                }
                if (other.contextLabel.isNotBlank()) {
                    Text(other.contextLabel, style = EduTheme.typography.caption, color = colors.primary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.xxs)) {
                    val voiceLabel = stringResource(R.string.x01_voice_message_preview)
                    val isVoicePreview = last?.body.isNullOrBlank() && last?.attachment?.type == MessageAttachmentType.Voice
                    if (isVoicePreview) {
                        Icon(Icons.Filled.Mic, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
                    }
                    Text(
                        text = last?.let { previewFor(it, voiceLabel) } ?: "",
                        style = EduTheme.typography.caption,
                        color = if (unread > 0) colors.textPrimary else colors.textSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    if (unread > 0) {
                        Box(
                            contentAlignment = Alignment.Center,
                            modifier = Modifier
                                .size(Sizing.iconSm)
                                .background(colors.danger, RoundedCornerShape(Radius.pill)),
                        ) {
                            Text(numeral(if (unread > 9) 9 else unread), style = EduTheme.typography.caption, color = colors.surface)
                        }
                    }
                }
            }
        }
    }
}

private fun previewFor(message: MessagingChatMessage, voiceLabel: String): String {
    if (message.body.isNotBlank()) return message.body
    val attachment = message.attachment ?: return ""
    return if (attachment.type == MessageAttachmentType.Voice) voiceLabel else attachment.label
}

@Composable
private fun MessagesListSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        repeat(4) { SkeletonListItem() }
    }
}
