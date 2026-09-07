package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherQuizStatus
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-10 · Quizzes — PDF page 14.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Lives inside Batch 1 [com.rork.eduspark.ui.navigation.RoleShell] when [onBack] is null.
 * Pending-essay attention uses the real [TeacherQuizAttempt.pendingEssayCount] from the mock repository.
 */
@Composable
fun TeacherQuizListScreen(
    onOpenEditor: (quizId: String) -> Unit,
    onOpenResults: (quizId: String) -> Unit,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    viewModel: TeacherQuizListViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.retry()
    }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherQuizListEvent.OpenEditor -> onOpenEditor(event.quizId)
            }
        }
    }

    val listBody: @Composable () -> Unit = {
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherQuizListSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { rows ->
            TeacherQuizListContent(
                rows = rows,
                statusFilter = state.statusFilter,
                courses = state.courses,
                showCoursePicker = state.showCoursePicker,
                isCreating = state.isCreating,
                pendingEssayCount = state.pendingEssayCount,
                pendingQuizId = state.pendingQuizId,
                onSelectFilter = viewModel::selectStatusFilter,
                onPickCourse = viewModel::pickCourse,
                onAddTapped = viewModel::onAddTapped,
                onOpenEditor = onOpenEditor,
                onOpenResults = onOpenResults,
            )
        }
    }

    if (onBack != null) {
        EduScaffold(
            title = stringResource(R.string.tc10_title),
            onBack = onBack,
            modifier = modifier,
        ) { _ ->
            listBody()
        }
    } else {
        Column(modifier = modifier.fillMaxSize()) {
            listBody()
        }
    }
}

@Composable
private fun TeacherQuizListContent(
    rows: List<TeacherQuizRow>,
    statusFilter: TeacherQuizStatus?,
    courses: List<TeacherCourseSummary>,
    showCoursePicker: Boolean,
    isCreating: Boolean,
    pendingEssayCount: Int,
    pendingQuizId: String?,
    onSelectFilter: (TeacherQuizStatus?) -> Unit,
    onPickCourse: (String) -> Unit,
    onAddTapped: () -> Unit,
    onOpenEditor: (String) -> Unit,
    onOpenResults: (String) -> Unit,
) {
    val filtered = rows.filter { row -> statusFilter == null || row.quiz.status == statusFilter }
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        if (pendingEssayCount > 0 && pendingQuizId != null) {
            item {
                EduCard(
                    onClick = { onOpenResults(pendingQuizId) },
                    borderColor = colors.danger,
                    modifier = Modifier.padding(bottom = Spacing.sm),
                ) {
                    Text(
                        text = stringResource(R.string.tc10_attention_title),
                        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                        color = colors.danger,
                    )
                    Text(
                        text = stringResource(R.string.tc10_attention_body, numeral(pendingEssayCount)),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textPrimary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                }
            }
        }

        item {
            QuizStatusFilterRow(
                selectedStatus = statusFilter,
                onSelectStatus = onSelectFilter,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
        }

        if (filtered.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Quiz,
                    title = stringResource(if (rows.isEmpty()) R.string.tc10_empty_title else R.string.tc10_empty_filter),
                    body = stringResource(R.string.tc10_empty_body),
                )
            }
        } else {
            items(filtered, key = { it.quiz.id }) { row ->
                val published = row.quiz.status == TeacherQuizStatus.Published
                QuizRow(
                    row = row,
                    course = courses.firstOrNull { it.id == row.quiz.courseId },
                    onClick = {
                        if (published) onOpenResults(row.quiz.id) else onOpenEditor(row.quiz.id)
                    },
                )
            }
        }

        if (showCoursePicker && courses.isNotEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.tc10_pick_course),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xs),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
                    courses.forEach { course ->
                        QuizFilterChip(
                            label = teacherCourseSubjectLabel(course.title),
                            selected = false,
                            onClick = { onPickCourse(course.id) },
                        )
                    }
                }
            }
        }

        item {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md, bottom = Spacing.section),
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(52.dp)
                        .background(EduTheme.colors.primary, CircleShape)
                        .eduClickable(
                            enabled = !isCreating && courses.isNotEmpty(),
                            role = Role.Button,
                            onClick = onAddTapped,
                        ),
                ) {
                    Text(
                        text = "+",
                        style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                        color = EduTheme.colors.onPrimary,
                    )
                }
            }
        }
    }
}

@Composable
private fun QuizStatusFilterRow(
    selectedStatus: TeacherQuizStatus?,
    onSelectStatus: (TeacherQuizStatus?) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = modifier.fillMaxWidth(),
    ) {
        QuizFilterChip(
            label = stringResource(R.string.tc03_filter_all),
            selected = selectedStatus == null,
            onClick = { onSelectStatus(null) },
        )
        QuizFilterChip(
            label = stringResource(R.string.tc03_filter_published),
            selected = selectedStatus == TeacherQuizStatus.Published,
            onClick = { onSelectStatus(TeacherQuizStatus.Published) },
        )
        QuizFilterChip(
            label = stringResource(R.string.tc03_filter_draft),
            selected = selectedStatus == TeacherQuizStatus.Draft,
            onClick = { onSelectStatus(TeacherQuizStatus.Draft) },
        )
    }
}

@Composable
private fun QuizFilterChip(
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
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
    )
}

@Composable
private fun QuizRow(
    row: TeacherQuizRow,
    course: TeacherCourseSummary?,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val quiz = row.quiz
    val published = quiz.status == TeacherQuizStatus.Published
    val subject = teacherCourseSubjectLabel(quiz.courseTitle)
    val grade = course?.let { teacherGradeShortLabel(it.grade) }
    val meta = when {
        row.averagePercent != null -> stringResource(
            R.string.tc12_row_meta,
            subject,
            stringResource(R.string.tc10_average_meta, stringResource(R.string.progress_percent, row.averagePercent)),
        )
        row.attemptsCount > 0 && grade != null -> listOf(
            subject,
            grade,
            stringResource(R.string.tc10_attempts_count, numeral(row.attemptsCount)),
        ).joinToString(" · ")
        grade != null -> stringResource(R.string.tc12_row_meta, subject, grade)
        else -> subject
    }

    EduCard(onClick = onClick, modifier = Modifier.padding(bottom = Spacing.xs)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = quiz.title.ifBlank { stringResource(R.string.tc10_untitled_quiz) },
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
            StatusPill(
                label = if (row.pendingEssayCount > 0) {
                    stringResource(R.string.tc10_pending_pill, numeral(row.pendingEssayCount))
                } else {
                    teacherQuizStatusLabel(quiz.status)
                },
                contentColor = when {
                    row.pendingEssayCount > 0 -> colors.danger
                    published -> colors.success
                    else -> colors.warning
                },
                containerColor = when {
                    row.pendingEssayCount > 0 -> colors.danger.copy(alpha = 0.14f)
                    published -> colors.success.copy(alpha = 0.14f)
                    else -> colors.warning.copy(alpha = 0.14f)
                },
            )
        }
        Text(
            text = meta,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun TeacherQuizListSkeleton() {
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
