package com.rork.eduspark.ui.screens.student

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.GraphicEq
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Quiz
import androidx.compose.material.icons.filled.QuestionAnswer
import androidx.compose.material.icons.filled.Subtitles
import androidx.compose.material.icons.filled.ZoomIn
import androidx.compose.material.icons.filled.ZoomOut
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.LessonDetail
import com.rork.eduspark.data.model.LessonMediaType
import com.rork.eduspark.data.model.LessonStatus
import com.rork.eduspark.data.model.QuizQuestion
import com.rork.eduspark.data.model.QuizResult
import com.rork.eduspark.data.model.matchesQuizAnswer
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.nav.SheetHandle
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonDetail
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.foundation.mirrorInRtl
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Motion
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-03 · Lesson Player.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Teacher materials stay the source lesson. EduMind wraps them with understand / example /
 * practice / quick check / finish. [availableMediaTypes] drives Step 1 and the persistent
 * "محتوى الدرس" panel — only media the lesson actually has. Existing [VideoSurface],
 * [PdfSurface], and [AudioSurface] are reused; nothing new is invented for playback.
 *
 * No `aiAccent` marking here: the lesson itself is teacher-authored content. Only the tutor's
 * replies in ST-04/ST-05 — reached from here via "Ask Tutor" — carry the mark.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LessonPlayerScreen(
    lessonId: String,
    onBack: () -> Unit,
    onBackToCourse: (courseId: String) -> Unit,
    onAskTutor: () -> Unit,
    onAskTutorWithPrompt: (prompt: String) -> Unit,
    onTakeQuiz: (quizId: String) -> Unit,
    onOpenQuizResults: (quizId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: LessonPlayerViewModel = koinViewModel(parameters = { parametersOf(lessonId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val lesson = (state.result as? UiState.Content)?.data
    val isReady = lesson != null && lesson.status !in setOf(LessonStatus.Draft, LessonStatus.Processing)
    var conceptSheetFor by remember { mutableStateOf<String?>(null) }
    var showCompletionSheet by remember { mutableStateOf(false) }
    var quickAccess by rememberSaveable(lessonId) { mutableStateOf<String?>(null) }
    val showingTests = quickAccess == LessonQuickAccess.Quizzes.name
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }
    val networkBody = stringResource(R.string.state_error_network_body)
    val serverBody = stringResource(R.string.state_error_server_body)
    val unauthorizedBody = stringResource(R.string.state_error_unauthorized_body)
    val notFoundBody = stringResource(R.string.state_error_not_found_body)
    val unknownBody = stringResource(R.string.state_error_unknown_body)

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.refreshSession()
    }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is LessonPlayerEvent.OpenExternalMedia -> {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(event.url))
                    runCatching { context.startActivity(intent) }
                        .onFailure {
                            snackbarHostState.showSnackbar(unknownBody)
                        }
                }
                is LessonPlayerEvent.MediaResolveFailed -> {
                    val message = when (event.error) {
                        AppError.Offline, AppError.Network -> networkBody
                        AppError.Server -> serverBody
                        AppError.SessionExpired -> unauthorizedBody
                        AppError.Forbidden -> unauthorizedBody
                        AppError.NotFound -> notFoundBody
                        else -> unknownBody
                    }
                    snackbarHostState.showSnackbar(message)
                }
            }
        }
    }

    EduScaffold(
        title = if (showingTests) stringResource(R.string.st03_quick_quizzes) else lesson?.title.orEmpty(),
        onBack = { if (showingTests) quickAccess = null else onBack() },
        snackbarHostState = snackbarHostState,
        modifier = modifier,
    ) {
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { SkeletonDetail(modifier = Modifier.padding(Spacing.gutter)) },
            modifier = Modifier.fillMaxSize(),
        ) { loadedLesson ->
            if (loadedLesson.status == LessonStatus.Draft || loadedLesson.status == LessonStatus.Processing) {
                MessageState(
                    icon = Icons.Filled.HourglassTop,
                    title = stringResource(R.string.st03_processing_title),
                    body = stringResource(R.string.st03_processing_body),
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                LessonContent(
                    lesson = loadedLesson,
                    state = state,
                    quickAccess = quickAccess,
                    onQuickAccessChange = { quickAccess = it },
                    onPreviousPage = viewModel::previousPage,
                    onNextPage = viewModel::nextPage,
                    onToggleZoom = viewModel::toggleZoom,
                    onTogglePlayback = viewModel::togglePlayback,
                    onSeek = viewModel::seekTo,
                    onCycleSpeed = viewModel::cyclePlaybackSpeed,
                    onToggleCaptions = viewModel::toggleCaptions,
                    onStartDownload = viewModel::startDownload,
                    onOpenPdf = viewModel::openPdfFile,
                    onOpenVideo = viewModel::openVideoFile,
                    onOpenAudio = viewModel::openAudioFile,
                    onOpenHomework = viewModel::openHomeworkFile,
                    onBackToCourse = onBackToCourse,
                    onAskTutor = onAskTutor,
                    onAskTutorWithPrompt = onAskTutorWithPrompt,
                    onTakeQuiz = onTakeQuiz,
                    onOpenQuizResults = onOpenQuizResults,
                    onMarkComplete = { showCompletionSheet = true },
                    onConceptTap = { concept -> conceptSheetFor = concept },
                )
            }
        }
    }

    val concept = conceptSheetFor
    if (concept != null && lesson != null) {
        ConceptActionSheet(
            concept = concept,
            lesson = lesson,
            onDismiss = { conceptSheetFor = null },
            onAskTutorWithPrompt = { prompt ->
                conceptSheetFor = null
                onAskTutorWithPrompt(prompt)
            },
            onTakeQuiz = { quizId ->
                conceptSheetFor = null
                onTakeQuiz(quizId)
            },
        )
    }

    if (showCompletionSheet && lesson != null) {
        LessonCompletionSheet(
            checklist = viewModel.buildCompletionChecklist(),
            onDismiss = { showCompletionSheet = false },
            onConfirm = {
                showCompletionSheet = false
                viewModel.markComplete()
            },
        )
    }
}

/** "1" not "1.0" for whole speeds; "1.25" kept as-is otherwise. */
private fun formatSpeed(speed: Float): String {
    val whole = speed.toInt()
    return if (speed == whole.toFloat()) whole.toString() else speed.toString()
}

/** Video first (richest surface), then PDF, then audio-only — see the file doc comment. */
private fun LessonDetail.primaryMediaType(): LessonMediaType = when {
    LessonMediaType.Video in mediaTypes -> LessonMediaType.Video
    LessonMediaType.Pdf in mediaTypes -> LessonMediaType.Pdf
    else -> LessonMediaType.Audio
}

private fun LessonDetail.availableMediaTypes(): List<LessonMediaType> = buildList {
    if (LessonMediaType.Video in mediaTypes) add(LessonMediaType.Video)
    if (LessonMediaType.Pdf in mediaTypes) add(LessonMediaType.Pdf)
    if (LessonMediaType.Audio in mediaTypes) add(LessonMediaType.Audio)
}

private enum class LessonPhaseKind { Teacher, Understand, Example, Try, QuickCheck, Finish }

private enum class LessonQuickAccess { Video, FileSummary, Quizzes }

