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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.School
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
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
import com.rork.eduspark.data.model.ParentSubjectTeacher
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.SearchField
import com.rork.eduspark.ui.components.nav.SheetHandle
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ParentSubjectsTeachersScreen(
    onBack: () -> Unit,
    onOpenLinkStudent: () -> Unit,
    onOpenThread: (threadId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentSubjectsTeachersViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    androidx.compose.runtime.LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is ParentSubjectsTeachersEvent.OpenThread -> onOpenThread(event.threadId)
            }
        }
    }

    EduScaffold(
        title = stringResource(R.string.pr10_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentSubjectsTeachersSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentSubjectsTeachersContent(
                data = data,
                onSelectStudent = viewModel::selectStudent,
                onQueryChange = viewModel::updateQuery,
                onOpenLinkStudent = onOpenLinkStudent,
                onOpenTeacherMessage = viewModel::openTeacherMessage,
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ParentSubjectsTeachersContent(
    data: ParentSubjectsTeachersData,
    onSelectStudent: (String) -> Unit,
    onQueryChange: (String) -> Unit,
    onOpenLinkStudent: () -> Unit,
    onOpenTeacherMessage: (ParentSubjectTeacher) -> Unit,
) {
    if (data.linkedStudents.isEmpty()) {
        ParentSubjectsTeachersEmptyState(onOpenLinkStudent = onOpenLinkStudent)
        return
    }

    val selectedStudent = data.linkedStudents.firstOrNull { it.id == data.selectedStudentId }
        ?: data.linkedStudents.first()
    var selectedTeacherId by rememberSaveable { mutableStateOf<String?>(null) }
    val snapshot = data.snapshot
    val filteredItems = snapshot?.items.orEmpty().filterSubjectsTeachers(data.query)
    val selectedTeacher = snapshot?.items?.firstOrNull { it.id == selectedTeacherId }

    if (selectedTeacher != null) {
        ParentTeacherProfileSheet(
            item = selectedTeacher,
            onDismiss = { selectedTeacherId = null },
        )
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            ParentSubjectsTeachersStudentCard(
                students = data.linkedStudents,
                selectedStudent = selectedStudent,
                onSelectStudent = onSelectStudent,
            )
        }
        item {
            SearchField(
                value = data.query,
                onValueChange = onQueryChange,
                placeholder = stringResource(R.string.pr10_search_hint),
            )
        }

        if (snapshot == null) {
            item { SkeletonCard() }
            item { SkeletonListItem() }
        } else {
            item { SectionHeader(title = stringResource(R.string.pr10_subjects_section)) }
            if (filteredItems.isEmpty()) {
                item { ParentSubjectsTeachersNoResultsCard() }
            } else {
                items(filteredItems, key = { it.id }) { item ->
                    ParentSubjectTeacherCard(
                        item = item,
                        onOpenProfile = { selectedTeacherId = item.id },
                        onOpenMessage = { onOpenTeacherMessage(item) },
                    )
                }
            }
            item { Spacer(modifier = Modifier.height(Spacing.section)) }
        }
    }
}

@Composable
private fun ParentSubjectsTeachersEmptyState(onOpenLinkStudent: () -> Unit) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(borderColor = colors.primary.copy(alpha = 0.32f)) {
                ParentSubjectsTeachersIconBadge(
                    icon = Icons.Filled.Link,
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                )
                Text(
                    text = stringResource(R.string.pr10_empty_title),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.pr10_empty_body),
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
private fun ParentSubjectsTeachersStudentCard(
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
private fun ParentSubjectTeacherCard(
    item: ParentSubjectTeacher,
    onOpenProfile: () -> Unit,
    onOpenMessage: () -> Unit,
) {
    val colors = EduTheme.colors
    val subject = item.subjectName.ifBlank { item.courseTitle }
    val teacherName = item.teacherName
    val status = parentSubjectTeacherStatusLabel(item)
    val description = stringResource(
        R.string.pr10_subject_row_a11y,
        subject,
        teacherName,
        numeral(item.progressPercent),
    )

    EduCard(modifier = Modifier.semantics { contentDescription = description }) {
        ListRow(
            title = subject,
            supporting = teacherName,
            leading = Icons.Filled.School,
            leadingTint = colors.primary,
            trailingContent = {
                StatusPill(
                    label = status,
                    contentColor = parentSubjectTeacherStatusColor(item.isOnTrack),
                    containerColor = parentSubjectTeacherStatusColor(item.isOnTrack).copy(alpha = 0.14f),
                )
            },
        )
        EduLinearProgress(
            progress = item.progressPercent / 100f,
            contentDescription = description,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Text(
            text = stringResource(
                R.string.pr05_summary_value,
                numeral(item.completedLessonCount),
                numeral(item.lessonCount),
            ),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        ) {
            SecondaryButton(
                text = stringResource(R.string.pr10_profile_action),
                onClick = onOpenProfile,
                modifier = Modifier.weight(1f),
                leadingIcon = Icons.Filled.Person,
            )
            PrimaryButton(
                text = stringResource(R.string.pr10_message_action),
                onClick = onOpenMessage,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ParentSubjectsTeachersNoResultsCard() {
    EduCard {
        Text(
            text = stringResource(R.string.pr10_no_results_title),
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.pr10_no_results_body),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ParentTeacherProfileSheet(
    item: ParentSubjectTeacher,
    onDismiss: () -> Unit,
) {
    val colors = EduTheme.colors
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = colors.surface,
        sheetState = rememberModalBottomSheetState(),
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
        ) {
            SheetHandle(modifier = Modifier.padding(bottom = Spacing.md))
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(
                    text = item.teacherInitial,
                    style = EduTheme.typography.display,
                    color = colors.primary,
                )
            }
            Text(
                text = item.teacherName,
                style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = item.courseTitle,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
            EduCard(
                containerColor = colors.neutralAlpha100,
                borderColor = colors.neutralAlpha100,
                modifier = Modifier.padding(top = Spacing.md),
            ) {
                ListRow(
                    title = stringResource(R.string.pr10_sheet_subject),
                    supporting = item.subjectName.ifBlank { item.courseTitle },
                    leading = Icons.Filled.School,
                    leadingTint = colors.primary,
                )
                ListRow(
                    title = stringResource(R.string.pr10_sheet_lessons),
                    supporting = stringResource(
                        R.string.pr05_summary_value,
                        numeral(item.completedLessonCount),
                        numeral(item.lessonCount),
                    ),
                    leading = Icons.Filled.Person,
                    leadingTint = colors.aiAccent,
                )
                ListRow(
                    title = stringResource(R.string.pr10_sheet_status),
                    supporting = parentSubjectTeacherStatusLabel(item),
                    leading = Icons.Filled.Person,
                    leadingTint = colors.success,
                )
            }
            Text(
                text = stringResource(R.string.pr10_sheet_read_only_note),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.sm),
            )
        }
    }
}

@Composable
private fun ParentSubjectsTeachersIconBadge(
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
private fun parentSubjectTeacherStatusLabel(item: ParentSubjectTeacher): String = item.statusLabel.ifBlank {
    stringResource(
        if (item.isOnTrack) R.string.pr10_status_on_track else R.string.pr10_status_needs_follow_up,
    )
}

@Composable
private fun parentSubjectTeacherStatusColor(isOnTrack: Boolean): Color {
    val colors = EduTheme.colors
    return if (isOnTrack) colors.success else colors.warning
}

private fun List<ParentSubjectTeacher>.filterSubjectsTeachers(query: String): List<ParentSubjectTeacher> {
    val normalized = query.trim()
    if (normalized.isBlank()) return this
    return filter { item ->
        listOf(
            item.subjectName,
            item.courseTitle,
            item.teacherName,
        ).any { it.contains(normalized, ignoreCase = true) }
    }
}

@Composable
private fun ParentSubjectsTeachersSkeleton() {
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
