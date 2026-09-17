package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Schedule
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
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentPlannerSession
import com.rork.eduspark.data.model.ParentPlannerSessionStatus
import com.rork.eduspark.data.model.ParentPlannerSnapshot
import com.rork.eduspark.data.model.ParentRoutineSlot
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
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

@Composable
fun ParentPlannerScreen(
    onBack: () -> Unit,
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentPlannerViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.pr07_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentPlannerSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentPlannerContent(
                data = data,
                onSelectStudent = viewModel::selectStudent,
                onOpenLinkStudent = onOpenLinkStudent,
            )
        }
    }
}

@Composable
private fun ParentPlannerContent(
    data: ParentPlannerData,
    onSelectStudent: (String) -> Unit,
    onOpenLinkStudent: () -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentPlannerEmptyState(onOpenLinkStudent = onOpenLinkStudent)
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
            ParentPlannerStudentCard(
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
            item { ParentPlannerCommitmentCard(snapshot = snapshot) }
            item {
                SectionHeader(
                    title = listOfNotNull(
                        stringResource(R.string.pr07_today_routine),
                        snapshot.todayLabel.takeIf { it.isNotBlank() },
                    ).joinToString(" · "),
                )
            }
            item { ParentPlannerRoutineCard(slots = snapshot.todayRoutine) }
            if (snapshot.sessions.isNotEmpty()) {
                item { SectionHeader(title = stringResource(R.string.pr07_planner_tasks)) }
                item { ParentPlannerSessionsCard(sessions = snapshot.sessions) }
            }
            val pattern = snapshot.consistencyLabel.ifBlank { snapshot.summary }
            if (pattern.isNotBlank()) {
                item { ParentPlannerPatternCard(pattern = pattern) }
            }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }
}

