package com.rork.eduspark.ui.screens.parent

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
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Link
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentLessonProgressFilter
import com.rork.eduspark.data.model.ParentLessonProgressItem
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLessonProgressStatus
import com.rork.eduspark.data.model.ParentLessonTopic
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentSubjectKind
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun ParentLessonProgressScreen(
    onBack: () -> Unit,
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentLessonProgressViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.pr05_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLessonProgressSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentLessonProgressContent(
                data = data,
                onSelectStudent = viewModel::selectStudent,
                onSelectFilter = viewModel::selectFilter,
                onOpenLinkStudent = onOpenLinkStudent,
            )
        }
    }
}

@Composable
private fun ParentLessonProgressContent(
    data: ParentLessonProgressData,
    onSelectStudent: (String) -> Unit,
    onSelectFilter: (ParentLessonProgressFilter) -> Unit,
    onOpenLinkStudent: () -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentLessonProgressEmptyState(onOpenLinkStudent = onOpenLinkStudent)
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
            ParentLessonStudentCard(
                students = data.linkedStudents,
                selectedStudent = selectedStudent,
                onSelectStudent = onSelectStudent,
            )
        }

        val snapshot = data.snapshot
        if (snapshot == null) {
            item { SkeletonCard() }
            item { SkeletonCard() }
            item { SkeletonListItem() }
        } else {
            item { ParentLessonSummaryCard(snapshot = snapshot) }
            item {
                ParentLessonFilterRow(
                    selectedFilter = data.selectedFilter,
                    onSelectFilter = onSelectFilter,
                )
            }
            item {
                ParentLessonListCard(
                    lessons = snapshot.lessons.filteredBy(data.selectedFilter),
                )
            }
            item { ParentLessonGuidanceCard() }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }
}

