package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Circle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.RadioButtonUnchecked
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonProcessingOverallStatus
import com.rork.eduspark.data.model.LessonProcessingStageState
import com.rork.eduspark.data.model.LessonProcessingStageStatus
import com.rork.eduspark.data.model.TeacherLessonProcessingState
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-06 · Lesson Processing Status — PDF page 10.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Maps the existing five [LessonProcessingStage] values onto the approved mobile labels.
 * Stage completion is read from [TeacherLessonProcessingState], never hardcoded.
 * Leaving this screen does not cancel the repository clock — the same draft resumes on return.
 */
@Composable
fun TeacherLessonProcessingScreen(
    courseId: String,
    lessonId: String,
    onBack: () -> Unit,
    onOpenPreview: (lessonId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherLessonProcessingViewModel = koinViewModel(parameters = { parametersOf(courseId, lessonId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val lessonTitle = (state.result as? UiState.Content)?.data?.lessonTitle
        ?: stringResource(R.string.tc06_title)

    EduScaffold(
        title = lessonTitle,
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherLessonProcessingSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { _ ->
            val processing = state.processing
            if (processing != null) {
                TeacherLessonProcessingContent(
                    processing = processing,
                    isRetrying = state.isRetrying,
                    onRetry = viewModel::retryProcessing,
                    onOpenPreview = { onOpenPreview(lessonId) },
                )
            }
        }
    }
}

@Composable
private fun TeacherLessonProcessingContent(
    processing: TeacherLessonProcessingState,
    isRetrying: Boolean,
    onRetry: () -> Unit,
    onOpenPreview: () -> Unit,
) {
    val colors = EduTheme.colors
    val overall = processing.overallStatus
    val failedStage = processing.stages.firstOrNull { it.status == LessonProcessingStageStatus.Failed }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            TeacherAiPipelineVisual(
                stages = processing.stages,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.sm),
            )
            Text(
                text = stringResource(R.string.tc06_headline),
                style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
        }

        item {
            EduCard(
                borderColor = if (overall == LessonProcessingOverallStatus.Failed) colors.danger else colors.border,
                modifier = Modifier.padding(bottom = Spacing.sm),
            ) {
                processing.stages.forEachIndexed { index, stageState ->
                    ProcessingStageRow(
                        stageState = stageState,
                        modifier = Modifier.padding(bottom = if (index == processing.stages.lastIndex) 0.dp else Spacing.sm),
                    )
                }
                if (failedStage != null) {
                    if (!failedStage.errorLabel.isNullOrBlank()) {
                        Text(
                            text = failedStage.errorLabel.orEmpty(),
                            style = EduTheme.typography.caption,
                            color = colors.danger,
                            modifier = Modifier.padding(top = Spacing.sm),
                        )
                    }
                    PrimaryButton(
                        text = stringResource(R.string.tc06_retry),
                        onClick = onRetry,
                        isLoading = isRetrying,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = Spacing.sm),
                    )
                }
            }
        }

        if (overall == LessonProcessingOverallStatus.Running) {
            item {
                Text(
                    text = stringResource(R.string.tc06_background_ok),
                    style = EduTheme.typography.caption,
                    color = colors.textMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.sm),
                )
            }
        }

        if (overall == LessonProcessingOverallStatus.Completed) {
            item {
                PrimaryButton(
                    text = stringResource(R.string.tc06_open_preview),
                    onClick = onOpenPreview,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.sm),
                )
            }
        }
    }
}

@Composable
private fun ProcessingStageRow(stageState: LessonProcessingStageState, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val (icon, tint, labelColor) = when (stageState.status) {
        LessonProcessingStageStatus.Complete -> Triple(Icons.Filled.Check, colors.success, colors.textPrimary)
        LessonProcessingStageStatus.Running -> Triple(Icons.Filled.Circle, colors.aiAccent, colors.aiAccent)
        LessonProcessingStageStatus.Failed -> Triple(Icons.Filled.ErrorOutline, colors.danger, colors.textPrimary)
        LessonProcessingStageStatus.Pending, LessonProcessingStageStatus.Skipped ->
            Triple(Icons.Filled.RadioButtonUnchecked, colors.border, colors.textMuted)
    }
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier.fillMaxWidth(),
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(Sizing.icon))
        Text(
            text = processingStageLabel(stageState.stage),
            style = EduTheme.typography.body.copy(
                fontWeight = if (stageState.status == LessonProcessingStageStatus.Running) FontWeight.SemiBold else FontWeight.Normal,
            ),
            color = labelColor,
        )
    }
}

@Composable
private fun TeacherLessonProcessingSkeleton() {
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
