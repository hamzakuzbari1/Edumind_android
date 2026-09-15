package com.rork.eduspark.ui.screens.student

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Audiotrack
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Message
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LearningPath
import com.rork.eduspark.data.model.LearningStep
import com.rork.eduspark.data.model.LearningUnit
import com.rork.eduspark.data.model.LessonMediaType
import com.rork.eduspark.data.model.LessonStatus
import com.rork.eduspark.data.model.LockedReason
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.progress.SpineNode
import com.rork.eduspark.ui.components.progress.SpineNodeState
import com.rork.eduspark.ui.components.progress.SpineRow
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.components.surface.SkeletonDetail
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import androidx.compose.foundation.shape.RoundedCornerShape
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

@Composable
fun CourseDetailScreen(
    courseId: String,
    onBack: () -> Unit,
    onContinueLesson: (lessonId: String) -> Unit,
    onOpenManualQuiz: () -> Unit,
    onSubscribe: () -> Unit,
    onMessageTeacher: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: CourseDetailViewModel = koinViewModel(parameters = { parametersOf(courseId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val course = (state.result as? UiState.Content)?.data

    EduScaffold(
        title = course?.title.orEmpty(),
        onBack = onBack,
        modifier = modifier,
    ) {
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { SkeletonDetail(modifier = Modifier.padding(Spacing.gutter)) },
            modifier = Modifier.fillMaxSize(),
        ) { loadedCourse ->
            when {
                !loadedCourse.isPublished -> MessageState(
                    icon = Icons.Filled.Schedule,
                    title = stringResource(R.string.st02_not_published_title),
                    body = stringResource(R.string.st02_not_published_body, loadedCourse.teacherName),
                    modifier = Modifier.fillMaxSize(),
                )
                !loadedCourse.isEntitled -> CourseLockedContent(
                    course = loadedCourse,
                    onSubscribe = onSubscribe,
                    onBack = onBack,
                )
                else -> CourseContent(
                    course = loadedCourse,
                    onOpenLesson = onContinueLesson,
                    onOpenManualQuiz = onOpenManualQuiz,
                    onMessageTeacher = onMessageTeacher,
                )
            }
        }
    }
}

@Composable
private fun CourseLockedContent(
    course: LearningPath,
    onSubscribe: () -> Unit,
    onBack: () -> Unit,
) {
    val colors = EduTheme.colors

    EduCard(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(Spacing.gutter),
        contentPadding = PaddingValues(horizontal = Spacing.card, vertical = Spacing.lg),
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(88.dp)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(
                    text = course.teacherName.take(1),
                    style = EduTheme.typography.display,
                    color = colors.primary,
                )
            }
            Text(
                text = course.title,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.md),
            )
            Text(
                text = stringResource(R.string.st02_locked_with_teacher, course.teacherName),
                style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.xxs),
            )

            Icon(
                imageVector = Icons.Filled.Lock,
                contentDescription = null,
                tint = colors.highlight,
                modifier = Modifier
                    .padding(top = Spacing.section)
                    .size(48.dp),
            )
            Text(
                text = stringResource(R.string.st02_locked_title),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.md),
            )
            Text(
                text = pluralStringResource(
                    R.plurals.st02_locked_subscribe_prompt,
                    course.totalLessonCount,
                    course.totalLessonCount,
                    course.teacherName,
                ),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            )

            PrimaryButton(
                text = stringResource(R.string.st02_locked_cta_subscribe),
                onClick = onSubscribe,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.section),
            )
            GhostButton(
                text = stringResource(R.string.st02_locked_back_to_subjects),
                onClick = onBack,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }
    }
}

private enum class CourseDetailTab { Lessons, Quizzes }

