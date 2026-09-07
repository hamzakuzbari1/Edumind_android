package com.rork.eduspark.ui.screens.messaging

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.ui.components.input.SearchField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * X-03 · New Conversation.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Contact rows reuse the exact [EduCard] + avatar-circle shape X-01's own thread rows and
 * [com.rork.eduspark.ui.screens.teacher.TeacherStudentsScreen]'s student rows already use —
 * the same list language throughout Messages, never a distinct "picker" style.
 */
@Composable
fun NewConversationScreen(
    onBack: () -> Unit,
    onOpenThread: (threadId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: NewConversationViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is NewConversationEvent.ThreadReady -> onOpenThread(event.threadId)
            }
        }
    }

    EduScaffold(
        title = stringResource(R.string.x03_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { NewConversationSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { contacts ->
            NewConversationContent(
                contacts = contacts,
                searchQuery = state.searchQuery,
                onSearchChange = viewModel::updateSearchQuery,
                onContactTap = viewModel::onContactTapped,
            )
        }
    }
}

@Composable
private fun NewConversationContent(
    contacts: List<MessageParticipant>,
    searchQuery: String,
    onSearchChange: (String) -> Unit,
    onContactTap: (String) -> Unit,
) {
    val filtered = contacts.filter {
        searchQuery.isBlank() ||
            it.displayName.contains(searchQuery, ignoreCase = true) ||
            it.contextLabel.contains(searchQuery, ignoreCase = true)
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            SearchField(
                value = searchQuery,
                onValueChange = onSearchChange,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.sm),
            )
        }

        if (contacts.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Groups,
                    title = stringResource(R.string.x03_empty_title),
                    body = stringResource(R.string.x03_empty_body),
                )
            }
        } else if (filtered.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Groups,
                    title = stringResource(R.string.x01_search_empty_title),
                    body = stringResource(R.string.x01_search_empty_body),
                )
            }
        } else {
            items(filtered, key = { it.id }) { contact ->
                ContactRow(contact = contact, onClick = { onContactTap(contact.id) })
            }
        }
    }
}

@Composable
private fun ContactRow(contact: MessageParticipant, onClick: () -> Unit) {
    val colors = EduTheme.colors

    EduCard(onClick = onClick, modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.zaytounSoft, CircleShape),
            ) {
                Text(contact.avatarInitial, style = EduTheme.typography.title, color = colors.zaytoun)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = contact.displayName,
                    style = EduTheme.typography.body.copy(fontWeight = androidx.compose.ui.text.font.FontWeight.SemiBold),
                    color = colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = messageParticipantRoleLabel(contact.role),
                    style = EduTheme.typography.caption,
                    color = colors.zaytoun,
                )
                if (contact.contextLabel.isNotBlank()) {
                    Text(
                        text = contact.contextLabel,
                        style = EduTheme.typography.caption,
                        color = colors.textMuted,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
private fun NewConversationSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        repeat(4) { SkeletonListItem() }
    }
}
