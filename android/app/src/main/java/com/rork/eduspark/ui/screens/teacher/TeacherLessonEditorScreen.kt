package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.AiReviewStatus
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.TeacherGeneratedQuestion
import com.rork.eduspark.data.model.TeacherLessonChunk
import com.rork.eduspark.data.model.TeacherLessonInsight
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduGroupedSurface
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-07 · Lesson Editor.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Review + edit + approve — a dense, professional workspace, not a form wall (Spacing.section
 * between the five section cards does the separating, no accordion library needed). The trust
 * rule this whole screen exists for: nothing a teacher hasn't explicitly reviewed here ever
 * reaches TC-08 — see [TeacherLessonEditorViewModel.canPublish]'s own doc comment for the gate.
 */
@Composable
fun TeacherLessonEditorScreen(
    courseId: String,
    lessonId: String,
    onBack: () -> Unit,
    onOpenPreview: (lessonId: String) -> Unit,
    onPublished: (lessonId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherLessonEditorViewModel = koinViewModel(parameters = { parametersOf(courseId, lessonId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                TeacherLessonEditorEvent.OpenPreview -> onOpenPreview(lessonId)
                TeacherLessonEditorEvent.Published -> onPublished(lessonId)
            }
        }
    }

    val data = (state.result as? UiState.Content)?.data

    EduScaffold(
        title = data?.lesson?.title.orEmpty(),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherLessonEditorSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { screenData ->
            TeacherLessonEditorContent(
                data = screenData,
                state = state,
                viewModel = viewModel,
            )
        }

        if (state.showPublishBlocked) {
            ConfirmDialog(
                title = stringResource(R.string.tc07_publish_blocked_title),
                body = publishBlockedBody(state),
                confirmLabel = stringResource(R.string.common_done),
                onConfirm = viewModel::dismissPublishBlocked,
                onDismiss = viewModel::dismissPublishBlocked,
            )
        }
    }
}

@Composable
private fun publishBlockedBody(state: TeacherLessonEditorUiState): String {
    val reasons = buildList {
        if (state.editor.extractedText.isBlank()) add(stringResource(R.string.tc07_gate_content))
        if (state.editor.chunks.none { it.text.isNotBlank() }) add(stringResource(R.string.tc07_gate_chunks))
        if (state.editor.generatedQuestions.any { it.reviewStatus == AiReviewStatus.Unreviewed }) add(stringResource(R.string.tc07_gate_questions))
        if (state.editor.insights.any { it.reviewStatus == AiReviewStatus.Unreviewed }) add(stringResource(R.string.tc07_gate_insights))
    }
    return reasons.joinToString(separator = "\n") { "• $it" }
}

@Composable
private fun TeacherLessonEditorContent(
    data: TeacherLessonEditorScreenData,
    state: TeacherLessonEditorUiState,
    viewModel: TeacherLessonEditorViewModel,
) {
    val colors = EduTheme.colors
    val editor = state.editor

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EditorHeader(courseTitle = data.courseTitle, hasUnsaved = state.hasUnsavedContentEdit || state.hasUnsavedChunkEdits)

            SectionHeader(title = stringResource(R.string.tc07_content_section))
            EduCard {
                EduTextField(
                    value = editor.extractedText,
                    onValueChange = viewModel::updateExtractedText,
                    label = stringResource(R.string.tc07_content_label),
                    singleLine = false,
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
                PrimaryButton(
                    text = stringResource(R.string.common_save),
                    onClick = viewModel::saveExtractedText,
                    isLoading = state.isSavingContent,
                    enabled = state.hasUnsavedContentEdit,
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            SectionHeader(title = stringResource(R.string.tc07_chunks_section))
        }

        itemsIndexed(editor.chunks) { index, chunk ->
            ChunkCard(
                chunk = chunk,
                canMergeUp = index > 0,
                canMergeDown = index < editor.chunks.lastIndex,
                onTextChange = { viewModel.updateChunkText(chunk.id, it) },
                onSplit = { viewModel.splitChunk(chunk.id) },
                onMergeUp = { viewModel.mergeChunkWithPrevious(chunk.id) },
                onMergeDown = { viewModel.mergeChunkWithNext(chunk.id) },
            )
        }

        item {
            PrimaryButton(
                text = stringResource(R.string.tc07_save_chunks),
                onClick = viewModel::saveChunks,
                isLoading = state.isSavingChunks,
                enabled = state.hasUnsavedChunkEdits,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.section),
            )

            SectionHeader(title = stringResource(R.string.tc07_quiz_section))
        }

        items(editor.generatedQuestions, key = { it.question.id }) { gq ->
            QuestionCard(
                generatedQuestion = gq,
                isExpanded = state.expandedQuestionId == gq.question.id,
                isSaving = state.savingQuestionId == gq.question.id,
                onToggleExpand = { viewModel.toggleExpandedQuestion(gq.question.id) },
                onDraftChange = { transform -> viewModel.updateQuestionDraft(gq.question.id, transform) },
                onSaveEdit = { viewModel.saveQuestionEdit(gq.question.id) },
                onReview = { status -> viewModel.reviewQuestion(gq.question.id, status) },
            )
        }

        item { SectionHeader(title = stringResource(R.string.tc07_insights_section)) }

        items(editor.insights, key = { it.id }) { insight ->
            InsightCard(insight = insight, onReview = { status -> viewModel.reviewInsight(insight.id, status) })
        }

        item {
            SectionHeader(title = stringResource(R.string.tc07_publish_section))
            PublishCard(state = state, onPreview = viewModel::openPreview, onPublish = viewModel::publish)
            Spacer(modifier = Modifier.height(Spacing.xl))
        }
    }
}

@Composable
private fun EditorHeader(courseTitle: String, hasUnsaved: Boolean) {
    val colors = EduTheme.colors
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        Text(courseTitle, style = EduTheme.typography.caption, color = colors.zaytoun)
        Text("·", style = EduTheme.typography.caption, color = colors.textMuted)
        StatusPill(label = stringResource(R.string.tc04_lesson_status_draft), contentColor = colors.textMuted, containerColor = colors.hajar100)
    }
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.section),
    ) {
        Text(
            text = stringResource(if (hasUnsaved) R.string.tc07_unsaved_changes else R.string.tc07_all_saved),
            style = EduTheme.typography.caption,
            color = if (hasUnsaved) colors.warning else colors.success,
        )
    }
}

