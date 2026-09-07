package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.StudentMonitoringStatus
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-13 · Student Profile — PDF page 13.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Header/status/flags reuse [TeacherStudentSummary]. Quiz percent is the first completed
 * published-quiz score already computed by [TeacherStudentProfileViewModel] — never a
 * fabricated number. Private-note CRUD and the student-message mock stay on the ViewModel.
 */
@Composable
fun TeacherStudentProfileScreen(
    studentId: String,
    onBack: () -> Unit,
    onOpenParentNote: (studentId: String) -> Unit,
    onOpenParentChat: (threadId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherStudentProfileViewModel = koinViewModel(parameters = { parametersOf(studentId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val studentName = (state.result as? UiState.Content)?.data?.student?.displayName
        ?: stringResource(R.string.tc13_title)

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherStudentProfileEvent.OpenParentChat -> onOpenParentChat(event.threadId)
            }
        }
    }

    if (state.showNoParentThread) {
        ConfirmDialog(
            title = stringResource(R.string.tc13_no_parent_thread_title),
            body = stringResource(R.string.tc13_no_parent_thread_body),
            confirmLabel = stringResource(R.string.common_close),
            onConfirm = viewModel::dismissNoParentThread,
            onDismiss = viewModel::dismissNoParentThread,
        )
    }

    EduScaffold(title = studentName, onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherStudentProfileSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherStudentProfileContent(
                data = data,
                onMessageParent = viewModel::onMessageParent,
                onAddNote = { onOpenParentNote(studentId) },
            )
        }
    }
}

@Composable
private fun TeacherStudentProfileContent(
    data: TeacherStudentProfileScreenData,
    onMessageParent: () -> Unit,
    onAddNote: () -> Unit,
) {
    val colors = EduTheme.colors
    val student = data.student
    val quizScore = data.quizHistory.firstOrNull { it.scorePercent != null }?.scorePercent
    val attention = studentAttention(student)

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(Sizing.avatarLg)
                            .background(colors.primaryContainer, CircleShape),
                    ) {
                        Text(
                            text = student.displayName.trim().firstOrNull()?.toString().orEmpty(),
                            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.primary,
                        )
                    }
                    Text(
                        text = student.displayName,
                        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textPrimary,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                    Text(
                        text = stringResource(
                            R.string.tc12_row_meta,
                            teacherGradeShortLabel(student.grade),
                            teacherCourseSubjectLabel(student.courseTitle),
                        ),
                        style = EduTheme.typography.caption,
                        color = colors.textMuted,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                }
            }
        }

        item {
            if (attention != null) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = Spacing.sm)
                        .background(
                            Brush.linearGradient(listOf(colors.primary, colors.primary.copy(alpha = 0.88f))),
                            RoundedCornerShape(Radius.lg),
                        )
                        .padding(Spacing.card),
                ) {
                    StatusPill(
                        label = attention.pill,
                        contentColor = colors.onPrimary,
                        containerColor = colors.onPrimary.copy(alpha = 0.18f),
                    )
                    Text(
                        text = attention.body,
                        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.onPrimary,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                }
            } else {
                EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
                    Text(
                        text = stringResource(R.string.tc13_no_attention),
                        style = EduTheme.typography.body,
                        color = colors.textMuted,
                    )
                }
            }
        }

        item {
            EduCard(modifier = Modifier.padding(bottom = Spacing.xs)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.tc13_progress), style = EduTheme.typography.body, color = colors.textMuted)
                    Text(
                        text = stringResource(R.string.progress_percent, (student.progressPercent * 100).toInt()),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textPrimary,
                    )
                }
                EduLinearProgress(
                    progress = student.progressPercent.coerceIn(0f, 1f),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
            }
        }

        item {
            EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.tc13_quiz), style = EduTheme.typography.body, color = colors.textMuted)
                    Text(
                        text = if (quizScore != null) {
                            stringResource(R.string.progress_percent, quizScore)
                        } else {
                            stringResource(R.string.tc13_quiz_none)
                        },
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textPrimary,
                    )
                }
            }
        }

        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            ) {
                PrimaryButton(
                    text = stringResource(R.string.tc13_message_parent),
                    onClick = onMessageParent,
                    modifier = Modifier.weight(1f),
                )
                SecondaryButton(
                    text = stringResource(R.string.tc13_add_parent_note),
                    onClick = onAddNote,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

private data class StudentAttention(val pill: String, val body: String)

@Composable
private fun studentAttention(student: TeacherStudentSummary): StudentAttention? {
    val flags = student.flags.toList()
    if (flags.isEmpty() && student.status == StudentMonitoringStatus.Active) return null
    val count = flags.size.coerceAtLeast(1)
    val pill = if (count == 1) {
        stringResource(R.string.tc13_attention_one)
    } else {
        stringResource(R.string.tc13_attention_count, numeral(count))
    }
    val body = when {
        flags.isNotEmpty() -> studentFlagLabel(flags.first())
        student.status == StudentMonitoringStatus.Inactive -> studentMonitoringStatusLabel(student.status)
        else -> studentMonitoringStatusLabel(StudentMonitoringStatus.NeedsAttention)
    }
    return StudentAttention(pill = pill, body = body)
}

@Composable
private fun TeacherStudentProfileSkeleton() {
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
