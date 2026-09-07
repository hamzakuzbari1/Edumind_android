package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ProjectReview
import com.rork.eduspark.data.model.ProjectSubmission
import com.rork.eduspark.data.model.RubricResult
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.ai.AiDisclosureFooter
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-06 · AI Review & Rubric.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deterministic MOCK evaluation only — see [ProjectReviewViewModel]'s own doc comment.
 * [SubmissionSummary] renders the student's own work with no jouri marking; the rubric,
 * strengths and improvement are the machine-generated part, wrapped in one jouri-bordered
 * [EduCard] with [AiMarker] and [AiDisclosureFooter] — the established jouri trust contract,
 * not a bare grade. Strengths render before the single improvement, per the Screen Inventory.
 */
@Composable
fun ProjectReviewScreen(
    projectId: String,
    taskId: String,
    onBack: () -> Unit,
    onResubmit: (taskId: String) -> Unit,
    onContinueProject: () -> Unit,
    onOpenPeerReview: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ProjectReviewViewModel = koinViewModel(parameters = { parametersOf(projectId, taskId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                ProjectReviewEvent.NavigateToComposer -> onResubmit(taskId)
            }
        }
    }

    EduScaffold(title = stringResource(R.string.pj06_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ReviewSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ReviewContent(
                submission = data.submission,
                review = data.review,
                isStartingResubmission = state.isStartingResubmission,
                onResubmit = viewModel::beginResubmission,
                onContinueProject = onContinueProject,
                onOpenPeerReview = onOpenPeerReview,
            )
        }
    }
}

@Composable
private fun ReviewContent(
    submission: ProjectSubmission,
    review: ProjectReview,
    isStartingResubmission: Boolean,
    onResubmit: () -> Unit,
    onContinueProject: () -> Unit,
    onOpenPeerReview: () -> Unit,
) {
    val colors = EduTheme.colors
    val totalScore = review.rubricResults.sumOf { it.score }
    val totalMax = review.rubricResults.sumOf { it.maxScore }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            SectionHeader(title = stringResource(R.string.pj06_submission_section))
            SubmissionSummary(submission)
        }

        item {
            SectionHeader(title = stringResource(R.string.pj06_rubric_section))
            EduCard(borderColor = colors.aiAccent) {
                AiMarker()
                Row(
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.sm),
                ) {
                    Text(stringResource(R.string.pj06_overall_label), style = EduTheme.typography.body, color = colors.textSecondary)
                    Text(
                        text = stringResource(R.string.pj06_score_format, numeral(totalScore), numeral(totalMax)),
                        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                    )
                }
                EduLinearProgress(
                    progress = if (totalMax == 0) 0f else totalScore / totalMax.toFloat(),
                    modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
                )

                review.rubricResults.forEach { result -> RubricRow(result) }

                Text(
                    text = stringResource(R.string.pj06_strengths_section),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xxs),
                )
                review.strengths.forEach { strength ->
                    Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(vertical = Spacing.xxs)) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success, modifier = Modifier.size(Sizing.iconSm))
                        Text(strength, style = EduTheme.typography.body, color = colors.textPrimary)
                    }
                }

                Text(
                    text = stringResource(R.string.pj06_improvement_section),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xxs),
                )
                Text(review.improvement, style = EduTheme.typography.body, color = colors.textPrimary)

                AiDisclosureFooter(modifier = Modifier.padding(top = Spacing.md))
            }
        }

        item {
            Column(modifier = Modifier.padding(top = Spacing.section)) {
                if (review.isAcceptable) {
                    PrimaryButton(
                        text = stringResource(R.string.pj06_continue_project),
                        onClick = onContinueProject,
                        modifier = Modifier.fillMaxWidth(),
                    )
                } else {
                    PrimaryButton(
                        text = stringResource(R.string.pj06_resubmit),
                        onClick = onResubmit,
                        isLoading = isStartingResubmission,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                // PJ-07's entry point — offered once this review exists, "a suitable
                // reviewed/submitted state" per the Screen Inventory. Never gated on whether
                // this particular review was accepted; reviewing a classmate is unrelated to
                // this task's own outcome.
                GhostButton(
                    text = stringResource(R.string.pj06_review_a_peer),
                    onClick = onOpenPeerReview,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
            }
        }
    }
}

@Composable
private fun SubmissionSummary(submission: ProjectSubmission) {
    val colors = EduTheme.colors
    EduCard {
        if (submission.writtenReflection.isNotBlank()) {
            Text(submission.writtenReflection, style = EduTheme.typography.body, color = colors.textPrimary)
        }
        if (submission.link.isNotBlank()) {
            Text(submission.link, style = EduTheme.typography.body, color = colors.primary, modifier = Modifier.padding(top = Spacing.xs))
        }
        if (submission.attachments.isNotEmpty()) {
            Text(
                text = stringResource(
                    R.string.pj06_attachments_count,
                    numeral(submission.attachments.size),
                ),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun RubricRow(result: RubricResult) {
    val colors = EduTheme.colors
    val scoreColor = when {
        result.score >= result.maxScore -> colors.success
        result.score <= 0 -> colors.danger
        else -> colors.warning
    }
    Column(modifier = Modifier.padding(vertical = Spacing.xs)) {
        Row(
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = result.criterionTitle,
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
            StatusPill(
                label = stringResource(R.string.pj06_score_format, numeral(result.score), numeral(result.maxScore)),
                contentColor = scoreColor,
                containerColor = scoreColor.copy(alpha = 0.14f),
            )
        }
        Text(
            text = result.reason,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun ReviewSkeleton() {
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

