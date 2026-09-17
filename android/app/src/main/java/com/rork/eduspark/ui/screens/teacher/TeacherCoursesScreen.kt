package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.TeacherCourseFormSubject
import com.rork.eduspark.data.model.TeacherCourseStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-03 · Classes list — operational roster, not a course catalog.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * RoleShell owns the chrome. This screen only composes filter chips + class cards from
 * existing [TeacherCoursesViewModel] state. Status filters map 1:1 onto
 * [TeacherCourseStatus]; they never invent a second publish flag.
 */
@Composable
fun TeacherCoursesScreen(
    onOpenCourse: (courseId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherCoursesViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.retry()
    }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherCoursesEvent.OpenCourse -> onOpenCourse(event.courseId)
            }
        }
    }

    if (state.create.visible) {
        CreateClassDialog(
            form = state.create,
            onDismiss = viewModel::dismissCreateDialog,
            onTitleChange = viewModel::updateCreateTitle,
            onDescriptionChange = viewModel::updateCreateDescription,
            onGradeChange = viewModel::selectCreateGrade,
            onSubjectChange = viewModel::selectCreateSubject,
            onPublishedChange = viewModel::updateCreatePublished,
            onSubmit = viewModel::submitCreate,
        )
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { TeacherCoursesSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { courses ->
        TeacherCoursesContent(
            courses = courses,
            selectedStatus = state.filters.status,
            onSelectStatus = viewModel::selectStatus,
            onOpenCourse = onOpenCourse,
            onCreateClass = viewModel::openCreateDialog,
        )
    }
}

@Composable
private fun TeacherCoursesContent(
    courses: List<TeacherCourseSummary>,
    selectedStatus: TeacherCourseStatus?,
    onSelectStatus: (TeacherCourseStatus?) -> Unit,
    onOpenCourse: (courseId: String) -> Unit,
    onCreateClass: () -> Unit,
) {
    val filtered = courses.filter { course ->
        selectedStatus == null || course.status == selectedStatus
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            PrimaryButton(
                text = stringResource(R.string.tc02_create_class),
                onClick = onCreateClass,
                leadingIcon = Icons.Filled.Add,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.sm),
            )
        }
        item {
            ClassStatusFilterRow(
                selectedStatus = selectedStatus,
                onSelectStatus = onSelectStatus,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
        }

        if (filtered.isEmpty()) {
            item {
                val noneAtAll = courses.isEmpty()
                MessageState(
                    icon = Icons.Filled.MenuBook,
                    title = stringResource(R.string.tc03_empty_title),
                    body = stringResource(
                        if (noneAtAll) R.string.tc03_empty_create_body else R.string.tc03_empty_body,
                    ),
                    primaryActionLabel = stringResource(
                        if (noneAtAll) R.string.tc02_create_class else R.string.tc03_filter_all,
                    ),
                    onPrimaryAction = if (noneAtAll) onCreateClass else ({ onSelectStatus(null) }),
                )
            }
        } else {
            items(filtered, key = { it.id }) { course ->
                TeacherClassCard(course = course, onClick = { onOpenCourse(course.id) })
            }
        }
    }
}

@Composable
private fun CreateClassDialog(
    form: TeacherCourseCreateUiState,
    onDismiss: () -> Unit,
    onTitleChange: (String) -> Unit,
    onDescriptionChange: (String) -> Unit,
    onGradeChange: (Grade) -> Unit,
    onSubjectChange: (String) -> Unit,
    onPublishedChange: (Boolean) -> Unit,
    onSubmit: () -> Unit,
) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = { if (!form.isSubmitting) onDismiss() },
        title = {
            Text(
                text = stringResource(R.string.tc02_create_class),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .heightIn(max = 420.dp)
                    .verticalScroll(rememberScrollState()),
            ) {
                EduTextField(
                    value = form.title,
                    onValueChange = onTitleChange,
                    label = stringResource(R.string.tc03_course_title_label),
                    placeholder = stringResource(R.string.tc03_course_title_placeholder),
                    errorText = if (form.showValidationError && form.title.trim().length < 2) {
                        stringResource(R.string.tc03_course_title_required)
                    } else {
                        null
                    },
                    labelPlacement = FieldLabelPlacement.Above,
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
                Text(
                    text = stringResource(R.string.tc01_grades_section),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.textSecondary,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = Spacing.sm),
                ) {
                    Grade.entries.forEach { grade ->
                        ClassFilterChip(
                            label = teacherSetupChipGradeLabel(grade),
                            selected = form.grade == grade,
                            onClick = { onGradeChange(grade) },
                        )
                    }
                }
                Text(
                    text = stringResource(R.string.tc01_subjects_section),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.textSecondary,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )
                CreateSubjectChips(
                    subjects = form.subjects,
                    selectedId = form.subjectId,
                    loading = form.subjectsLoading,
                    showError = form.showValidationError && form.subjectId == null,
                    onSelect = onSubjectChange,
                )
                EduTextField(
                    value = form.description,
                    onValueChange = onDescriptionChange,
                    label = stringResource(R.string.tc03_course_description_label),
                    singleLine = false,
                    labelPlacement = FieldLabelPlacement.Above,
                    modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.sm),
                )
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        text = stringResource(R.string.tc03_publish_now),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                        color = colors.textPrimary,
                        modifier = Modifier.weight(1f),
                    )
                    Switch(
                        checked = form.published,
                        onCheckedChange = onPublishedChange,
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = colors.onPrimary,
                            checkedTrackColor = colors.primary,
                        ),
                    )
                }
                if (form.error != null) {
                    Text(
                        text = createCourseErrorText(form.error),
                        style = EduTheme.typography.caption,
                        color = colors.danger,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                }
            }
        },
        confirmButton = {
            PrimaryButton(
                text = stringResource(R.string.tc02_create_class),
                onClick = onSubmit,
                enabled = !form.subjectsLoading,
                isLoading = form.isSubmitting,
            )
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !form.isSubmitting) {
                Text(stringResource(R.string.common_cancel))
            }
        },
    )
}

