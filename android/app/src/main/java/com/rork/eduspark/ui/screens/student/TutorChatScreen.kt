package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.TipsAndUpdates
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
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ChatSender
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.ai.AiMessageBubble
import com.rork.eduspark.ui.components.ai.AiTypingIndicator
import com.rork.eduspark.ui.components.ai.UserMessageBubble
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-04 · AI Tutor Chat.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Grounded in the current lesson via [TutorChatViewModel]'s context pill. Every tutor reply
 * renders through [AiMessageBubble] — the ONLY bubble allowed aiAccent marking — while every
 * student line uses [UserMessageBubble], never marked. Message actions (regenerate, explain
 * simpler, give an example) only appear under the most recent tutor reply, matching how
 * every other chat surface scopes those actions.
 *
 * The tutor genuinely does not stream (Source Audit §4) — [AiTypingIndicator] is an honest
 * wait, not a fake token reveal, exactly as [com.rork.eduspark.ui.components.ai.AiComponents.kt]
 * documents.
 */
@Composable
fun TutorChatScreen(
    onBack: () -> Unit,
    onVoiceMode: () -> Unit,
    viewModel: TutorChatViewModel,
    modifier: Modifier = Modifier,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    val quizMePrompt = stringResource(R.string.st04_chip_quiz_me)

    LaunchedEffect(state.messages.size, state.isSending) {
        val lastIndex = state.messages.size - 1 + if (state.isSending) 1 else 0
        if (lastIndex >= 0) listState.animateScrollToItem(lastIndex)
    }

    EduScaffold(
        title = stringResource(R.string.st04_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
        ) {
            ChatPanelHeader(
                lessonTitle = state.lessonTitle,
                isOnline = state.isOnline,
            )

            EduCard(
                contentPadding = PaddingValues(0.dp),
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            ) {
                Column(modifier = Modifier.fillMaxSize()) {
                    ChatTranscriptHeader(messageCount = state.messages.size)
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth(),
                    ) {
                if (state.messages.isEmpty()) {
                            EmptyChatState(onSuggestionTap = { viewModel.sendMessage(it) })
                } else {
                    val lastTutorIndex = state.messages.indexOfLast { it.sender == ChatSender.Tutor }
                    LazyColumn(
                        state = listState,
                                contentPadding = PaddingValues(horizontal = Spacing.card, vertical = Spacing.sm),
                        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
                        modifier = Modifier.fillMaxSize(),
                    ) {
                        itemsIndexed(state.messages, key = { _, message -> message.id }) { index, message ->
                            when (message.sender) {
                                ChatSender.Student -> UserMessageBubble(text = message.text)
                                ChatSender.Tutor -> Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                                    AiMessageBubble(
                                        text = message.text,
                                        footer = {
                                            MessageActions(
                                                text = message.text,
                                                showFollowUps = index == lastTutorIndex && !state.isSending,
                                                onRegenerate = viewModel::regenerateLast,
                                                onSimpler = viewModel::explainSimpler,
                                                onExample = viewModel::giveExample,
                                            )
                                        },
                                    )
                                    if (index == lastTutorIndex) {
                                        TutorStructuredAnswerCard(
                                            lessonId = state.lessonId,
                                            lessonTitle = state.lessonTitle,
                                            onSimpler = viewModel::explainSimpler,
                                            onExample = viewModel::giveExample,
                                            onQuizMe = { viewModel.sendMessage(quizMePrompt) },
                                        )
                                    }
                                }
                            }
                        }
                        if (state.isSending) {
                            item(key = "typing") {
                                AiTypingIndicator(modifier = Modifier.padding(vertical = Spacing.xs))
                            }
                        }
                        if (state.error != null) {
                            item(key = "error") {
                                ChatErrorRow(onRetry = viewModel::retry)
                            }
                        }
                    }
                }
            }

                    SuggestionChipRow(
                        enabled = !state.isSending,
                        onAnotherExample = viewModel::giveExample,
                        onExplainSimpler = viewModel::explainSimpler,
                        onQuizMe = { viewModel.sendMessage(quizMePrompt) },
                    )

                    ChatInputBar(
                        enabled = !state.isSending,
                        onVoiceMode = onVoiceMode,
                        onSend = { text -> viewModel.sendMessage(text) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ChatPanelHeader(lessonTitle: String, isOnline: Boolean) {
    val colors = EduTheme.colors
    EduCard(
        borderColor = colors.primary.copy(alpha = 0.22f),
        contentPadding = PaddingValues(Spacing.sm),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(40.dp)
                    .background(colors.primaryContainer, androidx.compose.foundation.shape.CircleShape),
            ) {
                Icon(Icons.Filled.School, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.icon))
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st04_panel_teacher_name),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                Text(
                    text = if (lessonTitle.isBlank()) {
                        stringResource(R.string.st04_panel_header_hint)
                    } else {
                        stringResource(R.string.st04_lesson_context, lessonTitle)
                    },
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
            Icon(
                imageVector = if (isOnline) Icons.Filled.CheckCircle else Icons.Filled.ErrorOutline,
                contentDescription = null,
                tint = if (isOnline) colors.success else colors.danger,
                modifier = Modifier.size(Sizing.iconSm),
            )
        }
    }
}

@Composable
private fun TutorStructuredAnswerCard(
    lessonId: String,
    lessonTitle: String,
    onSimpler: () -> Unit,
    onExample: () -> Unit,
    onQuizMe: () -> Unit,
) {
    val colors = EduTheme.colors
    val resolvedLessonTitle = if (lessonTitle.isBlank()) stringResource(R.string.st04_panel_header_hint) else lessonTitle
    EduCard(borderColor = colors.aiAccent.copy(alpha = 0.36f)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            AiMarker()
            Text(
                text = stringResource(R.string.st04_answer_why),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.aiAccent,
            )
        }
        SubjectVisual(
            courseId = lessonId.substringBefore("-"),
            compact = true,
            fillWidth = false,
            modifier = Modifier
                .padding(top = Spacing.sm)
                .size(88.dp)
                .align(Alignment.CenterHorizontally),
        )
        Text(
            text = stringResource(R.string.st04_structured_summary, resolvedLessonTitle),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.md),
        )
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm)
                .background(colors.textPrimary, RoundedCornerShape(Radius.md))
                .padding(vertical = Spacing.sm),
        ) {
            Text(
                text = if (lessonId.contains("math", ignoreCase = true)) {
                    stringResource(R.string.st03_formula_math)
                } else {
                    stringResource(R.string.st04_formula_physics)
                },
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.surface,
            )
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        ) {
            GhostButton(text = stringResource(R.string.st04_chip_explain_simpler), onClick = onSimpler, modifier = Modifier.weight(1f))
            GhostButton(text = stringResource(R.string.st04_chip_another_example), onClick = onExample, modifier = Modifier.weight(1f))
            GhostButton(text = stringResource(R.string.st04_chip_quiz_me), onClick = onQuizMe, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun ChatTranscriptHeader(messageCount: Int) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.card, vertical = Spacing.sm),
    ) {
        Column {
            Text(
                text = stringResource(R.string.st04_panel_title),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                color = EduTheme.colors.textPrimary,
            )
            Text(
                text = stringResource(R.string.st04_panel_subtitle),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
            )
        }
        Text(
            text = stringResource(R.string.st04_panel_message_count, messageCount),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.primary,
        )
    }
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(Sizing.hairline)
            .background(EduTheme.colors.border),
    )
}

