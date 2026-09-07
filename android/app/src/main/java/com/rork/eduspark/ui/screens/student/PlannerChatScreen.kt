package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.PlannerChangeProposal
import com.rork.eduspark.data.model.PlannerChatSender
import com.rork.eduspark.data.model.ProposalStatus
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.ai.AiMessageBubble
import com.rork.eduspark.ui.components.ai.AiTypingIndicator
import com.rork.eduspark.ui.components.ai.UserMessageBubble
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-11 · Planner AI Chat.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Every proposed change renders as a diff card the student must explicitly Accept or
 * Reject — nothing here ever mutates the plan on its own. Only [PlannerChatViewModel.accept]
 * writes through to [com.rork.eduspark.data.repository.PlannerRepository]; Reject just marks
 * the card locally and leaves the plan untouched, exactly as required.
 *
 * The assistant's replies are template text over regex parsing (Source Audit §6/§7), but
 * they are still AI-mediated planner assistance, so they render through [AiMessageBubble]
 * and carry aiAccent marking like every other AI surface in the app.
 */
@Composable
fun PlannerChatScreen(
    onBack: () -> Unit,
    onOpenExamCapture: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PlannerChatViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    var showExamCaptureOptions by rememberSaveable { mutableStateOf(false) }
    val examIntentMessage = stringResource(R.string.st11_exam_intent_message)

    LaunchedEffect(state.messages.size, state.isSending) {
        val lastIndex = state.messages.size - 1 + if (state.isSending) 1 else 0
        if (lastIndex >= 0) listState.animateScrollToItem(lastIndex)
    }

    EduScaffold(
        title = stringResource(R.string.st11_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        Column(modifier = Modifier.fillMaxSize()) {
            Box(modifier = Modifier.weight(1f)) {
                if (state.messages.isEmpty()) {
                    EmptyPlannerChatState(onSuggestionTap = { viewModel.sendMessage(it) })
                } else {
                    LazyColumn(
                        state = listState,
                        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
                        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
                        modifier = Modifier.fillMaxSize(),
                    ) {
                        items(state.messages, key = { it.id }) { message ->
                            when (message.sender) {
                                PlannerChatSender.Student -> UserMessageBubble(text = message.text)
                                PlannerChatSender.Assistant -> AiMessageBubble(
                                    text = message.text,
                                    footer = {
                                        val proposal = message.proposedChange
                                        if (proposal != null) {
                                            DiffCard(
                                                proposal = proposal,
                                                onAccept = { viewModel.accept(message.id, proposal.id) },
                                                onReject = { viewModel.reject(message.id, proposal.id) },
                                            )
                                        }
                                    },
                                )
                            }
                        }
                        if (state.isSending) {
                            item(key = "typing") { AiTypingIndicator(modifier = Modifier.padding(vertical = Spacing.xs)) }
                        }
                        if (state.error != null) {
                            item(key = "error") { PlannerChatErrorRow() }
                        }
                    }
                }
            }

            PlannerChatInputBar(
                enabled = !state.isSending,
                onSend = { text -> viewModel.sendMessage(text) },
                onAttachmentClick = { showExamCaptureOptions = true },
            )
        }
    }

    if (showExamCaptureOptions) {
        ExamCaptureOptionsDialog(
            onDismiss = { showExamCaptureOptions = false },
            onSelect = {
                showExamCaptureOptions = false
                viewModel.announceExamCaptureIntent(examIntentMessage)
                onOpenExamCapture()
            },
        )
    }
}

@Composable
private fun EmptyPlannerChatState(onSuggestionTap: (String) -> Unit) {
    val colors = EduTheme.colors
    val suggestions = listOf(
        stringResource(R.string.st11_suggestion_1),
        stringResource(R.string.st11_suggestion_2),
        stringResource(R.string.st11_suggestion_3),
    )

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm, Alignment.CenterVertically),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.section),
    ) {
        Icon(
            imageVector = Icons.Filled.AutoAwesome,
            contentDescription = null,
            tint = colors.aiAccent,
            modifier = Modifier.size(Sizing.stateIcon),
        )
        Text(
            text = stringResource(R.string.st11_empty_title),
            style = EduTheme.typography.brandTitle,
            color = colors.textPrimary,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.st11_empty_body),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            textAlign = TextAlign.Center,
        )
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.xs),
        ) {
            suggestions.forEach { suggestion ->
                EduChip(label = suggestion, selected = false, onClick = { onSuggestionTap(suggestion) })
            }
        }
    }
}