@Composable
private fun ParentLessonProgressEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentLessonIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr05_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr05_empty_body),
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
private fun ParentLessonStudentCard(
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
                Text(
                    text = stringResource(
                        R.string.pr_linked_student_grade_section,
                        selectedStudent.gradeLabel,
                        selectedStudent.sectionLabel,
                    ),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
            StatusPill(
                label = stringResource(R.string.pr04_read_only),
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
private fun ParentLessonSummaryCard(snapshot: ParentLessonProgressSnapshot) {
    val colors = EduTheme.colors
    val progress = snapshot.completedLessons.toFloat() / snapshot.totalLessons.coerceAtLeast(1)
    EduCard(
        containerColor = colors.primary,
        borderColor = colors.primary,
    ) {
        Text(
            text = stringResource(R.string.pr05_summary_title),
            style = EduTheme.typography.caption,
            color = colors.onPrimary.copy(alpha = 0.82f),
        )
        Text(
            text = stringResource(
                R.string.pr05_summary_value,
                numeral(snapshot.completedLessons),
                numeral(snapshot.totalLessons),
            ),
            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.onPrimary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Spacer(modifier = Modifier.height(Spacing.md))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(Spacing.xs)
                .background(colors.onPrimary.copy(alpha = 0.28f), RoundedCornerShape(Radius.pill)),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(progress.coerceIn(0f, 1f))
                    .height(Spacing.xs)
                    .background(colors.onPrimary, RoundedCornerShape(Radius.pill)),
            )
        }
    }
}

@Composable
private fun ParentLessonFilterRow(
    selectedFilter: ParentLessonProgressFilter,
    onSelectFilter: (ParentLessonProgressFilter) -> Unit,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        ParentLessonProgressFilter.entries.forEach { filter ->
            EduChip(
                label = parentLessonFilterLabel(filter),
                selected = filter == selectedFilter,
                onClick = { onSelectFilter(filter) },
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentLessonListCard(lessons: List<ParentLessonProgressItem>) {
    EduCard {
        lessons.forEachIndexed { index, lesson ->
            ParentLessonProgressRow(
                lesson = lesson,
                index = index,
            )
            if (index != lessons.lastIndex) {
                EduDivider()
            }
        }
    }
}

@Composable
private fun ParentLessonProgressRow(
    lesson: ParentLessonProgressItem,
    index: Int,
) {
    val colors = EduTheme.colors
    val title = parentLessonTopicLabel(lesson.topic)
    val status = parentLessonStatusLabel(lesson.status)
    val description = stringResource(
        R.string.pr05_lesson_row_a11y,
        title,
        status,
        numeral(lesson.progressPercent),
    )

    Row(
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.sm)
            .semantics { contentDescription = description },
    ) {
        ParentLessonNumberBadge(
            number = index + 1,
            status = lesson.status,
        )
        Column(modifier = Modifier.weight(1f)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            ) {
                Text(
                    text = title,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                if (lesson.status == ParentLessonProgressStatus.Completed) {
                    StatusPill(
                        label = status,
                        contentColor = colors.success,
                        containerColor = colors.success.copy(alpha = 0.14f),
                    )
                } else {
                    Text(
                        text = stringResource(R.string.pr02_percent_value, numeral(lesson.progressPercent)),
                        style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textSecondary,
                    )
                }
            }
            Text(
                text = parentLessonSupportingText(lesson),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
            if (lesson.status == ParentLessonProgressStatus.InProgress) {
                EduLinearProgress(
                    progress = lesson.progressPercent / 100f,
                    contentDescription = description,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }
    }
}

@Composable
private fun ParentLessonNumberBadge(
    number: Int,
    status: ParentLessonProgressStatus,
) {
    val colors = EduTheme.colors
    val contentColor = when (status) {
        ParentLessonProgressStatus.Completed -> colors.success
        ParentLessonProgressStatus.InProgress -> colors.primary
    }
    val containerColor = when (status) {
        ParentLessonProgressStatus.Completed -> colors.success.copy(alpha = 0.14f)
        ParentLessonProgressStatus.InProgress -> colors.primaryContainer
    }
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(Sizing.touchTarget)
            .background(containerColor, RoundedCornerShape(Radius.pill)),
    ) {
        Text(
            text = numeral(number),
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
            color = contentColor,
        )
    }
}

@Composable
private fun ParentLessonGuidanceCard() {
    val colors = EduTheme.colors
    EduCard(
        containerColor = colors.aiAccentContainer,
        borderColor = colors.aiAccent.copy(alpha = 0.32f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Icon(
                imageVector = Icons.Filled.Info,
                contentDescription = null,
                tint = colors.aiAccent,
                modifier = Modifier.size(Sizing.icon),
            )
            Text(
                text = stringResource(R.string.pr05_guidance_body),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
        }
    }
}

@Composable
private fun ParentLessonIconBadge(
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

private fun List<ParentLessonProgressItem>.filteredBy(
    filter: ParentLessonProgressFilter,
): List<ParentLessonProgressItem> = when (filter) {
    ParentLessonProgressFilter.All -> this
    ParentLessonProgressFilter.InProgress -> filter { it.status == ParentLessonProgressStatus.InProgress }
    ParentLessonProgressFilter.Completed -> filter { it.status == ParentLessonProgressStatus.Completed }
}

@Composable
private fun parentLessonFilterLabel(filter: ParentLessonProgressFilter): String = when (filter) {
    ParentLessonProgressFilter.All -> stringResource(R.string.pr05_filter_all)
    ParentLessonProgressFilter.InProgress -> stringResource(R.string.pr05_filter_in_progress)
    ParentLessonProgressFilter.Completed -> stringResource(R.string.pr05_filter_completed)
}

@Composable
private fun parentLessonTopicLabel(topic: ParentLessonTopic): String = when (topic) {
    ParentLessonTopic.DecimalFractions -> stringResource(R.string.pr05_lesson_decimal_fractions)
    ParentLessonTopic.RespiratorySystem -> stringResource(R.string.pr05_lesson_respiratory_system)
    ParentLessonTopic.ObjectPronoun -> stringResource(R.string.pr05_lesson_object_pronoun)
}

@Composable
private fun parentLessonSubjectLabel(subject: ParentSubjectKind): String = when (subject) {
    ParentSubjectKind.Mathematics -> stringResource(R.string.pr03_subject_math)
    ParentSubjectKind.Science -> stringResource(R.string.pr03_subject_science)
    ParentSubjectKind.Arabic -> stringResource(R.string.pr03_subject_arabic)
}

@Composable
private fun parentLessonStatusLabel(status: ParentLessonProgressStatus): String = when (status) {
    ParentLessonProgressStatus.Completed -> stringResource(R.string.pr05_status_completed)
    ParentLessonProgressStatus.InProgress -> stringResource(R.string.pr05_status_in_progress)
}

@Composable
private fun parentLessonSupportingText(lesson: ParentLessonProgressItem): String {
    val subject = parentLessonSubjectLabel(lesson.subject)
    return when (lesson.status) {
        ParentLessonProgressStatus.Completed -> stringResource(R.string.pr05_completed_supporting, subject)
        ParentLessonProgressStatus.InProgress -> stringResource(
            R.string.pr05_activity_supporting,
            subject,
            numeral(lesson.completedActivities),
            numeral(lesson.totalActivities),
        )
    }
}

@Composable
private fun ParentLessonProgressSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonListItem()
        SkeletonCard()
        SkeletonCard()
        SkeletonListItem()
    }
}