@Composable
private fun ParentPlannerEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentPlannerIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr07_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr07_empty_body),
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
private fun ParentPlannerStudentCard(
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
private fun ParentPlannerCommitmentCard(snapshot: ParentPlannerSnapshot) {
    val colors = EduTheme.colors
    EduCard(
        containerColor = colors.primary,
        borderColor = colors.primary,
    ) {
        Text(
            text = stringResource(R.string.pr07_commitment_label),
            style = EduTheme.typography.caption,
            color = colors.onPrimary.copy(alpha = 0.82f),
        )
        Text(
            text = stringResource(R.string.pr07_commitment_value, numeral(snapshot.commitmentPercent)),
            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.onPrimary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Text(
            text = stringResource(
                R.string.pr07_commitment_body,
                numeral(snapshot.completedSessions),
                numeral(snapshot.totalSessions),
                numeral(snapshot.postponedSessions),
            ),
            style = EduTheme.typography.body,
            color = colors.onPrimary.copy(alpha = 0.86f),
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.md),
        ) {
            ParentPlannerHeroStat(
                value = numeral(snapshot.completedSessions),
                label = stringResource(R.string.pr07_completed_sessions),
                modifier = Modifier.weight(1f),
            )
            ParentPlannerHeroStat(
                value = numeral(snapshot.totalSessions),
                label = stringResource(R.string.pr07_planned_sessions),
                modifier = Modifier.weight(1f),
            )
            ParentPlannerHeroStat(
                value = numeral(snapshot.postponedSessions),
                label = stringResource(R.string.pr07_postponed_sessions),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentPlannerHeroStat(
    value: String,
    label: String,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .heightIn(min = Sizing.avatarLg)
            .background(colors.onPrimary.copy(alpha = 0.10f), RoundedCornerShape(Radius.sm))
            .border(Sizing.hairline, colors.onPrimary.copy(alpha = 0.18f), RoundedCornerShape(Radius.sm))
            .padding(horizontal = Spacing.xs, vertical = Spacing.sm),
    ) {
        Text(
            text = value,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.onPrimary,
            maxLines = 1,
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = colors.onPrimary.copy(alpha = 0.76f),
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun ParentPlannerRoutineCard(slots: List<ParentRoutineSlot>) {
    EduCard {
        if (slots.isEmpty()) {
            Text(
                text = stringResource(R.string.pr07_no_routine),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
            )
            return@EduCard
        }
        slots.forEachIndexed { index, slot ->
            ParentPlannerRoutineRow(slot = slot)
            if (index != slots.lastIndex) {
                EduDivider()
            }
        }
    }
}

@Composable
private fun ParentPlannerRoutineRow(slot: ParentRoutineSlot) {
    val title = listOfNotNull(
        slot.subject?.takeIf { it.isNotBlank() },
        slot.title.takeIf { it.isNotBlank() },
    ).joinToString(" · ").ifBlank { slot.timeLabel }
    val status = localizedRoutineStatus(slot)
    val details = listOfNotNull(
        slot.timeLabel.takeIf { it.isNotBlank() },
        slot.durationMinutes?.takeIf { it > 0 }?.let { stringResource(R.string.pr08_minutes_value, numeral(it)) },
    ).joinToString(" · ")
    val description = stringResource(
        R.string.pr07_session_row_a11y,
        title,
        details,
        status,
    )
    ListRow(
        title = title,
        supporting = details,
        leading = parentPlannerStatusIcon(slot.status),
        leadingTint = parentPlannerStatusColor(slot.status),
        trailingContent = {
            StatusPill(
                label = status,
                contentColor = parentPlannerStatusColor(slot.status),
                containerColor = parentPlannerStatusColor(slot.status).copy(alpha = 0.14f),
            )
        },
        modifier = Modifier.semantics { contentDescription = description },
    )
}

@Composable
private fun localizedRoutineStatus(slot: ParentRoutineSlot): String {
    val raw = slot.statusLabel.trim().lowercase()
    return if (raw.isBlank() || raw == "completed" || raw == "missed" || raw == "planned") {
        parentPlannerStatusLabel(slot.status)
    } else {
        slot.statusLabel
    }
}

@Composable
private fun ParentPlannerSessionsCard(sessions: List<ParentPlannerSession>) {
    EduCard {
        if (sessions.isEmpty()) {
            Text(
                text = stringResource(R.string.pr07_no_sessions),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
            )
        }
        sessions.forEachIndexed { index, session ->
            ParentPlannerSessionRow(session = session)
            if (index != sessions.lastIndex) {
                EduDivider()
            }
        }
    }
}

@Composable
private fun ParentPlannerSessionRow(session: ParentPlannerSession) {
    val title = listOfNotNull(
        session.subjectName.takeIf { it.isNotBlank() },
        session.taskName.takeIf { it.isNotBlank() },
    ).joinToString(" · ")
    val status = session.statusLabel.ifBlank { parentPlannerStatusLabel(session.status) }
    val description = stringResource(
        R.string.pr07_session_row_a11y,
        title,
        session.timeLabel,
        status,
    )
    ListRow(
        title = title,
        supporting = session.timeLabel,
        leading = parentPlannerStatusIcon(session.status),
        leadingTint = parentPlannerStatusColor(session.status),
        trailingContent = {
            StatusPill(
                label = status,
                contentColor = parentPlannerStatusColor(session.status),
                containerColor = parentPlannerStatusColor(session.status).copy(alpha = 0.14f),
            )
        },
        modifier = Modifier.semantics { contentDescription = description },
    )
}

@Composable
private fun ParentPlannerPatternCard(pattern: String) {
    val colors = EduTheme.colors
    EduCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentPlannerIconBadge(
                icon = Icons.Filled.Schedule,
                contentColor = colors.aiAccent,
                containerColor = colors.aiAccentContainer,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.pr07_pattern_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = pattern,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
    }
}

@Composable
private fun ParentPlannerIconBadge(
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
private fun parentPlannerStatusLabel(status: ParentPlannerSessionStatus): String = when (status) {
    ParentPlannerSessionStatus.Completed -> stringResource(R.string.pr07_status_completed)
    ParentPlannerSessionStatus.Planned -> stringResource(R.string.pr07_status_planned)
    ParentPlannerSessionStatus.Missed -> stringResource(R.string.pr07_status_missed)
}

@Composable
private fun parentPlannerStatusColor(status: ParentPlannerSessionStatus): Color {
    val colors = EduTheme.colors
    return when (status) {
        ParentPlannerSessionStatus.Completed -> colors.success
        ParentPlannerSessionStatus.Planned -> colors.primary
        ParentPlannerSessionStatus.Missed -> colors.warning
    }
}

private fun parentPlannerStatusIcon(status: ParentPlannerSessionStatus): ImageVector = when (status) {
    ParentPlannerSessionStatus.Completed -> Icons.Filled.Check
    ParentPlannerSessionStatus.Planned -> Icons.Filled.Schedule
    ParentPlannerSessionStatus.Missed -> Icons.Filled.WarningAmber
}

@Composable
private fun ParentPlannerSkeleton() {
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
