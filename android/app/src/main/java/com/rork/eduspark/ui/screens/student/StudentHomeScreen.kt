package com.rork.eduspark.ui.screens.student

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.core.animateFloatAsState
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.EventNote
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.Achievement
import com.rork.eduspark.data.model.AchievementStatus
import com.rork.eduspark.data.model.ContinueLearningItem
import com.rork.eduspark.data.model.CourseCardState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.PlannerItem
import com.rork.eduspark.data.model.PlannerRecommendation
import com.rork.eduspark.data.model.RoutineSlot
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.data.model.StudentHomeSnapshot
import com.rork.eduspark.data.model.cardState
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduGroupedSurface
import com.rork.eduspark.ui.components.surface.SkeletonBlock
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.LocalReducedMotion
import com.rork.eduspark.ui.theme.Motion
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import com.rork.eduspark.ui.theme.standardSpec
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.filled.LocalFireDepartment
import androidx.compose.animation.core.tween
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StudentHomeScreen(
    onOpenCourse: (courseId: String) -> Unit,
    onOpenLesson: (lessonId: String) -> Unit,
    onOpenPlanner: () -> Unit,
    onOpenRoutine: () -> Unit,
    onOpenSubscriptions: () -> Unit,
    onOpenAchievements: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: StudentHomeViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { StudentHomeSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { snapshot ->
        PullToRefreshBox(
            isRefreshing = state.isRefreshing,
            onRefresh = viewModel::refresh,
            modifier = Modifier.fillMaxSize(),
        ) {
            val continueCourse = snapshot.continueItem?.courseId?.let { courseId ->
                state.courses.firstOrNull { it.courseId == courseId }
            }
            val todayItems = state.todayPlannerItems.ifEmpty { snapshot.todayPlan }
            val nextRoutineSlot = state.todayRoutineSlots.firstOrNull()

            LazyColumn(
                contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.xs),
                modifier = Modifier.fillMaxSize(),
            ) {
                item {
                    Text(
                        text = stringResource(R.string.st01_greeting, snapshot.studentName),
                        style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                        color = EduTheme.colors.textPrimary,
                    )
                    Text(
                        text = stringResource(R.string.st01_ready_to_continue),
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                        color = EduTheme.colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                    Spacer(modifier = Modifier.height(Spacing.xs))
                }

                item {
                    JourneyHero(
                        snapshot = snapshot,
                        continueCourse = continueCourse,
                        onOpenCourse = onOpenCourse,
                        onOpenLesson = onOpenLesson,
                        onOpenSubscriptions = onOpenSubscriptions,
                    )
                    Spacer(modifier = Modifier.height(Spacing.xs))
                }

                item {
                    TodayContextSection(
                        items = todayItems,
                        nextRoutineSlot = nextRoutineSlot,
                        onOpenPlanner = onOpenPlanner,
                        onOpenRoutine = onOpenRoutine,
                    )
                    Spacer(modifier = Modifier.height(Spacing.xs))
                }

                item {
                    val review = resolveDistinctHomeReview(
                        snapshot = snapshot,
                        courses = state.courses,
                        onOpenCourse = onOpenCourse,
                        onOpenSubscriptions = onOpenSubscriptions,
                    )
                    if (review != null) {
                        SmartRecommendationCard(target = review)
                        Spacer(modifier = Modifier.height(Spacing.xs))
                    }
                }

                item {
                    ProgressSnapshotSection(
                        snapshot = snapshot,
                        courses = state.courses,
                        onOpenAchievements = onOpenAchievements,
                    )
                }
            }
        }
    }
}

@Composable
private fun TodayContextSection(
    items: List<PlannerItem>,
    nextRoutineSlot: RoutineSlot?,
    onOpenPlanner: () -> Unit,
    onOpenRoutine: () -> Unit,
) {
    val timeline = buildTodayTimeline(items, nextRoutineSlot)
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = stringResource(R.string.st01_today_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
        )
        if (timeline.isEmpty()) {
            Text(
                text = stringResource(R.string.st01_today_empty),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        } else {
            Column(modifier = Modifier.padding(top = Spacing.xs)) {
                timeline.forEachIndexed { index, entry ->
                    TodayTimelineRow(
                        time = entry.time,
                        title = entry.title,
                        isCurrent = index == 0,
                        isLast = index == timeline.lastIndex,
                    )
                }
            }
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
            modifier = Modifier
                .eduClickable(
                    onClickLabel = stringResource(R.string.st01_see_daily),
                    onClick = onOpenPlanner,
                )
                .padding(top = Spacing.xxs, bottom = Spacing.xxs),
        ) {
            Text(
                text = stringResource(R.string.st01_see_daily),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.primary,
            )
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = EduTheme.colors.primary,
                modifier = Modifier.size(Sizing.iconSm),
            )
        }
    }
}

