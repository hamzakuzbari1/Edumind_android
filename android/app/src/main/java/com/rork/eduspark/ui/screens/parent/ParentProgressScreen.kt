package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.Class
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentAchievementSummary
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNamedAchievement
import com.rork.eduspark.data.model.ParentPerformanceSnapshot
import com.rork.eduspark.data.model.ParentPerformanceTrend
import com.rork.eduspark.data.model.ParentQuizResult
import com.rork.eduspark.data.model.ParentSubjectPerformance
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun ParentProgressScreen(
    onOpenLinkStudent: () -> Unit,
    onOpenAttendanceStudyTime: () -> Unit,
    onOpenLessonProgress: () -> Unit,
    onOpenSubjectsTeachers: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentProgressViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { ParentProgressSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        ParentProgressContent(
            data = data,
            onSelectStudent = viewModel::selectStudent,
            onOpenLinkStudent = onOpenLinkStudent,
            onOpenAttendanceStudyTime = onOpenAttendanceStudyTime,
            onOpenLessonProgress = onOpenLessonProgress,
            onOpenSubjectsTeachers = onOpenSubjectsTeachers,
        )
    }
}

@Composable
private fun ParentProgressContent(
    data: ParentProgressData,
    onSelectStudent: (String) -> Unit,
    onOpenLinkStudent: () -> Unit,
    onOpenAttendanceStudyTime: () -> Unit,
    onOpenLessonProgress: () -> Unit,
    onOpenSubjectsTeachers: () -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentProgressEmptyState(onOpenLinkStudent = onOpenLinkStudent)
        return
    }

    val selectedStudent = data.linkedStudents.firstOrNull { it.id == data.selectedStudentId }
        ?: data.linkedStudents.first()

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            ParentProgressStudentCard(
                students = data.linkedStudents,
                selectedStudent = selectedStudent,
                onSelectStudent = onSelectStudent,
            )
        }

        val performance = data.performance
        if (performance == null) {
            item { SkeletonCard() }
            item { SkeletonCard() }
            item { SkeletonListItem() }
        } else {
            item { ParentPerformanceSummaryRow(performance = performance) }
            if (performance.trend != null) {
                item { ParentAcademicTrendCard(performance = performance, trend = performance.trend) }
            }
            item { ParentRecentQuizzesCard(quizzes = performance.recentQuizzes) }
            item { ParentAttendanceStudyTimeEntry(onOpen = onOpenAttendanceStudyTime) }
            item { ParentLessonProgressEntry(onOpen = onOpenLessonProgress) }
            item { ParentSubjectsTeachersEntry(onOpen = onOpenSubjectsTeachers) }
            item { ParentSubjectPerformanceCard(subjects = performance.subjects) }
            performance.achievements?.let { achievements ->
                item { ParentAchievementSummaryCard(summary = achievements) }
            }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }
}

@Composable
private fun ParentProgressEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentProgressIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr03_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr03_empty_body),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
                PrimaryButton(
                    text = stringResource(R.string.pr02_empty_action),
                    onClick = onOpenLinkStudent,
                    leadingIcon = Icons.Filled.Link,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            }
        }
    }
}

