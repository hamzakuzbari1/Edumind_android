package com.rork.eduspark.ui.screens.student

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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.model.ProjectTeam
import com.rork.eduspark.data.model.SharedDeliverable
import com.rork.eduspark.data.model.TeamMember
import com.rork.eduspark.data.model.TeamMessage
import com.rork.eduspark.data.model.TeamRole
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.ai.UserMessageBubble
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-08 · Team Workspace.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Overview is the default tab — chat is a second, opt-in tab behind [EduChip] toggles, not
 * the dominant surface, so this reads as a project workspace, never a Slack/Discord clone.
 * [MemberRow] never shows a real photo, only an initial; the current student's own row is the
 * only one carrying [TeamMember.isCurrentStudent]. Chat reuses [UserMessageBubble] for the
 * student's own lines (it carries no AI marking, so it fits a peer-to-peer thread as-is);
 * other members render through the new [PeerMessageBubble] below, deliberately NOT
 * [com.rork.eduspark.ui.components.ai.AiMessageBubble] — that bubble's jouri border/disclosure
 * would falsely claim a teammate's message is AI-generated.
 */
@Composable
fun TeamWorkspaceScreen(
    projectId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeamWorkspaceViewModel = koinViewModel(parameters = { parametersOf(projectId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.pj08_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeamWorkspaceSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            Column(modifier = Modifier.fillMaxSize()) {
                TeamHeader(projectTitle = data.projectTitle, team = data.team)
                TabSelector(tab = state.tab, onSelectTab = viewModel::selectTab)
                when (state.tab) {
                    TeamWorkspaceTab.Overview -> OverviewContent(
                        data = data,
                        onAssignToMe = viewModel::assignToMe,
                        onUnassignMine = viewModel::unassignMine,
                        modifier = Modifier.weight(1f),
                    )
                    TeamWorkspaceTab.Chat -> ChatContent(
                        team = data.team,
                        isSending = state.isSendingMessage,
                        onSend = viewModel::sendMessage,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

@Composable
private fun TeamHeader(projectTitle: String, team: ProjectTeam) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
    ) {
        Text(projectTitle, style = EduTheme.typography.caption, color = colors.primary)
        Text(
            text = team.teamName,
            style = EduTheme.typography.titleLg,
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Text(
            text = stringResource(R.string.pj08_member_count, numeral(team.members.size)),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun TabSelector(tab: TeamWorkspaceTab, onSelectTab: (TeamWorkspaceTab) -> Unit) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.padding(horizontal = Spacing.gutter, vertical = Spacing.xs),
    ) {
        EduChip(
            label = stringResource(R.string.pj08_tab_overview),
            selected = tab == TeamWorkspaceTab.Overview,
            onClick = { onSelectTab(TeamWorkspaceTab.Overview) },
        )
        EduChip(
            label = stringResource(R.string.pj08_tab_chat),
            selected = tab == TeamWorkspaceTab.Chat,
            onClick = { onSelectTab(TeamWorkspaceTab.Chat) },
        )
    }
}

@Composable
private fun OverviewContent(
    data: TeamWorkspaceScreenData,
    onAssignToMe: (String) -> Unit,
    onUnassignMine: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val team = data.team
    val self = team.members.firstOrNull { it.isCurrentStudent }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = modifier.fillMaxSize(),
    ) {
        item { SectionHeader(title = stringResource(R.string.pj08_members_section)) }
        items(team.members, key = { it.id }) { member -> MemberRow(member) }

        item { SectionHeader(title = stringResource(R.string.pj08_tasks_section)) }
        items(data.tasks, key = { it.id }) { task ->
            val assignment = team.taskAssignments.firstOrNull { it.taskId == task.id }
            val assignee = team.members.firstOrNull { it.id == assignment?.assigneeMemberId }
            TaskAssignmentRow(
                task = task,
                assignee = assignee,
                isMine = self != null && assignee?.id == self.id,
                onAssignToMe = { onAssignToMe(task.id) },
                onUnassign = { onUnassignMine(task.id) },
            )
        }

        item {
            SectionHeader(title = stringResource(R.string.pj08_deliverable_section))
            DeliverableCard(deliverable = team.deliverable, members = team.members)
        }
    }
}

@Composable
private fun MemberRow(member: TeamMember) {
    val colors = EduTheme.colors
    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(
                    text = member.displayName.take(1),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.primary,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(member.displayName, style = EduTheme.typography.body, color = colors.textPrimary)
                Text(teamRoleLabel(member.role), style = EduTheme.typography.caption, color = colors.textSecondary)
            }
            if (member.isCurrentStudent) {
                StatusPill(
                    label = stringResource(R.string.pj08_you_badge),
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
            }
        }
    }
}

@Composable
private fun TaskAssignmentRow(
    task: ProjectTask,
    assignee: TeamMember?,
    isMine: Boolean,
    onAssignToMe: () -> Unit,
    onUnassign: () -> Unit,
) {
    val colors = EduTheme.colors
    val statusColor = projectTaskStatusColor(task.status)
    EduCard {
        Text(task.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        ) {
            StatusPill(
                label = projectTaskStatusLabel(task.status),
                contentColor = statusColor,
                containerColor = statusColor.copy(alpha = 0.14f),
            )
            Text(
                text = assignee?.displayName ?: stringResource(R.string.pj08_unassigned),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
        }
        when {
            assignee == null -> SecondaryButton(
                text = stringResource(R.string.pj08_assign_to_me),
                onClick = onAssignToMe,
                modifier = Modifier.padding(top = Spacing.xs),
            )
            isMine -> GhostButton(
                text = stringResource(R.string.pj08_unassign),
                onClick = onUnassign,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun DeliverableCard(deliverable: SharedDeliverable, members: List<TeamMember>) {
    val colors = EduTheme.colors
    val lastUpdatedBy = members.firstOrNull { it.id == deliverable.lastUpdatedByMemberId }?.displayName.orEmpty()
    EduCard {
        Text(deliverable.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        StatusPill(
            label = deliverable.stateLabel,
            contentColor = colors.primary,
            containerColor = colors.primaryContainer,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Text(
            text = stringResource(R.string.pj08_deliverable_updated_by, lastUpdatedBy, deliverable.lastUpdatedAtLabel),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        if (deliverable.referenceLabel != null) {
            Text(
                text = deliverable.referenceLabel,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

@Composable
private fun ChatContent(team: ProjectTeam, isSending: Boolean, onSend: (String) -> Unit, modifier: Modifier = Modifier) {
    val listState = rememberLazyListState()

    LaunchedEffect(team.messages.size) {
        if (team.messages.isNotEmpty()) listState.animateScrollToItem(team.messages.size - 1)
    }

    Column(modifier = modifier.fillMaxSize()) {
        LazyColumn(
            state = listState,
            contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.weight(1f),
        ) {
            items(team.messages, key = { it.id }) { message ->
                val sender = team.members.firstOrNull { it.id == message.senderMemberId }
                if (sender?.isCurrentStudent == true) {
                    UserMessageBubble(text = message.text)
                } else {
                    PeerMessageBubble(senderName = sender?.displayName.orEmpty(), message = message)
                }
            }
        }
        TeamChatInputBar(enabled = !isSending, onSend = onSend)
    }
}

/** A team member's own line — deliberately not [com.rork.eduspark.ui.components.ai.AiMessageBubble]; see this file's own doc comment for why. */
@Composable
private fun PeerMessageBubble(senderName: String, message: TeamMessage) {
    val colors = EduTheme.colors
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = stringResource(R.string.pj08_message_sender_format, senderName, message.sentAtLabel),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(bottom = Spacing.xxs),
        )
        Row(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = message.text,
                style = EduTheme.typography.bodyLg,
                color = colors.textPrimary,
                modifier = Modifier
                    .background(colors.neutralAlpha100, RoundedCornerShape(Radius.md))
                    .padding(Spacing.card),
            )
            Box(modifier = Modifier.width(Spacing.lg))
        }
    }
}

@Composable
private fun TeamChatInputBar(enabled: Boolean, onSend: (String) -> Unit) {
    var input by rememberSaveable { mutableStateOf("") }
    val colors = EduTheme.colors

    Row(
        verticalAlignment = Alignment.Bottom,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
    ) {
        EduTextField(
            value = input,
            onValueChange = { input = it },
            label = stringResource(R.string.pj08_message_hint),
            enabled = enabled,
            labelPlacement = FieldLabelPlacement.Floating,
            modifier = Modifier.weight(1f),
        )
        EduIconButton(
            icon = Icons.AutoMirrored.Filled.Send,
            contentDescription = stringResource(R.string.pj08_send_message),
            enabled = enabled && input.isNotBlank(),
            onClick = {
                onSend(input)
                input = ""
            },
        )
    }
}

@Composable
private fun teamRoleLabel(role: TeamRole): String = when (role) {
    TeamRole.Leader -> stringResource(R.string.pj08_role_leader)
    TeamRole.Member -> stringResource(R.string.pj08_role_member)
}

@Composable
private fun TeamWorkspaceSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}