@Composable
private fun CreateSubjectChips(
    subjects: List<TeacherCourseFormSubject>,
    selectedId: String?,
    loading: Boolean,
    showError: Boolean,
    onSelect: (String) -> Unit,
) {
    val colors = EduTheme.colors
    when {
        loading -> Text(
            text = stringResource(R.string.tc03_subjects_loading),
            style = EduTheme.typography.caption,
            color = colors.textTertiary,
        )
        subjects.isEmpty() -> Text(
            text = stringResource(R.string.tc03_subjects_empty),
            style = EduTheme.typography.caption,
            color = if (showError) colors.danger else colors.textTertiary,
        )
        else -> {
            Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                subjects.chunked(2).forEach { row ->
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        row.forEach { subject ->
                            ClassFilterChip(
                                label = subject.name,
                                selected = selectedId == subject.id,
                                onClick = { onSelect(subject.id) },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ClassStatusFilterRow(
    selectedStatus: TeacherCourseStatus?,
    onSelectStatus: (TeacherCourseStatus?) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier.fillMaxWidth(),
    ) {
        ClassFilterChip(
            label = stringResource(R.string.tc03_filter_all),
            selected = selectedStatus == null,
            onClick = { onSelectStatus(null) },
        )
        ClassFilterChip(
            label = stringResource(R.string.tc03_filter_published),
            selected = selectedStatus == TeacherCourseStatus.Published,
            onClick = { onSelectStatus(TeacherCourseStatus.Published) },
        )
        ClassFilterChip(
            label = stringResource(R.string.tc03_filter_draft),
            selected = selectedStatus == TeacherCourseStatus.Draft,
            onClick = { onSelectStatus(TeacherCourseStatus.Draft) },
        )
    }
}

@Composable
private fun ClassFilterChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.pill)
    Text(
        text = label,
        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
        color = if (selected) colors.primary else colors.textPrimary,
        modifier = Modifier
            .background(if (selected) colors.primaryContainer else colors.surface, shape)
            .border(Sizing.hairline, if (selected) colors.primary else colors.border, shape)
            .eduClickable(role = Role.RadioButton, onClick = onClick)
            .semantics { this.selected = selected }
            .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
    )
}

@Composable
private fun TeacherClassCard(course: TeacherCourseSummary, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    val published = course.status == TeacherCourseStatus.Published
    val (statusColor, statusContainer) = when (course.status) {
        TeacherCourseStatus.Published -> colors.success to colors.success.copy(alpha = 0.14f)
        TeacherCourseStatus.Draft -> colors.warning to colors.highlightContainer
        TeacherCourseStatus.Archived -> colors.textSecondary to colors.neutralAlpha100
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = Spacing.sm)
            .background(colors.surface, shape)
            .border(Sizing.hairline, colors.border, shape)
            .clip(shape)
            .eduClickable(onClick = onClick),
    ) {
        if (published) {
            TeacherClassSubjectVisual()
        }
        Column(modifier = Modifier.padding(horizontal = Spacing.sm, vertical = Spacing.sm)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = stringResource(
                        R.string.tc03_class_title,
                        course.subjectTitle,
                        teacherGradeLabel(course.grade),
                    ),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.weight(1f),
                )
                StatusPill(
                    label = classStatusBadgeLabel(course.status),
                    contentColor = statusColor,
                    containerColor = statusContainer,
                )
            }
            Text(
                text = classCardMeta(course),
                style = EduTheme.typography.caption,
                color = colors.textTertiary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun classStatusBadgeLabel(status: TeacherCourseStatus): String = when (status) {
    TeacherCourseStatus.Published -> stringResource(R.string.tc03_filter_published)
    TeacherCourseStatus.Draft -> stringResource(R.string.tc03_filter_draft)
    TeacherCourseStatus.Archived -> teacherCourseStatusLabel(status)
}

@Composable
private fun classCardMeta(course: TeacherCourseSummary): String {
    val students = stringResource(R.string.tc03_student_count, numeral(course.studentCount))
    val lessons = stringResource(R.string.tc03_lesson_count, numeral(course.lessonCount))
    return if (course.status == TeacherCourseStatus.Draft) {
        stringResource(R.string.tc03_class_meta, lessons, stringResource(R.string.tc03_needs_publish))
    } else {
        stringResource(R.string.tc03_class_meta, students, lessons)
    }
}

@Composable
private fun TeacherCoursesSkeleton() {
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

@Composable
private fun createCourseErrorText(error: AppError): String {
    val generic = stringResource(R.string.tc03_create_error)
    val detail = when (error) {
        is AppError.Domain -> error.code
        is AppError.Validation -> error.fieldErrors.entries.joinToString("\n") { "${it.key}: ${it.value}" }
        AppError.Network, AppError.Offline -> "network"
        AppError.Server -> "server"
        AppError.SessionExpired -> "session"
        AppError.Forbidden -> "forbidden"
        AppError.NotFound -> "not_found"
        AppError.Unknown -> "unexpected"
    }
    return if (detail.isBlank()) generic else "$generic\n$detail"
}