@Composable
private fun LessonContent(
    lesson: LessonDetail,
    state: LessonPlayerUiState,
    quickAccess: String?,
    onQuickAccessChange: (String?) -> Unit,
    onPreviousPage: () -> Unit,
    onNextPage: () -> Unit,
    onToggleZoom: () -> Unit,
    onTogglePlayback: () -> Unit,
    onSeek: (Float) -> Unit,
    onCycleSpeed: () -> Unit,
    onToggleCaptions: () -> Unit,
    onStartDownload: () -> Unit,
    onOpenPdf: () -> Unit,
    onOpenVideo: () -> Unit,
    onOpenAudio: () -> Unit,
    onOpenHomework: () -> Unit,
    onBackToCourse: (courseId: String) -> Unit,
    onAskTutor: () -> Unit,
    onAskTutorWithPrompt: (prompt: String) -> Unit,
    onTakeQuiz: (quizId: String) -> Unit,
    onOpenQuizResults: (quizId: String) -> Unit,
    onMarkComplete: () -> Unit,
    onConceptTap: (String) -> Unit,
) {
    val quizSession = state.quizSession
    val contentEngaged = state.currentPage > 1 || state.positionFraction > 0f || lesson.isCompleted
    val quizProgress = quizSession?.let { if (it.totalCount == 0) 0f else it.answeredCount / it.totalCount.toFloat() } ?: 0f
    val availableMedia = lesson.availableMediaTypes()
    val phases = remember(availableMedia) {
        buildList {
            if (availableMedia.isNotEmpty()) add(LessonPhaseKind.Teacher)
            add(LessonPhaseKind.Understand)
            add(LessonPhaseKind.Example)
            add(LessonPhaseKind.Try)
            add(LessonPhaseKind.QuickCheck)
            add(LessonPhaseKind.Finish)
        }
    }
    var phaseIndex by rememberSaveable(lesson.id) { mutableStateOf(0) }
    val currentPhase = phases.getOrElse(phaseIndex) { phases.last() }
    var selectedMediaName by rememberSaveable(lesson.id) {
        mutableStateOf(availableMedia.firstOrNull()?.name.orEmpty())
    }
    var pdfOpened by rememberSaveable(lesson.id) { mutableStateOf(false) }
    var showMaterialSheet by rememberSaveable(lesson.id) { mutableStateOf(false) }
    var quickCheckSelected by rememberSaveable(lesson.id) { mutableStateOf<Int?>(null) }
    val selectedQuickAccess = LessonQuickAccess.entries.firstOrNull { it.name == quickAccess }
    val showingTests = selectedQuickAccess == LessonQuickAccess.Quizzes
    val hasVideo = LessonMediaType.Video in lesson.mediaTypes
    val selectedMedia = availableMedia.firstOrNull { it.name == selectedMediaName }
        ?: availableMedia.firstOrNull()
    val phaseTitle = when (currentPhase) {
        LessonPhaseKind.Teacher -> stringResource(R.string.st03_phase_teacher)
        LessonPhaseKind.Understand -> stringResource(R.string.st03_phase_understand)
        LessonPhaseKind.Example -> stringResource(R.string.st03_phase_example)
        LessonPhaseKind.Try -> stringResource(R.string.st03_phase_try)
        LessonPhaseKind.QuickCheck -> stringResource(R.string.st03_phase_quick_check)
        LessonPhaseKind.Finish -> stringResource(R.string.st03_phase_finish)
    }
    val mediaPanel: @Composable () -> Unit = {
        if (selectedMedia != null) {
            LessonTeacherMediaPanel(
                lesson = lesson,
                state = state,
                availableMedia = availableMedia,
                selectedMedia = selectedMedia,
                pdfOpened = pdfOpened,
                onSelectMedia = { selectedMediaName = it.name },
                onOpenPdf = {
                    pdfOpened = true
                    onOpenPdf()
                },
                onOpenVideo = onOpenVideo,
                onOpenAudio = onOpenAudio,
                onOpenHomework = onOpenHomework,
                onPreviousPage = onPreviousPage,
                onNextPage = onNextPage,
                onToggleZoom = onToggleZoom,
                onTogglePlayback = onTogglePlayback,
                onSeek = onSeek,
                onCycleSpeed = onCycleSpeed,
                onToggleCaptions = onToggleCaptions,
            )
        }
    }

    if (showingTests) {
        LessonTestsPanel(
            lesson = lesson,
            quizSession = quizSession,
            quickCheckCompleted = quickCheckSelected != null,
            onOpenQuickCheck = {
                val index = phases.indexOf(LessonPhaseKind.QuickCheck)
                if (index >= 0) phaseIndex = index
                onQuickAccessChange(null)
            },
            onTakeQuiz = onTakeQuiz,
            onOpenQuizResults = onOpenQuizResults,
            modifier = Modifier.fillMaxSize(),
        )
        return
    }

    Column(modifier = Modifier.fillMaxSize()) {
        LessonPhaseHeader(
            lesson = lesson,
            phaseIndex = phaseIndex.coerceAtMost(phases.lastIndex),
            phaseTitle = phaseTitle,
            totalPhases = phases.size,
            onBackToCourse = { onBackToCourse(lesson.courseId) },
            onOpenLessonMaterial = if (availableMedia.isNotEmpty() && currentPhase != LessonPhaseKind.Teacher) {
                { showMaterialSheet = true }
            } else {
                null
            },
        )
        LessonQuickAccessRow(
            hasVideo = hasVideo,
            selected = selectedQuickAccess,
            onSelect = { access ->
                if (access == LessonQuickAccess.Video && hasVideo) {
                    selectedMediaName = LessonMediaType.Video.name
                }
                if (access == LessonQuickAccess.FileSummary && LessonMediaType.Pdf in lesson.mediaTypes) {
                    selectedMediaName = LessonMediaType.Pdf.name
                }
                onQuickAccessChange(access.name)
            },
            onAskEduMind = onAskTutor,
        )
        LazyColumn(
            contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.section),
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
        ) {
            item {
                AnimatedContent(
                    targetState = currentPhase,
                    transitionSpec = {
                        fadeIn(tween(Motion.STANDARD_MS)) togetherWith fadeOut(tween(Motion.QUICK_MS))
                    },
                    label = "lessonPhase",
                ) { phase ->
                    when (phase) {
                        LessonPhaseKind.Teacher -> mediaPanel()
                        LessonPhaseKind.Understand -> LessonConceptPhase(lesson = lesson, onConceptTap = onConceptTap)
                        LessonPhaseKind.Example -> LessonExamplePhase(lesson = lesson)
                        LessonPhaseKind.Try -> LessonTryPhase(lesson = lesson, onSeek = onSeek)
                        LessonPhaseKind.QuickCheck -> LessonQuickCheckPhase(
                            lesson = lesson,
                            quizSession = quizSession,
                            quizProgress = quizProgress,
                            selected = quickCheckSelected,
                            onSelect = { quickCheckSelected = it },
                            onTakeQuiz = onTakeQuiz,
                            onOpenQuizResults = onOpenQuizResults,
                            onAskTutorWithPrompt = onAskTutorWithPrompt,
                        )
                        LessonPhaseKind.Finish -> CompletionGateCard(
                            checklist = LessonCompletionChecklist(
                                contentEngaged = contentEngaged,
                                quizRequired = lesson.quizId != null,
                                quizCompleted = quizSession?.isCompleted == true,
                            ),
                            isCompleted = lesson.isCompleted,
                            onMarkComplete = onMarkComplete,
                        )
                    }
                }
            }
            if (currentPhase == LessonPhaseKind.Finish) {
                item {
                    DownloadRow(state = state, onStartDownload = onStartDownload)
                    if (lesson.isCompleted) {
                        NextLessonActionCard(
                            lesson = lesson,
                            onBackToCourse = { onBackToCourse(lesson.courseId) },
                        )
                    }
                }
            }
        }
        LessonPhaseBottomBar(
            lesson = lesson,
            phaseIndex = phaseIndex.coerceAtMost(phases.lastIndex),
            phaseCount = phases.size,
            quizCompleted = quizSession?.isCompleted == true,
            onAskTutor = onAskTutor,
            onTakeQuiz = onTakeQuiz,
            onMarkComplete = onMarkComplete,
            onNext = {
                if (phaseIndex == 0) onSeek(0.18f)
                phaseIndex = (phaseIndex + 1).coerceAtMost(phases.lastIndex)
            },
        )
    }

    if (showMaterialSheet && availableMedia.isNotEmpty()) {
        LessonMaterialSheet(
            onDismiss = { showMaterialSheet = false },
            content = mediaPanel,
        )
    }

    if (selectedQuickAccess == LessonQuickAccess.Video || selectedQuickAccess == LessonQuickAccess.FileSummary) {
        LessonQuickAccessSheet(
            access = selectedQuickAccess,
            onDismiss = { onQuickAccessChange(null) },
        ) {
            when (selectedQuickAccess) {
                LessonQuickAccess.Video -> LessonVideoQuickPanel(
                    lesson = lesson,
                    state = state,
                    onTogglePlayback = onTogglePlayback,
                    onSeek = onSeek,
                    onCycleSpeed = onCycleSpeed,
                    onToggleCaptions = onToggleCaptions,
                )
                LessonQuickAccess.FileSummary -> LessonFileSummaryPanel(
                    lesson = lesson,
                    state = state,
                    pdfOpened = pdfOpened,
                    onOpenPdf = {
                        pdfOpened = true
                        onOpenPdf()
                    },
                    onPreviousPage = onPreviousPage,
                    onNextPage = onNextPage,
                    onToggleZoom = onToggleZoom,
                )
                LessonQuickAccess.Quizzes -> Unit
            }
        }
    }
}

@Composable
private fun LessonPhaseHeader(
    lesson: LessonDetail,
    phaseIndex: Int,
    phaseTitle: String,
    totalPhases: Int,
    onBackToCourse: () -> Unit,
    onOpenLessonMaterial: (() -> Unit)? = null,
) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            EduIconButton(
                icon = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = stringResource(R.string.st03_nav_back_to_course),
                onClick = onBackToCourse,
                modifier = Modifier.mirrorInRtl(),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = lesson.title,
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    maxLines = 1,
                )
                Text(
                    text = stringResource(R.string.st03_phase_count, numeral(phaseIndex + 1), numeral(totalPhases), phaseTitle),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    color = colors.textSecondary,
                )
                if (onOpenLessonMaterial != null) {
                    Text(
                        text = stringResource(R.string.st03_lesson_material),
                        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                        color = colors.primary,
                        modifier = Modifier.eduClickable(
                            onClickLabel = stringResource(R.string.st03_lesson_material),
                            onClick = onOpenLessonMaterial,
                        ),
                    )
                }
            }
        }
        LessonPhaseSegments(currentIndex = phaseIndex, total = totalPhases, modifier = Modifier.padding(top = Spacing.sm))
    }
}

