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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.RateReview
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
import com.rork.eduspark.data.model.AiPreReviewAvailability
import com.rork.eduspark.data.model.ProjectReviewStatus
import com.rork.eduspark.data.model.TeacherProjectSubmission
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-18 · Project Review Queue.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Submission-first list — project/student/context/submitted-date/status, review-focused rather
 * than a dashboard. AI pre-review availability is shown as its own small indicator, deliberately
 * never mixed into the teacher [ProjectReviewStatus] pill — see [TeacherProjectSubmission]'s own
 * doc comment.
 */
@Composable
fun TeacherReviewQueueScreen(
    onBack: () -> Unit,
    onOpenSubmission: (submissionId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherReviewQueueViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherReviewQueueEvent.OpenDetail -> onOpenSubmission(event.submissionId)
            }
        }
    }

    EduScaffold(title = stringResource(R.string.tc18_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherReviewQueueSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { submissions ->
            if (submissions.isEmpty()) {
                MessageState(
                    icon = Icons.Filled.RateReview,
                    title = stringResource(R.string.tc18_empty_title),
                    body = stringResource(R.string.tc18_empty_body),
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    items(submissions, key = { it.id }) { submission ->
                        SubmissionRow(submission = submission, onClick = { viewModel.onSubmissionTapped(submission.id) })
                    }
                }
            }
        }
    }
}

@Composable
private fun SubmissionRow(submission: TeacherProjectSubmission, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val statusColor = when (submission.reviewStatus) {
        ProjectReviewStatus.AwaitingReview -> colors.warning
        ProjectReviewStatus.InReview -> colors.zaytoun
        ProjectReviewStatus.Reviewed -> colors.success
    }

    EduCard(onClick = onClick, modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.weight(1f)) {
                Text(submission.projectTitle, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                Text(submission.studentName, style = EduTheme.typography.caption, color = colors.zaytoun, modifier = Modifier.padding(top = Spacing.xxs))
            }
            StatusPill(label = projectReviewStatusLabel(submission.reviewStatus), contentColor = statusColor, containerColor = statusColor.copy(alpha = 0.14f))
        }
        Text(submission.milestoneTitle, style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.sm))
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth().padding(top = Spacing.xxs)) {
            Text(submission.submittedLabel, style = EduTheme.typography.caption, color = colors.textMuted)
            if (submission.aiAvailability == AiPreReviewAvailability.Ready) {
                Text(stringResource(R.string.tc18_ai_ready), style = EduTheme.typography.caption, color = colors.zaytoun)
            }
        }
    }
}

@Composable
private fun TeacherReviewQueueSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
    }
}
