package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyItemScope
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.filled.DragHandle
import androidx.compose.material.icons.filled.MenuBook
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.zIndex
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.LessonProcessingStageStatus
import com.rork.eduspark.data.model.TeacherCourseStatus
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonStatus
import com.rork.eduspark.data.model.TeacherStudentSummary
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf
import kotlin.math.roundToInt

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-04 · Class Detail — operate one class.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Lesson tap destinations, reorder persistence, and add-lesson routing stay on
 * [TeacherCourseDetailViewModel]. This screen only restyles the existing payload.
 */
@Composable
fun TeacherCourseDetailScreen(
    courseId: String,
    onBack: () -> Unit,
    onAddLesson: () -> Unit,
    onOpenProcessingLesson: (lessonId: String) -> Unit,
    onOpenLessonEditor: (lessonId: String) -> Unit,
    onOpenLessonPreview: (lessonId: String) -> Unit,
    modifier: Modifier = Modifier,
    onOpenStudents: () -> Unit = {},
    onOpenStudent: (studentId: String) -> Unit = {},
    viewModel: TeacherCourseDetailViewModel = koinViewModel(parameters = { parametersOf(courseId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val course = (state.result as? UiState.Content)?.data?.course

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.retry()
    }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherCourseDetailEvent.OpenLessonProcessing -> onOpenProcessingLesson(event.lessonId)
                is TeacherCourseDetailEvent.OpenLessonEditor -> onOpenLessonEditor(event.lessonId)
                is TeacherCourseDetailEvent.OpenLessonPreview -> onOpenLessonPreview(event.lessonId)
            }
        }
    }

    val title = course?.let {
        stringResource(R.string.tc04_class_title, it.subjectTitle, teacherGradeShortLabel(it.grade))
    }.orEmpty()

    EduScaffold(
        title = title,
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherCourseDetailSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherCourseDetailContent(
                data = data,
                onLessonTapped = viewModel::onLessonTapped,
                onReorder = viewModel::reorderLessons,
                onAddLesson = onAddLesson,
                onOpenStudents = onOpenStudents,
                onOpenStudent = onOpenStudent,
            )
        }
    }
}

