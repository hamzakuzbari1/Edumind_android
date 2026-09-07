package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ProjectReviewStatus
import com.rork.eduspark.data.model.TeacherCriterionReview
import com.rork.eduspark.data.model.TeacherProjectSubmission
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-18 · Review Detail — submission first, rubric second, AI advisory clearly separated.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Jouri boundary, exactly: [AiMarker] wraps only the AI pre-review block (suggested scores,
 * strengths, concerns, suggested feedback) — every teacher-facing score/feedback field below it
 * (confirmed/overridden criterion scores, the teacher's own feedback text, the private comment)
 * is plain, never Jouri-marked, even when it started as an accepted AI suggestion. The teacher
 * is always the final authority: a criterion score never becomes "confirmed" until the teacher
 * taps something, and Finalize is its own explicit, confirmed action.
 */
@Composable
fun TeacherReviewDetailScreen(
    submissionId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherReviewDetailViewModel = koinViewModel(parameters = { parametersOf(submissionId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.tc18_detail_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherReviewDetailSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { submission ->
            TeacherReviewDetailContent(submission = submission, state = state, viewModel = viewModel)
        }
    }

    val editingCriterionId = state.editingCriterionId
    if (editingCriterionId != null) {
        val submission = (state.result as? UiState.Content)?.data
        val criterion = submission?.criteria?.firstOrNull { it.criterionId == editingCriterionId }
        if (criterion != null) ScoreEditorDialog(criterion = criterion, state = state, viewModel = viewModel)
    }

    if (state.showFinalizeConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.tc18_finalize_confirm_title),
            body = stringResource(R.string.tc18_finalize_confirm_body),
            confirmLabel = stringResource(R.string.tc18_finalize),
            onConfirm = viewModel::confirmFinalize,
            onDismiss = viewModel::dismissFinalizeConfirm,
        )
    }
}

@Composable
private fun TeacherReviewDetailContent(submission: TeacherProjectSubmission, state: TeacherReviewDetailUiState, viewModel: TeacherReviewDetailViewModel) {
    val colors = EduTheme.colors
    val isFinalized = submission.reviewStatus == ProjectReviewStatus.Reviewed

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        // ── Submission ────────────────────────────────────────────────────
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(submission.studentName, style = EduTheme.typography.titleLg, color = colors.textPrimary)
                    Text(submission.projectTitle, style = EduTheme.typography.body, color = colors.zaytoun, modifier = Modifier.padding(top = Spacing.xxs))
                }
                val statusColor = when (submission.reviewStatus) {
                    ProjectReviewStatus.AwaitingReview -> colors.warning
                    ProjectReviewStatus.InReview -> colors.zaytoun
                    ProjectReviewStatus.Reviewed -> colors.success
                }
                StatusPill(label = projectReviewStatusLabel(submission.reviewStatus), contentColor = statusColor, containerColor = statusColor.copy(alpha = 0.14f))
            }

            SectionHeader(title = stringResource(R.string.tc18_submission_section))
            EduCard {
                Text(submission.milestoneTitle, style = EduTheme.typography.caption, color = colors.textMuted)
                Text(submission.submittedLabel, style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.xxs))
                Text(submission.artifactSummary, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
                if (submission.studentComment.isNotBlank()) {
                    Text(submission.studentComment, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
                }
            }
        }

        // ── AI pre-review — Jouri-marked. The jouri border is the exact same technique
        // AiMessageBubble already uses for AI-authored content, so this block reads as the
        // advisory zone at a glance, distinct from the submission/rubric/feedback around it. ──
        item {
            SectionHeader(title = stringResource(R.string.tc18_ai_pre_review_section))
            EduCard(borderColor = colors.jouri) {
                AiMarker()
                if (submission.aiStrengths.isNotEmpty()) {
                    Text(stringResource(R.string.tc18_ai_strengths), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.sm))
                    submission.aiStrengths.forEach { strength -> Text("• $strength", style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs)) }
                }
                if (submission.aiConcerns.isNotEmpty()) {
                    Text(stringResource(R.string.tc18_ai_concerns), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.sm))
                    submission.aiConcerns.forEach { concern -> Text("• $concern", style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs)) }
                }
                if (submission.aiSuggestedFeedback.isNotBlank()) {
                    Text(stringResource(R.string.tc18_ai_suggested_feedback), style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.sm))
                    Text(submission.aiSuggestedFeedback, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs))
                }
            }
        }

        // ── Rubric + teacher scoring ──────────────────────────────────────
        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth().padding(top = Spacing.section)) {
                SectionHeader(title = stringResource(R.string.tc18_rubric_section), modifier = Modifier.weight(1f))
                val finalScore = submission.finalScore
                Text(
                    text = if (finalScore != null) stringResource(R.string.tc18_score_of, finalScore, submission.maxScore) else stringResource(R.string.tc18_score_pending),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                    color = if (finalScore != null) colors.success else colors.textMuted,
                )
            }
        }
        items(submission.criteria, key = { it.criterionId }) { criterion ->
            CriterionReviewRow(
                criterion = criterion, isFinalized = isFinalized,
                onEditScore = { viewModel.openScoreEditor(criterion) },
                onAcceptAi = { viewModel.acceptAiSuggestion(criterion) },
            )
        }

        // ── Teacher feedback ───────────────────────────────────────────────
        item {
            SectionHeader(title = stringResource(R.string.tc18_feedback_section))
            EduCard {
                EduTextField(value = state.feedbackDraft, onValueChange = viewModel::updateFeedbackDraft, label = stringResource(R.string.tc18_feedback_label), singleLine = false, enabled = !isFinalized)
                GhostButton(text = stringResource(R.string.tc18_use_ai_feedback), onClick = viewModel::useAiSuggestedFeedback, enabled = !isFinalized, modifier = Modifier.padding(top = Spacing.xs))
                EduTextField(
                    value = state.privateCommentDraft, onValueChange = viewModel::updatePrivateCommentDraft, label = stringResource(R.string.tc18_private_comment_label),
                    singleLine = false, enabled = !isFinalized, modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(if (state.hasUnsavedFeedback) R.string.tc16_unsaved else R.string.tc16_all_saved),
                    style = EduTheme.typography.caption,
                    color = if (state.hasUnsavedFeedback) colors.warning else colors.success,
                    modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.xs),
                )
                PrimaryButton(
                    text = stringResource(R.string.common_save), onClick = viewModel::saveFeedback,
                    isLoading = state.isSavingFeedback, enabled = state.hasUnsavedFeedback && !isFinalized,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }

        // ── Finalize ──────────────────────────────────────────────────────
        item {
            SectionHeader(title = stringResource(R.string.tc18_finalize_section))
            if (isFinalized) {
                Text(stringResource(R.string.tc18_already_finalized), style = EduTheme.typography.body, color = colors.success, modifier = Modifier.padding(bottom = Spacing.xl))
            } else {
                val confirmedCount = submission.criteria.count { it.isTeacherConfirmed }
                val allConfirmed = submission.allCriteriaConfirmed
                if (state.finalizeError) {
                    Text(stringResource(R.string.tc18_finalize_failed), style = EduTheme.typography.caption, color = colors.danger, modifier = Modifier.padding(bottom = Spacing.sm))
                }
                Text(
                    text = if (allConfirmed) {
                        stringResource(R.string.tc18_finalize_hint)
                    } else {
                        stringResource(R.string.tc18_finalize_blocked, confirmedCount, submission.criteria.size)
                    },
                    style = EduTheme.typography.caption,
                    color = if (allConfirmed) colors.textMuted else colors.warning,
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
                PrimaryButton(
                    text = stringResource(R.string.tc18_finalize), onClick = viewModel::requestFinalize,
                    isLoading = state.isFinalizing, enabled = allConfirmed,
                    modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.xl),
                )
            }
        }
    }
}