private data class TodayTimelineEntry(val time: String, val title: String)

private fun buildTodayTimeline(
    items: List<PlannerItem>,
    nextRoutineSlot: RoutineSlot?,
): List<TodayTimelineEntry> {
    val fromPlan = items.take(3).map { TodayTimelineEntry(time = it.time, title = it.title) }
    if (fromPlan.isNotEmpty()) return fromPlan
    val slot = nextRoutineSlot ?: return emptyList()
    return listOf(TodayTimelineEntry(time = slot.startTime, title = slot.title))
}

@Composable
private fun TodayTimelineRow(
    time: String,
    title: String,
    isCurrent: Boolean,
    isLast: Boolean,
) {
    val colors = EduTheme.colors
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(16.dp)
                    .background(if (isCurrent) colors.primary else colors.surface, CircleShape)
                    .border(
                        width = 2.5.dp,
                        color = if (isCurrent) colors.primary else colors.border,
                        shape = CircleShape,
                    ),
            )
            if (!isLast) {
                Box(
                    modifier = Modifier
                        .padding(vertical = 2.dp)
                        .size(width = 2.dp, height = 18.dp)
                        .background(colors.border, RoundedCornerShape(Radius.pill)),
                )
            }
        }
        Column(
            modifier = Modifier
                .weight(1f)
                .padding(bottom = if (isLast) 0.dp else Spacing.xs),
        ) {
            Text(
                text = time,
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = colors.textSecondary,
            )
            Text(
                text = title,
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun RoutineSignalRow(slot: RoutineSlot, onOpenRoutine: () -> Unit) {
    val time = slot.endTime?.let { end ->
        stringResource(R.string.st01_routine_time_range, slot.startTime, end)
    } ?: slot.startTime

    EduGroupedSurface(
        modifier = Modifier
            .padding(top = Spacing.xs)
            .eduClickable(onClickLabel = stringResource(R.string.tab_student_routine), onClick = onOpenRoutine),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Icon(
                imageVector = Icons.Filled.CalendarToday,
                contentDescription = null,
                tint = EduTheme.colors.success,
                modifier = Modifier.size(Sizing.icon),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st01_routine_signal_title),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.success,
                )
                Text(
                    text = slot.title,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                    color = EduTheme.colors.textPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Text(
                text = time,
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
            )
        }
    }
}

private data class HomeReviewTarget(
    val topic: String,
    val courseId: String,
    val reason: String,
    val onAction: () -> Unit,
)

@Composable
private fun resolveDistinctHomeReview(
    snapshot: StudentHomeSnapshot,
    courses: List<StudentCourseSummary>,
    onOpenCourse: (courseId: String) -> Unit,
    onOpenSubscriptions: () -> Unit,
): HomeReviewTarget? {
    val hero = snapshot.continueItem
    val heroCourseId = hero?.courseId
    val heroLesson = hero?.lessonTitle?.trim().orEmpty()
    val heroSubject = hero?.subjectTitle?.trim().orEmpty()

    val candidates = snapshot.subjects
        .filter { subject ->
            val course = courses.firstOrNull { it.courseId == subject.courseId }
            val published = course?.isPublished != false
            val sameCourse = !heroCourseId.isNullOrBlank() && subject.courseId == heroCourseId
            val sameName = listOf(subject.title, subject.currentLabel).any { label ->
                label.equals(heroLesson, ignoreCase = true) ||
                    label.equals(heroSubject, ignoreCase = true) ||
                    (heroLesson.isNotBlank() && label.contains(heroLesson, ignoreCase = true))
            }
            published && !sameCourse && !sameName
        }
        .sortedBy { it.progress }

    val pick = candidates.firstOrNull { it.progress < 0.5f } ?: candidates.firstOrNull() ?: return null
    val course = courses.firstOrNull { it.courseId == pick.courseId }
    return HomeReviewTarget(
        topic = pick.title,
        courseId = pick.courseId,
        reason = stringResource(R.string.st01_review_reason_weak),
        onAction = {
            when (course?.cardState()) {
                CourseCardState.Locked -> onOpenSubscriptions()
                else -> onOpenCourse(pick.courseId)
            }
        },
    )
}

@Composable
private fun SmartRecommendationCard(target: HomeReviewTarget) {
    val colors = EduTheme.colors
    EduCard(
        onClick = target.onAction,
        onClickLabel = stringResource(R.string.st01_lets_review_this),
        borderColor = colors.aiAccent.copy(alpha = 0.28f),
        contentPadding = PaddingValues(Spacing.xs),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        ) {
            Icon(
                imageVector = Icons.Filled.AutoAwesome,
                contentDescription = null,
                tint = colors.aiAccent,
                modifier = Modifier.size(Sizing.icon),
            )
            Text(
                text = stringResource(R.string.st01_lets_review_this),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.aiAccent,
            )
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.padding(top = Spacing.xs),
        ) {
            SubjectVisual(
                courseId = target.courseId,
                compact = true,
                fillWidth = false,
                modifier = Modifier.size(56.dp),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = target.topic,
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = target.reason,
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        ) {
            Text(
                text = stringResource(R.string.st01_review_ten_minutes),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.aiAccent,
            )
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = colors.aiAccent,
                modifier = Modifier.size(Sizing.icon),
            )
        }
    }
}

