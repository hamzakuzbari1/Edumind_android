package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.PeerReviewDraft
import com.rork.eduspark.data.model.PeerSubmissionPreview
import com.rork.eduspark.data.model.RubricCriterion
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import androidx.compose.foundation.background
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-07 · Peer Review.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A dedicated, focused flow — no tab bar, no distractions, one anonymized submission at a
 * time. [AnonymizedSubmissionCard] shows only [PeerSubmissionPreview.anonymizedLabel] and the
 * work itself, never a name or photo. The tone warning and the length hint both surface next
 * to the comment field so the reviewer sees exactly what to fix before resending — see
 * [PeerReviewViewModel]'s own doc comment for the deterministic MOCK tone check.
 */
@Composable
fun PeerReviewScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PeerReviewViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.pj07_title), onBack = onBack, modifier = modifier) { _ ->
        if (state.phase == PeerReviewPhase.Submitted) {
            MessageState(
                icon = Icons.Filled.CheckCircle,
                iconTint = EduTheme.colors.success,
                title = stringResource(R.string.pj07_submitted_title),
                body = stringResource(R.string.pj07_submitted_body),
                primaryActionLabel = stringResource(R.string.common_done),
                onPrimaryAction = onBack,
            )
        } else {
            ScreenStateHost(
                state = state.result,
                onRetry = viewModel::retry,
                isOffline = !state.isOnline,
                loading = { PeerReviewSkeleton() },
                modifier = Modifier.fillMaxSize(),
            ) { data ->
                Column(modifier = Modifier.fillMaxSize()) {
                    PeerReviewContent(
                        assignment = data.assignment,
                        draft = data.draft,
                        showValidationError = state.showValidationError,
                        showToneWarning = state.showToneWarning,
                        onSetScore = viewModel::setScore,
                        onUpdateComment = viewModel::updateComment,
                        modifier = Modifier.weight(1f),
                    )
                    Row(modifier = Modifier.fillMaxWidth().background(EduTheme.colors.surface).padding(Spacing.gutter)) {
                        PrimaryButton(
                            text = stringResource(R.string.pj07_submit),
                            onClick = viewModel::submit,
                            isLoading = state.phase == PeerReviewPhase.Submitting,
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun PeerReviewContent(
    assignment: PeerSubmissionPreview,
    draft: PeerReviewDraft,
    showValidationError: Boolean,
    showToneWarning: Boolean,
    onSetScore: (String, Int) -> Unit,
    onUpdateComment: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = modifier.fillMaxSize(),
    ) {
        item {
            Row(modifier = Modifier.padding(bottom = Spacing.xs)) {
                Icon(Icons.Filled.VisibilityOff, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
                Text(
                    text = stringResource(R.string.pj07_anonymous_notice),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(start = Spacing.xxs),
                )
            }
            AnonymizedSubmissionCard(assignment)
        }

        item {
            SectionHeader(title = stringResource(R.string.pj07_rubric_section))
        }
        items(assignment.criteria, key = { it.id }) { criterion ->
            CriterionRatingRow(
                criterion = criterion,
                selectedScore = draft.scores[criterion.id],
                onSelectScore = { score -> onSetScore(criterion.id, score) },
            )
        }

        item {
            SectionHeader(title = stringResource(R.string.pj07_comment_section))
            EduTextField(
                value = draft.comment,
                onValueChange = onUpdateComment,
                label = stringResource(R.string.pj07_comment_label),
                singleLine = false,
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                text = stringResource(R.string.pj07_comment_min_length, numeral(PeerReviewViewModel.MIN_COMMENT_LENGTH)),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
            if (showToneWarning) {
                Row(modifier = Modifier.padding(top = Spacing.sm)) {
                    Icon(Icons.Filled.WarningAmber, contentDescription = null, tint = colors.warning, modifier = Modifier.size(Sizing.iconSm))
                    Text(
                        text = stringResource(R.string.pj07_tone_warning),
                        style = EduTheme.typography.caption,
                        color = colors.warning,
                        modifier = Modifier.padding(start = Spacing.xxs),
                    )
                }
            }
            if (showValidationError) {
                Text(
                    text = stringResource(R.string.pj07_validation_error),
                    style = EduTheme.typography.caption,
                    color = colors.danger,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
        }
    }
}

@Composable
private fun AnonymizedSubmissionCard(assignment: PeerSubmissionPreview) {
    val colors = EduTheme.colors
    EduCard {
        Text(
            text = assignment.anonymizedLabel,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
        )
        if (assignment.submission.writtenReflection.isNotBlank()) {
            Text(
                text = assignment.submission.writtenReflection,
                style = EduTheme.typography.body,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
        if (assignment.submission.attachments.isNotEmpty()) {
            Text(
                text = stringResource(R.string.pj06_attachments_count, numeral(assignment.submission.attachments.size)),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun CriterionRatingRow(criterion: RubricCriterion, selectedScore: Int?, onSelectScore: (Int) -> Unit) {
    val colors = EduTheme.colors
    Column(modifier = Modifier.padding(vertical = Spacing.xs)) {
        Text(criterion.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.xxs),
        ) {
            for (score in 0..criterion.maxScore) {
                EduChip(
                    label = numeral(score),
                    selected = selectedScore == score,
                    onClick = { onSelectScore(score) },
                )
            }
        }
    }
}

@Composable
private fun PeerReviewSkeleton() {
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