@Composable
private fun CourseContent(
    course: LearningPath,
    onOpenLesson: (lessonId: String) -> Unit,
    onOpenManualQuiz: () -> Unit,
    onMessageTeacher: () -> Unit,
) {
    var showTeacherProfile by rememberSaveable { mutableStateOf(false) }
    val units = course.toCourseUnits()
    val currentUnitIndex = units.indexOfFirst { unit -> unit.steps.any { it.isCurrent } }.takeIf { it >= 0 } ?: 0
    var expandedUnit by rememberSaveable(course.id) { mutableStateOf(currentUnitIndex) }

    if (showTeacherProfile) {
        TeacherProfileDialog(course = course, onDismiss = { showTeacherProfile = false })
    }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            CourseHeroCard(
                course = course,
                onMessageTeacher = onMessageTeacher,
                onViewProfile = { showTeacherProfile = true },
            )
            Spacer(modifier = Modifier.height(Spacing.md))
        }

        item {
            CourseCurrentLessonCard(
                course = course,
                lesson = course.currentJourneyLesson(),
                allCompleted = course.allLessonsCompleted(),
                onContinue = { lessonId -> onOpenLesson(lessonId) },
            )
            Spacer(modifier = Modifier.height(Spacing.section))
        }

        item {
            Text(
                text = stringResource(R.string.st02_journey_title),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.textPrimary,
            )
            Spacer(modifier = Modifier.height(Spacing.sm))
        }

        if (course.steps.isEmpty()) {
            item { CourseJourneyEmpty() }
        } else {
            itemsIndexed(units) { unitIndex, unit ->
                CourseUnitAccordion(
                    unit = unit,
                    expanded = expandedUnit == unitIndex,
                    onToggle = {
                        expandedUnit = if (expandedUnit == unitIndex) -1 else unitIndex
                    },
                    onOpenLesson = onOpenLesson,
                )
                if (unitIndex != units.lastIndex) {
                    Spacer(modifier = Modifier.height(Spacing.xs))
                }
            }
        }

        if (course.quizCount > 0) {
            item {
                GhostButton(
                    text = stringResource(R.string.st02_tab_quizzes_count, course.quizCount),
                    onClick = onOpenManualQuiz,
                    leadingIcon = Icons.Filled.Quiz,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
        }
    }
}

@Composable
private fun CourseHeroCard(
    course: LearningPath,
    onMessageTeacher: () -> Unit,
    onViewProfile: () -> Unit,
) {
    val colors = EduTheme.colors

    EduCard(contentPadding = PaddingValues(0.dp)) {
        Box {
            SubjectVisual(
                courseId = course.id,
                modifier = Modifier.height(170.dp),
                compact = false,
            )
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(Spacing.md)
                    .size(48.dp)
                    .background(colors.textPrimary.copy(alpha = 0.12f), CircleShape)
                    .eduClickable(onClickLabel = stringResource(R.string.common_back), onClick = onViewProfile),
            ) {
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = colors.textPrimary, modifier = Modifier.size(Sizing.iconLg))
            }
        }
        Column(modifier = Modifier.padding(Spacing.card)) {
            Text(
                text = course.title,
                style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier.padding(top = Spacing.sm),
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(Sizing.avatarSm)
                        .background(colors.accentContainer, CircleShape),
                ) {
                    Text(text = course.teacherName.take(1), style = EduTheme.typography.caption, color = colors.accent)
                }
                Text(
                    text = course.teacherName,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                    modifier = Modifier.weight(1f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                GhostButton(
                    text = stringResource(R.string.st02_hero_message_teacher),
                    onClick = onMessageTeacher,
                    leadingIcon = Icons.Filled.Message,
                )
            }

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            ) {
                Text(text = stringResource(R.string.st02_course_progress_label), style = EduTheme.typography.caption, color = colors.textSecondary)
                Text(text = stringResource(R.string.progress_percent, (course.progress.coerceIn(0f, 1f) * 100).toInt()), style = EduTheme.typography.mono.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
            }
            EduLinearProgress(progress = course.progress.coerceIn(0f, 1f), modifier = Modifier.padding(top = Spacing.xs))
        }
    }
}

@Composable
private fun CourseUnitAccordion(
    unit: CourseUnitGroup,
    expanded: Boolean,
    onToggle: () -> Unit,
    onOpenLesson: (lessonId: String) -> Unit,
) {
    val colors = EduTheme.colors
    EduCard(
        contentPadding = PaddingValues(0.dp),
        modifier = Modifier.animateContentSize(),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier
                .fillMaxWidth()
                .eduClickable(onClickLabel = unit.title, onClick = onToggle)
                .padding(Spacing.card),
        ) {
            Icon(
                imageVector = if (expanded) Icons.Filled.KeyboardArrowDown else Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = colors.textSecondary,
                modifier = Modifier.size(Sizing.icon),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = unit.title,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.st02_unit_progress, numeral(unit.steps.count { it.isCompleted }), numeral(unit.steps.size)),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        AnimatedVisibility(visible = expanded) {
            Column(modifier = Modifier.padding(start = Spacing.card, end = Spacing.card, bottom = Spacing.sm)) {
                unit.steps.forEach { step ->
                    LessonJourneyRow(
                        step = step,
                        onClick = { onOpenLesson(step.id) }.takeIf { !step.isLockedForStudent() },
                    )
                }
            }
        }
    }
}