@Composable
private fun CriterionReviewRow(criterion: TeacherCriterionReview, isFinalized: Boolean, onEditScore: () -> Unit, onAcceptAi: () -> Unit) {
    val colors = EduTheme.colors
    val confirmed = criterion.isTeacherConfirmed

    EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.weight(1f)) {
                Text(criterion.criterionTitle, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xxs), modifier = Modifier.padding(top = Spacing.xxs)) {
                    AiMarker()
                    Text(
                        text = stringResource(R.string.tc18_ai_suggestion, criterion.aiSuggestedScore, criterion.maxScore),
                        style = EduTheme.typography.caption, color = colors.textMuted,
                    )
                }
            }
            StatusPill(
                label = stringResource(R.string.tc18_score_of, criterion.teacherScore ?: criterion.aiSuggestedScore, criterion.maxScore),
                contentColor = if (confirmed) colors.success else colors.textMuted,
                containerColor = (if (confirmed) colors.success else colors.textMuted).copy(alpha = 0.14f),
            )
        }
        if (!isFinalized) {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
                SecondaryButton(text = stringResource(R.string.tc18_accept_ai), onClick = onAcceptAi, modifier = Modifier.weight(1f))
                GhostButton(text = stringResource(R.string.tc18_override), onClick = onEditScore, modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun ScoreEditorDialog(criterion: TeacherCriterionReview, state: TeacherReviewDetailUiState, viewModel: TeacherReviewDetailViewModel) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = viewModel::dismissScoreEditor,
        title = { Text(criterion.criterionTitle, style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            EduTextField(
                value = state.scoreDraftText, onValueChange = viewModel::updateScoreDraftText,
                label = stringResource(R.string.tc18_score_label, criterion.maxScore),
                keyboardType = KeyboardType.Number,
                errorText = if (state.scoreDraftError) stringResource(R.string.tc18_score_range_error, criterion.maxScore) else null,
            )
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_save), onClick = viewModel::confirmScore) },
        dismissButton = { GhostButton(text = stringResource(R.string.common_cancel), onClick = viewModel::dismissScoreEditor) },
        containerColor = colors.surface, titleContentColor = colors.textPrimary, textContentColor = colors.textMuted,
    )
}

@Composable
private fun TeacherReviewDetailSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