@Composable
private fun DiffCard(proposal: PlannerChangeProposal, onAccept: () -> Unit, onReject: () -> Unit) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.sm)

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.xs)
            .background(colors.background, shape)
            .padding(Spacing.card),
    ) {
        Text(
            text = proposal.subjectTitle,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
        )
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.xs),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(text = stringResource(R.string.st11_diff_old), style = EduTheme.typography.caption, color = colors.textSecondary)
                Text(
                    text = "${proposal.oldDay.fullLabel()} · ${proposal.oldStartTime}",
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                contentDescription = null,
                tint = colors.primary,
                modifier = Modifier.size(Sizing.iconSm),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(text = stringResource(R.string.st11_diff_new), style = EduTheme.typography.caption, color = colors.primary)
                Text(
                    text = "${proposal.newDay.fullLabel()} · ${proposal.newStartTime}",
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        Text(
            text = proposal.reason,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )

        when (proposal.status) {
            ProposalStatus.Pending -> Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            ) {
                SecondaryButton(text = stringResource(R.string.st11_reject), onClick = onReject, modifier = Modifier.weight(1f))
                PrimaryButton(text = stringResource(R.string.st11_accept), onClick = onAccept, modifier = Modifier.weight(1f))
            }

            ProposalStatus.Accepted -> ProposalStatusRow(
                icon = Icons.Filled.CheckCircle,
                label = stringResource(R.string.st11_accepted_label),
                tint = colors.success,
            )

            ProposalStatus.Rejected -> ProposalStatusRow(
                icon = Icons.Filled.Cancel,
                label = stringResource(R.string.st11_rejected_label),
                tint = colors.textSecondary,
            )
        }
    }
}

@Composable
private fun ProposalStatusRow(icon: ImageVector, label: String, tint: Color) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = Modifier.padding(top = Spacing.sm),
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(Sizing.iconSm))
        Text(text = label, style = EduTheme.typography.caption, color = tint)
    }
}

@Composable
private fun PlannerChatErrorRow() {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.xs),
    ) {
        Icon(Icons.Filled.ErrorOutline, contentDescription = null, tint = colors.danger, modifier = Modifier.size(Sizing.icon))
        Text(
            text = stringResource(R.string.st04_error_body),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
        )
    }
}

@Composable
private fun PlannerChatInputBar(enabled: Boolean, onSend: (String) -> Unit, onAttachmentClick: () -> Unit) {
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
        EduIconButton(
            icon = Icons.Filled.CameraAlt,
            contentDescription = stringResource(R.string.st11_attach_exam_schedule),
            enabled = enabled,
            onClick = onAttachmentClick,
        )
        EduTextField(
            value = input,
            onValueChange = { input = it },
            label = stringResource(R.string.st11_input_hint),
            enabled = enabled,
            modifier = Modifier.weight(1f),
        )
        EduIconButton(
            icon = Icons.AutoMirrored.Filled.Send,
            contentDescription = stringResource(R.string.st04_send),
            enabled = enabled && input.isNotBlank(),
            onClick = {
                onSend(input)
                input = ""
            },
        )
    }
}

/**
 * ST-14 entry point. Both rows reuse ST-14's own action wording verbatim (no new labels
 * invented) and both just open the existing ST-14 flow — nothing here renders any
 * capture/OCR UI, holds any OCR state, or touches [com.rork.eduspark.data.repository.ExamRepository]
 * directly. ST-14 stays the single source of truth for the whole capture → correct → confirm
 * journey.
 */
@Composable
private fun ExamCaptureOptionsDialog(onDismiss: () -> Unit, onSelect: () -> Unit) {
    val colors = EduTheme.colors
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.surface, RoundedCornerShape(Radius.lg))
                .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.lg))
                .padding(Spacing.card),
        ) {
            Text(
                text = stringResource(R.string.st11_attach_exam_schedule),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
            ListRow(
                title = stringResource(R.string.st14_take_photo),
                leading = Icons.Filled.CameraAlt,
                onClick = onSelect,
            )
            ListRow(
                title = stringResource(R.string.st14_import_gallery),
                leading = Icons.Filled.PhotoLibrary,
                onClick = onSelect,
            )
        }
    }
}
