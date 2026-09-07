package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonStatus
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonDetail
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-08 · Lesson Preview — PDF page 11.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Teacher original source is first-class. AI chunks/quiz stay in the ViewModel for the
 * existing editor path; this surface does not duplicate the Student lesson player.
 */
@Composable
fun TeacherLessonPreviewScreen(
    courseId: String,
    lessonId: String,
    onBack: () -> Unit,
    onEdit: (lessonId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherLessonPreviewViewModel = koinViewModel(parameters = { parametersOf(courseId, lessonId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val lesson = (state.result as? UiState.Content)?.data?.lesson
    val title = lesson?.title ?: stringResource(R.string.tc08_title)

    EduScaffold(
        title = title,
        onBack = onBack,
        actions = {
            if (lesson != null) {
                GhostButton(
                    text = stringResource(R.string.tc08_edit),
                    onClick = { onEdit(lessonId) },
                )
            }
        },
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { SkeletonDetail(modifier = Modifier.padding(Spacing.gutter)) },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherSourcePreviewContent(lesson = data.lesson)
        }
    }
}

@Composable
private fun TeacherSourcePreviewContent(lesson: TeacherLesson) {
    val colors = EduTheme.colors
    val typeLabel = lessonContentTypeLabel(lesson.contentType)
    val statusLabel = when (lesson.status) {
        TeacherLessonStatus.Published -> stringResource(R.string.tc04_lesson_ready)
        TeacherLessonStatus.Processing -> stringResource(R.string.tc04_lesson_status_processing)
        TeacherLessonStatus.Draft -> stringResource(R.string.tc04_lesson_status_draft)
    }
    val statusColor = when (lesson.status) {
        TeacherLessonStatus.Published -> colors.success
        TeacherLessonStatus.Processing -> colors.aiAccent
        TeacherLessonStatus.Draft -> colors.textMuted
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.padding(bottom = Spacing.sm),
            ) {
                StatusPill(
                    label = typeLabel,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                StatusPill(
                    label = statusLabel,
                    contentColor = statusColor,
                    containerColor = statusColor.copy(alpha = 0.14f),
                )
            }

            EduCard(contentPadding = PaddingValues(0.dp)) {
                when (lesson.contentType) {
                    LessonContentType.Video -> TeacherVideoMediaWell(
                        durationLabel = lesson.durationLabel,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(190.dp)
                            .clip(RoundedCornerShape(topStart = Radius.md, topEnd = Radius.md)),
                    )
                    LessonContentType.Pdf -> TeacherPdfMediaWell(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(190.dp)
                            .padding(Spacing.card),
                    )
                }
                Column(modifier = Modifier.padding(Spacing.card)) {
                    Text(
                        text = stringResource(R.string.tc08_teacher_source),
                        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textPrimary,
                    )
                    if (lesson.status != TeacherLessonStatus.Published) {
                        Text(
                            text = stringResource(R.string.tc08_ai_after_processing),
                            style = EduTheme.typography.caption,
                            color = colors.textMuted,
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                    }
                }
            }
        }
    }
}