/**
 * Deliberately [EduGroupedSurface], not [EduCard] — a chunk is raw teacher-owned text with no
 * review state of its own (unlike [QuestionCard]/[InsightCard] below, whose bordered
 * [EduCard] treatment carries real meaning: the border color IS the AI-review status). Giving
 * chunks the lighter tint keeps them visually subordinate to the entities that actually need
 * a teacher decision, rather than every section reading as the same weight.
 */
@Composable
private fun ChunkCard(
    chunk: TeacherLessonChunk,
    canMergeUp: Boolean,
    canMergeDown: Boolean,
    onTextChange: (String) -> Unit,
    onSplit: () -> Unit,
    onMergeUp: () -> Unit,
    onMergeDown: () -> Unit,
) {
    val colors = EduTheme.colors
    EduGroupedSurface(modifier = Modifier.padding(bottom = Spacing.sm)) {
        Text(
            text = stringResource(R.string.tc07_chunk_number, numeral(chunk.order)),
            style = EduTheme.typography.caption,
            color = colors.textMuted,
            modifier = Modifier.padding(bottom = Spacing.xxs),
        )
        EduTextField(
            value = chunk.text,
            onValueChange = onTextChange,
            label = stringResource(R.string.tc07_chunk_text_label),
            singleLine = false,
            modifier = Modifier.padding(bottom = Spacing.xs),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            GhostButton(text = stringResource(R.string.tc07_split_chunk), onClick = onSplit)
            GhostButton(text = stringResource(R.string.tc07_merge_up), onClick = onMergeUp, enabled = canMergeUp)
            GhostButton(text = stringResource(R.string.tc07_merge_down), onClick = onMergeDown, enabled = canMergeDown)
        }
    }
}