@Composable
private fun TeacherCourseDetailContent(
    data: TeacherCourseDetailData,
    onLessonTapped: (TeacherLesson) -> Unit,
    onReorder: (List<String>) -> Unit,
    onAddLesson: () -> Unit,
    onOpenStudents: () -> Unit,
    onOpenStudent: (studentId: String) -> Unit,
) {
    val colors = EduTheme.colors
    val course = data.course

    var orderedIds by remember(data.lessons.map { it.lesson.id }) {
        mutableStateOf(data.lessons.map { it.lesson.id })
    }
    val rowsById = remember(data.lessons) { data.lessons.associateBy { it.lesson.id } }
    var draggingId by remember { mutableStateOf<String?>(null) }
    var dragDeltaPx by remember { mutableFloatStateOf(0f) }
    val rowHeightsPx = remember { mutableStateMapOf<String, Int>() }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.sm)
                    .clip(RoundedCornerShape(Radius.md)),
            ) {
                TeacherClassSubjectVisual(modifier = Modifier.height(96.dp))
            }
            ClassDetailMetaRow(data = data)
            Text(
                text = stringResource(R.string.tc04_lessons_section),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xs),
            )
        }

        if (data.lessons.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.MenuBook,
                    title = stringResource(R.string.tc04_empty_title),
                    body = stringResource(R.string.tc04_empty_body),
                    primaryActionLabel = stringResource(R.string.tc04_add_lesson),
                    onPrimaryAction = onAddLesson,
                )
            }
        } else {
            items(orderedIds, key = { it }) { id ->
                val row = rowsById[id] ?: return@items
                LessonRowItem(
                    row = row,
                    isDragging = id == draggingId,
                    dragOffsetPx = if (id == draggingId) dragDeltaPx else 0f,
                    onClick = { onLessonTapped(row.lesson) },
                    onMeasuredHeight = { px -> rowHeightsPx[id] = px },
                    dragHandleModifier = Modifier.dragHandlePointerInput(
                        id = id,
                        onDragStart = { draggingId = id; dragDeltaPx = 0f },
                        onDragDelta = { deltaY -> dragDeltaPx += deltaY },
                        onDragEnd = {
                            val fromIndex = orderedIds.indexOf(id)
                            val rowHeight = rowHeightsPx[id]?.takeIf { it > 0 } ?: 1
                            val steps = (dragDeltaPx / rowHeight).roundToInt()
                            val toIndex = (fromIndex + steps).coerceIn(0, orderedIds.lastIndex)
                            if (toIndex != fromIndex) {
                                orderedIds = orderedIds.toMutableList().also { it.add(toIndex, it.removeAt(fromIndex)) }
                                onReorder(orderedIds)
                            }
                            draggingId = null
                            dragDeltaPx = 0f
                        },
                        onDragCancel = { draggingId = null; dragDeltaPx = 0f },
                    ),
                )
            }
        }

        if (data.attentionStudents.isNotEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.tc04_students_attention),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xs),
                )
                AttentionStudentsCard(
                    students = data.attentionStudents,
                    onOpenStudent = onOpenStudent,
                    onOpenAll = onOpenStudents,
                )
            }
        } else {
            item {
                Text(
                    text = stringResource(R.string.tc04_all_students),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    color = colors.primary,
                    modifier = Modifier
                        .padding(top = Spacing.md)
                        .eduClickable(onClick = onOpenStudents)
                        .padding(vertical = Spacing.xs),
                )
            }
        }

        item {
            PrimaryButton(
                text = stringResource(R.string.tc04_add_lesson),
                onClick = onAddLesson,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md, bottom = Spacing.sm),
            )
        }
    }
}

@Composable
private fun ClassDetailMetaRow(data: TeacherCourseDetailData) {
    val colors = EduTheme.colors
    val course = data.course
    val published = course.status == TeacherCourseStatus.Published
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        StatusPill(
            label = if (published) {
                stringResource(R.string.tc03_filter_published)
            } else {
                teacherCourseStatusLabel(course.status)
            },
            contentColor = if (published) colors.success else colors.warning,
            containerColor = if (published) colors.success.copy(alpha = 0.14f) else colors.highlightContainer,
        )
        Text(
            text = classDetailMetaText(data),
            style = EduTheme.typography.caption,
            color = colors.textTertiary,
        )
    }
}

@Composable
private fun classDetailMetaText(data: TeacherCourseDetailData): String {
    val students = numeral(data.course.studentCount)
    val percent = data.completionPercent
    return if (percent != null) {
        stringResource(R.string.tc04_class_meta_progress, students, numeral(percent))
    } else {
        stringResource(R.string.tc04_class_meta, students)
    }
}

private fun Modifier.dragHandlePointerInput(
    id: String,
    onDragStart: () -> Unit,
    onDragDelta: (Float) -> Unit,
    onDragEnd: () -> Unit,
    onDragCancel: () -> Unit,
): Modifier = this.pointerInput(id) {
    detectDragGesturesAfterLongPress(
        onDragStart = { onDragStart() },
        onDragEnd = onDragEnd,
        onDragCancel = onDragCancel,
    ) { change, dragAmount ->
        change.consume()
        onDragDelta(dragAmount.y)
    }
}