@Composable
private fun ParentProgressStudentCard(
    students: List<ParentLinkedStudent>,
    selectedStudent: ParentLinkedStudent,
    onSelectStudent: (String) -> Unit,
) {
    val colors = EduTheme.colors
    EduCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentAvatar(
                initial = selectedStudent.avatarInitial,
                modifier = Modifier.size(Sizing.avatarLg),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = selectedStudent.displayName,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (selectedStudent.gradeLabel.isNotBlank()) {
                    Text(
                        text = selectedStudent.gradeLabel,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
            }
            StatusPill(
                label = stringResource(R.string.pr03_scope_read_only),
                contentColor = colors.primary,
                containerColor = colors.primaryContainer,
            )
        }

        if (students.size > 1) {
            Text(
                text = stringResource(R.string.pr02_student_selector_label),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.padding(top = Spacing.xs),
            ) {
                items(students, key = { it.id }) { student ->
                    EduChip(
                        label = student.displayName,
                        selected = student.id == selectedStudent.id,
                        onClick = { onSelectStudent(student.id) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ParentPerformanceSummaryRow(performance: ParentPerformanceSnapshot) {
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        ParentMetricCard(
            value = stringResource(R.string.pr02_percent_value, numeral(performance.testAveragePercent)),
            label = stringResource(R.string.pr03_test_average),
            modifier = Modifier.weight(1f),
        )
        ParentMetricCard(
            value = stringResource(R.string.pr02_percent_value, numeral(performance.subjectProgressPercent)),
            label = stringResource(R.string.pr03_subject_progress),
            modifier = Modifier.weight(1f),
        )
        ParentMetricCard(
            value = if (performance.hasImprovementData) {
                stringResource(R.string.pr03_improvement_value, numeral(performance.improvementPercent))
            } else {
                stringResource(R.string.pr_no_data_short)
            },
            label = stringResource(R.string.pr03_improvement),
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun ParentMetricCard(
    value: String,
    label: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    EduCard(
        contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.md),
        modifier = modifier.heightIn(min = Sizing.avatarLg + Spacing.sm),
    ) {
        Text(
            text = value,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            maxLines = 1,
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun ParentAcademicTrendCard(
    performance: ParentPerformanceSnapshot,
    trend: ParentPerformanceTrend,
) {
    val colors = EduTheme.colors
    EduCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.pr03_academic_intelligence),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = performance.summary.ifBlank { stringResource(R.string.pr03_trend_body) },
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            if (performance.periodLabel.isNotBlank()) {
                StatusPill(
                    label = performance.periodLabel,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
            }
        }

        ParentTrendChart(
            trend = trend,
            modifier = Modifier
                .fillMaxWidth()
                .height(Sizing.heroBadge + Spacing.xl),
        )
    }
}

@Composable
private fun ParentTrendChart(
    trend: ParentPerformanceTrend,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val description = stringResource(R.string.pr03_trend_chart_a11y)
    val currentLine = colors.primary
    val previousLine = colors.aiAccent
    val baseline = colors.border

    Canvas(
        modifier = modifier
            .padding(top = Spacing.md)
            .semantics { contentDescription = description },
    ) {
        val topPadding = Spacing.sm.toPx()
        val bottomPadding = Spacing.sm.toPx()
        val leftPadding = Spacing.xs.toPx()
        val rightPadding = Spacing.xs.toPx()
        val chartWidth = size.width - leftPadding - rightPadding
        val chartHeight = size.height - topPadding - bottomPadding
        // Scores come straight from the backend, so the axis follows the data instead of a fixed band.
        val allScores = trend.currentScores + trend.previousScores
        val minScore = (allScores.minOrNull() ?: 0).toFloat()
        val maxScore = (allScores.maxOrNull() ?: 100).toFloat()
        val span = (maxScore - minScore).takeIf { it > 0f } ?: 1f

        fun pointAt(values: List<Int>, index: Int): Offset {
            val x = leftPadding + chartWidth * (index.toFloat() / (values.size - 1).coerceAtLeast(1))
            val y = topPadding + chartHeight * (1f - ((values[index] - minScore) / span))
            return Offset(x, y)
        }

        drawLine(
            color = baseline,
            start = Offset(leftPadding, size.height - bottomPadding),
            end = Offset(size.width - rightPadding, size.height - bottomPadding),
            strokeWidth = Sizing.hairline.toPx(),
        )

        fun drawSeries(values: List<Int>, color: Color, dashed: Boolean) {
            values.indices.drop(1).forEach { index ->
                drawLine(
                    color = color,
                    start = pointAt(values, index - 1),
                    end = pointAt(values, index),
                    strokeWidth = Spacing.xxs.toPx(),
                    cap = StrokeCap.Round,
                    pathEffect = if (dashed) PathEffect.dashPathEffect(floatArrayOf(16f, 14f)) else null,
                )
            }
        }

        drawSeries(trend.previousScores, previousLine, dashed = true)
        drawSeries(trend.currentScores, currentLine, dashed = false)
    }
}

@Composable
private fun ParentAttendanceStudyTimeEntry(onOpen: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        ListRow(
            title = stringResource(R.string.pr04_title),
            supporting = stringResource(R.string.pr04_nav_body),
            leading = Icons.Filled.Timer,
            leadingTint = colors.primary,
            showChevron = true,
            onClick = onOpen,
        )
    }
}

@Composable
private fun ParentLessonProgressEntry(onOpen: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        ListRow(
            title = stringResource(R.string.pr05_title),
            supporting = stringResource(R.string.pr05_nav_body),
            leading = Icons.Filled.AutoStories,
            leadingTint = colors.primary,
            showChevron = true,
            onClick = onOpen,
        )
    }
}

@Composable
private fun ParentSubjectsTeachersEntry(onOpen: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        ListRow(
            title = stringResource(R.string.pr10_title),
            supporting = stringResource(R.string.pr10_nav_body),
            leading = Icons.Filled.Class,
            leadingTint = colors.primary,
            showChevron = true,
            onClick = onOpen,
        )
    }
}

@Composable
private fun ParentRecentQuizzesCard(quizzes: List<ParentQuizResult>) {
    EduCard {
        Text(
            text = stringResource(R.string.pr03_recent_quizzes),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
        )
        if (quizzes.isEmpty()) {
            Text(
                text = stringResource(R.string.pr03_recent_quizzes_empty),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
            return@EduCard
        }
        quizzes.forEachIndexed { index, quiz ->
            ParentRecentQuizRow(quiz = quiz)
            if (index != quizzes.lastIndex) EduDivider()
        }
    }
}

@Composable
private fun ParentRecentQuizRow(quiz: ParentQuizResult) {
    val title = quiz.title.ifBlank { quiz.subject }
    val supporting = listOfNotNull(
        quiz.subject.takeIf { it.isNotBlank() && it != title },
        quiz.dateLabel.takeIf { it.isNotBlank() },
    ).joinToString(" · ")
    ListRow(
        title = title.ifBlank { stringResource(R.string.pr03_recent_quizzes) },
        supporting = supporting.takeIf { it.isNotBlank() },
        leading = Icons.Filled.Quiz,
        leadingTint = EduTheme.colors.primary,
        trailingContent = {
            Text(
                text = stringResource(R.string.pr02_percent_value, numeral(quiz.scorePercent)),
                style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.textSecondary,
            )
        },
        modifier = Modifier.semantics {
            contentDescription = listOfNotNull(
                title.takeIf { it.isNotBlank() },
                supporting.takeIf { it.isNotBlank() },
                "${quiz.scorePercent}%",
            ).joinToString(", ")
        },
    )
}

@Composable
private fun ParentSubjectPerformanceCard(subjects: List<ParentSubjectPerformance>) {
    EduCard {
        Text(
            text = stringResource(R.string.pr03_subject_performance),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
        )
        if (subjects.isEmpty()) {
            Text(
                text = stringResource(R.string.pr03_subject_performance_empty),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
        subjects.forEach { subject ->
            ParentSubjectPerformanceRow(
                subject = subject,
                modifier = Modifier.padding(top = Spacing.md),
            )
        }
    }
}

@Composable
private fun ParentSubjectPerformanceRow(
    subject: ParentSubjectPerformance,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = subject.subjectName,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                if (subject.statusLabel.isNotBlank()) {
                    Text(
                        text = subject.statusLabel,
                        style = EduTheme.typography.caption,
                        color = if (subject.isStrong) colors.success else colors.warning,
                    )
                }
            }
            Text(
                text = stringResource(R.string.pr02_percent_value, numeral(subject.percent)),
                style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textSecondary,
            )
        }
        EduLinearProgress(
            progress = subject.percent / 100f,
            contentDescription = stringResource(
                R.string.pr03_subject_progress_a11y,
                subject.subjectName,
                numeral(subject.percent),
            ),
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentAchievementSummaryCard(summary: ParentAchievementSummary) {
    val colors = EduTheme.colors
    EduCard(
        borderColor = colors.highlight.copy(alpha = 0.32f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentProgressIconBadge(
                icon = Icons.Filled.Star,
                contentColor = colors.highlight,
                containerColor = colors.highlightContainer,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.pr03_achievements_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.pr03_achievements_body),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
        }
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.md),
        ) {
            StatusPill(
                label = stringResource(R.string.pr03_streak_days, numeral(summary.streakDays)),
                contentColor = colors.textSecondary,
                containerColor = colors.neutralAlpha100,
                modifier = Modifier.weight(1f),
            )
            StatusPill(
                label = stringResource(R.string.pr03_badges_count, numeral(summary.badgeCount)),
                contentColor = colors.textSecondary,
                containerColor = colors.neutralAlpha100,
                modifier = Modifier.weight(1f),
            )
            StatusPill(
                label = stringResource(R.string.pr03_level_value, numeral(summary.level)),
                contentColor = colors.textSecondary,
                containerColor = colors.neutralAlpha100,
                modifier = Modifier.weight(1f),
            )
        }
        summary.totalXp?.let { xp ->
            StatusPill(
                label = stringResource(R.string.pr03_xp_value, numeral(xp)),
                contentColor = colors.textSecondary,
                containerColor = colors.neutralAlpha100,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
        if (summary.namedAchievements.isNotEmpty()) {
            summary.namedAchievements.forEachIndexed { index, achievement ->
                if (index == 0) Spacer(modifier = Modifier.height(Spacing.sm))
                ParentNamedAchievementRow(achievement = achievement)
                if (index != summary.namedAchievements.lastIndex) EduDivider()
            }
        }
    }
}

@Composable
private fun ParentNamedAchievementRow(achievement: ParentNamedAchievement) {
    val supporting = listOfNotNull(
        achievement.description.takeIf { it.isNotBlank() },
        achievement.unlockedAtLabel.takeIf { it.isNotBlank() },
    ).joinToString(" · ")
    ListRow(
        title = achievement.title,
        supporting = supporting.takeIf { it.isNotBlank() },
        leading = Icons.Filled.Star,
        leadingTint = EduTheme.colors.highlight,
    )
}

@Composable
private fun ParentProgressIconBadge(
    icon: ImageVector,
    contentColor: Color,
    containerColor: Color,
    modifier: Modifier = Modifier,
) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(Sizing.touchTarget)
            .background(containerColor, RoundedCornerShape(Radius.pill)),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = contentColor,
            modifier = Modifier.size(Sizing.icon),
        )
    }
}

@Composable
private fun ParentProgressSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonListItem()
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