@Composable
private fun QuestionCard(
    generatedQuestion: TeacherGeneratedQuestion,
    isExpanded: Boolean,
    isSaving: Boolean,
    onToggleExpand: () -> Unit,
    onDraftChange: ((QuizQuestion) -> QuizQuestion) -> Unit,
    onSaveEdit: () -> Unit,
    onReview: (AiReviewStatus) -> Unit,
) {
    val colors = EduTheme.colors
    val question = generatedQuestion.question
    val review = generatedQuestion.reviewStatus

    EduCard(
        borderColor = reviewBorderColor(review),
        modifier = Modifier.padding(bottom = Spacing.sm),
    ) {
        Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            AiMarker(modifier = Modifier.padding(top = Spacing.xxs))
            Text(
                text = question.prompt,
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
            StatusPill(
                label = aiReviewStatusLabel(review),
                contentColor = reviewBorderColor(review),
                containerColor = reviewBorderColor(review).copy(alpha = 0.14f),
            )
        }

        if (isExpanded) {
            EduTextField(
                value = question.prompt,
                onValueChange = { text -> onDraftChange { it.copy(prompt = text) } },
                label = stringResource(R.string.tc07_question_prompt_label),
                singleLine = false,
                modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.xs),
            )
            question.options.forEach { option ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.padding(bottom = Spacing.xxs),
                ) {
                    EduChip(
                        label = stringResource(R.string.tc07_mark_correct),
                        selected = question.correctAnswer == option.id,
                        onClick = { onDraftChange { it.copy(correctAnswer = option.id) } },
                    )
                    EduTextField(
                        value = option.text,
                        onValueChange = { text ->
                            onDraftChange { q -> q.copy(options = q.options.map { o -> if (o.id == option.id) o.copy(text = text) else o }) }
                        },
                        label = stringResource(R.string.tc07_option_label),
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            EduTextField(
                value = question.explanation,
                onValueChange = { text -> onDraftChange { it.copy(explanation = text) } },
                label = stringResource(R.string.tc07_explanation_label),
                singleLine = false,
                modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.xs),
            )
            PrimaryButton(
                text = stringResource(R.string.tc07_save_question),
                onClick = onSaveEdit,
                isLoading = isSaving,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.sm),
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.xs)) {
            GhostButton(text = stringResource(R.string.tc07_edit), onClick = onToggleExpand)
            SecondaryButton(text = stringResource(R.string.tc07_accept), onClick = { onReview(AiReviewStatus.Accepted) }, enabled = review != AiReviewStatus.Accepted)
            GhostButton(text = stringResource(R.string.tc07_reject), onClick = { onReview(AiReviewStatus.Rejected) }, enabled = review != AiReviewStatus.Rejected)
        }
    }
}

@Composable
private fun InsightCard(insight: TeacherLessonInsight, onReview: (AiReviewStatus) -> Unit) {
    val colors = EduTheme.colors
    val review = insight.reviewStatus
    EduCard(
        borderColor = reviewBorderColor(review),
        modifier = Modifier.padding(bottom = Spacing.sm),
    ) {
        Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            AiMarker(modifier = Modifier.padding(top = Spacing.xxs))
            Column(modifier = Modifier.weight(1f)) {
                Text(lessonInsightKindLabel(insight.kind), style = EduTheme.typography.caption, color = colors.textMuted)
                Text(insight.text, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs))
            }
            StatusPill(
                label = aiReviewStatusLabel(review),
                contentColor = reviewBorderColor(review),
                containerColor = reviewBorderColor(review).copy(alpha = 0.14f),
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            SecondaryButton(text = stringResource(R.string.tc07_accept), onClick = { onReview(AiReviewStatus.Accepted) }, enabled = review != AiReviewStatus.Accepted)
            GhostButton(text = stringResource(R.string.tc07_reject), onClick = { onReview(AiReviewStatus.Rejected) }, enabled = review != AiReviewStatus.Rejected)
        }
    }
}

@Composable
private fun PublishCard(state: TeacherLessonEditorUiState, onPreview: () -> Unit, onPublish: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        if (!state.canPublish) {
            Text(
                text = stringResource(R.string.tc07_publish_gate_hint),
                style = EduTheme.typography.caption,
                color = colors.textMuted,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            SecondaryButton(text = stringResource(R.string.tc07_preview), onClick = onPreview, modifier = Modifier.weight(1f))
            PrimaryButton(
                text = stringResource(R.string.tc07_publish),
                onClick = onPublish,
                isLoading = state.isPublishing,
                enabled = state.canPublish,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun reviewBorderColor(status: AiReviewStatus): Color {
    val colors = EduTheme.colors
    return when (status) {
        AiReviewStatus.Unreviewed -> colors.textMuted
        AiReviewStatus.Accepted -> colors.success
        AiReviewStatus.Rejected -> colors.danger
    }
}

@Composable
private fun TeacherLessonEditorSkeleton() {
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
