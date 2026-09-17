package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ChildCare
import androidx.compose.material.icons.filled.EventAvailable
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ParentActivity
import com.rork.eduspark.data.model.ParentCourseProgress
import com.rork.eduspark.data.model.ParentDashboard
import com.rork.eduspark.data.model.ParentInsight
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentNote
import com.rork.eduspark.data.model.ParentNoteReply
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun ParentDashboardScreen(
    modifier: Modifier = Modifier,
    viewModel: ParentDashboardViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { ParentDashboardSkeleton() },
        empty = { ParentEmptyState(state.parent?.displayName.orEmpty()) },
        modifier = modifier.fillMaxSize(),
    ) { dashboard ->
        ParentDashboardContent(
            parentName = state.parent?.displayName.orEmpty(),
            students = state.students,
            selectedStudentId = state.selectedStudentId,
            dashboard = dashboard,
            notes = state.notes,
            notesUnreadCount = state.notesUnreadCount,
            replyDrafts = state.replyDrafts,
            acknowledgingNoteId = state.acknowledgingNoteId,
            replyingNoteId = state.replyingNoteId,
            onSelectStudent = viewModel::selectStudent,
            onAcknowledgeNote = viewModel::acknowledgeNote,
            onMarkNoteRead = viewModel::markNoteRead,
            onUpdateReplyDraft = viewModel::updateReplyDraft,
            onReplyToNote = viewModel::replyToNote,
        )
    }
}

@Composable
private fun ParentDashboardContent(
    parentName: String,
    students: List<ParentLinkedStudent>,
    selectedStudentId: String?,
    dashboard: ParentDashboard,
    notes: List<ParentNote>,
    notesUnreadCount: Int,
    replyDrafts: Map<String, String>,
    acknowledgingNoteId: String?,
    replyingNoteId: String?,
    onSelectStudent: (String) -> Unit,
    onAcknowledgeNote: (String) -> Unit,
    onMarkNoteRead: (String) -> Unit,
    onUpdateReplyDraft: (String, String) -> Unit,
    onReplyToNote: (String) -> Unit,
) {
    LazyColumn(
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            ParentHero(parentName = parentName, child = dashboard.child)
        }
        if (students.size > 1) {
            item {
                ChildSelector(
                    students = students,
                    selectedStudentId = selectedStudentId,
                    onSelectStudent = onSelectStudent,
                )
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
                ParentMetricCard(
                    icon = Icons.Filled.EventAvailable,
                    label = stringResource(R.string.parent_metric_sessions),
                    value = numeral(dashboard.weeklySessions),
                    modifier = Modifier.weight(1f),
                )
                ParentMetricCard(
                    icon = Icons.Filled.Quiz,
                    label = stringResource(R.string.parent_metric_quizzes),
                    value = numeral(dashboard.weeklyQuizzes),
                    modifier = Modifier.weight(1f),
                )
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
                ParentMetricCard(
                    icon = Icons.Filled.CheckCircle,
                    label = stringResource(R.string.parent_metric_score),
                    value = "${numeral(dashboard.averageScore)}%",
                    modifier = Modifier.weight(1f),
                )
                ParentMetricCard(
                    icon = Icons.Filled.Insights,
                    label = stringResource(R.string.parent_metric_attendance),
                    value = "${numeral(dashboard.attendancePercentage)}%",
                    modifier = Modifier.weight(1f),
                )
            }
        }
        item {
            SectionTitle(stringResource(R.string.parent_courses_title))
        }
        if (dashboard.courseProgress.isEmpty()) {
            item {
                EduCard {
                    Text(
                        text = stringResource(R.string.parent_courses_empty),
                        style = EduTheme.typography.body,
                        color = EduTheme.colors.textSecondary,
                    )
                }
            }
        } else {
            items(dashboard.courseProgress, key = { it.courseId }) { course ->
                ParentCourseRow(course)
            }
        }
        item {
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                SectionTitle(stringResource(R.string.parent_notes_title), modifier = Modifier.weight(1f))
                if (notesUnreadCount > 0) {
                    Text(
                        text = stringResource(R.string.parent_notes_unread, numeral(notesUnreadCount)),
                        style = EduTheme.typography.caption,
                        color = EduTheme.colors.danger,
                    )
                }
            }
        }
        if (notes.isEmpty()) {
            item {
                EduCard {
                    Text(
                        text = stringResource(R.string.parent_notes_empty),
                        style = EduTheme.typography.body,
                        color = EduTheme.colors.textSecondary,
                    )
                }
            }
        } else {
            items(notes, key = { it.id }) { note ->
                ParentNoteCard(
                    note = note,
                    replyDraft = replyDrafts[note.id].orEmpty(),
                    isAcknowledging = acknowledgingNoteId == note.id,
                    isReplying = replyingNoteId == note.id,
                    onAcknowledge = { onAcknowledgeNote(note.id) },
                    onMarkRead = { onMarkNoteRead(note.id) },
                    onDraftChange = { onUpdateReplyDraft(note.id, it) },
                    onReply = { onReplyToNote(note.id) },
                )
            }
        }
        item {
            SectionTitle(stringResource(R.string.parent_insights_title))
        }
        if (dashboard.insights.isEmpty()) {
            item {
                EduCard {
                    Text(
                        text = stringResource(R.string.parent_insights_empty),
                        style = EduTheme.typography.body,
                        color = EduTheme.colors.textSecondary,
                    )
                }
            }
        } else {
            items(dashboard.insights.take(3), key = { it.id }) { insight ->
                ParentInsightRow(insight)
            }
        }
        item {
            SectionTitle(stringResource(R.string.parent_activity_title))
        }
        if (dashboard.recentActivity.isEmpty()) {
            item {
                EduCard {
                    Text(
                        text = stringResource(R.string.parent_activity_empty),
                        style = EduTheme.typography.body,
                        color = EduTheme.colors.textSecondary,
                    )
                }
            }
        } else {
            items(dashboard.recentActivity.take(4), key = { it.id }) { activity ->
                ParentActivityRow(activity)
            }
        }
    }
}

