package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.GradePublicationStatus
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-14 · Grades.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reached from a TC-02 Dashboard link — the Teacher tab bar has no Grades slot, same reasoning
 * TC-09/TC-10/TC-15 already document. A per-course gradebook listing the SAME canonical
 * students TC-12 already lists; each row's quiz component is read fresh from TC-11's own data
 * (see [TeacherGradebookViewModel]'s own doc comment), never re-entered by the teacher.
 */
@Composable
fun TeacherGradebookScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherGradebookViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.tc14_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherGradebookSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherGradebookContent(
                data = data,
                onSelectCourse = viewModel::selectCourse,
                onEditRow = viewModel::openEditor,
                onPublishOne = viewModel::publishOne,
                onRequestBulkPublish = viewModel::requestBulkPublish,
            )
        }
    }

    val editingStudentId = state.editingStudentId
    if (editingStudentId != null) {
        GradeEditorDialog(
            scoreDraft = state.scoreDraft,
            commentDraft = state.commentDraft,
            hasValidationError = state.hasValidationError,
            onScoreChange = viewModel::updateScoreDraft,
            onCommentChange = viewModel::updateCommentDraft,
            onSave = viewModel::saveEntry,
            onDismiss = viewModel::dismissEditor,
        )
    }

    if (state.showBulkPublishConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.tc14_bulk_publish_title),
            body = stringResource(R.string.tc14_bulk_publish_body),
            confirmLabel = stringResource(R.string.tc14_publish),
            onConfirm = viewModel::confirmBulkPublish,
            onDismiss = viewModel::dismissBulkPublishConfirm,
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TeacherGradebookContent(
    data: TeacherGradebookScreenData,
    onSelectCourse: (String) -> Unit,
    onEditRow: (TeacherGradeRow) -> Unit,
    onPublishOne: (String) -> Unit,
    onRequestBulkPublish: () -> Unit,
) {
    val colors = EduTheme.colors
    val hasDrafts = data.rows.any { it.entry.publicationStatus == GradePublicationStatus.Draft && it.entry.courseworkScore != null }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.sm),
            ) {
                data.courses.forEach { course ->
                    EduChip(label = course.title, selected = course.id == data.selectedCourseId, onClick = { onSelectCourse(course.id) })
                }
            }
        }

        if (hasDrafts) {
            item {
                SecondaryButton(
                    text = stringResource(R.string.tc14_bulk_publish),
                    onClick = onRequestBulkPublish,
                    modifier = Modifier.fillMaxWidth().padding(bottom = Spacing.sm),
                )
            }
        }

        if (data.rows.isEmpty()) {
            item {
                Text(stringResource(R.string.tc14_empty), style = EduTheme.typography.caption, color = colors.textMuted)
            }
        } else {
            items(data.rows, key = { it.student.studentId }) { row ->
                GradeRowCard(row = row, onEdit = { onEditRow(row) }, onPublish = { onPublishOne(row.student.studentId) })
            }
        }
    }
}

@Composable
private fun GradeRowCard(row: TeacherGradeRow, onEdit: () -> Unit, onPublish: () -> Unit) {
    val colors = EduTheme.colors
    val statusColor = if (row.entry.publicationStatus == GradePublicationStatus.Published) colors.success else colors.textMuted

    EduCard(onClick = onEdit, modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Text(row.student.displayName, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary, modifier = Modifier.weight(1f))
            StatusPill(label = gradePublicationStatusLabel(row.entry.publicationStatus), contentColor = statusColor, containerColor = statusColor.copy(alpha = 0.14f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.section), modifier = Modifier.padding(top = Spacing.sm)) {
            GradeComponentStat(labelRes = R.string.tc14_coursework, value = row.entry.courseworkScore)
            GradeComponentStat(labelRes = R.string.tc14_quiz_component, value = row.quizComponentPercent)
            GradeComponentStat(labelRes = R.string.tc14_overall, value = row.overallPercent, emphasized = true)
        }
        if (row.entry.comment.isNotBlank()) {
            Text(row.entry.comment, style = EduTheme.typography.caption, color = colors.textMuted, modifier = Modifier.padding(top = Spacing.sm))
        }
        if (row.entry.publicationStatus == GradePublicationStatus.Draft && row.entry.courseworkScore != null) {
            GhostButton(text = stringResource(R.string.tc14_publish), onClick = onPublish, modifier = Modifier.padding(top = Spacing.xs))
        }
    }
}

@Composable
private fun GradeComponentStat(labelRes: Int, value: Int?, emphasized: Boolean = false) {
    val colors = EduTheme.colors
    Column {
        Text(
            text = if (value != null) stringResource(R.string.progress_percent, value) else stringResource(R.string.tc14_no_value),
            style = if (emphasized) EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold) else EduTheme.typography.body,
            color = if (value != null) colors.textPrimary else colors.textMuted,
        )
        Text(stringResource(labelRes), style = EduTheme.typography.caption, color = colors.textMuted)
    }
}

@Composable
private fun GradeEditorDialog(
    scoreDraft: String,
    commentDraft: String,
    hasValidationError: Boolean,
    onScoreChange: (String) -> Unit,
    onCommentChange: (String) -> Unit,
    onSave: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.tc14_editor_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = {
            Column {
                EduTextField(
                    value = scoreDraft, onValueChange = onScoreChange, label = stringResource(R.string.tc14_coursework),
                    keyboardType = KeyboardType.Number,
                    errorText = if (hasValidationError) stringResource(R.string.tc14_score_range_error) else null,
                )
                EduTextField(
                    value = commentDraft, onValueChange = onCommentChange, label = stringResource(R.string.tc14_comment_label),
                    singleLine = false, modifier = Modifier.padding(top = Spacing.sm),
                )
            }
        },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_save), onClick = onSave) },
        dismissButton = { GhostButton(text = stringResource(R.string.common_cancel), onClick = onDismiss) },
        containerColor = colors.surface, titleContentColor = colors.textPrimary, textContentColor = colors.textMuted,
    )
}

@Composable
private fun TeacherGradebookSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize().padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