@Composable
private fun ProgressSnapshotSection(
    snapshot: StudentHomeSnapshot,
    courses: List<StudentCourseSummary>,
    onOpenAchievements: () -> Unit,
) {
    EduCard(
        onClick = onOpenAchievements,
        onClickLabel = stringResource(R.string.st01_achievements_title),
        contentPadding = PaddingValues(horizontal = Spacing.xs, vertical = Spacing.xs),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceEvenly,
            modifier = Modifier.fillMaxWidth(),
        ) {
            CompactProgressStat(
                label = stringResource(R.string.st01_progress_level_short),
                value = numeral(snapshot.gamification.level),
            )
            CompactProgressStat(
                label = stringResource(R.string.st01_progress_days_short),
                value = numeral(snapshot.streakDays),
                highlight = true,
            )
            CompactProgressStat(
                label = stringResource(R.string.st01_progress_xp_short),
                value = numeral(snapshot.gamification.xp),
            )
        }
    }
}

@Composable
private fun CompactProgressStat(
    label: String,
    value: String,
    highlight: Boolean = false,
) {
    val colors = EduTheme.colors
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            if (highlight) {
                Icon(
                    imageVector = Icons.Filled.LocalFireDepartment,
                    contentDescription = null,
                    tint = colors.highlight,
                    modifier = Modifier.size(14.dp),
                )
            }
            Text(
                text = value,
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                color = if (highlight) colors.highlight else colors.textPrimary,
            )
        }
        Text(
            text = label,
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = colors.textSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun HomeMetricTile(
    label: String,
    value: String,
    icon: ImageVector,
    tint: Color,
    modifier: Modifier = Modifier,
) {
    EduGroupedSurface(modifier = modifier) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(Sizing.icon))
        Text(
            text = value,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun SubjectSnapshotSection(
    courses: List<StudentCourseSummary>,
    gradeLabel: String,
    onOpenCourse: (courseId: String) -> Unit,
    onOpenSubscriptions: () -> Unit,
) {
    val colors = EduTheme.colors
    val activeCourses = courses.filter { it.isPublished && it.isEntitled }
    val visibleCourses = activeCourses.ifEmpty { courses.filter { it.isPublished } }.take(3)
    Column(modifier = Modifier.fillMaxWidth()) {
        StudentWebSectionIntro(
            eyebrow = stringResource(R.string.st01_subjects_eyebrow),
            title = stringResource(R.string.st01_subject_snapshot_title),
            subtitle = stringResource(R.string.st01_subject_snapshot_subtitle, gradeLabel),
        )
        Spacer(modifier = Modifier.height(Spacing.sm))

        EduCard {
            Text(
                text = stringResource(R.string.st01_subject_snapshot_active_count, numeral(activeCourses.size)),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = colors.primary,
            )
            if (visibleCourses.isEmpty()) {
                Text(
                    text = stringResource(R.string.st01_subjects_empty_body),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.sm)) {
                    visibleCourses.forEach { course ->
                        SubjectSnapshotRow(
                            course = course,
                            onClick = {
                                if (course.cardState() == CourseCardState.Locked) onOpenSubscriptions() else onOpenCourse(course.courseId)
                            },
                        )
                    }
                }
            }
            val remaining = (courses.size - visibleCourses.size).coerceAtLeast(0)
            if (remaining > 0) {
                Text(
                    text = stringResource(R.string.st01_subject_snapshot_more, numeral(remaining)),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
        }
    }
}

@Composable
private fun SubjectSnapshotRow(course: StudentCourseSummary, onClick: () -> Unit) {
    val colors = EduTheme.colors
    val state = course.cardState()
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.neutralAlpha100, androidx.compose.foundation.shape.RoundedCornerShape(com.rork.eduspark.ui.theme.Radius.md))
            .eduClickable(onClickLabel = course.title, onClick = onClick)
            .padding(Spacing.sm)
            .then(Modifier),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(40.dp)
                .background(if (state == CourseCardState.Locked) colors.neutralAlpha100 else colors.primaryContainer, CircleShape),
        ) {
            Icon(
                imageVector = if (state == CourseCardState.Locked) Icons.Filled.Lock else Icons.Filled.AutoStories,
                contentDescription = null,
                tint = if (state == CourseCardState.Locked) colors.textSecondary else colors.primary,
                modifier = Modifier.size(Sizing.icon),
            )
        }
        Column(
            modifier = Modifier
                .weight(1f)
                .then(Modifier),
        ) {
            Text(
                text = course.title,
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = course.currentLabel.ifBlank { course.teacherName },
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            EduLinearProgress(
                progress = course.progress.coerceIn(0f, 1f),
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
        Icon(
            imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
            contentDescription = null,
            tint = colors.textSecondary,
            modifier = Modifier.size(Sizing.icon),
        )
    }
}

@Composable
private fun JourneyHero(
    snapshot: StudentHomeSnapshot,
    continueCourse: StudentCourseSummary?,
    onOpenCourse: (courseId: String) -> Unit,
    onOpenLesson: (lessonId: String) -> Unit,
    onOpenSubscriptions: () -> Unit,
) {
    val colors = EduTheme.colors
    val mission = snapshot.continueItem
    val reducedMotion = LocalReducedMotion.current
    var entered by remember { mutableStateOf(reducedMotion) }
    LaunchedEffect(Unit) { entered = true }

    val openCurrent = {
        when {
            mission != null -> onOpenLesson(mission.lessonId)
            continueCourse != null -> onOpenCourse(continueCourse.courseId)
            else -> onOpenSubscriptions()
        }
    }
    val done = continueCourse?.completedLessonCount ?: mission?.let { (it.lessonIndex - 1).coerceAtLeast(0) } ?: 0
    val total = continueCourse?.totalLessonCount ?: mission?.lessonTotal ?: 0
    val progress = if (total > 0) done.toFloat() / total.toFloat() else 0f

    AnimatedVisibility(
        visible = entered,
        enter = fadeIn(tween(Motion.STANDARD_MS)) + slideInVertically(tween(Motion.STANDARD_MS)) { it / 8 },
    ) {
        EduCard(
            containerColor = colors.primary,
            borderColor = colors.primary.copy(alpha = 0.28f),
            contentPadding = PaddingValues(Spacing.xs),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    StatusPill(
                        label = stringResource(R.string.st01_current_start_here),
                        contentColor = colors.onPrimary,
                        containerColor = colors.onPrimary.copy(alpha = 0.16f),
                    )
                    Text(
                        text = mission?.lessonTitle ?: stringResource(R.string.st01_first_day_heading),
                        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.onPrimary,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                    if (mission != null) {
                        Text(
                            text = stringResource(
                                R.string.st01_start_here_meta,
                                mission.subjectTitle,
                                numeral(mission.minutesLeft),
                                numeral(mission.lessonIndex),
                                numeral(mission.lessonTotal),
                            ),
                            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                            color = colors.onPrimary.copy(alpha = 0.88f),
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                    } else {
                        Text(
                            text = stringResource(R.string.st01_first_day_body),
                            style = EduTheme.typography.caption,
                            color = colors.onPrimary.copy(alpha = 0.82f),
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                    }
                    if (total > 0) {
                        OnPrimaryProgress(
                            progress = progress,
                            modifier = Modifier.padding(top = Spacing.xs),
                        )
                    }
                }
                SubjectVisual(
                    courseId = mission?.courseId ?: continueCourse?.courseId.orEmpty(),
                    compact = true,
                    fillWidth = false,
                    modifier = Modifier.size(88.dp),
                )
            }
            Button(
                onClick = openCurrent,
                shape = RoundedCornerShape(Radius.sm),
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.surface,
                    contentColor = colors.primary,
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        text = if (mission != null) {
                            stringResource(R.string.st01_continue_lesson_cta)
                        } else {
                            stringResource(R.string.st01_catalog_cta_ready)
                        },
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                    )
                    Icon(
                        imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                        contentDescription = null,
                        modifier = Modifier.size(Sizing.icon),
                    )
                }
            }
        }
    }
}

@Composable
private fun OnPrimaryProgress(progress: Float, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val animated by animateFloatAsState(
        targetValue = progress.coerceIn(0f, 1f),
        animationSpec = standardSpec(),
        label = "homeHeroProgress",
    )
    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(5.dp)
            .background(colors.onPrimary.copy(alpha = 0.22f), RoundedCornerShape(Radius.pill)),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(animated)
                .height(5.dp)
                .background(colors.onPrimary, RoundedCornerShape(Radius.pill)),
        )
    }
}