@Composable
private fun ParentNoteCard(
    note: ParentNote,
    replyDraft: String,
    isAcknowledging: Boolean,
    isReplying: Boolean,
    onAcknowledge: () -> Unit,
    onMarkRead: () -> Unit,
    onDraftChange: (String) -> Unit,
    onReply: () -> Unit,
) {
    LaunchedEffect(note.id, note.isRead) {
        if (!note.isRead) onMarkRead()
    }
    EduCard {
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = note.title.ifBlank { note.description },
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textPrimary,
                )
                Text(
                    text = stringResource(
                        R.string.parent_notes_from_teacher,
                        note.teacherName.ifBlank { note.categoryLabel },
                        note.createdLabel,
                    ),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
            }
            if (!note.isRead) {
                Text(
                    text = stringResource(R.string.parent_notes_new_badge),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.danger,
                )
            }
        }
        if (note.description.isNotBlank() && note.title.isNotBlank()) {
            Text(
                text = note.description,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }
        Text(
            text = listOf(note.categoryLabel, note.statusLabel, note.priorityLabel)
                .filter { it.isNotBlank() }
                .joinToString(" · "),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        note.replies.forEach { reply ->
            ParentNoteReplyRow(reply = reply, modifier = Modifier.padding(top = Spacing.sm))
        }
        if (!note.isRead) {
            SecondaryButton(
                text = stringResource(R.string.parent_notes_acknowledge),
                onClick = onAcknowledge,
                isLoading = isAcknowledging,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            )
        }
        if (note.isClosed) {
            Text(
                text = stringResource(R.string.parent_notes_closed),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        } else if (note.canReply) {
            EduTextField(
                value = replyDraft,
                onValueChange = onDraftChange,
                label = "",
                placeholder = stringResource(R.string.parent_notes_reply_hint),
                labelPlacement = FieldLabelPlacement.Above,
                singleLine = false,
                imeAction = ImeAction.Default,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            PrimaryButton(
                text = stringResource(R.string.parent_notes_reply_send),
                onClick = onReply,
                enabled = replyDraft.isNotBlank(),
                isLoading = isReplying,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun ParentNoteReplyRow(reply: ParentNoteReply, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth()) {
        Text(
            text = stringResource(
                R.string.parent_notes_reply_by,
                reply.authorName.ifBlank { reply.authorRole },
                reply.createdLabel,
            ),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
        )
        Text(
            text = reply.body,
            style = EduTheme.typography.body,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentHero(parentName: String, child: ParentLinkedStudent) {
    EduCard {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Filled.ChildCare, contentDescription = null, tint = EduTheme.colors.primary)
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.parent_home_greeting, parentName.ifBlank { stringResource(R.string.parent_default_name) }),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
                Text(
                    text = child.name,
                    style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textPrimary,
                )
                Text(
                    text = listOf(child.gradeLabel, child.academicStatusLabel).filter { it.isNotBlank() }.joinToString(" · "),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
            }
        }
    }
}

@Composable
private fun ChildSelector(
    students: List<ParentLinkedStudent>,
    selectedStudentId: String?,
    onSelectStudent: (String) -> Unit,
) {
    EduCard {
        Text(
            text = stringResource(R.string.parent_child_selector),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            students.forEach { student ->
                AssistChip(
                    onClick = { onSelectStudent(student.id) },
                    label = { Text(student.name) },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = if (student.id == selectedStudentId) EduTheme.colors.primaryContainer else EduTheme.colors.surface,
                        labelColor = EduTheme.colors.textPrimary,
                    ),
                )
            }
        }
    }
}

@Composable
private fun ParentMetricCard(icon: ImageVector, label: String, value: String, modifier: Modifier = Modifier) {
    EduCard(modifier = modifier) {
        Icon(icon, contentDescription = null, tint = EduTheme.colors.primary)
        Text(
            text = value,
            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Text(text = label, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
    }
}

@Composable
private fun ParentCourseRow(course: ParentCourseProgress) {
    EduCard {
        Text(
            text = course.courseTitle,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = course.subjectName,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
        )
        LinearProgressIndicator(
            progress = { course.completionPercentage.coerceIn(0f, 1f) },
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
        Text(
            text = stringResource(R.string.parent_course_progress, numeral((course.completionPercentage * 100).toInt())),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ParentInsightRow(insight: ParentInsight) {
    EduCard {
        Text(
            text = insight.text,
            style = EduTheme.typography.body,
            color = EduTheme.colors.textPrimary,
        )
    }
}

@Composable
private fun ParentActivityRow(activity: ParentActivity) {
    EduCard {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Filled.MenuBook, contentDescription = null, tint = EduTheme.colors.primary)
            Column(modifier = Modifier.weight(1f)) {
                Text(activity.title, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                activity.description?.takeIf { it.isNotBlank() }?.let {
                    Text(it, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                }
                Text(activity.relativeTime, style = EduTheme.typography.caption, color = EduTheme.colors.textMuted)
            }
        }
    }
}

@Composable
private fun SectionTitle(title: String, modifier: Modifier = Modifier) {
    Text(
        text = title,
        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
        color = EduTheme.colors.textPrimary,
        modifier = modifier.padding(top = Spacing.xs),
    )
}

@Composable
private fun ParentEmptyState(parentName: String) {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm, Alignment.CenterVertically),
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxSize()
            .padding(Spacing.gutter),
    ) {
        Icon(Icons.Filled.ChildCare, contentDescription = null, tint = EduTheme.colors.primary)
        Text(
            text = stringResource(R.string.parent_empty_title),
            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.parent_empty_body, parentName.ifBlank { stringResource(R.string.parent_default_name) }),
            style = EduTheme.typography.body,
            color = EduTheme.colors.textSecondary,
        )
    }
}

@Composable
private fun ParentDashboardSkeleton() {
    LazyColumn(
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        items(5) { SkeletonCard() }
    }
}