private typealias CourseUnitGroup = LearningUnit

private fun LearningPath.toCourseUnits(): List<CourseUnitGroup> =
    units.ifEmpty {
        if (steps.isEmpty()) {
            emptyList()
        } else {
            listOf(
                LearningUnit(
                    id = null,
                    title = "عام",
                    progress = progress,
                    completedLessonCount = completedLessonCount,
                    totalLessonCount = totalLessonCount,
                    steps = steps,
                )
            )
        }
    }

@Composable
private fun CourseCurrentLessonCard(
    course: LearningPath,
    lesson: LearningStep?,
    allCompleted: Boolean,
    onContinue: (lessonId: String) -> Unit,
) {
    if (lesson == null && course.totalLessonCount == 0) {
        EduCard {
            Icon(
                imageVector = Icons.Filled.AutoStories,
                contentDescription = null,
                tint = EduTheme.colors.primary,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .size(36.dp),
            )
            Text(
                text = stringResource(R.string.st02_current_empty_title),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                color = EduTheme.colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            )
            Text(
                text = stringResource(R.string.st02_current_empty_body),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        return
    }

    val currentLesson = lesson ?: return
    val colors = EduTheme.colors
    val position = course.steps.indexOfFirst { it.id == currentLesson.id }.coerceAtLeast(0) + 1
    val total = course.totalLessonCount.coerceAtLeast(course.steps.size)

    EduCard(
        containerColor = colors.primary,
        borderColor = colors.primary.copy(alpha = 0.28f),
        contentPadding = PaddingValues(Spacing.sm),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = when {
                        allCompleted -> stringResource(R.string.st02_current_eyebrow_all_done)
                        else -> stringResource(R.string.st02_current_eyebrow_here)
                    },
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.onPrimary.copy(alpha = 0.88f),
                )
                Text(
                    text = currentLesson.title,
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.onPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Text(
                    text = stringResource(
                        R.string.st01_start_here_meta,
                        course.title,
                        numeral(currentLesson.durationMinutes.coerceAtLeast(1)),
                        numeral(position),
                        numeral(total),
                    ),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.onPrimary.copy(alpha = 0.82f),
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                EduLinearProgress(
                    progress = course.progress.coerceIn(0f, 1f),
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
            SubjectVisual(
                courseId = course.id,
                compact = true,
                fillWidth = false,
                modifier = Modifier.size(88.dp),
            )
        }
        PrimaryButton(
            text = when {
                allCompleted -> stringResource(R.string.st02_current_cta_review)
                course.completedLessonCount == 0 -> stringResource(R.string.st02_current_cta_start)
                else -> stringResource(R.string.st01_continue_lesson_cta)
            },
            onClick = { onContinue(currentLesson.id) },
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun LessonJourneyRow(
    step: LearningStep,
    onClick: (() -> Unit)?,
) {
    val colors = EduTheme.colors
    val isLocked = step.isLockedForStudent()
    val rowModifier = Modifier
        .fillMaxWidth()
        .padding(vertical = Spacing.xs)
        .then(
            if (step.isCurrent) {
                Modifier
                    .background(colors.primaryContainer, RoundedCornerShape(Radius.sm))
                    .padding(horizontal = Spacing.sm, vertical = Spacing.xs)
            } else {
                Modifier
            },
        )
        .then(
            if (onClick != null) {
                Modifier.eduClickable(onClickLabel = step.title, onClick = onClick)
            } else {
                Modifier
            },
        )

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = rowModifier,
    ) {
        LessonStatusGlyph(step = step)
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = step.title,
                style = EduTheme.typography.body.copy(fontWeight = if (step.isCurrent) FontWeight.ExtraBold else FontWeight.SemiBold),
                color = if (isLocked) colors.textSecondary else colors.textPrimary,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (step.isCurrent) {
                Text(
                    text = stringResource(R.string.st02_you_are_here),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.primary,
                )
            }
        }
        if (step.durationMinutes > 0) {
            Text(
                text = stringResource(R.string.st02_duration_minutes_short, numeral(step.durationMinutes)),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
        }
    }
}

@Composable
private fun LessonStatusGlyph(step: LearningStep) {
    val colors = EduTheme.colors
    when {
        step.isCompleted -> Icon(
            imageVector = Icons.Filled.CheckCircle,
            contentDescription = stringResource(R.string.st02_journey_state_completed),
            tint = colors.success,
            modifier = Modifier.size(Sizing.icon),
        )
        step.isCurrent -> Box(
            modifier = Modifier
                .size(14.dp)
                .background(colors.primary, CircleShape),
        )
        step.isLockedForStudent() -> Icon(
            imageVector = Icons.Filled.Lock,
            contentDescription = stringResource(R.string.st02_journey_state_locked),
            tint = colors.textSecondary,
            modifier = Modifier.size(Sizing.icon),
        )
        else -> Box(
            modifier = Modifier
                .size(14.dp)
                .background(colors.surface, CircleShape)
                .border(2.dp, colors.border, CircleShape),
        )
    }
}

@Composable
private fun CourseQuizzesPanel(course: LearningPath, onOpenManualQuiz: () -> Unit) {
    Column(modifier = Modifier.fillMaxWidth()) {
        StudentWebSectionIntro(
            title = stringResource(R.string.st02_quizzes_title),
            subtitle = stringResource(R.string.st02_quizzes_subtitle),
        )
        Spacer(modifier = Modifier.height(Spacing.sm))

        if (course.quizCount > 0) {
            EduCard {
                Row(
                    verticalAlignment = Alignment.Top,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                ) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(44.dp)
                            .background(EduTheme.colors.primaryContainer, CircleShape),
                    ) {
                        Icon(Icons.Filled.Quiz, contentDescription = null, tint = EduTheme.colors.primary, modifier = Modifier.size(Sizing.icon))
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Row(
                            verticalAlignment = Alignment.Top,
                            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text(
                                text = stringResource(R.string.st02_manual_quiz_row),
                                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                                color = EduTheme.colors.textPrimary,
                                modifier = Modifier.weight(1f),
                            )
                            StatusPill(
                                label = stringResource(R.string.st02_quizzes_status_available),
                                contentColor = EduTheme.colors.primary,
                                containerColor = EduTheme.colors.primaryContainer,
                            )
                        }
                        Text(
                            text = pluralStringResource(R.plurals.st02_quizzes_meta, course.quizCount, course.quizCount),
                            style = EduTheme.typography.caption,
                            color = EduTheme.colors.textSecondary,
                            modifier = Modifier.padding(top = Spacing.xs),
                        )
                    }
                }
                PrimaryButton(
                    text = stringResource(R.string.st02_quizzes_cta_start),
                    onClick = onOpenManualQuiz,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            }
        } else {
            EduCard {
                Icon(
                    imageVector = Icons.Filled.Quiz,
                    contentDescription = null,
                    tint = EduTheme.colors.textSecondary,
                    modifier = Modifier
                        .align(Alignment.CenterHorizontally)
                        .size(44.dp),
                )
                Text(
                    text = stringResource(R.string.st02_no_quizzes),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
                Text(
                    text = stringResource(R.string.st02_quizzes_empty_body),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun CourseJourneyEmpty() {
    EduCard {
        Icon(
            imageVector = Icons.Filled.AutoStories,
            contentDescription = null,
            tint = EduTheme.colors.primary,
            modifier = Modifier
                .align(Alignment.CenterHorizontally)
                .size(36.dp),
        )
        Text(
            text = stringResource(R.string.st02_journey_empty_title),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        )
        Text(
            text = stringResource(R.string.st02_journey_empty_body),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun CourseInlineTabs(
    selectedTab: CourseDetailTab,
    lessonsLabel: String,
    quizzesLabel: String,
    onSelect: (CourseDetailTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.lg),
        modifier = modifier.fillMaxWidth(),
    ) {
        CourseInlineTab(
            label = lessonsLabel,
            selected = selectedTab == CourseDetailTab.Lessons,
            onClick = { onSelect(CourseDetailTab.Lessons) },
            modifier = Modifier.weight(1f),
        )
        CourseInlineTab(
            label = quizzesLabel,
            selected = selectedTab == CourseDetailTab.Quizzes,
            onClick = { onSelect(CourseDetailTab.Quizzes) },
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun CourseInlineTab(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = modifier.eduClickable(onClickLabel = label, onClick = onClick),
    ) {
        Text(
            text = label,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = if (selected) colors.primary else colors.textSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Box(
            modifier = Modifier
                .padding(top = Spacing.xs)
                .fillMaxWidth()
                .height(3.dp)
                .background(if (selected) colors.primary else colors.border),
        )
    }
}

@Composable
private fun TeacherProfileDialog(course: LearningPath, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            GhostButton(text = stringResource(R.string.common_close), onClick = onDismiss)
        },
        title = {
            Text(
                text = stringResource(R.string.st02_teacher_profile_title, course.teacherName),
                style = EduTheme.typography.title,
            )
        },
        text = {
            Text(
                text = stringResource(R.string.st02_teacher_profile_body, course.title, course.subtitle),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textSecondary,
            )
        },
    )
}

private fun LearningPath.currentJourneyLesson(): LearningStep? {
    if (steps.isEmpty()) return null
    steps.firstOrNull { it.isCurrent }?.let { return it }
    steps.firstOrNull { !it.isCompleted && it.status == LessonStatus.Processed }?.let { return it }
    return steps.lastOrNull()
}

private fun LearningPath.allLessonsCompleted(): Boolean = steps.isNotEmpty() && steps.all { it.isCompleted }

@Composable
private fun LearningPath.progressLine(): String {
    val total = totalLessonCount
    val done = completedLessonCount
    return when {
        total <= 0 -> stringResource(R.string.st02_hero_progress_empty)
        done == 0 -> pluralStringResource(R.plurals.st02_hero_lessons_waiting, total, total)
        done >= total -> stringResource(R.string.st02_hero_progress_all_completed)
        else -> stringResource(R.string.st02_hero_lessons_completed, numeral(done), numeral(total))
    }
}

private fun LearningStep.toSpineState(): SpineNodeState = when {
    isCompleted -> SpineNodeState.Completed
    isCurrent -> SpineNodeState.Current
    else -> SpineNodeState.Locked
}

private fun LearningStep.isLockedForStudent(): Boolean =
    status == LessonStatus.LockedSequential || status == LessonStatus.LockedByEntitlement

@Composable
private fun LearningStep.journeyStateLabel(): String = when {
    isCompleted -> stringResource(R.string.st02_journey_state_completed)
    isCurrent -> stringResource(R.string.st02_journey_state_current)
    isLockedForStudent() -> stringResource(R.string.st02_journey_state_locked)
    else -> stringResource(R.string.st02_journey_state_upcoming)
}

@Composable
private fun DurationText(minutes: Int) {
    Text(
        text = pluralStringResource(R.plurals.st01_plan_duration, minutes, minutes),
        style = EduTheme.typography.caption,
        color = EduTheme.colors.textSecondary,
    )
}

@Composable
private fun MediaTypeIconsRow(mediaTypes: Set<LessonMediaType>) {
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
        if (LessonMediaType.Pdf in mediaTypes) {
            Icon(Icons.Filled.Description, contentDescription = null, tint = EduTheme.colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
        }
        if (LessonMediaType.Video in mediaTypes) {
            Icon(Icons.Filled.Videocam, contentDescription = null, tint = EduTheme.colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
        }
        if (LessonMediaType.Audio in mediaTypes) {
            Icon(Icons.Filled.Audiotrack, contentDescription = null, tint = EduTheme.colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
        }
    }
}

@Composable
private fun lockedReasonText(reason: LockedReason?): String = when (reason) {
    is LockedReason.RequiresStep -> stringResource(R.string.st02_locked_requires_step, reason.stepTitle)
    is LockedReason.RequiresStepCount -> pluralStringResource(R.plurals.st02_locked_requires_count, reason.count, reason.count)
    LockedReason.RequiresEntitlement -> stringResource(R.string.st02_locked_requires_entitlement)
    null -> ""
}