@Composable
private fun ContinueLearningSection(
    item: ContinueLearningItem?,
    onOpenLesson: (lessonId: String) -> Unit,
    onOpenSubscriptions: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        StudentWebSectionIntro(
            title = stringResource(R.string.st01_continue_title),
            subtitle = stringResource(R.string.st01_continue_subtitle),
        )
        Spacer(modifier = Modifier.height(Spacing.sm))

        if (item != null) {
            ContinueLearningCard(item = item, onClick = { onOpenLesson(item.lessonId) })
        } else {
            EduCard {
                Text(
                    text = stringResource(R.string.st01_continue_empty_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = EduTheme.colors.textPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(
                    text = stringResource(R.string.st01_continue_empty_body),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xxs, bottom = Spacing.sm),
                )
                PrimaryButton(
                    text = stringResource(R.string.st01_catalog_cta_locked),
                    onClick = onOpenSubscriptions,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun ContinueLearningCard(item: ContinueLearningItem, onClick: () -> Unit) {
    EduCard(onClick = onClick, onClickLabel = item.lessonTitle) {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(36.dp)
                    .background(EduTheme.colors.primaryContainer, CircleShape),
            ) {
                Icon(
                    imageVector = Icons.Filled.AutoStories,
                    contentDescription = null,
                    tint = EduTheme.colors.primary,
                    modifier = Modifier.size(Sizing.icon),
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st01_continue_eyebrow),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
                Text(
                    text = item.lessonTitle,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Text(
                    text = item.subjectTitle,
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = EduTheme.colors.textSecondary,
                modifier = Modifier.size(Sizing.icon),
            )
        }
    }
}

@Composable
private fun HomeAchievementsSection(
    achievements: List<Achievement>,
    onViewAll: () -> Unit,
) {
    val recent = achievements.firstOrNull { it.status == AchievementStatus.Earned }
    val next = achievements.firstOrNull { it.status == AchievementStatus.Locked }

    Column(modifier = Modifier.fillMaxWidth()) {
        StudentWebSectionIntro(
            title = stringResource(R.string.st01_achievements_title),
            subtitle = stringResource(R.string.st01_achievements_subtitle),
        )
        Spacer(modifier = Modifier.height(Spacing.sm))

        AchievementSummaryCard(
            label = stringResource(R.string.st01_achievement_recent_label),
            achievement = recent,
            emptyTitle = stringResource(R.string.st01_recent_achievement_empty),
            isLocked = false,
        )
        Spacer(modifier = Modifier.height(Spacing.sm))
        AchievementSummaryCard(
            label = stringResource(R.string.st01_achievement_next_label),
            achievement = next,
            emptyTitle = stringResource(R.string.st01_next_achievement_empty),
            isLocked = next != null,
            onViewAll = onViewAll,
        )
    }
}

@Composable
private fun AchievementSummaryCard(
    label: String,
    achievement: Achievement?,
    emptyTitle: String,
    isLocked: Boolean,
    onViewAll: (() -> Unit)? = null,
) {
    val colors = EduTheme.colors
    val description = achievement?.description.orEmpty()

    EduCard(
        borderColor = if (isLocked) colors.primary.copy(alpha = 0.18f) else colors.success.copy(alpha = 0.2f),
    ) {
        Text(
            text = label,
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = colors.textSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .padding(top = Spacing.sm)
                .align(Alignment.CenterHorizontally)
                .size(Sizing.avatarLg)
                .background(if (isLocked) colors.neutralAlpha100 else colors.highlightContainer, CircleShape),
        ) {
            Icon(
                imageVector = achievement?.kind?.icon() ?: if (isLocked) Icons.Filled.Lock else Icons.Filled.EmojiEvents,
                contentDescription = null,
                tint = if (isLocked) colors.textSecondary else colors.highlight,
                modifier = Modifier.size(Sizing.iconLg),
            )
        }
        Text(
            text = achievement?.title ?: emptyTitle,
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
            color = colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
        if (description.isNotBlank()) {
            Text(
                text = description,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                textAlign = TextAlign.Center,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xxs),
            )
        }
        if (onViewAll != null) {
            GhostButton(
                text = stringResource(R.string.st01_view_all_achievements),
                onClick = onViewAll,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun Grade.label(): String = when (this) {
    Grade.Grade10 -> stringResource(R.string.a07_grade_10)
    Grade.Grade11 -> stringResource(R.string.a07_grade_11)
    Grade.Baccalaureate -> stringResource(R.string.a07_grade_12)
}

private fun initials(name: String): String {
    val parts = name.trim().split(Regex("\\s+")).filter { it.isNotBlank() }
    return when {
        parts.size >= 2 -> "${parts[0].take(1)}${parts[1].take(1)}"
        parts.isNotEmpty() -> parts[0].take(2)
        else -> ""
    }
}

@Composable
private fun StudentHomeSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonBlock(widthFraction = 0.45f, height = 22.dp)
        SkeletonListItem()
        SkeletonListItem()
        SkeletonCard()
        SkeletonCard()
    }
}
