package com.rork.eduspark.ui.screens.teacher

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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.TeacherWorkItem
import com.rork.eduspark.data.model.TeacherWorkItemKind
import com.rork.eduspark.data.model.TeacherWorkItemUrgency
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import java.util.Calendar

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-02 · Teacher Home — operational attention, not a dashboard wall.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * RoleShell owns the chrome. This screen only composes Home content: greeting, one
 * dominant Action Now card from existing work-queue state, then compact Today rows.
 */
@Composable
fun TeacherDashboardScreen(
    onOpenCourses: () -> Unit,
    onOpenLessonProcessing: (courseId: String, lessonId: String) -> Unit,
    onOpenVoiceProfile: () -> Unit,
    onOpenQuizzes: () -> Unit,
    onOpenGrades: () -> Unit,
    onOpenAnalytics: () -> Unit,
    modifier: Modifier = Modifier,
    onOpenStudents: () -> Unit = {},
    onOpenMessages: () -> Unit = {},
    viewModel: TeacherDashboardViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.retry()
    }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherDashboardEvent.OpenLessonProcessing -> onOpenLessonProcessing(event.courseId, event.lessonId)
                TeacherDashboardEvent.OpenVoiceProfile -> onOpenVoiceProfile()
                TeacherDashboardEvent.OpenQuizzes -> onOpenQuizzes()
                TeacherDashboardEvent.OpenGrades -> onOpenGrades()
                TeacherDashboardEvent.OpenAnalytics -> onOpenAnalytics()
                TeacherDashboardEvent.OpenCourses -> onOpenCourses()
                TeacherDashboardEvent.OpenStudents -> onOpenStudents()
                TeacherDashboardEvent.OpenMessages -> onOpenMessages()
            }
        }
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { TeacherDashboardSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        TeacherHomeContent(
            data = data,
            onWorkItemTap = viewModel::onWorkItemTapped,
            onOpenCourses = viewModel::onCoursesTapped,
            onOpenStudents = viewModel::onStudentsTapped,
        )
    }

    if (state.showComingSoon) {
        TeacherComingSoonDialog(onDismiss = viewModel::dismissComingSoon)
    }
}

@Composable
private fun TeacherHomeContent(
    data: TeacherDashboardScreenData,
    onWorkItemTap: (TeacherWorkItem) -> Unit,
    onOpenCourses: () -> Unit,
    onOpenStudents: () -> Unit,
) {
    val colors = EduTheme.colors
    val workItems = data.summary.workItems
    val heroItem = workItems.firstOrNull { it.kind == TeacherWorkItemKind.SubmissionAwaitingReview }
        ?: workItems.firstOrNull()
    val todayItems = workItems.filter { it.id != heroItem?.id }.take(2)
    val hasUrgentWork = workItems.any { it.urgency == TeacherWorkItemUrgency.Urgent } ||
        workItems.isNotEmpty() ||
        data.summary.unreadMessagesCount > 0
    val inactiveTitle = when {
        data.inactiveStudentCount <= 0 -> ""
        data.inactiveStudentCount == 1 -> stringResource(R.string.tc02_inactive_one)
        else -> stringResource(R.string.tc02_inactive_many, numeral(data.inactiveStudentCount))
    }
    val todayRows = buildTodayRows(
        todayItems = todayItems,
        inactiveTitle = inactiveTitle,
        inactiveSubtitle = data.inactiveStudentContext,
        onWorkItemTap = onWorkItemTap,
        onOpenStudents = onOpenStudents,
    )

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Text(
                text = teacherHomeGreeting(data.teacherDisplayName),
                style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
            )
            Text(
                text = stringResource(if (hasUrgentWork) R.string.tc02_status_urgent else R.string.tc02_status_clear),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
            )
        }

        item {
            if (heroItem != null) {
                AttentionCard(item = heroItem, onAction = { onWorkItemTap(heroItem) })
            } else {
                ClearHomeCard(onCreateClass = onOpenCourses)
            }
        }

        if (todayRows.isNotEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.tc02_today_section),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xs),
                )
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(colors.surface, RoundedCornerShape(Radius.md))
                        .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.md))
                        .padding(Spacing.sm),
                ) {
                    todayRows.forEachIndexed { index, row ->
                        TodayRow(
                            title = row.title,
                            subtitle = row.subtitle,
                            urgent = row.urgent,
                            onClick = row.onClick,
                        )
                        if (index != todayRows.lastIndex) {
                            Spacer(modifier = Modifier.height(Spacing.sm))
                        }
                    }
                }
            }
        }
    }
}

private data class TodayRowData(
    val title: String,
    val subtitle: String,
    val urgent: Boolean,
    val onClick: () -> Unit,
)