@Composable
private fun LazyItemScope.LessonRowItem(
    row: TeacherLessonRow,
    isDragging: Boolean,
    dragOffsetPx: Float,
    onClick: () -> Unit,
    onMeasuredHeight: (Int) -> Unit,
    dragHandleModifier: Modifier,
) {
    val colors = EduTheme.colors
    val lesson = row.lesson
    val shape = RoundedCornerShape(Radius.md)

    Box(
        modifier = Modifier
            .animateItem()
            .zIndex(if (isDragging) 1f else 0f)
            .graphicsLayer { translationY = dragOffsetPx }
            .onGloballyPositioned { coords -> onMeasuredHeight(coords.size.height) }
            .padding(bottom = Spacing.xs),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.surface, shape)
                .border(Sizing.hairline, colors.border, shape)
                .eduClickable(onClick = onClick)
                .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .then(
                        if (lesson.status == TeacherLessonStatus.Draft) {
                            Modifier.border(Sizing.hairline, colors.textTertiary, CircleShape)
                        } else {
                            Modifier.background(lessonStatusDotColor(lesson.status), CircleShape)
                        },
                    ),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = lesson.title,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(
                        R.string.tc04_lesson_meta,
                        compactLessonTypeLabel(lesson.contentType),
                        compactLessonStatusLabel(lesson.status),
                    ),
                    style = EduTheme.typography.caption,
                    color = if (row.activeStageStatus == LessonProcessingStageStatus.Failed) {
                        colors.danger
                    } else {
                        colors.textTertiary
                    },
                )
            }
            Icon(
                imageVector = Icons.Filled.DragHandle,
                contentDescription = stringResource(R.string.tc04_reorder_handle),
                tint = colors.border,
                modifier = Modifier
                    .size(Sizing.touchTarget)
                    .padding(Spacing.sm)
                    .then(dragHandleModifier),
            )
        }
    }
}

@Composable
private fun compactLessonTypeLabel(type: LessonContentType): String = when (type) {
    LessonContentType.Video -> stringResource(R.string.tc04_content_type_video)
    LessonContentType.Pdf -> stringResource(R.string.tc04_content_type_pdf)
}

@Composable
private fun compactLessonStatusLabel(status: TeacherLessonStatus): String = when (status) {
    TeacherLessonStatus.Published -> stringResource(R.string.tc04_lesson_ready)
    TeacherLessonStatus.Processing -> stringResource(R.string.tc04_lesson_processing_short)
    TeacherLessonStatus.Draft -> stringResource(R.string.tc04_lesson_status_draft)
}

@Composable
private fun lessonStatusDotColor(status: TeacherLessonStatus): Color {
    val colors = EduTheme.colors
    return when (status) {
        TeacherLessonStatus.Published -> colors.success
        TeacherLessonStatus.Processing -> colors.aiAccent
        TeacherLessonStatus.Draft -> colors.textTertiary
    }
}

@Composable
private fun AttentionStudentsCard(
    students: List<TeacherStudentSummary>,
    onOpenStudent: (studentId: String) -> Unit,
    onOpenAll: () -> Unit,
) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface, shape)
            .border(Sizing.hairline, colors.border, shape)
            .padding(horizontal = Spacing.sm, vertical = Spacing.sm),
    ) {
        students.forEach { student ->
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier
                    .fillMaxWidth()
                    .eduClickable(onClick = { onOpenStudent(student.studentId) })
                    .padding(vertical = Spacing.xxs),
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(Sizing.avatarSm)
                        .background(colors.primaryContainer, CircleShape),
                ) {
                    Text(
                        text = student.displayName.firstOrNull()?.toString().orEmpty(),
                        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.primary,
                    )
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = student.displayName,
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                        color = colors.textPrimary,
                    )
                    Text(
                        text = attentionCaption(student),
                        style = EduTheme.typography.caption,
                        color = colors.textTertiary,
                    )
                }
            }
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .eduClickable(onClick = onOpenAll)
                .padding(top = Spacing.xs),
        ) {
            Text(
                text = stringResource(R.string.tc04_all_students),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.primary,
            )
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                contentDescription = null,
                tint = colors.primary,
                modifier = Modifier.size(Sizing.icon),
            )
        }
    }
}

@Composable
private fun attentionCaption(student: TeacherStudentSummary): String {
    val flag = student.flags.firstOrNull()
    return if (flag != null) studentFlagLabel(flag) else studentMonitoringStatusLabel(student.status)
}

@Composable
private fun TeacherCourseDetailSkeleton() {
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
