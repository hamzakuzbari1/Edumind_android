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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.WarningAmber
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentLessonActivityEvent
import com.rork.eduspark.data.model.ParentLessonActivityTime
import com.rork.eduspark.data.model.ParentLessonActivityType
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonProgressStatus
import com.rork.eduspark.data.model.ParentLessonTopic
import com.rork.eduspark.data.model.ParentLessonUnit
import com.rork.eduspark.data.model.ParentLessonVerificationItem
import com.rork.eduspark.data.model.ParentLessonVerificationStatus
import com.rork.eduspark.data.model.ParentLessonVerificationType
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentSubjectKind
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.progress.ProgressSpine
import com.rork.eduspark.ui.components.progress.SpineNode
import com.rork.eduspark.ui.components.progress.SpineNodeState
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

@Composable
fun ParentLessonDetailsScreen(
    lessonId: String,
    onBack: () -> Unit,
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentLessonDetailsViewModel = koinViewModel(parameters = { parametersOf(lessonId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.pr06_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLessonDetailsSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentLessonDetailsContent(
                data = data,
                onOpenLinkStudent = onOpenLinkStudent,
            )
        }
    }
}

@Composable
private fun ParentLessonDetailsContent(
    data: ParentLessonDetailsData,
    onOpenLinkStudent: () -> Unit,
) {
    val linkedStudent = data.linkedStudent
    val details = data.details
    if (linkedStudent == null || details == null) {
        ParentLessonDetailsEmptyState(onOpenLinkStudent = onOpenLinkStudent)
        return
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item { ParentLessonDetailsStudentCard(student = linkedStudent) }
        item { ParentLessonOverviewCard(details = details) }
        item { ParentLessonMetricsRow(details = details) }
        item { SectionHeader(title = stringResource(R.string.pr06_checklist_title)) }
        item { ParentLessonChecklistCard(items = details.checklist) }
        if (details.missingRequirements > 0) {
            item { ParentLessonMissingRequirementsCard(missingRequirements = details.missingRequirements) }
        }
        item { SectionHeader(title = stringResource(R.string.pr06_timeline_title)) }
        item { ParentLessonTimelineCard(events = details.timeline) }
        item { Spacer(modifier = Modifier.height(Spacing.section)) }
    }
}

@Composable
private fun ParentLessonDetailsEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentLessonDetailsIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr06_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr06_empty_body),
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
private fun ParentLessonDetailsStudentCard(student: ParentLinkedStudent) {
    val colors = EduTheme.colors
    EduCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentAvatar(
                initial = student.avatarInitial,
                modifier = Modifier.size(Sizing.avatarLg),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = student.displayName,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = stringResource(
                        R.string.pr_linked_student_grade_section,
                        student.gradeLabel,
                        student.sectionLabel,
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
    }
}

@Composable
private fun ParentLessonOverviewCard(details: ParentLessonDetails) {
    val colors = EduTheme.colors
    val lesson = details.lesson
    val title = parentLessonDetailsTopicLabel(lesson.topic)
    val subject = parentLessonDetailsSubjectLabel(lesson.subject)
    val unit = parentLessonDetailsUnitLabel(details.unit)
    val status = parentLessonDetailsStatusLabel(lesson.status, lesson.progressPercent)
    val progress = lesson.progressPercent / 100f
    val description = stringResource(
        R.string.pr06_lesson_overview_a11y,
        title,
        subject,
        numeral(lesson.progressPercent),
    )

    EduCard(
        containerColor = colors.primary,
        borderColor = colors.primary,
        modifier = Modifier.semantics { contentDescription = description },
    ) {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.onPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = stringResource(R.string.pr06_subject_unit, subject, unit),
                    style = EduTheme.typography.body,
                    color = colors.onPrimary.copy(alpha = 0.82f),
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            StatusPill(
                label = status,
                contentColor = colors.primary,
                containerColor = colors.onPrimary,
            )
        }
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
private fun ParentLessonMetricsRow(details: ParentLessonDetails) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        ParentLessonMetricCard(
            value = stringResource(
                R.string.pr06_pages_value,
                numeral(details.pagesViewed),
                numeral(details.totalPages),
            ),
            label = stringResource(R.string.pr06_pages_viewed),
            modifier = Modifier.weight(1f),
        )
        ParentLessonMetricCard(
            value = stringResource(
                R.string.pr06_requirements_value,
                numeral(details.requirementsCompleted),
                numeral(details.requirementsTotal),
            ),
            label = stringResource(R.string.pr06_requirements),
            modifier = Modifier.weight(1f),
        )
        ParentLessonMetricCard(
            value = stringResource(R.string.pr06_minutes_short, numeral(details.learningMinutes)),
            label = stringResource(R.string.pr06_learning_time),
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun ParentLessonMetricCard(
    value: String,
    label: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    EduCard(
        contentPadding = PaddingValues(Spacing.sm),
        modifier = modifier,
    ) {
        Text(
            text = value,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
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
private fun ParentLessonChecklistCard(items: List<ParentLessonVerificationItem>) {
    val colors = EduTheme.colors
    EduCard {
        items.forEachIndexed { index, item ->
            val complete = item.status == ParentLessonVerificationStatus.Complete
            ListRow(
                title = parentLessonVerificationTitle(item.type),
                supporting = parentLessonVerificationStatusLabel(item.status),
                leading = if (complete) Icons.Filled.Check else Icons.Filled.WarningAmber,
                leadingTint = if (complete) colors.success else colors.warning,
            )
            if (index != items.lastIndex) {
                EduDivider()
            }
        }
    }
}

@Composable
private fun ParentLessonMissingRequirementsCard(missingRequirements: Int) {
    val colors = EduTheme.colors
    EduCard(
        containerColor = colors.warning.copy(alpha = 0.12f),
        borderColor = colors.warning.copy(alpha = 0.34f),
    ) {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentLessonDetailsIconBadge(
                icon = Icons.Filled.WarningAmber,
                contentColor = colors.warning,
                containerColor = colors.warning.copy(alpha = 0.18f),
                modifier = Modifier.size(Sizing.touchTarget),
            )
            Text(
                text = stringResource(R.string.pr06_missing_warning, numeral(missingRequirements)),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentLessonTimelineCard(events: List<ParentLessonActivityEvent>) {
    EduCard {
        ProgressSpine(
            nodes = events.map { SpineNode(id = it.id, state = SpineNodeState.Completed) },
        ) { index, _ ->
            val event = events[index]
            Column(
                verticalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = if (index == events.lastIndex) 0.dp else Spacing.sm),
            ) {
                Text(
                    text = parentLessonTimelineTitle(event.type),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = EduTheme.colors.textPrimary,
                )
                Text(
                    text = parentLessonTimelineTime(event.time),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
            }
        }
    }
}

@Composable
private fun ParentLessonDetailsIconBadge(
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
private fun parentLessonDetailsTopicLabel(topic: ParentLessonTopic): String = when (topic) {
    ParentLessonTopic.DecimalFractions -> stringResource(R.string.pr05_lesson_decimal_fractions)
    ParentLessonTopic.RespiratorySystem -> stringResource(R.string.pr05_lesson_respiratory_system)
    ParentLessonTopic.ObjectPronoun -> stringResource(R.string.pr05_lesson_object_pronoun)
}

@Composable
private fun parentLessonDetailsSubjectLabel(subject: ParentSubjectKind): String = when (subject) {
    ParentSubjectKind.Mathematics -> stringResource(R.string.pr03_subject_math)
    ParentSubjectKind.Science -> stringResource(R.string.pr03_subject_science)
    ParentSubjectKind.Arabic -> stringResource(R.string.pr03_subject_arabic)
}

@Composable
private fun parentLessonDetailsUnitLabel(unit: ParentLessonUnit): String = when (unit) {
    ParentLessonUnit.UnitThree -> stringResource(R.string.pr06_unit_three)
}

@Composable
private fun parentLessonDetailsStatusLabel(
    status: ParentLessonProgressStatus,
    progressPercent: Int,
): String = when (status) {
    ParentLessonProgressStatus.Completed -> stringResource(R.string.pr05_status_completed)
    ParentLessonProgressStatus.InProgress -> stringResource(R.string.pr02_percent_value, numeral(progressPercent))
}

@Composable
private fun parentLessonVerificationTitle(type: ParentLessonVerificationType): String = when (type) {
    ParentLessonVerificationType.OpenedLessonFile -> stringResource(R.string.pr06_check_opened_file)
    ParentLessonVerificationType.ReadRequiredPages -> stringResource(R.string.pr06_check_read_pages)
    ParentLessonVerificationType.CompletedVerificationActivity -> stringResource(R.string.pr06_check_completed_activity)
}

@Composable
private fun parentLessonVerificationStatusLabel(status: ParentLessonVerificationStatus): String = when (status) {
    ParentLessonVerificationStatus.Complete -> stringResource(R.string.pr06_check_complete)
    ParentLessonVerificationStatus.Missing -> stringResource(R.string.pr06_check_missing)
}

@Composable
private fun parentLessonTimelineTitle(type: ParentLessonActivityType): String = when (type) {
    ParentLessonActivityType.CompletedTermsActivity -> stringResource(R.string.pr06_timeline_completed_terms)
    ParentLessonActivityType.OpenedPages -> stringResource(R.string.pr06_timeline_opened_pages)
    ParentLessonActivityType.StartedLesson -> stringResource(R.string.pr06_timeline_started_lesson)
}

@Composable
private fun parentLessonTimelineTime(time: ParentLessonActivityTime): String = when (time) {
    ParentLessonActivityTime.Today1640 -> stringResource(R.string.pr06_time_today_1640)
    ParentLessonActivityTime.Today1615 -> stringResource(R.string.pr06_time_today_1615)
    ParentLessonActivityTime.Today1600 -> stringResource(R.string.pr06_time_today_1600)
}

@Composable
private fun ParentLessonDetailsSkeleton() {
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