private fun buildTodayRows(
    todayItems: List<TeacherWorkItem>,
    inactiveTitle: String,
    inactiveSubtitle: String,
    onWorkItemTap: (TeacherWorkItem) -> Unit,
    onOpenStudents: () -> Unit,
): List<TodayRowData> {
    val rows = mutableListOf<TodayRowData>()
    todayItems.forEach { item ->
        rows += TodayRowData(
            title = item.title,
            subtitle = item.contextLabel,
            urgent = item.urgency == TeacherWorkItemUrgency.Urgent,
            onClick = { onWorkItemTap(item) },
        )
    }
    if (inactiveTitle.isNotBlank()) {
        rows += TodayRowData(
            title = inactiveTitle,
            subtitle = inactiveSubtitle,
            urgent = false,
            onClick = onOpenStudents,
        )
    }
    return rows.take(3)
}

@Composable
private fun AttentionCard(item: TeacherWorkItem, onAction: () -> Unit) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.linearGradient(listOf(Color(0xFF6366F1), Color(0xFF4F46E5))),
                RoundedCornerShape(Radius.lg),
            )
            .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.tc02_now_label),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                    color = Color.White.copy(alpha = 0.85f),
                )
                Text(
                    text = item.title,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    color = Color.White,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Text(
                    text = item.contextLabel,
                    style = EduTheme.typography.caption,
                    color = Color.White.copy(alpha = 0.88f),
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .border(2.dp, Color(0xFFC7D2FE), CircleShape),
            ) {
                Icon(
                    imageVector = Icons.Filled.Check,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(Sizing.icon),
                )
            }
        }
        Button(
            onClick = onAction,
            shape = RoundedCornerShape(Radius.sm),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color.White,
                contentColor = colors.primary,
            ),
            contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xs),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs)
                .height(Sizing.touchTarget),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = attentionActionLabel(item.kind),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                )
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                    contentDescription = null,
                )
            }
        }
    }
}

@Composable
private fun attentionActionLabel(kind: TeacherWorkItemKind): String = when (kind) {
    TeacherWorkItemKind.SubmissionAwaitingReview -> stringResource(R.string.tc02_correct_now)
    TeacherWorkItemKind.LessonProcessingFailed -> stringResource(R.string.tc02_reprocess)
    TeacherWorkItemKind.UnreadMessage -> stringResource(R.string.tc02_open_messages)
    TeacherWorkItemKind.DraftLesson -> stringResource(R.string.tc02_open_class)
}

@Composable
private fun ClearHomeCard(onCreateClass: () -> Unit) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.linearGradient(listOf(Color(0xFF6366F1), Color(0xFF4F46E5))),
                RoundedCornerShape(Radius.lg),
            )
            .padding(Spacing.sm),
    ) {
        Text(
            text = stringResource(R.string.tc02_now_label),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
            color = Color.White.copy(alpha = 0.9f),
        )
        Text(
            text = stringResource(R.string.tc02_all_clear_title),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
            color = Color.White,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Text(
            text = stringResource(R.string.tc02_all_clear_body),
            style = EduTheme.typography.caption,
            color = Color.White.copy(alpha = 0.9f),
            modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
        )
        Button(
            onClick = onCreateClass,
            shape = RoundedCornerShape(Radius.sm),
            colors = ButtonDefaults.buttonColors(containerColor = Color.White, contentColor = colors.primary),
            modifier = Modifier.fillMaxWidth().height(Sizing.touchTarget),
        ) {
            Text(stringResource(R.string.tc02_create_class), style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold))
        }
    }
}

@Composable
private fun TodayRow(
    title: String,
    subtitle: String,
    urgent: Boolean,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .eduClickable(onClick = onClick)
            .padding(vertical = Spacing.xxs),
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .background(if (urgent) colors.warning else colors.primary, CircleShape),
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
            if (subtitle.isNotBlank()) {
                Text(subtitle, style = EduTheme.typography.caption, color = colors.textTertiary)
            }
        }
    }
}

@Composable
private fun teacherHomeGreeting(displayName: String): String {
    val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
    val name = teacherGreetingName(displayName)
    return stringResource(
        if (hour < 17) R.string.tc02_greeting_morning else R.string.tc02_greeting_evening,
        name,
    )
}

private fun teacherGreetingName(displayName: String): String {
    val cleaned = displayName
        .removePrefix("أ. ")
        .removePrefix("أ.")
        .removePrefix("الأستاذة ")
        .removePrefix("الأستاذ ")
        .trim()
    return cleaned.split(Regex("\\s+")).firstOrNull().orEmpty().ifBlank { displayName }
}

@Composable
private fun TeacherDashboardSkeleton() {
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
