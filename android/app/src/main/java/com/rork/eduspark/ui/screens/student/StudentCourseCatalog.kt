package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.CourseCardState
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.data.model.cardState
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

@Composable
internal fun StudentWebSectionIntro(
    title: String,
    modifier: Modifier = Modifier,
    eyebrow: String? = null,
    subtitle: String? = null,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        if (!eyebrow.isNullOrBlank()) {
            Text(
                text = eyebrow,
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = EduTheme.colors.primary,
            )
            Spacer(modifier = Modifier.height(Spacing.xxs))
        }
        Text(
            text = title,
            style = EduTheme.typography.title,
            color = EduTheme.colors.textPrimary,
        )
        if (!subtitle.isNullOrBlank()) {
            Text(
                text = subtitle,
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

@Composable
internal fun StudentCourseCatalogSection(
    courses: List<StudentCourseSummary>,
    gradeLabel: String?,
    onOpenCourse: (courseId: String) -> Unit,
    onOpenSubscriptions: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        if (courses.isEmpty()) {
            EduCard {
                Text(
                    text = stringResource(R.string.st01_subjects_empty_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = EduTheme.colors.textPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(
                    text = stringResource(R.string.st01_subjects_empty_body),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xxs),
                )
            }
        } else {
            Column(
                verticalArrangement = Arrangement.spacedBy(Spacing.md),
                modifier = Modifier.fillMaxWidth(),
            ) {
                courses.forEach { course ->
                    SubjectCatalogCard(
                        course = course,
                        onOpenCourse = onOpenCourse,
                        onOpenSubscriptions = onOpenSubscriptions,
                    )
                }
            }
        }
    }
}

@Composable
private fun SubjectCatalogCard(
    course: StudentCourseSummary,
    onOpenCourse: (courseId: String) -> Unit,
    onOpenSubscriptions: () -> Unit,
) {
    val colors = EduTheme.colors
    val state = course.cardState()
    val isLocked = state == CourseCardState.Locked
    val action = if (isLocked) onOpenSubscriptions else ({ onOpenCourse(course.courseId) })
    val (ctaLabel, ctaIcon, ctaColor, ctaContainer) = catalogCta(state)

    EduCard(
        onClick = action,
        onClickLabel = course.title,
        borderColor = if (isLocked) colors.highlight.copy(alpha = 0.28f) else colors.border,
        contentPadding = PaddingValues(0.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        SubjectVisual(
            courseId = course.courseId,
            modifier = Modifier
                .fillMaxWidth()
                .height(120.dp),
            compact = true,
        )

        Column(
            horizontalAlignment = Alignment.Start,
            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier
                .fillMaxWidth()
                .padding(Spacing.card),
        ) {
            Text(
                text = course.title,
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = course.teacherName,
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (state == CourseCardState.Locked || state == CourseCardState.ComingSoon) {
                Text(
                    text = progressText(course, state),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textSecondary,
                )
            } else {
                Text(
                    text = stringResource(R.string.progress_percent, (course.progress.coerceIn(0f, 1f) * 100).toInt()),
                    style = EduTheme.typography.mono.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                EduLinearProgress(progress = course.progress.coerceIn(0f, 1f))
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            ) {
                Text(
                    text = ctaLabel,
                    style = EduTheme.typography.label,
                    color = ctaColor,
                )
                Icon(ctaIcon, contentDescription = null, tint = ctaColor, modifier = Modifier.size(Sizing.icon))
            }
        }
    }
}

@Composable
private fun CourseCardState.catalogStateText(): String = when (this) {
    CourseCardState.ComingSoon -> stringResource(R.string.st01_catalog_cta_coming_soon)
    CourseCardState.Locked -> stringResource(R.string.st02_journey_state_locked)
    CourseCardState.Ready -> stringResource(R.string.st02_journey_state_upcoming)
    CourseCardState.InProgress -> stringResource(R.string.common_active)
    CourseCardState.Completed -> stringResource(R.string.st02_journey_state_completed)
}

@Composable
private fun progressText(course: StudentCourseSummary, state: CourseCardState): String = when {
    state == CourseCardState.ComingSoon -> stringResource(R.string.st_courses_coming_soon)
    state == CourseCardState.Locked && course.totalLessonCount > 0 -> {
        stringResource(R.string.st01_catalog_progress_zero_of, numeral(course.totalLessonCount))
    }
    state == CourseCardState.Locked -> stringResource(R.string.st01_catalog_progress_unavailable)
    course.totalLessonCount > 0 -> {
        stringResource(
            R.string.st01_catalog_progress_of,
            numeral(course.completedLessonCount),
            numeral(course.totalLessonCount),
        )
    }
    course.completedLessonCount > 0 -> {
        stringResource(R.string.st01_catalog_progress_completed_only, numeral(course.completedLessonCount))
    }
    else -> stringResource(R.string.st01_catalog_progress_not_started)
}

@Composable
private fun catalogCta(state: CourseCardState): CatalogCta {
    val colors = EduTheme.colors
    return when (state) {
        CourseCardState.Locked -> CatalogCta(
            stringResource(R.string.st01_catalog_cta_locked),
            Icons.Filled.Lock,
            colors.highlight,
            colors.highlightContainer,
        )
        CourseCardState.Completed -> CatalogCta(
            stringResource(R.string.st01_catalog_cta_done),
            Icons.Filled.CheckCircle,
            colors.success,
            colors.success.copy(alpha = 0.12f),
        )
        CourseCardState.InProgress -> CatalogCta(
            stringResource(R.string.st01_catalog_cta_active),
            Icons.Filled.PlayArrow,
            colors.primary,
            colors.primaryContainer,
        )
        CourseCardState.Ready -> CatalogCta(
            stringResource(R.string.st01_catalog_cta_ready),
            Icons.Filled.AutoStories,
            colors.primary,
            colors.primaryContainer,
        )
        CourseCardState.ComingSoon -> CatalogCta(
            stringResource(R.string.st01_catalog_cta_coming_soon),
            Icons.Filled.Schedule,
            colors.textSecondary,
            colors.neutralAlpha100,
        )
    }
}

@Composable
private fun catalogAccent(state: CourseCardState): Color {
    val colors = EduTheme.colors
    return when (state) {
        CourseCardState.Completed -> colors.success.copy(alpha = 0.7f)
        CourseCardState.Locked -> colors.textSecondary.copy(alpha = 0.45f)
        CourseCardState.ComingSoon -> colors.border
        else -> colors.primary
    }
}

private data class CatalogCta(
    val label: String,
    val icon: ImageVector,
    val color: Color,
    val container: Color,
)