@Composable
private fun LessonPhaseSegments(currentIndex: Int, total: Int, modifier: Modifier = Modifier) {
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = modifier.fillMaxWidth()) {
        repeat(total) { index ->
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(5.dp)
                    .background(
                        if (index <= currentIndex) EduTheme.colors.primary else EduTheme.colors.border,
                        RoundedCornerShape(Radius.pill),
                    ),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LessonMaterialSheet(
    onDismiss: () -> Unit,
    content: @Composable () -> Unit,
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = EduTheme.colors.surface,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
        ) {
            SheetHandle(modifier = Modifier.padding(bottom = Spacing.md))
            Text(
                text = stringResource(R.string.st03_lesson_material),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.textPrimary,
            )
            Box(modifier = Modifier.padding(top = Spacing.md)) {
                content()
            }
        }
    }
}

@Composable
private fun LessonQuickAccessRow(
    hasVideo: Boolean,
    selected: LessonQuickAccess?,
    onSelect: (LessonQuickAccess) -> Unit,
    onAskEduMind: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(horizontal = Spacing.gutter, vertical = Spacing.xs),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
            LessonQuickAccessTile(
                label = stringResource(R.string.st03_media_video),
                icon = Icons.Filled.PlayArrow,
                selected = selected == LessonQuickAccess.Video,
                enabled = hasVideo,
                onClick = { onSelect(LessonQuickAccess.Video) },
                modifier = Modifier.weight(1f),
            )
            LessonQuickAccessTile(
                label = stringResource(R.string.st03_quick_file_summary),
                icon = Icons.Filled.Description,
                selected = selected == LessonQuickAccess.FileSummary,
                enabled = true,
                onClick = { onSelect(LessonQuickAccess.FileSummary) },
                modifier = Modifier.weight(1f),
            )
            LessonQuickAccessTile(
                label = stringResource(R.string.st03_quick_quizzes),
                icon = Icons.Filled.Quiz,
                selected = selected == LessonQuickAccess.Quizzes,
                enabled = true,
                onClick = { onSelect(LessonQuickAccess.Quizzes) },
                modifier = Modifier.weight(1f),
            )
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier
                .fillMaxWidth()
                .defaultMinSize(minHeight = Sizing.touchTarget)
                .background(colors.aiAccentContainer, RoundedCornerShape(Radius.sm))
                .eduClickable(onClickLabel = stringResource(R.string.st03_ask_edumind), onClick = onAskEduMind)
                .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
        ) {
            Icon(
                imageVector = Icons.Filled.AutoAwesome,
                contentDescription = null,
                tint = colors.aiAccent,
                modifier = Modifier.size(Sizing.icon),
            )
            Text(
                text = stringResource(R.string.st03_ask_edumind),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = colors.aiAccent,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun LessonQuickAccessTile(
    label: String,
    icon: ImageVector,
    selected: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .background(
                when {
                    !enabled -> colors.neutralAlpha100
                    selected -> colors.primary
                    else -> colors.primaryContainer
                },
                RoundedCornerShape(Radius.sm),
            )
            .then(
                if (enabled) Modifier.eduClickable(onClickLabel = label, onClick = onClick)
                else Modifier
            )
            .padding(horizontal = Spacing.xxs, vertical = Spacing.xs),
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = when {
                !enabled -> colors.textTertiary
                selected -> colors.onPrimary
                else -> colors.primary
            },
            modifier = Modifier.size(Sizing.icon),
        )
        Text(
            text = label,
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = when {
                !enabled -> colors.textTertiary
                selected -> colors.onPrimary
                else -> colors.primary
            },
            textAlign = TextAlign.Center,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun LessonTestsPanel(
    lesson: LessonDetail,
    quizSession: LessonQuizSession?,
    quickCheckCompleted: Boolean,
    onOpenQuickCheck: () -> Unit,
    onTakeQuiz: (quizId: String) -> Unit,
    onOpenQuizResults: (quizId: String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val quizId = lesson.quizId
    val quizCompleted = quizSession?.isCompleted == true
    Box(
        modifier = modifier
            .fillMaxSize()
            .background(colors.surface),
    ) {
        Column(
            verticalArrangement = Arrangement.spacedBy(Spacing.md),
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.gutter, vertical = Spacing.section),
        ) {
            LessonTestItemCard(
                title = stringResource(R.string.st03_phase_quick_check),
                completed = quickCheckCompleted,
                details = emptyList(),
                actionLabel = if (quickCheckCompleted) {
                    stringResource(R.string.st03_open_quick_check)
                } else {
                    stringResource(R.string.st03_start_quick_check)
                },
                onAction = onOpenQuickCheck,
            )
            if (quizId != null) {
                val questionCount = quizSession?.totalCount?.takeIf { it > 0 }
                val questionLabel = questionCount?.let {
                    stringResource(R.string.st03_quiz_questions, numeral(it))
                }
                val requiredLabel = stringResource(R.string.st03_quiz_required_label)
                LessonTestItemCard(
                    title = stringResource(R.string.st03_open_full_quiz),
                    completed = quizCompleted,
                    details = listOfNotNull(questionLabel, requiredLabel),
                    actionLabel = if (quizCompleted) {
                        stringResource(R.string.st03_view_quiz_result)
                    } else {
                        stringResource(R.string.st03_take_quiz)
                    },
                    onAction = {
                        if (quizCompleted) onOpenQuizResults(quizId) else onTakeQuiz(quizId)
                    },
                )
            }
            val completedStatus = stringResource(R.string.st03_test_completed)
            val completedBits = listOfNotNull(
                if (quickCheckCompleted) {
                    "${stringResource(R.string.st03_phase_quick_check)} · $completedStatus"
                } else {
                    null
                },
                if (quizCompleted) {
                    "${stringResource(R.string.st03_open_full_quiz)} · $completedStatus"
                } else {
                    null
                },
            )
            if (completedBits.isNotEmpty()) {
                Text(
                    text = completedBits.joinToString("  ·  "),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun LessonTestItemCard(
    title: String,
    completed: Boolean,
    details: List<String>,
    actionLabel: String,
    onAction: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard(
        modifier = Modifier.defaultMinSize(minHeight = 148.dp),
    ) {
        Text(
            text = title,
            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            verticalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.sm),
        ) {
            StatusPill(
                label = stringResource(
                    if (completed) R.string.st03_test_completed else R.string.st03_test_not_started,
                ),
                contentColor = if (completed) colors.success else colors.textSecondary,
                containerColor = if (completed) colors.success.copy(alpha = 0.12f) else colors.neutralAlpha100,
            )
            details.forEach { detail ->
                StatusPill(
                    label = detail,
                    contentColor = colors.textSecondary,
                    containerColor = colors.neutralAlpha100,
                )
            }
        }
        PrimaryButton(
            text = actionLabel,
            onClick = onAction,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LessonQuickAccessSheet(
    access: LessonQuickAccess,
    onDismiss: () -> Unit,
    content: @Composable () -> Unit,
) {
    val title = when (access) {
        LessonQuickAccess.Video -> stringResource(R.string.st03_media_video)
        LessonQuickAccess.FileSummary -> stringResource(R.string.st03_quick_file_summary)
        LessonQuickAccess.Quizzes -> stringResource(R.string.st03_quick_quizzes)
    }
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = EduTheme.colors.surface,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
        ) {
            SheetHandle(modifier = Modifier.padding(bottom = Spacing.md))
            Text(
                text = title,
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.textPrimary,
            )
            Box(modifier = Modifier.padding(top = Spacing.md)) {
                content()
            }
        }
    }
}

@Composable
private fun LessonVideoQuickPanel(
    lesson: LessonDetail,
    state: LessonPlayerUiState,
    onTogglePlayback: () -> Unit,
    onSeek: (Float) -> Unit,
    onCycleSpeed: () -> Unit,
    onToggleCaptions: () -> Unit,
) {
    val colors = EduTheme.colors
    if (LessonMediaType.Video !in lesson.mediaTypes) {
        Text(
            text = stringResource(R.string.st03_no_video),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
        )
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        VideoSurface(state, onTogglePlayback, onSeek, onCycleSpeed, onToggleCaptions)
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Text(
                text = stringResource(R.string.st03_play_video),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = colors.primary,
                modifier = Modifier.eduClickable(
                    onClickLabel = stringResource(R.string.st03_play_video),
                    onClick = onTogglePlayback,
                ),
            )
            Text(
                text = stringResource(R.string.st03_media_clock, numeral(lesson.durationMinutes)),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
        }
    }
}

@Composable
private fun LessonFileSummaryPanel(
    lesson: LessonDetail,
    state: LessonPlayerUiState,
    pdfOpened: Boolean,
    onOpenPdf: () -> Unit,
    onPreviousPage: () -> Unit,
    onNextPage: () -> Unit,
    onToggleZoom: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
        Text(
            text = stringResource(R.string.st03_teacher_source),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textSecondary,
        )
        if (LessonMediaType.Pdf in lesson.mediaTypes) {
            if (pdfOpened) {
                PdfSurface(lesson, state, onPreviousPage, onNextPage, onToggleZoom)
            } else {
                LessonPdfPreviewCard(lesson = lesson, onOpen = onOpenPdf)
            }
        } else {
            Text(
                text = stringResource(R.string.st03_no_document),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
            )
        }
        Text(
            text = stringResource(R.string.st03_edumind_summary),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.aiAccent,
        )
        lesson.keyIdeas.take(3).forEach { idea ->
            Row(
                verticalAlignment = Alignment.Top,
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            ) {
                Icon(
                    imageVector = Icons.Filled.AutoAwesome,
                    contentDescription = null,
                    tint = colors.aiAccent,
                    modifier = Modifier.size(Sizing.iconSm),
                )
                Text(
                    text = idea,
                    style = EduTheme.typography.body,
                    color = colors.textPrimary,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun LessonTeacherMediaPanel(
    lesson: LessonDetail,
    state: LessonPlayerUiState,
    availableMedia: List<LessonMediaType>,
    selectedMedia: LessonMediaType,
    pdfOpened: Boolean,
    onSelectMedia: (LessonMediaType) -> Unit,
    onOpenPdf: () -> Unit,
    onOpenVideo: () -> Unit,
    onOpenAudio: () -> Unit,
    onOpenHomework: () -> Unit,
    onPreviousPage: () -> Unit,
    onNextPage: () -> Unit,
    onToggleZoom: () -> Unit,
    onTogglePlayback: () -> Unit,
    onSeek: (Float) -> Unit,
    onCycleSpeed: () -> Unit,
    onToggleCaptions: () -> Unit,
) {
    val colors = EduTheme.colors
        val attachmentNames = buildList {
            if (!lesson.homeworkUrl.isNullOrBlank()) {
                add(
                    lesson.homeworkUrl.substringAfterLast('/')
                        .ifBlank { stringResource(R.string.tc17_media_document) },
                )
            }
        }
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.primary, CircleShape),
            ) {
                Text(
                    text = lesson.teacherName.take(1),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.onPrimary,
                )
            }
            Text(
                text = stringResource(R.string.st03_teacher_explain, lesson.teacherName),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
                maxLines = 2,
                modifier = Modifier.weight(1f),
            )
        }
        if (availableMedia.size > 1) {
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
                availableMedia.forEach { type ->
                    LessonMediaChip(
                        label = type.selectorLabel(),
                        selected = type == selectedMedia,
                        onClick = { onSelectMedia(type) },
                    )
                }
            }
        }
        when (selectedMedia) {
            LessonMediaType.Video -> {
                VideoSurface(state, onTogglePlayback, onSeek, onCycleSpeed, onToggleCaptions)
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                ) {
                    Text(
                        text = stringResource(R.string.st03_play_video),
                        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                        color = colors.primary,
                        modifier = Modifier.eduClickable(
                            onClickLabel = stringResource(R.string.st03_play_video),
                            onClick = {
                                if (!lesson.videoUrl.isNullOrBlank()) onOpenVideo()
                                else onTogglePlayback()
                            },
                        ),
                    )
                    Text(
                        text = stringResource(R.string.st03_media_clock, numeral(lesson.durationMinutes)),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
            }
            LessonMediaType.Pdf -> {
                if (pdfOpened) {
                    PdfSurface(lesson, state, onPreviousPage, onNextPage, onToggleZoom)
                } else {
                    LessonPdfPreviewCard(lesson = lesson, onOpen = onOpenPdf)
                }
            }
            LessonMediaType.Audio -> {
                AudioSurface(lesson, state, onTogglePlayback, onSeek, showTranscript = false)
                Text(
                    text = stringResource(R.string.st03_media_clock, numeral(lesson.durationMinutes)),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.textSecondary,
                    modifier = if (!lesson.audioUrl.isNullOrBlank()) {
                        Modifier.eduClickable(
                            onClickLabel = stringResource(R.string.st03_media_audio),
                            onClick = onOpenAudio,
                        )
                    } else {
                        Modifier
                    },
                )
            }
        }
        LessonAttachmentsRow(
            names = attachmentNames,
            onOpen = if (!lesson.homeworkUrl.isNullOrBlank()) onOpenHomework else null,
        )
    }
}

@Composable
private fun LessonAttachmentsRow(
    names: List<String>,
    onOpen: (() -> Unit)? = null,
) {
    if (names.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xxs)) {
        Text(
            text = stringResource(R.string.st03_attachments_title),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textTertiary,
        )
        names.forEach { name ->
            Text(
                text = name,
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                modifier = if (onOpen != null) {
                    Modifier.eduClickable(onClickLabel = name, onClick = onOpen)
                } else {
                    Modifier
                },
            )
        }
    }
}

@Composable
private fun LessonMediaType.selectorLabel(): String = stringResource(
    when (this) {
        LessonMediaType.Video -> R.string.st03_media_video
        LessonMediaType.Pdf -> R.string.st03_media_pdf
        LessonMediaType.Audio -> R.string.st03_media_audio
    },
)

@Composable
private fun LessonMediaChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    Text(
        text = label,
        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
        color = if (selected) colors.primary else colors.textSecondary,
        modifier = Modifier
            .background(if (selected) colors.primaryContainer else colors.surface, RoundedCornerShape(Radius.pill))
            .border(Sizing.hairline, if (selected) colors.primary else colors.border, RoundedCornerShape(Radius.pill))
            .eduClickable(onClickLabel = label, onClick = onClick)
            .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
    )
}

@Composable
private fun LessonPdfPreviewCard(lesson: LessonDetail, onOpen: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(1.4f)
                .background(colors.background, RoundedCornerShape(Radius.sm)),
        ) {
            Icon(
                imageVector = Icons.Filled.Description,
                contentDescription = null,
                tint = colors.primary,
                modifier = Modifier.size(Sizing.stateIcon),
            )
        }
        Text(
            text = stringResource(R.string.st03_pdf_filename, lesson.title),
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        if (lesson.pageCount > 0) {
            Text(
                text = stringResource(R.string.st03_pdf_pages, numeral(lesson.pageCount)),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
        SecondaryButton(
            text = stringResource(R.string.st03_open_file),
            onClick = onOpen,
            leadingIcon = Icons.Filled.Description,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun LessonConceptPhase(lesson: LessonDetail, onConceptTap: (String) -> Unit) {
    LessonPhaseCard(
        badge = stringResource(R.string.st03_phase_understand),
        title = lesson.title,
        body = lesson.keyIdeas.firstOrNull() ?: lesson.learnGuideText(),
        courseId = lesson.courseId,
    )
}

@Composable
private fun LessonExamplePhase(lesson: LessonDetail) {
    LessonPhaseCard(
        badge = stringResource(R.string.st03_phase_example),
        title = stringResource(R.string.st03_example_title, lesson.title),
        body = stringResource(R.string.st03_example_body),
        courseId = lesson.courseId,
    ) {
        FormulaStrip(text = if (lesson.courseId == "physics") stringResource(R.string.st03_formula_physics) else stringResource(R.string.st03_formula_math))
    }
}

@Composable
private fun LessonTryPhase(
    lesson: LessonDetail,
    onSeek: (Float) -> Unit,
) {
    val (correct, wrong) = if (lesson.courseId.contains("math", ignoreCase = true)) {
        stringResource(R.string.st03_try_math_correct) to stringResource(R.string.st03_try_math_wrong)
    } else {
        stringResource(R.string.st03_try_physics_correct) to stringResource(R.string.st03_try_physics_wrong)
    }
    var selectedCorrect by rememberSaveable(lesson.id) { mutableStateOf<Boolean?>(null) }
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
        LessonPhaseCard(
            badge = stringResource(R.string.st03_phase_try),
            title = stringResource(R.string.st03_try_prompt),
            body = stringResource(R.string.st03_try_title),
            courseId = lesson.courseId,
            compactVisual = true,
        )
        PracticeChoice(
            text = correct,
            selected = selectedCorrect == true,
            tone = when (selectedCorrect) {
                true -> PracticeTone.Success
                else -> PracticeTone.Neutral
            },
            onClick = {
                selectedCorrect = true
                onSeek(0.28f)
            },
        )
        PracticeChoice(
            text = wrong,
            selected = selectedCorrect == false,
            tone = when (selectedCorrect) {
                false -> PracticeTone.Danger
                else -> PracticeTone.Neutral
            },
            onClick = {
                selectedCorrect = false
                onSeek(0.12f)
            },
        )
        selectedCorrect?.let { correctPick ->
            Text(
                text = stringResource(if (correctPick) R.string.st03_try_correct else R.string.st03_try_incorrect),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = if (correctPick) EduTheme.colors.success else EduTheme.colors.danger,
            )
        }
    }
}

private enum class PracticeTone { Neutral, Success, Danger }

@Composable
private fun PracticeChoice(
    text: String,
    selected: Boolean,
    tone: PracticeTone,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val border = when (tone) {
        PracticeTone.Success -> colors.success
        PracticeTone.Danger -> colors.danger
        PracticeTone.Neutral -> if (selected) colors.primary else colors.border
    }
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface, RoundedCornerShape(Radius.md))
            .border(Sizing.hairline, border, RoundedCornerShape(Radius.md))
            .eduClickable(onClickLabel = text, onClick = onClick)
            .padding(Spacing.sm),
    ) {
        Text(
            text = text,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
            color = colors.textPrimary,
        )
    }
}

@Composable
private fun LessonQuickCheckPhase(
    lesson: LessonDetail,
    quizSession: LessonQuizSession?,
    quizProgress: Float,
    selected: Int?,
    onSelect: (Int) -> Unit,
    onTakeQuiz: (quizId: String) -> Unit,
    onOpenQuizResults: (quizId: String) -> Unit,
    onAskTutorWithPrompt: (prompt: String) -> Unit,
) {
    val quizId = lesson.quizId
    val correct = lesson.keyIdeas.firstOrNull() ?: lesson.title
    val wrong = lesson.keyIdeas.getOrNull(1) ?: stringResource(R.string.st03_quick_check_wrong)
    val options = listOf(correct, wrong, stringResource(R.string.st03_quick_check_wrong))
    EduCard {
        StatusPill(label = stringResource(R.string.st03_phase_quick_check), contentColor = EduTheme.colors.primary, containerColor = EduTheme.colors.primaryContainer)
        SubjectVisual(
            courseId = lesson.courseId,
            compact = true,
            fillWidth = false,
            modifier = Modifier
                .padding(top = Spacing.md)
                .size(88.dp)
                .align(Alignment.CenterHorizontally),
        )
        Text(
            text = stringResource(R.string.st03_quick_check_local_prompt),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.md),
        )
        Column(
            verticalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.md),
        ) {
            options.forEachIndexed { index, option ->
                val isCorrect = index == 0
                val isSelected = selected == index
                PracticeChoice(
                    text = option,
                    selected = isSelected,
                    tone = when {
                        selected == null -> PracticeTone.Neutral
                        isSelected && isCorrect -> PracticeTone.Success
                        isSelected -> PracticeTone.Danger
                        selected != null && isCorrect -> PracticeTone.Success
                        else -> PracticeTone.Neutral
                    },
                    onClick = { onSelect(index) },
                )
            }
        }
        if (quizId != null) {
            GhostButton(
                text = if (quizSession?.isCompleted == true) {
                    stringResource(R.string.st03_review_quiz_results)
                } else {
                    stringResource(R.string.st03_open_full_quiz)
                },
                onClick = { if (quizSession?.isCompleted == true) onOpenQuizResults(quizId) else onTakeQuiz(quizId) },
                leadingIcon = Icons.Filled.Quiz,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }
    }
}

@Composable
private fun LessonPhaseCard(
    badge: String,
    title: String,
    body: String,
    courseId: String,
    compactVisual: Boolean = false,
    content: @Composable (() -> Unit)? = null,
) {
    EduCard(contentPadding = PaddingValues(0.dp)) {
        SubjectVisual(courseId = courseId, compact = compactVisual)
        Column(modifier = Modifier.padding(Spacing.card)) {
            StatusPill(label = badge, contentColor = EduTheme.colors.accent, containerColor = EduTheme.colors.accentContainer)
            Text(
                text = title,
                style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = body,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
            content?.invoke()
        }
    }
}

@Composable
private fun FormulaStrip(text: String) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.md)
            .background(EduTheme.colors.textPrimary, RoundedCornerShape(Radius.md))
            .padding(vertical = Spacing.md),
    ) {
        Text(text = text, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.surface)
    }
}

@Composable
private fun LessonPhaseBottomBar(
    lesson: LessonDetail,
    phaseIndex: Int,
    phaseCount: Int,
    quizCompleted: Boolean,
    onAskTutor: () -> Unit,
    onTakeQuiz: (quizId: String) -> Unit,
    onMarkComplete: () -> Unit,
    onNext: () -> Unit,
) {
    val isLast = phaseIndex == phaseCount - 1
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(EduTheme.colors.surface)
            .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
    ) {
        EduIconButton(icon = Icons.Filled.Chat, contentDescription = stringResource(R.string.st03_ask_tutor), onClick = onAskTutor)
        PrimaryButton(
            text = when {
                isLast -> stringResource(R.string.st03_mark_complete)
                else -> stringResource(R.string.common_next)
            },
            onClick = if (isLast) onMarkComplete else onNext,
            modifier = Modifier.weight(1f),
        )
    }
}

private enum class LessonSessionTab { Ask, Quiz }

@Composable
private fun LessonCourseNavCard(lesson: LessonDetail, onBackToCourse: () -> Unit) {
    EduCard(contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xs)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            GhostButton(
                text = stringResource(R.string.st03_nav_back_to_course),
                onClick = onBackToCourse,
                leadingIcon = Icons.AutoMirrored.Filled.KeyboardArrowRight,
            )
            Text(
                text = stringResource(R.string.st03_context, lesson.courseTitle, lesson.lessonIndex, lesson.lessonTotal),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun LessonSessionHeaderCard(
    lesson: LessonDetail,
    progress: Float,
    quizSession: LessonQuizSession?,
    contentEngaged: Boolean,
    onAskTutor: () -> Unit,
    onTakeQuiz: () -> Unit,
    onOpenQuizResults: () -> Unit,
    onMarkComplete: () -> Unit,
) {
    val colors = EduTheme.colors
    val percent = (progress * 100).toInt().coerceIn(0, 100)
    val quizDone = quizSession?.isCompleted == true
    val nextText = when {
        lesson.isCompleted -> stringResource(R.string.st03_next_completed)
        quizDone -> stringResource(R.string.st03_next_finish)
        lesson.quizId != null && contentEngaged -> stringResource(R.string.st03_next_take_quiz)
        contentEngaged -> stringResource(R.string.st03_next_ask_teacher)
        else -> stringResource(R.string.st03_next_watch_or_read)
    }
    val nextCta = when {
        lesson.isCompleted -> null
        quizDone -> stringResource(R.string.st03_mark_complete)
        lesson.quizId != null && contentEngaged -> stringResource(R.string.st03_take_quiz)
        contentEngaged -> stringResource(R.string.st03_ask_tutor)
        else -> null
    }
    val nextAction = when {
        lesson.isCompleted -> null
        quizDone -> onMarkComplete
        lesson.quizId != null && contentEngaged -> onTakeQuiz
        contentEngaged -> onAskTutor
        else -> null
    }

    EduCard(borderColor = colors.primary.copy(alpha = 0.22f)) {
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(72.dp)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(
                    text = lesson.teacherName.take(1),
                    style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.primary,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = lesson.teacherName,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                Text(
                    text = lesson.courseTitle,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Text(
                    text = lesson.title,
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
                StatusPill(
                    label = stringResource(R.string.st03_header_position, numeral(lesson.lessonIndex), numeral(lesson.lessonTotal)),
                    contentColor = colors.primary,
                    containerColor = colors.primaryContainer,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }

        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        ) {
            Text(
                text = stringResource(R.string.st03_header_session_progress),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = colors.primary,
            )
            Text(
                text = "$percent%",
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
            )
        }
        EduLinearProgress(progress = progress, modifier = Modifier.padding(top = Spacing.xs))

        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md)
                .background(colors.highlightContainer, RoundedCornerShape(Radius.sm))
                .padding(Spacing.sm),
        ) {
            Icon(Icons.Filled.Flag, contentDescription = null, tint = colors.highlight, modifier = Modifier.size(Sizing.icon))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st03_header_next_step),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.highlight,
                )
                Text(
                    text = nextText,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            if (nextCta != null && nextAction != null) {
                PrimaryButton(text = nextCta, onClick = nextAction)
            } else if (quizDone && lesson.quizId != null) {
                GhostButton(text = stringResource(R.string.st03_review_quiz_results), onClick = onOpenQuizResults)
            }
        }
    }
}

@Composable
private fun LessonLearnIntroCard(lesson: LessonDetail) {
    val colors = EduTheme.colors
    EduCard {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(52.dp)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(text = lesson.teacherName.take(1), style = EduTheme.typography.title, color = colors.primary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st03_learn_eyebrow),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.primary,
                )
                Text(
                    text = stringResource(R.string.st03_learn_title_with_teacher, lesson.teacherName),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = lesson.learnGuideText(),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
    }
}

@Composable
private fun SessionToolsCard(
    lesson: LessonDetail,
    quizSession: LessonQuizSession?,
    selectedTab: LessonSessionTab,
    onSelectTab: (LessonSessionTab) -> Unit,
    onAskTutor: () -> Unit,
    onAskTutorWithPrompt: (prompt: String) -> Unit,
    onTakeQuiz: (quizId: String) -> Unit,
    onOpenQuizResults: (quizId: String) -> Unit,
) {
    EduCard(contentPadding = PaddingValues(0.dp)) {
        Column(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = stringResource(R.string.st03_session_tools_title),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(horizontal = Spacing.card, vertical = Spacing.sm),
            )
            LessonSessionTabs(selectedTab = selectedTab, onSelectTab = onSelectTab)
            Box(modifier = Modifier
                .fillMaxWidth()
                .height(Sizing.hairline)
                .background(EduTheme.colors.border))
            Column(modifier = Modifier.padding(Spacing.card)) {
                if (selectedTab == LessonSessionTab.Ask) {
                    AskTeacherPanel(
                        lesson = lesson,
                        onAskTutor = onAskTutor,
                        onAskTutorWithPrompt = onAskTutorWithPrompt,
                    )
                } else {
                    QuizSessionPanel(
                        lesson = lesson,
                        quizSession = quizSession,
                        onTakeQuiz = onTakeQuiz,
                        onOpenQuizResults = onOpenQuizResults,
                        onAskTutorWithPrompt = onAskTutorWithPrompt,
                    )
                }
            }
        }
    }
}

@Composable
private fun LessonSessionTabs(selectedTab: LessonSessionTab, onSelectTab: (LessonSessionTab) -> Unit) {
    Row(modifier = Modifier.fillMaxWidth()) {
        LessonSessionTabButton(
            label = stringResource(R.string.st03_step_ask),
            icon = Icons.Filled.Chat,
            selected = selectedTab == LessonSessionTab.Ask,
            onClick = { onSelectTab(LessonSessionTab.Ask) },
            modifier = Modifier.weight(1f),
        )
        LessonSessionTabButton(
            label = stringResource(R.string.st03_step_quiz),
            icon = Icons.Filled.Quiz,
            selected = selectedTab == LessonSessionTab.Quiz,
            onClick = { onSelectTab(LessonSessionTab.Quiz) },
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun LessonSessionTabButton(
    label: String,
    icon: ImageVector,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
        modifier = modifier
            .background(if (selected) colors.primaryContainer else colors.surface)
            .eduClickable(onClickLabel = label, onClick = onClick)
            .padding(vertical = Spacing.sm),
    ) {
        Icon(icon, contentDescription = null, tint = if (selected) colors.primary else colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
        Text(
            text = label,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
            color = if (selected) colors.primary else colors.textSecondary,
            modifier = Modifier.padding(start = Spacing.xs),
        )
    }
}

@Composable
private fun AskTeacherPanel(
    lesson: LessonDetail,
    onAskTutor: () -> Unit,
    onAskTutorWithPrompt: (prompt: String) -> Unit,
) {
    val colors = EduTheme.colors
    val explainPrompt = stringResource(R.string.st03_session_ask_summary_prompt, lesson.title)
    val quizPrompt = stringResource(R.string.st03_session_ask_quiz_prompt, lesson.title)
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        InlineAskTutorRow(teacherName = lesson.teacherName, onClick = onAskTutor)
        Text(
            text = stringResource(R.string.st03_session_ask_hint),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
            SecondaryButton(
                text = stringResource(R.string.st03_concept_explain),
                onClick = { onAskTutorWithPrompt(explainPrompt) },
                leadingIcon = Icons.Filled.Lightbulb,
                modifier = Modifier.weight(1f),
            )
            SecondaryButton(
                text = stringResource(R.string.st03_concept_quiz),
                onClick = { onAskTutorWithPrompt(quizPrompt) },
                leadingIcon = Icons.Filled.QuestionAnswer,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun QuizSessionPanel(
    lesson: LessonDetail,
    quizSession: LessonQuizSession?,
    onTakeQuiz: (quizId: String) -> Unit,
    onOpenQuizResults: (quizId: String) -> Unit,
    onAskTutorWithPrompt: (prompt: String) -> Unit,
) {
    val colors = EduTheme.colors
    val quizId = lesson.quizId
    if (quizId == null || quizSession == null) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Filled.Quiz, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.stateIcon))
            Text(
                text = stringResource(R.string.st03_quiz_none_title),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = stringResource(R.string.st03_quiz_none_body),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
        return
    }

    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        QuizProgressCard(quizSession = quizSession)
        if (quizSession.isCompleted && quizSession.result != null) {
            QuizResultFollowUp(
                result = quizSession.result,
                onReviewResults = { onOpenQuizResults(quizId) },
                onAskTutorWithPrompt = onAskTutorWithPrompt,
            )
        } else {
            PrimaryButton(
                text = if (quizSession.answeredCount > 0) stringResource(R.string.st03_quiz_continue) else stringResource(R.string.st03_take_quiz),
                onClick = { onTakeQuiz(quizId) },
                leadingIcon = Icons.Filled.Quiz,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun QuizProgressCard(quizSession: LessonQuizSession) {
    val colors = EduTheme.colors
    val progress = if (quizSession.totalCount == 0) 0f else quizSession.answeredCount / quizSession.totalCount.toFloat()
    EduCard(borderColor = colors.primary.copy(alpha = 0.22f)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Icon(Icons.Filled.Quiz, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.iconLg))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.st03_quiz_session_title),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.st03_quiz_answered_count, numeral(quizSession.answeredCount), numeral(quizSession.totalCount)),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        EduLinearProgress(progress = progress, modifier = Modifier.padding(top = Spacing.sm))
    }
}

@Composable
private fun QuizResultFollowUp(
    result: QuizResult,
    onReviewResults: () -> Unit,
    onAskTutorWithPrompt: (prompt: String) -> Unit,
) {
    val colors = EduTheme.colors
    val wrongQuestions = result.wrongQuestions()
    EduCard(borderColor = if (wrongQuestions.isEmpty()) colors.success.copy(alpha = 0.3f) else colors.danger.copy(alpha = 0.32f)) {
        Text(
            text = stringResource(R.string.st03_quiz_result_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.st07_correct_count, numeral(result.correctCount), numeral(result.totalCount)),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        if (wrongQuestions.isNotEmpty()) {
            Text(
                text = stringResource(R.string.st03_mistake_review_title),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.md),
            )
            wrongQuestions.take(2).forEach { question ->
                MistakePreviewRow(
                    result = result,
                    question = question,
                    onAskTutorWithPrompt = onAskTutorWithPrompt,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        } else {
            Text(
                text = stringResource(R.string.st03_quiz_no_mistakes),
                style = EduTheme.typography.caption,
                color = colors.success,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.md)) {
            PrimaryButton(
                text = stringResource(R.string.st03_review_quiz_results),
                onClick = onReviewResults,
                modifier = Modifier.weight(1f),
            )
            if (wrongQuestions.isNotEmpty()) {
                SecondaryButton(
                    text = stringResource(R.string.st03_practice_mistakes),
                    onClick = onReviewResults,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun MistakePreviewRow(
    result: QuizResult,
    question: QuizQuestion,
    onAskTutorWithPrompt: (prompt: String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val response = result.attempt.answers[question.id]?.response
    val yourAnswerText = question.options.find { it.id == response }?.text ?: response.orEmpty()
    val correctAnswerText = question.options.find { it.id == question.correctAnswer }?.text ?: question.correctAnswer
    val prompt = stringResource(
        R.string.st07_ask_tutor_mistake_prompt,
        question.prompt,
        yourAnswerText.ifBlank { "—" },
        correctAnswerText,
    )
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(colors.danger.copy(alpha = 0.08f), RoundedCornerShape(Radius.sm))
            .padding(Spacing.sm),
    ) {
        Text(text = question.prompt, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        Text(
            text = stringResource(R.string.st07_your_answer, yourAnswerText.ifBlank { "—" }),
            style = EduTheme.typography.caption,
            color = colors.danger,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Text(
            text = stringResource(R.string.st07_correct_answer, correctAnswerText),
            style = EduTheme.typography.caption,
            color = colors.success,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        GhostButton(
            text = stringResource(R.string.st07_ask_tutor_about_mistake),
            onClick = { onAskTutorWithPrompt(prompt) },
            leadingIcon = Icons.Filled.Chat,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun CompletionGateCard(
    checklist: LessonCompletionChecklist,
    isCompleted: Boolean,
    onMarkComplete: () -> Unit,
) {
    EduCard(borderColor = if (isCompleted) EduTheme.colors.success.copy(alpha = 0.32f) else EduTheme.colors.border) {
        Text(
            text = stringResource(R.string.st03_completion_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.st03_completion_subtitle),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
        )
        CompletionCheckRow(met = checklist.contentEngaged, label = stringResource(R.string.st03_done_teacher))
        CompletionCheckRow(met = checklist.contentEngaged || isCompleted, label = stringResource(R.string.st03_done_understand))
        CompletionCheckRow(met = checklist.contentEngaged || isCompleted, label = stringResource(R.string.st03_done_try))
        CompletionCheckRow(met = checklist.contentEngaged || isCompleted, label = stringResource(R.string.st03_done_check))
        if (checklist.quizRequired) {
            CompletionCheckRow(met = checklist.quizCompleted, label = stringResource(R.string.st03_completion_check_quiz))
        }
        if (isCompleted) {
            StatusPill(
                label = stringResource(R.string.st03_completed_label),
                icon = Icons.Filled.CheckCircle,
                contentColor = EduTheme.colors.success,
                containerColor = EduTheme.colors.success.copy(alpha = 0.12f),
                modifier = Modifier.padding(top = Spacing.sm),
            )
        } else {
            PrimaryButton(
                text = stringResource(R.string.st03_mark_complete),
                onClick = onMarkComplete,
                enabled = checklist.allMet,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            )
        }
    }
}

@Composable
private fun NextLessonActionCard(lesson: LessonDetail, onBackToCourse: () -> Unit) {
    EduCard(borderColor = EduTheme.colors.primary.copy(alpha = 0.22f)) {
        Text(
            text = stringResource(R.string.st03_next_action_title),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.st03_next_action_body, lesson.courseTitle),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        PrimaryButton(
            text = stringResource(R.string.st03_nav_back_to_course),
            onClick = onBackToCourse,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
    }
}

private fun QuizResult.wrongQuestions(): List<QuizQuestion> =
    quiz.questions.filter { question ->
        !attempt.answers[question.id]?.response.matchesQuizAnswer(question.correctAnswer)
    }

@Composable
private fun LessonDetail.learnGuideText(): String {
    val parts = buildList {
        if (LessonMediaType.Video in mediaTypes) add(stringResource(R.string.st03_learn_prompt_watch))
        if (LessonMediaType.Pdf in mediaTypes) add(stringResource(R.string.st03_learn_prompt_read))
        if (keyIdeas.isNotEmpty()) add(stringResource(R.string.st03_learn_prompt_review))
        if (keyIdeas.isNotEmpty()) add(stringResource(R.string.st03_learn_prompt_interact))
    }
    return if (parts.isEmpty()) {
        stringResource(R.string.st03_learn_prompt_empty)
    } else {
        stringResource(R.string.st03_learn_prompt_joined, parts.joinToString("، "))
    }
}

private enum class LessonFlowStepState { Done, Current, Todo }

private data class LessonFlowStep(val icon: ImageVector, val label: String, val state: LessonFlowStepState)

/**
 * Approved design's small dedicated stepper (LessonPlayer.dc.html's `.steps` row) — built
 * fresh rather than reusing [com.rork.eduspark.ui.components.progress.HorizontalSpine], whose
 * continuous-segments visual language doesn't match this row of 4 labeled icon dots joined by
 * thin connector lines.
 */
@Composable
private fun LessonFlowStepper(
    isCompleted: Boolean,
    contentEngaged: Boolean,
    quizSession: LessonQuizSession?,
    modifier: Modifier = Modifier,
) {
    val quizDone = quizSession?.isCompleted == true
    val quizStarted = (quizSession?.answeredCount ?: 0) > 0
    val steps = listOf(
        LessonFlowStep(Icons.Filled.AutoStories, stringResource(R.string.st03_step_learn), if (contentEngaged || isCompleted) LessonFlowStepState.Done else LessonFlowStepState.Current),
        LessonFlowStep(Icons.Filled.Chat, stringResource(R.string.st03_step_ask), if (contentEngaged || quizStarted || isCompleted) LessonFlowStepState.Done else LessonFlowStepState.Todo),
        LessonFlowStep(Icons.Filled.Quiz, stringResource(R.string.st03_step_quiz), when {
            quizDone -> LessonFlowStepState.Done
            quizStarted -> LessonFlowStepState.Current
            else -> LessonFlowStepState.Todo
        }),
        LessonFlowStep(Icons.Filled.Flag, stringResource(R.string.st03_step_finish), if (isCompleted) LessonFlowStepState.Current else LessonFlowStepState.Todo),
    )
    Row(verticalAlignment = Alignment.Top, modifier = modifier.fillMaxWidth()) {
        steps.forEachIndexed { index, step ->
            LessonFlowStepDot(step)
            if (index != steps.lastIndex) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .padding(top = Sizing.avatar / 2)
                        .height(Sizing.hairline)
                        .background(EduTheme.colors.border),
                )
            }
        }
    }
}

@Composable
private fun LessonFlowStepDot(step: LessonFlowStep, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val (container, tint) = when (step.state) {
        LessonFlowStepState.Done -> colors.primaryContainer to colors.primary
        LessonFlowStepState.Current -> colors.primary to colors.onPrimary
        LessonFlowStepState.Todo -> colors.neutralAlpha100 to colors.textSecondary
    }
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = modifier) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(Sizing.avatar)
                .background(container, CircleShape),
        ) {
            Icon(step.icon, contentDescription = step.label, tint = tint, modifier = Modifier.size(Sizing.iconSm))
        }
        Text(
            text = step.label,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

/**
 * Approved design's "الأفكار الأساسية" card (LessonPlayer.dc.html). Each idea is now also this
 * screen's concept-action entry point (Test-2SY's tappable lesson keywords) — [LessonDetail]
 * has no separate `keywords` list, only [LessonDetail.keyIdeas], so these rows serve double
 * duty rather than a second, fabricated content system.
 */
@Composable
private fun KeyIdeasCard(keyIdeas: List<String>, onConceptTap: (String) -> Unit) {
    val colors = EduTheme.colors
    Column {
        Text(text = stringResource(R.string.st03_key_ideas_title), style = EduTheme.typography.title, color = colors.textPrimary)
        EduCard(modifier = Modifier.padding(top = Spacing.xs)) {
            keyIdeas.forEachIndexed { index, idea ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                    modifier = Modifier
                        .fillMaxWidth()
                        .eduClickable(onClickLabel = idea, onClick = { onConceptTap(idea) })
                        .padding(top = if (index == 0) 0.dp else Spacing.sm),
                ) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(Sizing.iconLg)
                            .background(colors.primaryContainer, RoundedCornerShape(Radius.sm)),
                    ) {
                        Text(text = numeral(index + 1), style = EduTheme.typography.mono, color = colors.primary)
                    }
                    Text(
                        text = idea,
                        style = EduTheme.typography.body,
                        color = colors.textPrimary,
                        modifier = Modifier.weight(1f),
                    )
                    Icon(
                        imageVector = Icons.Filled.Chat,
                        contentDescription = null,
                        tint = colors.aiAccent,
                        modifier = Modifier.size(Sizing.iconSm),
                    )
                }
            }
        }
    }
}

/** Approved design's inline "ما فهمت نقطة؟" contextual Ask Tutor row (LessonPlayer.dc.html). */
@Composable
private fun InlineAskTutorRow(teacherName: String, onClick: () -> Unit) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.primaryContainer, RoundedCornerShape(Radius.md))
            .eduClickable(onClickLabel = stringResource(R.string.st03_ask_inline_title), onClick = onClick)
            .padding(Spacing.card),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(Sizing.avatar)
                .background(colors.primary, CircleShape),
        ) {
            Text(text = teacherName.take(1), style = EduTheme.typography.caption, color = colors.onPrimary)
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = stringResource(R.string.st03_ask_inline_title),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
            )
            Text(
                text = stringResource(R.string.st03_ask_inline_subtitle, teacherName),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
        }
        Icon(
            imageVector = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
            contentDescription = null,
            tint = colors.primary,
            modifier = Modifier.mirrorInRtl(),
        )
    }
}

@Composable
private fun PdfSurface(
    lesson: LessonDetail,
    state: LessonPlayerUiState,
    onPreviousPage: () -> Unit,
    onNextPage: () -> Unit,
    onToggleZoom: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(if (state.isZoomed) 0.55f else 0.72f)
                .background(colors.background, RoundedCornerShape(Radius.sm)),
        ) {
            Icon(
                imageVector = Icons.Filled.Description,
                contentDescription = null,
                // A decorative placeholder icon needs an opaque muted tint, not the new
                // hairline-strength alpha `border` token — textTertiary is the closest
                // equivalent to the old solid hajar-300 gray in this specific role.
                tint = colors.textTertiary,
                modifier = Modifier.size(Sizing.stateIcon),
            )
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        ) {
            EduIconButton(
                icon = Icons.AutoMirrored.Filled.KeyboardArrowLeft,
                contentDescription = stringResource(R.string.st03_previous_page),
                onClick = onPreviousPage,
                enabled = state.currentPage > 1,
                modifier = Modifier.mirrorInRtl(),
            )
            Text(
                text = stringResource(R.string.st03_pdf_page, numeral(state.currentPage), numeral(lesson.pageCount)),
                style = EduTheme.typography.body,
                color = colors.textPrimary,
            )
            Row {
                EduIconButton(
                    icon = if (state.isZoomed) Icons.Filled.ZoomOut else Icons.Filled.ZoomIn,
                    contentDescription = stringResource(
                        if (state.isZoomed) R.string.st03_zoom_out else R.string.st03_zoom_in
                    ),
                    onClick = onToggleZoom,
                )
                EduIconButton(
                    icon = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    contentDescription = stringResource(R.string.st03_next_page),
                    onClick = onNextPage,
                    enabled = state.currentPage < lesson.pageCount,
                    modifier = Modifier.mirrorInRtl(),
                )
            }
        }
    }
}

@Composable
private fun VideoSurface(
    state: LessonPlayerUiState,
    onTogglePlayback: () -> Unit,
    onSeek: (Float) -> Unit,
    onCycleSpeed: () -> Unit,
    onToggleCaptions: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(16f / 9f)
                .background(colors.textPrimary, RoundedCornerShape(Radius.sm)),
        ) {
            EduIconButton(
                icon = if (state.isPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                contentDescription = stringResource(if (state.isPlaying) R.string.st03_pause else R.string.st03_play),
                onClick = onTogglePlayback,
                tint = colors.onPrimary,
            )
            if (state.captionsOn) {
                Text(
                    text = stringResource(R.string.st03_captions_sample),
                    style = EduTheme.typography.caption,
                    color = colors.onPrimary,
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(Spacing.sm),
                )
            }
        }
        Slider(
            value = state.positionFraction,
            onValueChange = onSeek,
            colors = SliderDefaults.colors(thumbColor = colors.primary, activeTrackColor = colors.primary),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        )
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            GhostButton(
                text = stringResource(R.string.st03_speed, numeral(formatSpeed(state.playbackSpeed))),
                onClick = onCycleSpeed,
            )
            GhostButton(
                text = stringResource(R.string.st03_captions),
                onClick = onToggleCaptions,
                leadingIcon = Icons.Filled.Subtitles,
            )
        }
    }
}

@Composable
private fun AudioSurface(
    lesson: LessonDetail,
    state: LessonPlayerUiState,
    onTogglePlayback: () -> Unit,
    onSeek: (Float) -> Unit,
    showTranscript: Boolean = true,
) {
    val colors = EduTheme.colors
    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            EduIconButton(
                icon = if (state.isPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                contentDescription = stringResource(if (state.isPlaying) R.string.st03_pause else R.string.st03_play),
                onClick = onTogglePlayback,
                modifier = Modifier.size(Sizing.touchTarget),
            )
            Icon(
                imageVector = Icons.Filled.GraphicEq,
                contentDescription = null,
                tint = colors.primary,
                modifier = Modifier
                    .weight(1f)
                    .height(Sizing.iconLg),
            )
        }
        Slider(
            value = state.positionFraction,
            onValueChange = onSeek,
            colors = SliderDefaults.colors(thumbColor = colors.primary, activeTrackColor = colors.primary),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        )
        if (showTranscript) {
            Text(
                text = stringResource(R.string.st03_audio_transcript),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = lesson.title,
                style = EduTheme.typography.body,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

@Composable
private fun DownloadRow(state: LessonPlayerUiState, onStartDownload: () -> Unit) {
    val colors = EduTheme.colors
    when (state.downloadState) {
        DownloadState.NotDownloaded -> SecondaryButton(
            text = stringResource(R.string.st03_download_offline),
            onClick = onStartDownload,
            leadingIcon = Icons.Filled.Download,
            modifier = Modifier.fillMaxWidth(),
        )

        DownloadState.Downloading -> Column {
            Text(text = stringResource(R.string.st03_downloading), style = EduTheme.typography.caption, color = colors.textSecondary)
            EduLinearProgress(
                progress = state.downloadProgress,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }

        DownloadState.Downloaded -> StatusPill(
            label = stringResource(R.string.st03_offline_available),
            icon = Icons.Filled.CloudDone,
            contentColor = colors.success,
            containerColor = colors.success.copy(alpha = 0.12f),
        )
    }
}

/**
 * Test-2SY's tappable lesson concept → Explain/Example/Quiz-me action set, as a mobile-native
 * bottom sheet rather than the web's inline chip menu — this app's own established "bottom
 * sheet first" convention (see [com.rork.eduspark.ui.screens.messaging.ConversationThreadScreen]'s
 * participant sheet). Explain/Example carry a contextual prompt straight into ST-04, auto-sent
 * exactly like Test-2SY's own `autoSend: true` behavior for these two actions. Quiz me prefers
 * the lesson's own real quiz (same "Take Quiz" destination the action bar already offers) over
 * asking the tutor to improvise one — no second quiz engine.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ConceptActionSheet(
    concept: String,
    lesson: LessonDetail,
    onDismiss: () -> Unit,
    onAskTutorWithPrompt: (String) -> Unit,
    onTakeQuiz: (String) -> Unit,
) {
    val colors = EduTheme.colors
    // Resolved here, inside composition — onClick lambdas below are plain closures, not
    // @Composable, so stringResource() can't be called from inside them directly.
    val explainPrompt = stringResource(R.string.st03_concept_explain_prompt, concept, lesson.title)
    val examplePrompt = stringResource(R.string.st03_concept_example_prompt, concept, lesson.title)
    val quizPrompt = stringResource(R.string.st03_concept_quiz_prompt, concept, lesson.title)

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = colors.surface,
        sheetState = rememberModalBottomSheetState(),
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.gutter, vertical = Spacing.sm)) {
            SheetHandle(modifier = Modifier.padding(bottom = Spacing.md))
            Text(
                text = concept,
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(bottom = Spacing.md),
            )
            ConceptActionRow(
                icon = Icons.Filled.Lightbulb,
                label = stringResource(R.string.st03_concept_explain),
                onClick = { onAskTutorWithPrompt(explainPrompt) },
            )
            ConceptActionRow(
                icon = Icons.Filled.QuestionAnswer,
                label = stringResource(R.string.st03_concept_example),
                onClick = { onAskTutorWithPrompt(examplePrompt) },
            )
            ConceptActionRow(
                icon = Icons.Filled.Quiz,
                label = stringResource(R.string.st03_concept_quiz),
                onClick = {
                    val quizId = lesson.quizId
                    if (quizId != null) onTakeQuiz(quizId) else onAskTutorWithPrompt(quizPrompt)
                },
            )
            Box(modifier = Modifier.height(Spacing.xs))
        }
    }
}

@Composable
private fun ConceptActionRow(icon: ImageVector, label: String, onClick: () -> Unit) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .eduClickable(onClickLabel = label, onClick = onClick)
            .padding(vertical = Spacing.sm),
    ) {
        Icon(icon, contentDescription = null, tint = colors.aiAccent, modifier = Modifier.size(Sizing.icon))
        Text(text = label, style = EduTheme.typography.bodyLg, color = colors.textPrimary)
    }
}

/**
 * ST-03's completion-verification gate (Phase 2) — blocks Confirm until every applicable check
 * is met, exactly like Test-2SY's own checklist dialog. Only checks this Android build can
 * actually verify are shown; see [LessonCompletionChecklist]'s own doc comment for what's
 * deliberately left out and why.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LessonCompletionSheet(
    checklist: LessonCompletionChecklist,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit,
) {
    val colors = EduTheme.colors
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = colors.surface,
        sheetState = rememberModalBottomSheetState(),
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.gutter, vertical = Spacing.sm)) {
            SheetHandle(modifier = Modifier.padding(bottom = Spacing.md))
            Text(
                text = stringResource(R.string.st03_completion_title),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
            )
            Text(
                text = stringResource(R.string.st03_completion_subtitle),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.md),
            )
            CompletionCheckRow(met = checklist.contentEngaged, label = stringResource(R.string.st03_completion_check_content))
            if (checklist.quizRequired) {
                CompletionCheckRow(met = checklist.quizCompleted, label = stringResource(R.string.st03_completion_check_quiz))
            }
            PrimaryButton(
                text = stringResource(R.string.st03_completion_confirm),
                onClick = onConfirm,
                enabled = checklist.allMet,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
            GhostButton(
                text = stringResource(R.string.st10_close),
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun CompletionCheckRow(met: Boolean, label: String) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.xs),
    ) {
        Icon(
            imageVector = if (met) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
            contentDescription = null,
            tint = if (met) colors.success else colors.textSecondary,
            modifier = Modifier.size(Sizing.iconSm),
        )
        Text(text = label, style = EduTheme.typography.body, color = if (met) colors.textPrimary else colors.textSecondary)
    }
}

@Composable
private fun LessonActionBar(
    lesson: LessonDetail,
    onAskTutor: () -> Unit,
    onTakeQuiz: (quizId: String) -> Unit,
    onMarkComplete: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
            SecondaryButton(
                text = stringResource(R.string.st03_ask_tutor),
                onClick = onAskTutor,
                leadingIcon = Icons.Filled.Chat,
                modifier = Modifier.weight(1f),
            )
            val quizId = lesson.quizId
            if (quizId != null) {
                SecondaryButton(
                    text = stringResource(R.string.st03_take_quiz),
                    onClick = { onTakeQuiz(quizId) },
                    leadingIcon = Icons.Filled.Quiz,
                    modifier = Modifier.weight(1f),
                )
            }
        }
        if (lesson.isCompleted) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier.padding(top = Spacing.sm),
            ) {
                Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success, modifier = Modifier.size(Sizing.iconSm))
                Text(
                    text = stringResource(R.string.st03_completed_label),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.success,
                )
            }
        } else {
            PrimaryButton(
                text = stringResource(R.string.st03_mark_complete),
                onClick = onMarkComplete,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            )
        }
    }
}