@Composable
private fun SuggestionChipRow(
    enabled: Boolean,
    onAnotherExample: () -> Unit,
    onExplainSimpler: () -> Unit,
    onQuizMe: () -> Unit,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .background(EduTheme.colors.surface)
            .padding(horizontal = Spacing.card, vertical = Spacing.xs),
    ) {
        EduChip(label = stringResource(R.string.st04_chip_another_example), selected = false, enabled = enabled, onClick = onAnotherExample)
        EduChip(label = stringResource(R.string.st04_chip_explain_simpler), selected = false, enabled = enabled, onClick = onExplainSimpler)
        EduChip(label = stringResource(R.string.st04_chip_quiz_me), selected = false, enabled = enabled, onClick = onQuizMe)
    }
}

@Composable
private fun LessonContextPill(lessonTitle: String) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.primaryContainer)
            .padding(horizontal = Spacing.gutter, vertical = Spacing.xs),
    ) {
        Text(
            text = stringResource(R.string.st04_lesson_context, lessonTitle),
            style = EduTheme.typography.caption,
            color = colors.primary,
        )
    }
}

@Composable
private fun EmptyChatState(onSuggestionTap: (String) -> Unit) {
    val colors = EduTheme.colors
    val suggestions = listOf(
        stringResource(R.string.st04_suggestion_1),
        stringResource(R.string.st04_suggestion_2),
        stringResource(R.string.st04_suggestion_3),
    )

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.card, vertical = Spacing.lg),
    ) {
        Icon(
            imageVector = Icons.Filled.AutoAwesome,
            contentDescription = null,
            tint = colors.aiAccent,
            modifier = Modifier.size(Sizing.iconLg),
        )
        Text(
            text = stringResource(R.string.st04_empty_title),
            style = EduTheme.typography.title,
            color = colors.textPrimary,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.st04_empty_body),
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
private fun MessageActions(
    text: String,
    showFollowUps: Boolean,
    onRegenerate: () -> Unit,
    onSimpler: () -> Unit,
    onExample: () -> Unit,
) {
    val clipboard = LocalClipboardManager.current
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
        EduIconButton(
            icon = Icons.Filled.ContentCopy,
            contentDescription = stringResource(R.string.st04_action_copy),
            onClick = { clipboard.setText(AnnotatedString(text)) },
            tint = EduTheme.colors.textSecondary,
        )
        if (showFollowUps) {
            EduIconButton(
                icon = Icons.Filled.Refresh,
                contentDescription = stringResource(R.string.st04_action_regenerate),
                onClick = onRegenerate,
                tint = EduTheme.colors.textSecondary,
            )
            EduIconButton(
                icon = Icons.Filled.Lightbulb,
                contentDescription = stringResource(R.string.st04_action_simpler),
                onClick = onSimpler,
                tint = EduTheme.colors.textSecondary,
            )
            EduIconButton(
                icon = Icons.Filled.TipsAndUpdates,
                contentDescription = stringResource(R.string.st04_action_example),
                onClick = onExample,
                tint = EduTheme.colors.textSecondary,
            )
        }
    }
}

@Composable
private fun ChatErrorRow(onRetry: () -> Unit) {
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
            modifier = Modifier.weight(1f),
        )
        GhostButton(text = stringResource(R.string.common_retry), onClick = onRetry)
    }
}

@Composable
private fun ChatInputBar(enabled: Boolean, onVoiceMode: () -> Unit, onSend: (String) -> Unit) {
    var input by rememberSaveable { mutableStateOf("") }
    val colors = EduTheme.colors

    Row(
        verticalAlignment = Alignment.Bottom,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(horizontal = Spacing.card, vertical = Spacing.sm),
    ) {
        // Approved design (TutorChat.dc.html): voice-mode entry sits in the composer itself,
        // not the top bar.
        EduIconButton(
            icon = Icons.Filled.Mic,
            contentDescription = stringResource(R.string.st04_voice_mode),
            enabled = enabled,
            onClick = onVoiceMode,
        )
        EduTextField(
            value = input,
            onValueChange = { input = it },
            label = stringResource(R.string.st04_input_hint),
            enabled = enabled,
            labelPlacement = FieldLabelPlacement.Floating,
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
