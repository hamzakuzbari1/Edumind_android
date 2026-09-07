package com.rork.eduspark.ui.screens.student

import androidx.annotation.StringRes
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.AutoStories
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.Headphones
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Insights
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Timer
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.isolateBidi
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.CefrLevel
import com.rork.eduspark.data.model.LanguageAccess
import com.rork.eduspark.data.model.LanguageAccessStatus
import com.rork.eduspark.data.model.LanguageArea
import com.rork.eduspark.data.model.LanguageChoiceQuestion
import com.rork.eduspark.data.model.LanguageCorrection
import com.rork.eduspark.data.model.LanguageDailyVocabQuiz
import com.rork.eduspark.data.model.LanguageGrammarLesson
import com.rork.eduspark.data.model.LanguageGrammarLessonPhase
import com.rork.eduspark.data.model.LanguageGrammarPracticeItem
import com.rork.eduspark.data.model.LanguageGrammarPracticeType
import com.rork.eduspark.data.model.LanguageGrammarSnapshot
import com.rork.eduspark.data.model.LanguageGrammarStage
import com.rork.eduspark.data.model.LanguageHubSnapshot
import com.rork.eduspark.data.model.LanguageJourneyLevel
import com.rork.eduspark.data.model.LanguageJourneySession
import com.rork.eduspark.data.model.LanguageJourneySnapshot
import com.rork.eduspark.data.model.LanguageJourneyStage
import com.rork.eduspark.data.model.LanguageListeningLesson
import com.rork.eduspark.data.model.LanguagePlacementAttempt
import com.rork.eduspark.data.model.LanguagePlacementHistory
import com.rork.eduspark.data.model.LanguagePlacementQuestion
import com.rork.eduspark.data.model.LanguagePlacementQuestionType
import com.rork.eduspark.data.model.LanguagePlacementReport
import com.rork.eduspark.data.model.LanguagePlacementSection
import com.rork.eduspark.data.model.LanguagePlacementSkillResult
import com.rork.eduspark.data.model.LanguageReadingAttempt
import com.rork.eduspark.data.model.LanguageReadingMode
import com.rork.eduspark.data.model.LanguageReadingOverview
import com.rork.eduspark.data.model.LanguageReadingQuestion
import com.rork.eduspark.data.model.LanguageReadingQuestionType
import com.rork.eduspark.data.model.LanguageReadingResult
import com.rork.eduspark.data.model.LanguageSkill
import com.rork.eduspark.data.model.LanguageSkillLevel
import com.rork.eduspark.data.model.LanguageSkillWorkspace
import com.rork.eduspark.data.model.LanguageSpeakingLesson
import com.rork.eduspark.data.model.LanguageSpeakingSession
import com.rork.eduspark.data.model.LanguageTrackStatus
import com.rork.eduspark.data.model.LanguageVocabularyCard
import com.rork.eduspark.data.model.LanguageVocabularyChallenge
import com.rork.eduspark.data.model.LanguageVocabularySnapshot
import com.rork.eduspark.data.model.LanguageWritingLesson
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.progress.CefrBadge
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.progress.ProgressRing
import com.rork.eduspark.ui.components.state.InlineLoader
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.EduGroupedSurface
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun LanguageModuleScreen(
    modifier: Modifier = Modifier,
    viewModel: LanguageModuleViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    ScreenStateHost(
        state = state.accessResult,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { LanguageFoundationSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { access ->
        when {
            !access.subscribed -> LanguageAccessGate(
                access = access,
                isBusy = state.isBusy,
                onSubscribe = viewModel::subscribe,
            )

            !access.placementCompleted || state.placementMode -> LanguagePlacementSurface(
                access = access,
                state = state,
                onSelectArea = viewModel::selectArea,
                onStartExam = viewModel::startPlacementExam,
                onStartFresh = viewModel::startFreshPlacementExam,
                onSkipLevel = viewModel::selectSkipLevel,
                onSkipPlacement = viewModel::skipPlacement,
                onGoToQuestion = viewModel::goToPlacementQuestion,
                onAnswerChange = viewModel::updateAnswerDraft,
                onUseSampleSpeaking = viewModel::useSampleSpeakingAnswer,
                onPlayAudio = viewModel::markListeningPlayed,
                onSubmitAnswer = viewModel::submitCurrentAnswer,
                onOpenHistory = viewModel::openPlacementHistory,
                onOpenIntro = viewModel::openPlacementIntro,
                onReturnHome = viewModel::returnToLanguageHome,
                onOpenArea = viewModel::openAreaFromPlacement,
            )

            else -> ScreenStateHost(
                state = state.hubResult,
                onRetry = viewModel::retry,
                isOffline = !state.isOnline,
                loading = { LanguageFoundationSkeleton() },
                modifier = Modifier.fillMaxSize(),
            ) { hub ->
                LanguageShellContent(
                    hub = hub,
                    state = state,
                    viewModel = viewModel,
                    selectedArea = state.selectedArea,
                    onSelectArea = viewModel::selectArea,
                    onOpenPlacement = viewModel::openPlacementIntro,
                    onOpenPlacementHistory = viewModel::openPlacementHistory,
                )
            }
        }
    }
}

@Composable
private fun LanguageAccessGate(
    access: LanguageAccess,
    isBusy: Boolean,
    onSubscribe: () -> Unit,
) {
    LazyColumn(
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            LanguagePageHeader(
                eyebrow = stringResource(R.string.ln01_access_eyebrow),
                title = stringResource(R.string.ln01_paywall_title),
                subtitle = stringResource(R.string.ln01_paywall_subtitle),
                icon = Icons.Filled.Language,
            )
        }
        item {
            LanguagePaywallCard(
                access = access,
                isBusy = isBusy,
                onSubscribe = onSubscribe,
            )
        }
    }
}

@Composable
private fun LanguageShellContent(
    hub: LanguageHubSnapshot,
    state: LanguageModuleUiState,
    viewModel: LanguageModuleViewModel,
    selectedArea: LanguageArea,
    onSelectArea: (LanguageArea) -> Unit,
    onOpenPlacement: () -> Unit,
    onOpenPlacementHistory: () -> Unit,
) {
    if (selectedArea == LanguageArea.Home) {
        LanguageApprovedHome(
            hub = hub,
            workspace = state.skillWorkspace,
            onSelectArea = onSelectArea,
        )
        return
    }

    Column(modifier = Modifier.fillMaxSize()) {
        LanguageDeepChrome(
            area = selectedArea,
            workspace = state.skillWorkspace,
            onBackHome = { onSelectArea(LanguageArea.Home) },
            onSelectArea = onSelectArea,
            modifier = Modifier.padding(horizontal = Spacing.gutter, vertical = Spacing.xs),
        )
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
            contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.sm),
            modifier = Modifier.fillMaxSize(),
        ) {
            item {
                LanguageSkillContent(
                    area = selectedArea,
                    state = state,
                    viewModel = viewModel,
                    workspace = state.skillWorkspace,
                    access = hub.access,
                    onBackHome = { onSelectArea(LanguageArea.Home) },
                    onOpenPlacementHistory = onOpenPlacementHistory,
                )
            }
        }
    }
}

internal enum class LanguageMissionScene {
    Cafe,
    Airport,
    School,
    Doctor,
    Shopping,
    Restaurant,
    Interview,
    Directions,
    GenericConversation,
}

@Composable
private fun LanguageApprovedHome(
    hub: LanguageHubSnapshot,
    workspace: LanguageSkillWorkspace?,
    onSelectArea: (LanguageArea) -> Unit,
) {
    val colors = EduTheme.colors
    val access = hub.access
    val rec = access.placementRecommendation
    val todayMission = workspace?.journey?.todayMission
    val missionTitle = todayMission?.title ?: rec?.startingTopic ?: hub.learningPath.nextTitle
    val missionScenario = todayMission?.scenario.orEmpty()
    val missionMinutes = todayMission?.estimatedMinutes
    val missionArea = when (rec?.focusSkill) {
        LanguageSkill.Listening -> LanguageArea.Listening
        LanguageSkill.Speaking -> LanguageArea.Speaking
        LanguageSkill.Writing -> LanguageArea.Writing
        LanguageSkill.Reading -> LanguageArea.Reading
        LanguageSkill.Journey -> LanguageArea.Journey
        LanguageSkill.Grammar -> LanguageArea.Grammar
        LanguageSkill.Vocabulary -> LanguageArea.Vocabulary
        null -> hub.learningPath.nextArea
    }
    val scene = remember(missionTitle, missionScenario, missionArea) {
        resolveLanguageMissionScene(missionTitle, missionScenario, missionArea)
    }
    val current = access.overallLevel ?: CefrLevel.A2
    val target = access.targetLevel ?: CefrLevel.B1
    val journeyProgress = (access.targetProgressPercent / 100f).coerceIn(0f, 1f)
    val coreSkills = listOf(
        LanguageArea.Listening,
        LanguageArea.Speaking,
        LanguageArea.Reading,
        LanguageArea.Writing,
    )
    val typeLabel = stringResource(missionArea.homeMissionTypeRes())
    val minutesLabel = missionMinutes?.let { stringResource(R.string.ln01_mission_minutes, numeral(it)) }
    var heroVisible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { heroVisible = true }

    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(start = Spacing.gutter, top = Spacing.sm, end = Spacing.gutter, bottom = Spacing.sm),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = stringResource(R.string.st01_english_title),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = colors.textSecondary,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = stringResource(R.string.ln01_level_range, current.code, target.code),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.primary,
            )
        }
        AnimatedVisibility(
            visible = heroVisible,
            enter = fadeIn(tween(280)) + slideInVertically(tween(280)) { it / 14 },
        ) {
            EduCard(
                onClick = { onSelectArea(missionArea) },
                containerColor = colors.primary,
                borderColor = colors.primary,
            ) {
                StatusPill(
                    label = stringResource(R.string.ln01_today_english),
                    contentColor = colors.onPrimary,
                    containerColor = colors.onPrimary.copy(alpha = 0.16f),
                )
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(132.dp)
                        .padding(top = Spacing.xs),
                ) {
                    LanguageHomeMissionVisual(
                        scene = scene,
                        area = missionArea,
                        ink = colors.onPrimary,
                    )
                }
                Text(
                    text = missionTitle.isolateBidi(),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(),
                    color = colors.onPrimary,
                )
                Text(
                    text = listOfNotNull(typeLabel, minutesLabel).joinToString(" · "),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                    color = colors.onPrimary.copy(alpha = 0.82f),
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .padding(top = Spacing.sm)
                        .fillMaxWidth()
                        .defaultMinSize(minHeight = Sizing.touchTarget)
                        .background(colors.surface, RoundedCornerShape(Radius.pill))
                        .padding(horizontal = Spacing.md, vertical = Spacing.sm),
                ) {
                    Text(
                        text = if (missionArea == LanguageArea.Speaking) {
                            stringResource(R.string.ln01_start_conversation)
                        } else {
                            stringResource(R.string.ln01_start_mission)
                        },
                        style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.primary,
                        modifier = Modifier.weight(1f),
                    )
                    Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = colors.primary)
                }
            }
        }
        coreSkills.chunked(2).forEach { row ->
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier.fillMaxWidth(),
            ) {
                row.forEach { area ->
                    val levelCode = hub.skillLevels.firstOrNull { it.skill == area.asCoreSkill() }?.level?.code
                    EduCard(
                        onClick = { onSelectArea(area) },
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xs),
                    ) {
                        if (area == LanguageArea.Listening) {
                            WaveformVisual(color = colors.primary)
                        } else {
                            Icon(
                                imageVector = area.icon(),
                                contentDescription = null,
                                tint = colors.primary,
                                modifier = Modifier.size(Sizing.icon),
                            )
                        }
                        Text(
                            text = stringResource(area.homeSkillLabelRes()),
                            style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                            color = colors.textPrimary,
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                        if (levelCode != null) {
                            Text(
                                text = levelCode,
                                style = EduTheme.typography.caption,
                                color = colors.textTertiary,
                            )
                        }
                    }
                }
            }
        }
        Text(
            text = stringResource(R.string.ln01_home_more_practice),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = colors.textTertiary,
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.fillMaxWidth(),
        ) {
            LanguageHomePracticeShortcut(
                title = stringResource(R.string.ln01_home_vocab_shortcut),
                onClick = { onSelectArea(LanguageArea.Vocabulary) },
                modifier = Modifier.weight(1f),
            ) {
                LanguageHomeVocabMark(color = colors.primary)
            }
            LanguageHomePracticeShortcut(
                title = stringResource(R.string.ln01_home_grammar_shortcut),
                onClick = { onSelectArea(LanguageArea.Grammar) },
                modifier = Modifier.weight(1f),
            ) {
                LanguageHomeGrammarMark(color = colors.primary)
            }
        }
        EduCard(
            onClick = { onSelectArea(LanguageArea.Journey) },
            contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xs),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            ) {
                Text(current.code, style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold), color = colors.success)
                Box(modifier = Modifier.weight(1f).height(12.dp), contentAlignment = Alignment.CenterStart) {
                    EduLinearProgress(progress = journeyProgress, modifier = Modifier.fillMaxWidth())
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(journeyProgress.coerceAtLeast(0.08f))
                            .fillMaxSize(),
                        contentAlignment = Alignment.CenterEnd,
                    ) {
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .background(colors.primary, CircleShape),
                        )
                    }
                }
                Text(target.code, style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold), color = colors.primary)
            }
        }
    }
}

@Composable
private fun LanguageHomePracticeShortcut(
    title: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    mark: @Composable () -> Unit,
) {
    EduCard(
        onClick = onClick,
        onClickLabel = title,
        modifier = modifier,
        contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xxs),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        ) {
            mark()
            Text(
                text = title,
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = EduTheme.colors.textSecondary,
            )
        }
    }
}

@Composable
private fun LanguageHomeVocabMark(color: Color) {
    val dim = color.copy(alpha = 0.42f)
    Canvas(modifier = Modifier.size(Sizing.iconSm)) {
        val w = size.width
        val h = size.height
        val sw = 1.6.dp.toPx()
        drawRoundRect(
            color = dim,
            topLeft = Offset(w * 0.18f, h * 0.08f),
            size = Size(w * 0.62f, h * 0.72f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(2.dp.toPx()),
            style = Stroke(width = sw),
        )
        drawRoundRect(
            color = color,
            topLeft = Offset(w * 0.28f, h * 0.22f),
            size = Size(w * 0.62f, h * 0.72f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(2.dp.toPx()),
            style = Stroke(width = sw),
        )
        drawLine(dim, Offset(w * 0.40f, h * 0.46f), Offset(w * 0.74f, h * 0.46f), sw, StrokeCap.Round)
    }
}

@Composable
private fun LanguageHomeGrammarMark(color: Color) {
    val dim = color.copy(alpha = 0.42f)
    Canvas(modifier = Modifier.size(Sizing.iconSm)) {
        val w = size.width
        val h = size.height
        val sw = 1.6.dp.toPx()
        drawLine(dim, Offset(w * 0.08f, h * 0.62f), Offset(w * 0.92f, h * 0.62f), sw, StrokeCap.Round)
        drawCircle(color, radius = 2.2.dp.toPx(), center = Offset(w * 0.22f, h * 0.62f))
        drawCircle(color, radius = 2.2.dp.toPx(), center = Offset(w * 0.50f, h * 0.34f))
        drawCircle(dim, radius = 2.2.dp.toPx(), center = Offset(w * 0.78f, h * 0.62f), style = Stroke(width = sw))
        drawLine(color, Offset(w * 0.22f, h * 0.62f), Offset(w * 0.50f, h * 0.34f), sw, StrokeCap.Round)
        drawLine(dim, Offset(w * 0.50f, h * 0.34f), Offset(w * 0.78f, h * 0.62f), sw, StrokeCap.Round)
    }
}

internal fun resolveLanguageMissionScene(
    title: String,
    scenario: String,
    area: LanguageArea,
): LanguageMissionScene {
    val haystack = "$title $scenario".lowercase()
    fun has(vararg keys: String) = keys.any { it in haystack }
    return when {
        has("cafe", "café", "coffee", "مقهى", "قهوة") -> LanguageMissionScene.Cafe
        has("airport", "flight", "boarding", "suitcase", "gate", "مطار") -> LanguageMissionScene.Airport
        has("school", "class", "classmate", "teacher", "classroom", "before class", "مدرسة", "صف") -> LanguageMissionScene.School
        has("doctor", "clinic", "hospital", "medical", "طبيب", "عيادة") -> LanguageMissionScene.Doctor
        has("shop", "store", "shopping", "buy", "price", "تسوق", "متجر") -> LanguageMissionScene.Shopping
        has("restaurant", "menu", "dinner", "lunch", "waiter", "مطعم") -> LanguageMissionScene.Restaurant
        has("interview", "job", "مقابلة") -> LanguageMissionScene.Interview
        has("direction", "directions", "map", "street", "where is", "اتجاه", "خريطة") -> LanguageMissionScene.Directions
        area == LanguageArea.Reading -> LanguageMissionScene.GenericConversation
        area == LanguageArea.Writing -> LanguageMissionScene.GenericConversation
        else -> LanguageMissionScene.GenericConversation
    }
}

@Composable
private fun LanguageHomeMissionVisual(
    scene: LanguageMissionScene,
    area: LanguageArea,
    ink: Color,
) {
    val dim = ink.copy(alpha = 0.42f)
    Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth().height(132.dp)) {
        LanguageHomeSceneVisual(scene = scene, area = area, ink = ink, dim = dim)
        if (area == LanguageArea.Listening) {
            LanguageHomeWaveformVisual(
                color = ink,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = Spacing.xxs),
            )
        }
    }
}

@Composable
internal fun LanguageHomeSceneVisual(
    scene: LanguageMissionScene,
    area: LanguageArea,
    ink: Color,
    dim: Color,
    modifier: Modifier = Modifier,
) {
    Canvas(modifier = modifier.size(132.dp)) {
        val w = size.width
        val h = size.height
        val sw = 2.6.dp.toPx()
        when (scene) {
            LanguageMissionScene.Cafe -> {
                val cup = Path().apply {
                    moveTo(w * 0.32f, h * 0.48f)
                    lineTo(w * 0.36f, h * 0.78f)
                    lineTo(w * 0.60f, h * 0.78f)
                    lineTo(w * 0.64f, h * 0.48f)
                    close()
                }
                drawPath(cup, ink, style = Stroke(width = sw, cap = StrokeCap.Round, join = androidx.compose.ui.graphics.StrokeJoin.Round))
                drawArc(dim, -70f, 140f, false, Offset(w * 0.62f, h * 0.52f), Size(w * 0.16f, h * 0.20f), style = Stroke(width = sw, cap = StrokeCap.Round))
                drawLine(dim, Offset(w * 0.40f, h * 0.40f), Offset(w * 0.40f, h * 0.28f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.48f, h * 0.38f), Offset(w * 0.48f, h * 0.24f), sw, StrokeCap.Round)
                drawRoundRect(ink, Offset(w * 0.12f, h * 0.16f), Size(w * 0.34f, h * 0.20f), androidx.compose.ui.geometry.CornerRadius(10.dp.toPx()), style = Stroke(width = sw))
                drawLine(ink, Offset(w * 0.18f, h * 0.24f), Offset(w * 0.36f, h * 0.24f), sw, StrokeCap.Round)
            }
            LanguageMissionScene.Airport -> {
                drawRoundRect(ink, Offset(w * 0.28f, h * 0.42f), Size(w * 0.36f, h * 0.32f), androidx.compose.ui.geometry.CornerRadius(8.dp.toPx()), style = Stroke(width = sw))
                drawLine(ink, Offset(w * 0.36f, h * 0.42f), Offset(w * 0.36f, h * 0.32f), sw, StrokeCap.Round)
                drawLine(ink, Offset(w * 0.56f, h * 0.42f), Offset(w * 0.56f, h * 0.32f), sw, StrokeCap.Round)
                drawLine(ink, Offset(w * 0.36f, h * 0.32f), Offset(w * 0.56f, h * 0.32f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.28f, h * 0.56f), Offset(w * 0.64f, h * 0.56f), sw, StrokeCap.Round)
                drawRoundRect(ink, Offset(w * 0.66f, h * 0.22f), Size(w * 0.22f, h * 0.28f), androidx.compose.ui.geometry.CornerRadius(6.dp.toPx()), style = Stroke(width = sw))
                drawLine(dim, Offset(w * 0.70f, h * 0.30f), Offset(w * 0.84f, h * 0.30f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.70f, h * 0.38f), Offset(w * 0.80f, h * 0.38f), sw, StrokeCap.Round)
            }
            LanguageMissionScene.School -> {
                drawRoundRect(ink, Offset(w * 0.18f, h * 0.12f), Size(w * 0.64f, h * 0.40f), androidx.compose.ui.geometry.CornerRadius(6.dp.toPx()), style = Stroke(width = sw))
                drawLine(dim, Offset(w * 0.26f, h * 0.24f), Offset(w * 0.74f, h * 0.24f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.26f, h * 0.34f), Offset(w * 0.62f, h * 0.34f), sw, StrokeCap.Round)
                drawLine(ink, Offset(w * 0.28f, h * 0.52f), Offset(w * 0.22f, h * 0.68f), sw, StrokeCap.Round)
                drawLine(ink, Offset(w * 0.72f, h * 0.52f), Offset(w * 0.78f, h * 0.68f), sw, StrokeCap.Round)
                drawCircle(ink, 7.dp.toPx(), Offset(w * 0.32f, h * 0.66f), style = Stroke(width = sw))
                drawLine(ink, Offset(w * 0.32f, h * 0.72f), Offset(w * 0.32f, h * 0.86f), sw, StrokeCap.Round)
                drawLine(ink, Offset(w * 0.32f, h * 0.78f), Offset(w * 0.42f, h * 0.74f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.18f, h * 0.88f), Offset(w * 0.82f, h * 0.88f), sw, StrokeCap.Round)
                drawRoundRect(ink, Offset(w * 0.50f, h * 0.68f), Size(w * 0.26f, h * 0.16f), androidx.compose.ui.geometry.CornerRadius(4.dp.toPx()), style = Stroke(width = sw))
                drawLine(ink, Offset(w * 0.63f, h * 0.68f), Offset(w * 0.63f, h * 0.84f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.54f, h * 0.74f), Offset(w * 0.60f, h * 0.74f), sw, StrokeCap.Round)
            }
            LanguageMissionScene.Doctor -> {
                drawCircle(ink, w * 0.16f, Offset(w * 0.36f, h * 0.38f), style = Stroke(width = sw))
                drawLine(ink, Offset(w * 0.36f, h * 0.28f), Offset(w * 0.36f, h * 0.48f), sw, StrokeCap.Round)
                drawLine(ink, Offset(w * 0.26f, h * 0.38f), Offset(w * 0.46f, h * 0.38f), sw, StrokeCap.Round)
                drawCircle(ink, 7.dp.toPx(), Offset(w * 0.68f, h * 0.30f), style = Stroke(width = sw))
                drawLine(ink, Offset(w * 0.68f, h * 0.36f), Offset(w * 0.68f, h * 0.62f), sw, StrokeCap.Round)
                drawRoundRect(dim, Offset(w * 0.58f, h * 0.64f), Size(w * 0.26f, h * 0.18f), androidx.compose.ui.geometry.CornerRadius(5.dp.toPx()), style = Stroke(width = sw))
            }
            LanguageMissionScene.Shopping -> {
                val bag = Path().apply {
                    moveTo(w * 0.30f, h * 0.40f)
                    lineTo(w * 0.26f, h * 0.80f)
                    lineTo(w * 0.62f, h * 0.80f)
                    lineTo(w * 0.58f, h * 0.40f)
                    close()
                }
                drawPath(bag, ink, style = Stroke(width = sw, cap = StrokeCap.Round, join = androidx.compose.ui.graphics.StrokeJoin.Round))
                drawArc(ink, 180f, 180f, false, Offset(w * 0.34f, h * 0.26f), Size(w * 0.20f, h * 0.18f), style = Stroke(width = sw, cap = StrokeCap.Round))
                drawRoundRect(dim, Offset(w * 0.64f, h * 0.28f), Size(w * 0.20f, h * 0.22f), androidx.compose.ui.geometry.CornerRadius(4.dp.toPx()), style = Stroke(width = sw))
                drawLine(dim, Offset(w * 0.74f, h * 0.28f), Offset(w * 0.74f, h * 0.22f), sw, StrokeCap.Round)
            }
            LanguageMissionScene.Restaurant -> {
                drawLine(ink, Offset(w * 0.18f, h * 0.72f), Offset(w * 0.82f, h * 0.72f), sw, StrokeCap.Round)
                drawOval(ink, Offset(w * 0.30f, h * 0.42f), Size(w * 0.28f, h * 0.16f), style = Stroke(width = sw))
                drawLine(dim, Offset(w * 0.44f, h * 0.50f), Offset(w * 0.44f, h * 0.72f), sw, StrokeCap.Round)
                drawRoundRect(ink, Offset(w * 0.64f, h * 0.36f), Size(w * 0.14f, h * 0.22f), androidx.compose.ui.geometry.CornerRadius(6.dp.toPx()), style = Stroke(width = sw))
                drawArc(dim, -80f, 160f, false, Offset(w * 0.76f, h * 0.40f), Size(w * 0.10f, h * 0.12f), style = Stroke(width = sw, cap = StrokeCap.Round))
            }
            LanguageMissionScene.Interview -> {
                drawCircle(ink, 8.dp.toPx(), Offset(w * 0.30f, h * 0.30f), style = Stroke(width = sw))
                drawLine(ink, Offset(w * 0.30f, h * 0.38f), Offset(w * 0.30f, h * 0.62f), sw, StrokeCap.Round)
                drawCircle(ink, 8.dp.toPx(), Offset(w * 0.70f, h * 0.30f), style = Stroke(width = sw))
                drawLine(ink, Offset(w * 0.70f, h * 0.38f), Offset(w * 0.70f, h * 0.62f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.18f, h * 0.72f), Offset(w * 0.82f, h * 0.72f), sw, StrokeCap.Round)
                drawRoundRect(ink, Offset(w * 0.14f, h * 0.12f), Size(w * 0.22f, h * 0.12f), androidx.compose.ui.geometry.CornerRadius(6.dp.toPx()), style = Stroke(width = sw))
                drawRoundRect(dim, Offset(w * 0.64f, h * 0.12f), Size(w * 0.22f, h * 0.12f), androidx.compose.ui.geometry.CornerRadius(6.dp.toPx()), style = Stroke(width = sw))
            }
            LanguageMissionScene.Directions -> {
                drawCircle(ink, 8.dp.toPx(), Offset(w * 0.50f, h * 0.28f), style = Stroke(width = sw))
                val pin = Path().apply {
                    moveTo(w * 0.50f, h * 0.52f)
                    lineTo(w * 0.38f, h * 0.32f)
                    lineTo(w * 0.62f, h * 0.32f)
                    close()
                }
                drawPath(pin, ink, style = Stroke(width = sw, cap = StrokeCap.Round, join = androidx.compose.ui.graphics.StrokeJoin.Round))
                drawLine(dim, Offset(w * 0.22f, h * 0.70f), Offset(w * 0.40f, h * 0.62f), sw, StrokeCap.Round)
                drawLine(ink, Offset(w * 0.40f, h * 0.62f), Offset(w * 0.62f, h * 0.78f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.62f, h * 0.78f), Offset(w * 0.80f, h * 0.68f), sw, StrokeCap.Round)
            }
            LanguageMissionScene.GenericConversation -> {
                if (area == LanguageArea.Writing) {
                    drawRoundRect(ink, Offset(w * 0.24f, h * 0.18f), Size(w * 0.44f, h * 0.58f), androidx.compose.ui.geometry.CornerRadius(8.dp.toPx()), style = Stroke(width = sw))
                    drawLine(dim, Offset(w * 0.32f, h * 0.34f), Offset(w * 0.60f, h * 0.34f), sw, StrokeCap.Round)
                    drawLine(dim, Offset(w * 0.32f, h * 0.46f), Offset(w * 0.56f, h * 0.46f), sw, StrokeCap.Round)
                    drawLine(ink, Offset(w * 0.32f, h * 0.58f), Offset(w * 0.50f, h * 0.58f), sw, StrokeCap.Round)
                } else if (area == LanguageArea.Reading) {
                    drawRoundRect(ink, Offset(w * 0.22f, h * 0.18f), Size(w * 0.56f, h * 0.62f), androidx.compose.ui.geometry.CornerRadius(8.dp.toPx()), style = Stroke(width = sw))
                    drawLine(ink, Offset(w * 0.50f, h * 0.20f), Offset(w * 0.50f, h * 0.78f), sw, StrokeCap.Round)
                    drawLine(dim, Offset(w * 0.28f, h * 0.34f), Offset(w * 0.44f, h * 0.34f), sw, StrokeCap.Round)
                    drawLine(dim, Offset(w * 0.56f, h * 0.34f), Offset(w * 0.72f, h * 0.34f), sw, StrokeCap.Round)
                } else {
                    drawRoundRect(ink, Offset(w * 0.12f, h * 0.22f), Size(w * 0.36f, h * 0.22f), androidx.compose.ui.geometry.CornerRadius(10.dp.toPx()), style = Stroke(width = sw))
                    drawRoundRect(dim, Offset(w * 0.52f, h * 0.50f), Size(w * 0.36f, h * 0.22f), androidx.compose.ui.geometry.CornerRadius(10.dp.toPx()), style = Stroke(width = sw))
                    drawCircle(ink, 7.dp.toPx(), Offset(w * 0.20f, h * 0.78f), style = Stroke(width = sw))
                    drawCircle(dim, 7.dp.toPx(), Offset(w * 0.80f, h * 0.18f), style = Stroke(width = sw))
                }
            }
        }
    }
}

@Composable
internal fun LanguageHomeWaveformVisual(color: Color, modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "language-home-wave")
    val phase by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(animation = tween(1200, easing = LinearEasing), repeatMode = RepeatMode.Restart),
        label = "language-home-wave-phase",
    )
    Canvas(modifier = modifier.size(width = 96.dp, height = 36.dp)) {
        val bars = intArrayOf(8, 16, 24, 12, 28, 10, 20, 14)
        val gap = 5.dp.toPx()
        val barW = 5.dp.toPx()
        bars.forEachIndexed { index, heightDp ->
            val pulse = 0.72f + 0.28f * kotlin.math.sin((phase + index / bars.size.toFloat()) * 2.0 * Math.PI).toFloat()
            val height = heightDp.dp.toPx() * pulse
            drawRoundRect(
                color = color,
                topLeft = Offset(index * (barW + gap), (size.height - height) / 2f),
                size = Size(barW, height),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(2.dp.toPx()),
            )
        }
    }
}

@StringRes
private fun LanguageArea.homeSkillLabelRes(): Int = when (this) {
    LanguageArea.Listening -> R.string.ln01_home_skill_listening
    LanguageArea.Speaking -> R.string.ln01_home_skill_speaking
    LanguageArea.Reading -> R.string.ln01_home_skill_reading
    LanguageArea.Writing -> R.string.ln01_home_skill_writing
    else -> titleRes()
}

@StringRes
private fun LanguageArea.homeMissionTypeRes(): Int = when (this) {
    LanguageArea.Speaking -> R.string.ln_area_speaking
    else -> homeSkillLabelRes()
}

private fun LanguageArea.asCoreSkill(): LanguageSkill? = when (this) {
    LanguageArea.Listening -> LanguageSkill.Listening
    LanguageArea.Speaking -> LanguageSkill.Speaking
    LanguageArea.Reading -> LanguageSkill.Reading
    LanguageArea.Writing -> LanguageSkill.Writing
    else -> null
}

@Composable
private fun LanguagePlacementSurface(
    access: LanguageAccess,
    state: LanguageModuleUiState,
    onSelectArea: (LanguageArea) -> Unit,
    onStartExam: () -> Unit,
    onStartFresh: () -> Unit,
    onSkipLevel: (CefrLevel) -> Unit,
    onSkipPlacement: () -> Unit,
    onGoToQuestion: (Int) -> Unit,
    onAnswerChange: (String) -> Unit,
    onUseSampleSpeaking: () -> Unit,
    onPlayAudio: () -> Unit,
    onSubmitAnswer: () -> Unit,
    onOpenHistory: () -> Unit,
    onOpenIntro: () -> Unit,
    onReturnHome: () -> Unit,
    onOpenArea: (LanguageArea) -> Unit,
) {
    LazyColumn(
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        if (access.placementCompleted) {
            item {
                LanguageModuleTabsRow(selectedArea = LanguageArea.Home, onSelectArea = onSelectArea)
            }
        }

        when (state.placementStage) {
            LanguagePlacementStage.Intro -> {
                item {
                    PlacementIntroContent(
                        access = access,
                        selectedLevel = state.skipLevel,
                        isBusy = state.isBusy,
                        onStartExam = onStartExam,
                        onSkipLevel = onSkipLevel,
                        onSkipPlacement = onSkipPlacement,
                        onOpenHistory = onOpenHistory,
                    )
                }
            }

            LanguagePlacementStage.Exam -> {
                item {
                    PlacementExamRunner(
                        attempt = state.placementAttempt,
                        answerDraft = state.answerDraft,
                        playedAudioQuestionIds = state.playedAudioQuestionIds,
                        onGoToQuestion = onGoToQuestion,
                        onAnswerChange = onAnswerChange,
                        onUseSampleSpeaking = onUseSampleSpeaking,
                        onPlayAudio = onPlayAudio,
                        onSubmitAnswer = onSubmitAnswer,
                        onStartFresh = onStartFresh,
                    )
                }
            }

            LanguagePlacementStage.Evaluating -> {
                item { PlacementEvaluatingCard() }
            }

            LanguagePlacementStage.Report -> {
                item {
                    state.placementReport?.let { report ->
                        PlacementReportContent(
                            report = report,
                            onReturnHome = onReturnHome,
                            onOpenJourney = { onOpenArea(LanguageArea.Journey) },
                            onOpenIntro = onOpenIntro,
                        )
                    }
                }
            }

            LanguagePlacementStage.History -> {
                item {
                    PlacementHistoryContent(
                        state = state.placementHistory,
                        onOpenIntro = onOpenIntro,
                        onReturnHome = onReturnHome,
                    )
                }
            }
        }
    }
}

@Composable
private fun LanguagePageHeader(
    eyebrow: String,
    title: String,
    subtitle: String,
    icon: ImageVector,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    EduCard(
        containerColor = colors.primaryContainer,
        borderColor = colors.primary.copy(alpha = 0.26f),
        modifier = modifier,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.md),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(colors.surface, CircleShape),
            ) {
                Icon(icon, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.iconLg))
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = eyebrow,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
                Text(
                    text = title,
                    style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Text(
                    text = subtitle,
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
    }
}

@Composable
private fun LanguageDashboardHeader(access: LanguageAccess) {
    val colors = EduTheme.colors
    LanguagePageHeader(
        eyebrow = stringResource(R.string.ln01_access_eyebrow),
        title = stringResource(R.string.ln01_home_title),
        subtitle = stringResource(R.string.ln01_home_subtitle),
        icon = Icons.Filled.Language,
    )
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.padding(top = Spacing.sm),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
            StatusPill(
                label = access.status.label(),
                icon = Icons.Filled.Shield,
                contentColor = access.status.color(),
                containerColor = access.status.color().copy(alpha = 0.13f),
                modifier = Modifier.weight(1f),
            )
            access.overallLevel?.let {
                StatusPill(
                    label = stringResource(R.string.ln01_overall_value, it.code),
                    contentColor = colors.primary,
                    containerColor = colors.surface,
                    modifier = Modifier.weight(1f),
                )
            }
        }
        access.expiresAtLabel?.let { date ->
            StatusPill(
                label = stringResource(R.string.ln01_renews_on, date),
                contentColor = colors.textSecondary,
                containerColor = colors.surface,
            )
        }
    }
}

@Composable
private fun LanguagePaywallCard(
    access: LanguageAccess,
    isBusy: Boolean,
    onSubscribe: () -> Unit,
) {
    val product = access.product
    val colors = EduTheme.colors
    EduCard(borderColor = colors.primary.copy(alpha = 0.24f)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Icon(Icons.Filled.Lock, contentDescription = null, tint = colors.primary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(product.name, style = EduTheme.typography.title.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
                StatusPill(
                    label = stringResource(R.string.ln01_status_inactive),
                    contentColor = colors.warning,
                    containerColor = colors.highlightContainer,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }

        Text(
            text = product.description,
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.md),
        )

        Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.md)) {
            LanguageBullet(text = stringResource(R.string.ln01_paywall_bullet_exam))
            LanguageBullet(text = stringResource(R.string.ln01_paywall_bullet_path))
            LanguageBullet(text = stringResource(R.string.ln01_paywall_bullet_guardian))
        }

        Text(
            text = stringResource(R.string.ln01_paywall_price, product.priceLabel, numeral(product.termDays)),
            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.primary,
            modifier = Modifier.padding(top = Spacing.md),
        )

        PrimaryButton(
            text = stringResource(R.string.ln01_paywall_cta),
            onClick = onSubscribe,
            isLoading = isBusy,
            leadingIcon = Icons.Filled.PlayArrow,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )
    }
}

@Composable
private fun LanguageBullet(text: String) {
    Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = EduTheme.colors.success, modifier = Modifier.size(Sizing.icon))
        Text(text, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary, modifier = Modifier.weight(1f))
    }
}

@Composable
private fun LanguageModuleTabsRow(
    selectedArea: LanguageArea,
    onSelectArea: (LanguageArea) -> Unit,
) {
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        contentPadding = PaddingValues(horizontal = Spacing.xxs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        items(LanguageArea.entries, key = { it.routeSegment }) { area ->
            EduChip(
                label = stringResource(area.titleRes()),
                selected = selectedArea == area,
                onClick = { onSelectArea(area) },
                leadingIcon = area.icon(),
            )
        }
    }
}

@Composable
private fun LanguageNextStepCard(
    access: LanguageAccess,
    nextTitle: String,
    onOpenJourney: () -> Unit,
) {
    val rec = access.placementRecommendation
    val colors = EduTheme.colors
    EduCard(borderColor = colors.aiAccent.copy(alpha = 0.28f)) {
        Text(
            text = if (rec != null) stringResource(R.string.ln01_from_placement) else stringResource(R.string.ln01_next_step),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
        )
        Text(
            text = if (rec != null) {
                stringResource(R.string.ln01_start_here_focus, stringResource(rec.focusSkill.labelRes()))
            } else {
                stringResource(R.string.ln01_continue_path)
            },
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.sm),
        ) {
            Icon(Icons.Filled.Lightbulb, contentDescription = null, tint = colors.aiAccent, modifier = Modifier.size(Sizing.icon))
            Text(
                text = rec?.startingTopic ?: nextTitle,
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.weight(1f),
            )
        }
        if (!rec?.corrections.isNullOrEmpty()) {
            EduDivider(modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.sm))
            Text(stringResource(R.string.ln01_common_mistakes), style = EduTheme.typography.caption, color = colors.textSecondary)
            CorrectionList(corrections = rec?.corrections.orEmpty())
        }
        PrimaryButton(
            text = stringResource(R.string.ln01_go_learning_path),
            onClick = onOpenJourney,
            leadingIcon = Icons.Filled.Flag,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )
    }
}

@Composable
private fun LanguageProgressStrip(hub: LanguageHubSnapshot) {
    val access = hub.access
    val target = access.targetLevel?.code ?: stringResource(R.string.common_not_available)
    EduCard {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
            ProgressMetric(
                value = "${numeral(hub.learningPath.itemsCompleted)}/${numeral(hub.learningPath.itemsTotal)}",
                label = stringResource(R.string.ln01_lessons_done),
                modifier = Modifier.weight(1f),
            )
            ProgressMetric(
                value = stringResource(R.string.progress_percent, access.targetProgressPercent),
                label = stringResource(R.string.ln01_to_goal),
                valueColor = EduTheme.colors.success,
                modifier = Modifier.weight(1f),
            )
        }
        Spacer(modifier = Modifier.height(Spacing.sm))
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
            ProgressMetric(
                value = access.overallLevel?.code ?: stringResource(R.string.common_not_available),
                label = stringResource(R.string.ln01_overall_level_label),
                modifier = Modifier.weight(1f),
            )
            ProgressMetric(
                value = target,
                label = access.estimatedTimeToNextLevel?.let {
                    stringResource(R.string.ln01_target_eta, it)
                } ?: stringResource(R.string.ln01_target_level),
                valueColor = EduTheme.colors.warning,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun ProgressMetric(
    value: String,
    label: String,
    modifier: Modifier = Modifier,
    valueColor: Color = EduTheme.colors.textPrimary,
) {
    EduGroupedSurface(modifier = modifier, contentPadding = PaddingValues(Spacing.sm)) {
        Text(
            text = value,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = valueColor,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun LanguageLevelsSection(
    levels: List<LanguageSkillLevel>,
    access: LanguageAccess,
    onOpenPlacement: () -> Unit,
    onOpenPlacementHistory: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.ln01_your_levels),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textPrimary,
                )
                Text(
                    text = levelSummary(levels),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
            GhostButton(text = stringResource(R.string.ln01_results), onClick = onOpenPlacementHistory, leadingIcon = Icons.Filled.History, modifier = Modifier.weight(1f))
            GhostButton(text = stringResource(R.string.ln01_retake), onClick = onOpenPlacement, leadingIcon = Icons.Filled.Flag, modifier = Modifier.weight(1f))
        }
        levels.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
                row.forEach { level ->
                    SkillLevelCard(level = level, modifier = Modifier.weight(1f))
                }
                if (row.size == 1) Spacer(modifier = Modifier.weight(1f))
            }
        }
        access.nextAllowedRetakeDateLabel?.let { date ->
            Text(
                text = stringResource(R.string.ln01_next_retake, date),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textTertiary,
            )
        }
    }
}

@Composable
private fun SkillLevelCard(level: LanguageSkillLevel, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    val border = when {
        level.isStrength -> colors.success.copy(alpha = 0.34f)
        level.isFocus -> colors.warning.copy(alpha = 0.34f)
        else -> colors.border
    }
    EduCard(modifier = modifier, borderColor = border, contentPadding = PaddingValues(Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            Icon(level.skill.icon(), contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.icon))
            Text(
                text = stringResource(level.skill.labelRes()),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.weight(1f),
            )
        }
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.xs),
        ) {
            CefrBadge(level = level.level?.code ?: "—")
            Text(
                text = stringResource(R.string.ln01_growth_value, numeral(level.growthPercent)),
                style = EduTheme.typography.caption,
                color = colors.textTertiary,
            )
        }
    }
}

@Composable
private fun ContinueLearningDestinations(onSelectArea: (LanguageArea) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        SectionHeader(title = stringResource(R.string.ln01_continue_learning))
        Text(
            text = stringResource(R.string.ln01_continue_learning_subtitle),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
        )
        LanguageArea.entries.filterNot { it == LanguageArea.Home }.forEach { area ->
            LanguageDestinationRow(area = area, onClick = { onSelectArea(area) })
        }
    }
}

@Composable
private fun LanguageDestinationRow(area: LanguageArea, onClick: () -> Unit) {
    EduCard(onClick = onClick, onClickLabel = stringResource(area.titleRes()), contentPadding = PaddingValues(Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(area.tint().copy(alpha = 0.14f), CircleShape),
            ) {
                Icon(area.icon(), contentDescription = null, tint = area.tint(), modifier = Modifier.size(Sizing.icon))
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(area.titleRes()),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textPrimary,
                )
                Text(
                    text = stringResource(area.subtitleRes()),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = EduTheme.colors.textSecondary,
                modifier = Modifier.size(Sizing.icon),
            )
        }
    }
}

@Composable
private fun LanguageAreaFoundationCard(
    area: LanguageArea,
    access: LanguageAccess,
    onBackHome: () -> Unit,
    onOpenPlacementHistory: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard(borderColor = area.tint().copy(alpha = 0.3f)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(area.tint().copy(alpha = 0.14f), CircleShape),
            ) {
                Icon(area.icon(), contentDescription = null, tint = area.tint(), modifier = Modifier.size(Sizing.iconLg))
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(area.titleRes()),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(area.subtitleRes()),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        EduGroupedSurface(modifier = Modifier.padding(top = Spacing.md)) {
            Text(
                text = stringResource(R.string.ln_area_foundation_title),
                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
            )
            Text(
                text = stringResource(R.string.ln_area_foundation_body, stringResource(area.titleRes())),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
                access.overallLevel?.let {
                    CefrBadge(level = it.code)
                }
                access.targetLevel?.let {
                    StatusPill(label = stringResource(R.string.ln01_target_value, it.code), contentColor = colors.primary)
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.md)) {
            SecondaryButton(text = stringResource(R.string.ln_area_back_home), onClick = onBackHome, modifier = Modifier.weight(1f))
            GhostButton(text = stringResource(R.string.ln_area_review_placement), onClick = onOpenPlacementHistory, leadingIcon = Icons.Filled.History, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun LanguageSkillContent(
    area: LanguageArea,
    state: LanguageModuleUiState,
    viewModel: LanguageModuleViewModel,
    workspace: LanguageSkillWorkspace?,
    access: LanguageAccess,
    onBackHome: () -> Unit,
    onOpenPlacementHistory: () -> Unit,
) {
    if (workspace == null) {
        EduCard { InlineLoader() }
        return
    }
    when (area) {
        LanguageArea.Reading -> LanguageReadingExperience(
            overview = workspace.readingOverview,
            attempt = workspace.readingAttempt,
            result = workspace.readingResult,
            stage = state.readingStage,
            onStartPractice = { viewModel.startReadingPractice(LanguageReadingMode.Practice) },
            onStartReadiness = { viewModel.startReadingPractice(LanguageReadingMode.Readiness) },
            onAnswer = viewModel::updateReadingAnswer,
            onSubmit = viewModel::submitReading,
            onRetry = { viewModel.startReadingPractice(workspace.readingAttempt?.mode ?: LanguageReadingMode.Practice) },
            onBackOverview = viewModel::resetReading,
        )

        LanguageArea.Listening -> LanguageListeningExperience(
            workspace = workspace,
            selectedTab = state.listeningTab,
            onSelectTab = viewModel::selectListeningTab,
            onSelectGoal = viewModel::selectListeningGoal,
            onStartPractice = viewModel::startListeningPractice,
            onAnswer = viewModel::updateListeningAnswer,
            onSubmit = viewModel::submitListening,
            onRetry = viewModel::retryListening,
            onNext = viewModel::nextListeningLesson,
        )

        LanguageArea.Writing -> LanguageWritingExperience(
            workspace = workspace,
            selectedTab = state.writingTab,
            onSelectTab = viewModel::selectWritingTab,
            onSelectGoal = viewModel::selectWritingGoal,
            onStartPractice = viewModel::startWritingPractice,
            onDraft = viewModel::updateWritingDraft,
            onSubmitDraft = { viewModel.submitWritingDraft(complete = false) },
            onComplete = { viewModel.submitWritingDraft(complete = true) },
        )

        LanguageArea.Speaking -> LanguageSpeakingExperience(
            workspace = workspace,
            selectedTab = state.speakingTab,
            onSelectTab = viewModel::selectSpeakingTab,
            onStartLearning = viewModel::startSpeakingLearning,
            onAdvanceLesson = viewModel::advanceSpeakingLesson,
            onToggleRecording = viewModel::toggleSpeakingRecording,
            onTranscript = viewModel::updateSpeakingTranscript,
            onSubmitTurn = viewModel::submitSpeakingTurn,
            onResetConversation = viewModel::resetSpeakingConversation,
        )

        LanguageArea.Vocabulary -> LanguageVocabularyExperience(
            vocabulary = workspace.vocabulary,
            selectedTab = state.vocabularyTab,
            filter = state.vocabularyFilter,
            onSelectTab = viewModel::selectVocabularyTab,
            onSelectFilter = viewModel::selectVocabularyFilter,
            onGenerate = viewModel::generateVocabularyBatch,
            onToggleArabic = viewModel::toggleVocabularyArabic,
            onGrade = viewModel::gradeVocabularyCard,
            onLookup = viewModel::lookupVocabularyWord,
            onLoadChallenge = viewModel::loadVocabularyChallenge,
            onChallengeAnswer = viewModel::setVocabularyChallengeAnswer,
            onCheckChallenge = viewModel::checkVocabularyChallenge,
            onStartQuiz = viewModel::startDailyVocabularyQuiz,
            onQuizGuess = viewModel::updateDailyVocabularyGuess,
            onSubmitSpelling = viewModel::submitDailyVocabularySpelling,
            onScorePronunciation = viewModel::scoreDailyVocabularyPronunciation,
            onNextQuiz = viewModel::nextDailyVocabularyQuizWord,
        )

        LanguageArea.Journey -> LanguageJourneyExperience(
            journey = workspace.journey,
            session = workspace.journeySession,
            mode = state.journeyMode,
            onOpenStage = viewModel::openJourneyStage,
            onStartSession = viewModel::startJourneySession,
            onCompleteSession = viewModel::completeJourneySession,
            onBackHome = viewModel::returnToJourneyHome,
        )

        LanguageArea.Grammar -> LanguageGrammarExperience(
            grammar = workspace.grammar,
            lesson = workspace.grammarLesson,
            mode = state.grammarMode,
            onStartLesson = viewModel::startGrammarLesson,
            onBackRoadmap = viewModel::returnToGrammarRoadmap,
            onGoToPhase = viewModel::goToGrammarPhase,
            onAdvanceLesson = viewModel::advanceGrammarLesson,
            onPracticeAnswer = viewModel::updateGrammarPractice,
            onCheckPractice = viewModel::checkGrammarPractice,
            onTutorDraft = viewModel::updateGrammarTutorDraft,
            onAskTutor = viewModel::askGrammarTutor,
            onCompleteLesson = viewModel::completeGrammarLesson,
        )

        LanguageArea.Home -> LanguageAreaFoundationCard(
            area = area,
            access = access,
            onBackHome = onBackHome,
            onOpenPlacementHistory = onOpenPlacementHistory,
        )
    }
}

@Composable
private fun LanguageJourneyExperience(
    journey: LanguageJourneySnapshot,
    session: LanguageJourneySession?,
    mode: LanguageJourneyMode,
    onOpenStage: (String) -> Unit,
    onStartSession: () -> Unit,
    onCompleteSession: () -> Unit,
    onBackHome: () -> Unit,
) {
    when (mode) {
        LanguageJourneyMode.Home -> LanguageJourneyHomePanel(
            journey = journey,
            onOpenStage = onOpenStage,
            onStartSession = onStartSession,
        )

        LanguageJourneyMode.Session -> LanguageJourneySessionPanel(
            session = session,
            fallback = journey,
            onCompleteSession = onCompleteSession,
            onBackHome = onBackHome,
        )

        LanguageJourneyMode.Complete -> LanguageJourneyCompletePanel(
            journey = journey,
            session = session,
            onBackHome = onBackHome,
            onStartSession = onStartSession,
        )
    }
}

@Composable
@Suppress("UNUSED_PARAMETER")
private fun LanguageJourneyHomePanel(
    journey: LanguageJourneySnapshot,
    onOpenStage: (String) -> Unit,
    onStartSession: () -> Unit,
) {
    LanguageFocusedJourney(journey = journey, onStartSession = onStartSession)
}

@Composable
private fun JourneyLevelBlock(level: LanguageJourneyLevel, onOpenStage: (String) -> Unit) {
    EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), verticalAlignment = Alignment.CenterVertically) {
            CefrBadge(level = level.cefrLevel.code)
            StatusPill(label = stringResource(level.status.statusLabelRes()), contentColor = level.status.statusColor())
            Spacer(modifier = Modifier.weight(1f))
            Text(text = "${numeral(level.completedStages)}/${numeral(level.totalStages)}", style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
        }
        level.stages.forEach { stage ->
            JourneyStageRow(stage = stage, onOpenStage = onOpenStage)
        }
    }
}

@Composable
private fun JourneyStageRow(stage: LanguageJourneyStage, onOpenStage: (String) -> Unit) {
    EduCard(
        onClick = if (stage.status == LanguageTrackStatus.Locked) null else ({ onOpenStage(stage.grammarId) }),
        borderColor = stage.status.statusColor().copy(alpha = 0.24f),
        contentPadding = PaddingValues(Spacing.sm),
        modifier = Modifier.padding(top = Spacing.xs),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Icon(
                imageVector = if (stage.status == LanguageTrackStatus.Locked) Icons.Filled.Lock else Icons.Filled.Flag,
                contentDescription = null,
                tint = stage.status.statusColor(),
                modifier = Modifier.size(Sizing.iconSm),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(text = stage.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                Text(text = stage.mission.goal, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }
            StatusPill(label = stringResource(stage.status.statusLabelRes()), contentColor = stage.status.statusColor())
        }
    }
}

@Composable
private fun LanguageJourneySessionPanel(
    session: LanguageJourneySession?,
    fallback: LanguageJourneySnapshot,
    onCompleteSession: () -> Unit,
    onBackHome: () -> Unit,
) {
    val active = session ?: LanguageJourneySession(
        sessionId = "fallback",
        currentGrammarName = fallback.todayMission.focusGrammar,
        mission = fallback.todayMission,
        sections = fallback.previewSections,
    )
    LanguageDeepScene(text = "${active.mission.title} ${active.mission.scenario}", area = LanguageArea.Journey)
    Text(text = active.mission.title, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    active.sections.forEach { section ->
        val mark = if (section.completed) "✓" else "○"
        Text(
            text = "$mark  ${section.title}",
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = if (section.completed) EduTheme.colors.success else EduTheme.colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
    PrimaryButton(text = stringResource(R.string.ln6c_complete_session), onClick = onCompleteSession, leadingIcon = Icons.Filled.CheckCircle, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
    GhostButton(text = stringResource(R.string.ln6c_back_to_journey), onClick = onBackHome, modifier = Modifier.fillMaxWidth().padding(top = Spacing.xs))
}

@Composable
private fun JourneyMissionBlock(title: String, goal: String, grammar: String, minutes: Int) {
    EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
        Text(text = title, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
        Text(text = goal, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xs))
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            StatusPill(label = grammar, contentColor = EduTheme.colors.aiAccent)
            StatusPill(label = stringResource(R.string.ln6c_minutes_short, numeral(minutes)), contentColor = EduTheme.colors.primary)
        }
    }
}

@Composable
private fun LanguageJourneyCompletePanel(
    journey: LanguageJourneySnapshot,
    session: LanguageJourneySession?,
    onBackHome: () -> Unit,
    onStartSession: () -> Unit,
) {
    EduCard(borderColor = EduTheme.colors.success.copy(alpha = 0.32f)) {
        Text(text = stringResource(R.string.ln6c_mission_complete), style = EduTheme.typography.display.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.success)
        Text(text = session?.mission?.goal ?: journey.currentGoal, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SkillMetricCard(label = stringResource(R.string.ln6c_streak), value = numeral(journey.streakDays), modifier = Modifier.weight(1f))
            SkillMetricCard(label = stringResource(R.string.ln6c_journey), value = "${numeral(journey.completedStages)}/${numeral(journey.totalStages)}", modifier = Modifier.weight(1f))
        }
        Text(text = journey.nextMilestone, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.md))
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SecondaryButton(text = stringResource(R.string.ln6c_journey_home), onClick = onBackHome, modifier = Modifier.weight(1f))
            PrimaryButton(text = stringResource(R.string.ln6c_next_mission), onClick = onStartSession, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun LanguageGrammarExperience(
    grammar: LanguageGrammarSnapshot,
    lesson: LanguageGrammarLesson?,
    mode: LanguageGrammarMode,
    onStartLesson: (String?) -> Unit,
    onBackRoadmap: () -> Unit,
    onGoToPhase: (LanguageGrammarLessonPhase) -> Unit,
    onAdvanceLesson: () -> Unit,
    onPracticeAnswer: (String, String) -> Unit,
    onCheckPractice: (String) -> Unit,
    onTutorDraft: (String) -> Unit,
    onAskTutor: (String) -> Unit,
    onCompleteLesson: () -> Unit,
) {
    when (mode) {
        LanguageGrammarMode.Roadmap -> LanguageGrammarRoadmapPanel(
            grammar = grammar,
            onStartLesson = onStartLesson,
        )

        LanguageGrammarMode.Lesson -> LanguageGrammarLessonPanel(
            grammar = grammar,
            lesson = lesson,
            onBackRoadmap = onBackRoadmap,
            onGoToPhase = onGoToPhase,
            onAdvanceLesson = onAdvanceLesson,
            onPracticeAnswer = onPracticeAnswer,
            onCheckPractice = onCheckPractice,
            onTutorDraft = onTutorDraft,
            onAskTutor = onAskTutor,
            onCompleteLesson = onCompleteLesson,
        )

        LanguageGrammarMode.Complete -> LanguageGrammarCompletePanel(
            grammar = grammar,
            lesson = lesson,
            onBackRoadmap = onBackRoadmap,
            onStartLesson = onStartLesson,
        )
    }
}

@Composable
private fun LanguageGrammarRoadmapPanel(
    grammar: LanguageGrammarSnapshot,
    onStartLesson: (String?) -> Unit,
) {
    LanguageFocusedGrammarRoadmap(grammar = grammar, onStartLesson = onStartLesson)
}

@Composable
private fun GrammarStageRow(stage: LanguageGrammarStage, onStartLesson: (String?) -> Unit) {
    EduCard(
        onClick = if (stage.status == LanguageTrackStatus.Locked) null else ({ onStartLesson(stage.grammarId) }),
        borderColor = stage.status.statusColor().copy(alpha = 0.24f),
        contentPadding = PaddingValues(Spacing.sm),
        modifier = Modifier.padding(top = Spacing.xs),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Icon(
                imageVector = if (stage.status == LanguageTrackStatus.Locked) Icons.Filled.Lock else Icons.Filled.Insights,
                contentDescription = null,
                tint = stage.status.statusColor(),
                modifier = Modifier.size(Sizing.iconSm),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(text = stage.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                Text(text = stringResource(R.string.ln6c_grammar_stage_meta, stage.cefrLevel.code, numeral(stage.estimatedMinutes), numeral(stage.masteryPercent)), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
            }
            StatusPill(label = stringResource(stage.status.statusLabelRes()), contentColor = stage.status.statusColor())
        }
    }
}

@Composable
@Suppress("UNUSED_PARAMETER")
private fun LanguageGrammarLessonPanel(
    grammar: LanguageGrammarSnapshot,
    lesson: LanguageGrammarLesson?,
    onBackRoadmap: () -> Unit,
    onGoToPhase: (LanguageGrammarLessonPhase) -> Unit,
    onAdvanceLesson: () -> Unit,
    onPracticeAnswer: (String, String) -> Unit,
    onCheckPractice: (String) -> Unit,
    onTutorDraft: (String) -> Unit,
    onAskTutor: (String) -> Unit,
    onCompleteLesson: () -> Unit,
) {
    val active = lesson ?: return SkillIntroCard(
        icon = Icons.Filled.Insights,
        title = grammar.currentName,
        body = grammar.recommendation,
        action = stringResource(R.string.ln6c_start_lesson),
        onAction = { onGoToPhase(LanguageGrammarLessonPhase.Welcome) },
    )
    Text(
        text = stringResource(R.string.ln_deep_progress, numeral(active.phaseIndex + 1), numeral(active.phaseTotal)),
        style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
        color = EduTheme.colors.textSecondary,
    )
    when (active.phase) {
        LanguageGrammarLessonPhase.Welcome -> GrammarWelcomeStage(active, onAdvanceLesson)
        LanguageGrammarLessonPhase.Mission -> GrammarMissionStage(active, onAdvanceLesson)
        LanguageGrammarLessonPhase.Learn -> GrammarLearnStage(active, onAdvanceLesson)
        LanguageGrammarLessonPhase.Practice -> GrammarPracticeStage(active, onPracticeAnswer, onCheckPractice, onAdvanceLesson)
        LanguageGrammarLessonPhase.Speaking -> GrammarSimpleProductionStage(stringResource(R.string.ln6c_phase_speaking), active.speakingPrompt, Icons.Filled.Mic, onAdvanceLesson)
        LanguageGrammarLessonPhase.Writing -> GrammarSimpleProductionStage(stringResource(R.string.ln6c_phase_writing), active.writingPrompt, Icons.Filled.Edit, onAdvanceLesson)
        LanguageGrammarLessonPhase.Reflection -> GrammarReflectionStage(active, onCompleteLesson)
        LanguageGrammarLessonPhase.Complete -> GrammarCompleteStage(active, onBackRoadmap)
    }
    val examplePrompt = stringResource(R.string.ln6c_example_prompt)
    GhostButton(text = stringResource(R.string.ln_deep_ask_example), onClick = { onAskTutor(examplePrompt) }, modifier = Modifier.padding(top = Spacing.xs))
    active.tutorMessages.lastOrNull()?.let { message ->
        Text(text = message.content, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, maxLines = 2, modifier = Modifier.padding(top = Spacing.xxs))
    }
    GhostButton(text = stringResource(R.string.ln6c_back_to_roadmap), onClick = onBackRoadmap, modifier = Modifier.fillMaxWidth())
}

@Composable
private fun GrammarWelcomeStage(lesson: LanguageGrammarLesson, onNext: () -> Unit) {
    LanguageDeepScene(text = lesson.displayName, area = LanguageArea.Grammar)
    Text(text = lesson.displayName, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    Text(text = lesson.lessonGoal, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary, maxLines = 2, modifier = Modifier.padding(top = Spacing.xxs))
    PrimaryButton(text = stringResource(R.string.common_continue), onClick = onNext, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
}

@Composable
private fun GrammarMissionStage(lesson: LanguageGrammarLesson, onNext: () -> Unit) {
    LanguageDeepScene(text = lesson.missionLine, area = LanguageArea.Grammar)
    Text(text = lesson.missionLine, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    Text(text = lesson.whereUsed, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, maxLines = 2, modifier = Modifier.padding(top = Spacing.xxs))
    PrimaryButton(text = stringResource(R.string.ln6c_start_learning), onClick = onNext, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
}

@Composable
private fun GrammarLearnStage(lesson: LanguageGrammarLesson, onNext: () -> Unit) {
    LanguageDeepScene(text = lesson.displayName, area = LanguageArea.Grammar)
    Text(text = lesson.explanationBlocks.firstOrNull().orEmpty(), style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    lesson.examples.firstOrNull()?.let { example ->
        Text(text = example.corrected, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.primary, modifier = Modifier.padding(top = Spacing.sm))
    }
    PrimaryButton(text = stringResource(R.string.ln6c_practice), onClick = onNext, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
}

@Composable
private fun GrammarPracticeStage(
    lesson: LanguageGrammarLesson,
    onPracticeAnswer: (String, String) -> Unit,
    onCheckPractice: (String) -> Unit,
    onNext: () -> Unit,
) {
    var index by remember(lesson.lessonId) { mutableIntStateOf(0) }
    val item = lesson.practiceItems.getOrNull(index) ?: return
    LanguageDeepScene(text = item.prompt, area = LanguageArea.Grammar)
    GrammarPracticeItemBlock(index, item, onPracticeAnswer, onCheckPractice)
    if (item.checked) {
        LanguageShortFeedback(correct = item.correct, reason = item.feedback, correctAnswer = item.correctAnswer)
        PrimaryButton(
            text = stringResource(R.string.common_continue),
            onClick = {
                if (index >= lesson.practiceItems.lastIndex) onNext() else index += 1
            },
            enabled = if (index >= lesson.practiceItems.lastIndex) lesson.canContinuePractice else true,
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun GrammarPracticeItemBlock(
    index: Int,
    item: LanguageGrammarPracticeItem,
    onPracticeAnswer: (String, String) -> Unit,
    onCheckPractice: (String) -> Unit,
) {
    EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
        Text(text = stringResource(R.string.ln6c_question_number, numeral(index + 1)), style = EduTheme.typography.caption, color = EduTheme.colors.primary)
        Text(text = item.prompt, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
        when (item.type) {
            LanguageGrammarPracticeType.Choice -> ChoiceList(
                choices = item.choices,
                selected = item.choices.indexOfFirst { it == item.answer }.takeIf { it >= 0 },
                onSelect = { onPracticeAnswer(item.id, item.choices[it]) },
            )

            LanguageGrammarPracticeType.FillBlank -> EduTextField(
                value = item.answer,
                onValueChange = { onPracticeAnswer(item.id, it) },
                label = stringResource(R.string.ln6c_your_answer),
                placeholder = item.hint,
                modifier = Modifier.padding(top = Spacing.sm),
            )

            LanguageGrammarPracticeType.WordBank -> {
                SkillSubTabs(
                    labels = item.wordBank.map { it to it },
                    selected = "",
                    onSelect = { token -> onPracticeAnswer(item.id, (item.answer + " " + token).trim()) },
                )
                EduTextField(
                    value = item.answer,
                    onValueChange = { onPracticeAnswer(item.id, it) },
                    label = stringResource(R.string.ln6c_built_sentence),
                    placeholder = item.wordBank.joinToString(" "),
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
        }
        if (item.checked) {
            StatusPill(
                label = if (item.correct) stringResource(R.string.ln6c_correct) else stringResource(R.string.ln6c_review),
                contentColor = if (item.correct) EduTheme.colors.success else EduTheme.colors.warning,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(text = item.feedback, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xs))
        } else {
            Text(text = item.hint, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xs))
        }
        SecondaryButton(text = stringResource(R.string.ln6c_check), onClick = { onCheckPractice(item.id) }, enabled = item.answer.isNotBlank(), modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm))
    }
}

@Composable
private fun GrammarSimpleProductionStage(
    title: String,
    prompt: String,
    icon: ImageVector,
    onNext: () -> Unit,
) {
    LanguageDeepScene(text = prompt, area = LanguageArea.Grammar)
    Text(text = title, style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
    Text(text = prompt, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs))
    PrimaryButton(text = stringResource(R.string.common_continue), onClick = onNext, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
}

@Composable
private fun GrammarReflectionStage(lesson: LanguageGrammarLesson, onComplete: () -> Unit) {
    LanguageDeepScene(text = lesson.displayName, area = LanguageArea.Grammar)
    Text(text = lesson.reflectionPrompt, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    Text(text = lesson.summary, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, maxLines = 2, modifier = Modifier.padding(top = Spacing.xxs))
    PrimaryButton(text = stringResource(R.string.ln6c_finish_lesson), onClick = onComplete, leadingIcon = Icons.Filled.CheckCircle, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
}

@Composable
private fun GrammarCompleteStage(lesson: LanguageGrammarLesson, onBackRoadmap: () -> Unit) {
    EduCard(borderColor = EduTheme.colors.success.copy(alpha = 0.32f)) {
        Text(text = stringResource(R.string.ln6c_lesson_complete), style = EduTheme.typography.display.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.success)
        Text(text = lesson.summary, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
        StatusPill(
            label = stringResource(R.string.ln6c_practice_correct, numeral(lesson.correctPracticeCount), numeral(lesson.practiceItems.size)),
            contentColor = EduTheme.colors.success,
            modifier = Modifier.padding(top = Spacing.md),
        )
        PrimaryButton(text = stringResource(R.string.ln6c_back_to_roadmap), onClick = onBackRoadmap, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
    }
}

@Composable
private fun GrammarTutorPanel(
    lesson: LanguageGrammarLesson,
    onTutorDraft: (String) -> Unit,
    onAskTutor: (String) -> Unit,
) {
    EduCard(borderColor = EduTheme.colors.aiAccent.copy(alpha = 0.24f)) {
        SkillSectionHeader(title = stringResource(R.string.ln6c_ask_teacher), subtitle = stringResource(R.string.ln6c_embedded_help, lesson.displayName))
        lesson.tutorMessages.takeLast(3).forEach { message ->
            EduGroupedSurface(modifier = Modifier.padding(top = Spacing.xs)) {
                StatusPill(
                    label = if (message.role == "assistant") stringResource(R.string.ln6c_ai_teacher_label) else stringResource(R.string.ln6c_you),
                    contentColor = if (message.role == "assistant") EduTheme.colors.aiAccent else EduTheme.colors.primary,
                )
                Text(text = message.content, style = EduTheme.typography.caption, color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xs))
            }
        }
        EduTextField(
            value = lesson.tutorDraft,
            onValueChange = onTutorDraft,
            label = stringResource(R.string.ln6c_ask_about_lesson),
            placeholder = stringResource(R.string.ln6c_explain_last_example),
            modifier = Modifier.padding(top = Spacing.sm),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.sm)) {
            val examplePrompt = stringResource(R.string.ln6c_example_prompt)
            SecondaryButton(text = stringResource(R.string.ln6c_example), onClick = { onAskTutor(examplePrompt) }, modifier = Modifier.weight(1f))
            PrimaryButton(text = stringResource(R.string.ln6c_ask), onClick = { onAskTutor(lesson.tutorDraft) }, leadingIcon = Icons.Filled.Send, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun LanguageGrammarCompletePanel(
    grammar: LanguageGrammarSnapshot,
    lesson: LanguageGrammarLesson?,
    onBackRoadmap: () -> Unit,
    onStartLesson: (String?) -> Unit,
) {
    EduCard(borderColor = EduTheme.colors.success.copy(alpha = 0.32f)) {
        Text(text = stringResource(R.string.ln6c_grammar_updated), style = EduTheme.typography.display.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.success)
        Text(text = lesson?.summary ?: grammar.recommendation, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SkillMetricCard(label = stringResource(R.string.ln6c_mastery), value = "${numeral(grammar.masteryPercent)}%", modifier = Modifier.weight(1f))
            SkillMetricCard(label = stringResource(R.string.ln6c_completed), value = "${numeral(grammar.completedStages)}/${numeral(grammar.totalStages)}", modifier = Modifier.weight(1f))
        }
        LanguageBulletList(
            title = stringResource(R.string.ln6c_next_actions),
            items = listOf(
                stringResource(R.string.ln6c_review_mistakes),
                stringResource(R.string.ln6c_ask_tutor_followup),
                stringResource(R.string.ln6c_start_next_grammar, grammar.nextGrammarName),
            ),
            tint = EduTheme.colors.aiAccent,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SecondaryButton(text = stringResource(R.string.ln6c_roadmap), onClick = onBackRoadmap, modifier = Modifier.weight(1f))
            PrimaryButton(text = stringResource(R.string.ln6c_next_lesson), onClick = { onStartLesson(null) }, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun LanguageReadingExperience(
    overview: LanguageReadingOverview,
    attempt: LanguageReadingAttempt?,
    result: LanguageReadingResult?,
    stage: LanguageReadingStage,
    onStartPractice: () -> Unit,
    onStartReadiness: () -> Unit,
    onAnswer: (String, String) -> Unit,
    onSubmit: () -> Unit,
    onRetry: () -> Unit,
    onBackOverview: () -> Unit,
) {
    when (stage) {
        LanguageReadingStage.Overview -> {
            LanguageFocusedReading(attempt = null, onStartPractice = onStartPractice, onAnswer = onAnswer, onSubmit = onSubmit)
            if (overview.readinessAvailable) {
                GhostButton(text = stringResource(R.string.ln6b_readiness_test), onClick = onStartReadiness, modifier = Modifier.padding(top = Spacing.xs))
            }
        }

        LanguageReadingStage.Practice -> LanguageFocusedReading(
            attempt = attempt,
            onStartPractice = onStartPractice,
            onAnswer = onAnswer,
            onSubmit = onSubmit,
        )

        LanguageReadingStage.Results -> result?.let { reading ->
            EduCard {
                Text(
                    text = stringResource(R.string.ln6b_score_value, reading.scorePercent),
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                    color = if (reading.passed) EduTheme.colors.success else EduTheme.colors.warning,
                )
                Text(text = reading.nextAction, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xs), maxLines = 2)
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
                    SecondaryButton(text = stringResource(R.string.ln6b_retry), onClick = onRetry, modifier = Modifier.weight(1f))
                    PrimaryButton(text = stringResource(R.string.common_next), onClick = onBackOverview, modifier = Modifier.weight(1f))
                }
            }
        } ?: LanguageFocusedReading(attempt = null, onStartPractice = onStartPractice, onAnswer = onAnswer, onSubmit = onSubmit)
    }
}

@Composable
private fun LanguageReadingOverviewPanel(
    overview: LanguageReadingOverview,
    onStartPractice: () -> Unit,
    onStartReadiness: () -> Unit,
) {
    EduCard(borderColor = EduTheme.colors.primary.copy(alpha = 0.28f)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
            CefrBadge(level = overview.currentLevel.code)
            Column(modifier = Modifier.weight(1f)) {
                Text(text = stringResource(R.string.ln6b_reading_stage), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                Text(text = overview.currentStage, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
                Text(text = stringResource(R.string.ln6b_reading_subtitle), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
            }
            StatusPill(label = overview.status, contentColor = EduTheme.colors.primary)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SkillMetricCard(label = stringResource(R.string.ln6b_mastery), value = "${overview.masteryPercent}%")
            SkillMetricCard(label = stringResource(R.string.ln6b_evidence), value = "${overview.evidenceMet}/${overview.evidenceTotal}")
            SkillMetricCard(label = stringResource(R.string.ln6b_readiness), value = overview.readinessLabel)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            PrimaryButton(text = stringResource(R.string.ln6b_start_practice), onClick = onStartPractice, leadingIcon = Icons.Filled.PlayArrow, modifier = Modifier.weight(1f))
            SecondaryButton(text = stringResource(R.string.ln6b_readiness_test), onClick = onStartReadiness, enabled = overview.readinessAvailable, leadingIcon = Icons.Filled.Flag, modifier = Modifier.weight(1f))
        }
    }
    ReadingEvidencePanel(overview)
    ReadingPathPanel(overview)
    ReadingSidePanel(overview)
}

@Composable
private fun ReadingEvidencePanel(overview: LanguageReadingOverview) {
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_stage_evidence), subtitle = stringResource(R.string.ln6b_stage_evidence_subtitle))
        EduLinearProgress(progress = overview.evidenceMet.toFloat() / overview.evidenceTotal.toFloat(), modifier = Modifier.padding(top = Spacing.sm))
        LanguageBulletList(title = stringResource(R.string.ln6b_focus), items = overview.focusSubskills, tint = EduTheme.colors.warning)
        LanguageBulletList(title = stringResource(R.string.ln6b_need_more), items = overview.needMoreSubskills, tint = EduTheme.colors.aiAccent)
        if (overview.blockers.isEmpty()) {
            StatusPill(label = stringResource(R.string.ln6b_ready_to_progress), contentColor = EduTheme.colors.success, modifier = Modifier.padding(top = Spacing.sm))
        } else {
            LanguageBulletList(title = stringResource(R.string.ln6b_unlock_next), items = overview.blockers, tint = EduTheme.colors.warning)
        }
    }
}

@Composable
private fun ReadingPathPanel(overview: LanguageReadingOverview) {
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_reading_journey), subtitle = stringResource(R.string.ln6b_reading_journey_subtitle))
        overview.stages.chunked(3).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
                row.forEach { node ->
                    EduGroupedSurface(modifier = Modifier.weight(1f)) {
                        Text(text = node.level.code, style = EduTheme.typography.caption, color = EduTheme.colors.primary)
                        Text(text = node.stage, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                        Text(text = node.status, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                    }
                }
            }
        }
    }
}

@Composable
private fun ReadingSidePanel(overview: LanguageReadingOverview) {
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_readiness), subtitle = overview.readinessDetail)
        StatusPill(label = overview.readinessTarget, contentColor = EduTheme.colors.warning)
        LanguageBulletList(title = stringResource(R.string.ln6b_recent), items = overview.history.map { "${it.completedAtLabel}: ${it.scorePercent ?: 0}% ${it.title}" }, tint = EduTheme.colors.primary)
    }
}

@Composable
private fun LanguageReadingPracticePanel(
    attempt: LanguageReadingAttempt,
    onAnswer: (String, String) -> Unit,
    onSubmit: () -> Unit,
) {
    EduCard {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), verticalAlignment = Alignment.CenterVertically) {
            CefrBadge(level = attempt.level.code)
            StatusPill(label = attempt.stage, contentColor = EduTheme.colors.primary)
            Spacer(modifier = Modifier.weight(1f))
            Text(text = stringResource(R.string.ln6b_answered_count, attempt.answeredCount, attempt.questions.size), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
        }
        Text(text = attempt.topic, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.md))
        Text(text = attempt.title, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
        attempt.grammarFocus?.let {
            StatusPill(label = stringResource(R.string.ln6b_grammar_focus, it), contentColor = EduTheme.colors.aiAccent, modifier = Modifier.padding(top = Spacing.xs))
        }
        EduGroupedSurface(modifier = Modifier.padding(top = Spacing.md)) {
            Text(text = attempt.passage, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary)
        }
    }
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_questions), subtitle = stringResource(R.string.ln6b_questions_subtitle))
        attempt.questions.forEachIndexed { index, question ->
            ReadingQuestionBlock(index = index, question = question, answer = attempt.answers[question.id].orEmpty(), onAnswer = onAnswer)
        }
        PrimaryButton(text = stringResource(R.string.ln6b_submit_answers), onClick = onSubmit, enabled = attempt.canSubmit, leadingIcon = Icons.Filled.CheckCircle, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun ReadingQuestionBlock(
    index: Int,
    question: LanguageReadingQuestion,
    answer: String,
    onAnswer: (String, String) -> Unit,
) {
    EduGroupedSurface(modifier = Modifier.padding(bottom = Spacing.sm)) {
        Text(text = stringResource(R.string.ln6b_question_number, index + 1), style = EduTheme.typography.caption, color = EduTheme.colors.primary)
        Text(text = if (question.type == LanguageReadingQuestionType.GapFill) question.sentenceWithBlank.orEmpty() else question.stem, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
        Text(text = question.subskill, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
        when (question.type) {
            LanguageReadingQuestionType.Mcq -> ChoiceList(question.choices, selected = answer.toIntOrNull(), onSelect = { onAnswer(question.id, it.toString()) })
            LanguageReadingQuestionType.TrueFalse -> ChoiceList(question.choices, selected = question.choices.indexOfFirst { it.equals(answer, true) }.takeIf { it >= 0 }, onSelect = { onAnswer(question.id, question.choices[it].lowercase()) })
            LanguageReadingQuestionType.GapFill,
            LanguageReadingQuestionType.ShortAnswer -> EduTextField(value = answer, onValueChange = { onAnswer(question.id, it) }, label = stringResource(R.string.ln6b_your_answer), singleLine = question.type != LanguageReadingQuestionType.ShortAnswer, modifier = Modifier.padding(top = Spacing.sm))
        }
    }
}

@Composable
private fun LanguageReadingResultPanel(
    result: LanguageReadingResult,
    onRetry: () -> Unit,
    onBackOverview: () -> Unit,
) {
    EduCard(borderColor = if (result.passed) EduTheme.colors.success.copy(alpha = 0.35f) else EduTheme.colors.warning.copy(alpha = 0.35f)) {
        Text(text = stringResource(R.string.ln6b_score_value, result.scorePercent), style = EduTheme.typography.display.copy(fontWeight = FontWeight.ExtraBold), color = if (result.passed) EduTheme.colors.success else EduTheme.colors.warning)
        Text(text = result.nextAction, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
        result.questionResults.forEach { row ->
            EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
                StatusPill(label = if (row.correct) stringResource(R.string.ln6b_correct) else stringResource(R.string.ln6b_review), contentColor = if (row.correct) EduTheme.colors.success else EduTheme.colors.warning)
                Text(text = row.question.stem, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xs))
                Text(text = row.question.explanation, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SecondaryButton(text = stringResource(R.string.ln6b_retry), onClick = onRetry, modifier = Modifier.weight(1f))
            PrimaryButton(text = stringResource(R.string.ln6b_back_to_skill), onClick = onBackOverview, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
@Suppress("UNUSED_PARAMETER")
private fun LanguageListeningExperience(
    workspace: LanguageSkillWorkspace,
    selectedTab: LanguageListeningTab,
    onSelectTab: (LanguageListeningTab) -> Unit,
    onSelectGoal: (String) -> Unit,
    onStartPractice: () -> Unit,
    onAnswer: (String, Int) -> Unit,
    onSubmit: () -> Unit,
    onRetry: () -> Unit,
    onNext: () -> Unit,
) {
    LanguageFocusedListening(
        lesson = workspace.listeningLesson,
        onStartPractice = onStartPractice,
        onAnswer = onAnswer,
        onSubmit = onSubmit,
        onRetry = onRetry,
        onNext = onNext,
    )
}

@Composable
private fun LanguageListeningPracticePanel(
    lesson: LanguageListeningLesson?,
    onStartPractice: () -> Unit,
    onAnswer: (String, Int) -> Unit,
    onSubmit: () -> Unit,
    onRetry: () -> Unit,
    onNext: () -> Unit,
) {
    if (lesson == null) {
        SkillIntroCard(icon = Icons.Filled.Headphones, title = stringResource(R.string.ln6b_listening_intro), body = stringResource(R.string.ln6b_listening_intro_body), action = stringResource(R.string.ln6b_start_practice), onAction = onStartPractice)
        return
    }
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_mission), subtitle = lesson.coachSummary)
        LanguageBulletList(title = stringResource(R.string.ln6b_today_we_practice), items = lesson.focusItems, tint = EduTheme.colors.aiAccent)
        Text(text = lesson.whyThisLesson, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            StatusPill(label = lesson.levelLabel, contentColor = EduTheme.colors.primary)
            StatusPill(label = lesson.goalLabel, contentColor = EduTheme.colors.aiAccent)
        }
    }
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_audio_surface), subtitle = lesson.audioInstructions)
        EduGroupedSurface {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                Icon(Icons.Filled.VolumeUp, contentDescription = null, tint = EduTheme.colors.aiAccent, modifier = Modifier.size(Sizing.iconLg))
                Text(text = lesson.audioSituation, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary, modifier = Modifier.weight(1f))
            }
        }
        Text(text = stringResource(R.string.ln6b_answered_count, lesson.answeredCount, lesson.questions.size), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
    }
    if (lesson.result == null) {
        EduCard {
            ChoiceQuestionList(questions = lesson.questions, answers = lesson.answers, onAnswer = onAnswer)
            PrimaryButton(text = stringResource(R.string.ln6b_submit_answers), onClick = onSubmit, enabled = lesson.canSubmit, modifier = Modifier.fillMaxWidth())
        }
    } else {
        ListeningResultCard(lesson.result, onRetry, onNext)
    }
}

@Composable
private fun ListeningResultCard(result: com.rork.eduspark.data.model.LanguageListeningResult, onRetry: () -> Unit, onNext: () -> Unit) {
    EduCard(borderColor = EduTheme.colors.success.copy(alpha = 0.35f)) {
        Text(text = result.headline, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
        Text(text = stringResource(R.string.ln6b_score_value, result.scorePercent), style = EduTheme.typography.display.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.success)
        Text(text = result.summary, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
        LanguageBulletList(title = stringResource(R.string.ln6b_today_improved), items = result.improved, tint = EduTheme.colors.success)
        LanguageBulletList(title = stringResource(R.string.ln6b_needs_practice), items = result.needsPractice, tint = EduTheme.colors.warning)
        Text(text = result.nextLessonTeaser, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SecondaryButton(text = stringResource(R.string.ln6b_retry), onClick = onRetry, modifier = Modifier.weight(1f))
            PrimaryButton(text = stringResource(R.string.ln6b_next_clip), onClick = onNext, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
@Suppress("UNUSED_PARAMETER")
private fun LanguageWritingExperience(
    workspace: LanguageSkillWorkspace,
    selectedTab: LanguageWritingTab,
    onSelectTab: (LanguageWritingTab) -> Unit,
    onSelectGoal: (String) -> Unit,
    onStartPractice: () -> Unit,
    onDraft: (String) -> Unit,
    onSubmitDraft: () -> Unit,
    onComplete: () -> Unit,
) {
    LanguageFocusedWriting(
        lesson = workspace.writingLesson,
        onStartPractice = onStartPractice,
        onDraft = onDraft,
        onSubmitDraft = onSubmitDraft,
        onComplete = onComplete,
    )
}

@Composable
private fun LanguageWritingPracticePanel(
    lesson: LanguageWritingLesson?,
    onStartPractice: () -> Unit,
    onDraft: (String) -> Unit,
    onSubmitDraft: () -> Unit,
    onComplete: () -> Unit,
) {
    if (lesson == null) {
        SkillIntroCard(icon = Icons.Filled.Edit, title = stringResource(R.string.ln6b_writing_intro), body = stringResource(R.string.ln6b_writing_intro_body), action = stringResource(R.string.ln6b_generate_lesson), onAction = onStartPractice)
        return
    }
    if (lesson.completed) {
        EduCard(borderColor = EduTheme.colors.success.copy(alpha = 0.35f)) {
            SkillSectionHeader(title = stringResource(R.string.ln6b_writing_completed), subtitle = lesson.evaluation?.nextLesson.orEmpty())
            PrimaryButton(text = stringResource(R.string.ln6b_new_lesson), onClick = onStartPractice, leadingIcon = Icons.Filled.Edit, modifier = Modifier.fillMaxWidth())
        }
        return
    }
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_mission), subtitle = lesson.missionTitle)
        LanguageBulletList(title = stringResource(R.string.ln6b_today_goal), items = lesson.learningOutcomes, tint = EduTheme.colors.aiAccent)
        Text(text = lesson.writingContext, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
        StatusPill(label = "${lesson.officialLevel.code} · ${lesson.goal}", contentColor = EduTheme.colors.primary, modifier = Modifier.padding(top = Spacing.sm))
    }
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_prompt), subtitle = lesson.expectedOutput)
        Text(text = lesson.prompt, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
        LanguageBulletList(title = stringResource(R.string.ln6b_instructions), items = lesson.instructions, tint = EduTheme.colors.primary)
        LanguageBulletList(title = stringResource(R.string.ln6b_success_criteria), items = lesson.checklist, tint = EduTheme.colors.success)
        EduTextField(
            value = lesson.draftText,
            onValueChange = onDraft,
            label = stringResource(R.string.ln6b_editor_label),
            placeholder = stringResource(R.string.ln04_write_placeholder),
            singleLine = false,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        Text(text = stringResource(R.string.ln04_words_count, lesson.wordCount, lesson.minWords, lesson.maxWords), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xs))
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SecondaryButton(text = if (lesson.revisionNumber > 0) stringResource(R.string.ln6b_resubmit) else stringResource(R.string.ln6b_submit_draft), onClick = onSubmitDraft, enabled = lesson.canSubmit, modifier = Modifier.weight(1f))
            PrimaryButton(text = stringResource(R.string.ln6b_complete), onClick = onComplete, enabled = lesson.evaluation?.readyToComplete == true, modifier = Modifier.weight(1f))
        }
    }
    lesson.evaluation?.let { evaluation ->
        EduCard {
            SkillSectionHeader(title = stringResource(R.string.ln6b_evaluation), subtitle = evaluation.encouragement)
            evaluation.dimensions.forEach { dimension ->
                EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), verticalAlignment = Alignment.CenterVertically) {
                        Text(text = dimension.label, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary, modifier = Modifier.weight(1f))
                        Text(text = "${dimension.scorePercent}%", style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.primary)
                    }
                    EduLinearProgress(progress = dimension.scorePercent / 100f, modifier = Modifier.padding(top = Spacing.xs))
                    Text(text = dimension.note, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                }
            }
            LanguageBulletList(title = stringResource(R.string.ln05_strengths), items = evaluation.strengths, tint = EduTheme.colors.success)
            LanguageBulletList(title = stringResource(R.string.ln05_to_work_on), items = evaluation.improvements, tint = EduTheme.colors.warning)
            EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
                Text(text = evaluation.mainIssue, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                Text(text = evaluation.whyItMatters, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                Text(text = "${evaluation.beforeExample} → ${evaluation.afterExample}", style = EduTheme.typography.caption, color = EduTheme.colors.primary, modifier = Modifier.padding(top = Spacing.xs))
            }
        }
    }
}

@Composable
@Suppress("UNUSED_PARAMETER")
private fun LanguageSpeakingExperience(
    workspace: LanguageSkillWorkspace,
    selectedTab: LanguageSpeakingTab,
    onSelectTab: (LanguageSpeakingTab) -> Unit,
    onStartLearning: () -> Unit,
    onAdvanceLesson: () -> Unit,
    onToggleRecording: () -> Unit,
    onTranscript: (String) -> Unit,
    onSubmitTurn: () -> Unit,
    onResetConversation: () -> Unit,
) {
    LanguageFocusedSpeaking(
        session = workspace.speakingSession,
        onOpenDiscussion = { onSelectTab(LanguageSpeakingTab.Discussion) },
        onToggleRecording = onToggleRecording,
        onTranscript = onTranscript,
        onSubmitTurn = onSubmitTurn,
    )
}

@Composable
private fun SpeakingLessonPanel(
    lesson: LanguageSpeakingLesson?,
    onStartLearning: () -> Unit,
    onAdvanceLesson: () -> Unit,
) {
    if (lesson == null) {
        SkillIntroCard(icon = Icons.Filled.Mic, title = stringResource(R.string.ln6b_speaking_intro), body = stringResource(R.string.ln6b_speaking_intro_body), action = stringResource(R.string.ln6b_start_session), onAction = onStartLearning)
        return
    }
    EduCard {
        SkillSectionHeader(title = lesson.title, subtitle = lesson.currentSection)
        EduLinearProgress(progress = lesson.sectionIndex.toFloat() / lesson.sectionTotal.toFloat(), modifier = Modifier.padding(top = Spacing.sm))
        LanguageBulletList(title = stringResource(R.string.ln6b_vocabulary), items = lesson.vocabulary, tint = EduTheme.colors.success)
        LanguageBulletList(title = stringResource(R.string.ln6b_teaching_blocks), items = lesson.teachingBlocks, tint = EduTheme.colors.aiAccent)
        EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
            Text(text = lesson.miniPrepPrompt, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
        }
        PrimaryButton(
            text = if (lesson.readyForDiscussion) stringResource(R.string.ln6b_start_discussion) else stringResource(R.string.common_next),
            onClick = onAdvanceLesson,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )
    }
}

@Composable
private fun SpeakingDiscussionPanel(
    session: LanguageSpeakingSession?,
    onSelectTab: (LanguageSpeakingTab) -> Unit,
    onToggleRecording: () -> Unit,
    onTranscript: (String) -> Unit,
    onSubmitTurn: () -> Unit,
    onResetConversation: () -> Unit,
) {
    if (session == null) {
        SkillIntroCard(icon = Icons.Filled.Mic, title = stringResource(R.string.ln6b_discussion_intro), body = stringResource(R.string.ln6b_discussion_intro_body), action = stringResource(R.string.ln6b_start_discussion), onAction = { onSelectTab(LanguageSpeakingTab.Discussion) })
        return
    }
    EduCard {
        SkillSectionHeader(title = session.caseTitle, subtitle = session.setting)
        LanguageBulletList(title = stringResource(R.string.ln6b_characters), items = session.characterHooks, tint = EduTheme.colors.aiAccent)
    }
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_live_voice_discussion), subtitle = stringResource(R.string.ln6b_press_record))
        if (session.turns.isEmpty()) {
            Text(text = stringResource(R.string.ln6b_empty_speaking), style = EduTheme.typography.body, color = EduTheme.colors.textSecondary, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.lg))
        }
        session.turns.forEach { turn ->
            EduGroupedSurface(modifier = Modifier.padding(bottom = Spacing.sm)) {
                StatusPill(label = if (turn.role == "user") stringResource(R.string.ln6b_you) else "Alex", contentColor = if (turn.role == "user") EduTheme.colors.primary else EduTheme.colors.aiAccent)
                Text(text = turn.content, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xs))
                turn.correction?.let {
                    LanguageCorrectionRow(correction = it, tint = EduTheme.colors.warning)
                }
                if (turn.pronunciationScore != null) {
                    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.xs)) {
                        StatusPill(label = stringResource(R.string.ln6b_pronunciation_score, turn.pronunciationScore), contentColor = EduTheme.colors.success)
                        StatusPill(label = stringResource(R.string.ln6b_fluency_score, turn.fluencyScore ?: 0), contentColor = EduTheme.colors.primary)
                    }
                }
            }
        }
        EduTextField(value = session.transcriptDraft, onValueChange = onTranscript, label = stringResource(R.string.ln6b_transcript), placeholder = stringResource(R.string.ln6b_transcript_placeholder), singleLine = false)
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
            SecondaryButton(text = if (session.recording) stringResource(R.string.ln6b_stop_recording) else stringResource(R.string.ln6b_start_recording), onClick = onToggleRecording, leadingIcon = Icons.Filled.Mic, modifier = Modifier.weight(1f))
            PrimaryButton(text = stringResource(R.string.ln6b_send_voice), onClick = onSubmitTurn, leadingIcon = Icons.Filled.Send, modifier = Modifier.weight(1f))
        }
        GhostButton(text = stringResource(R.string.ln6b_new_conversation), onClick = onResetConversation, modifier = Modifier.padding(top = Spacing.xs))
    }
}

@Composable
private fun SpeakingAlexPanel(session: LanguageSpeakingSession?, onSelectTab: (LanguageSpeakingTab) -> Unit) {
    EduCard(borderColor = EduTheme.colors.aiAccent.copy(alpha = 0.35f)) {
        SkillSectionHeader(title = stringResource(R.string.ln6b_alex_title), subtitle = session?.caseTitle ?: stringResource(R.string.ln6b_alex_need_session))
        Text(text = stringResource(R.string.ln6b_alex_body), style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
        PrimaryButton(text = stringResource(R.string.ln6b_back_discussion), onClick = { onSelectTab(LanguageSpeakingTab.Discussion) }, leadingIcon = Icons.Filled.Mic, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
    }
}

@Composable
@Suppress("UNUSED_PARAMETER")
private fun LanguageVocabularyExperience(
    vocabulary: LanguageVocabularySnapshot,
    selectedTab: LanguageVocabularyTab,
    filter: LanguageVocabularyFilter,
    onSelectTab: (LanguageVocabularyTab) -> Unit,
    onSelectFilter: (LanguageVocabularyFilter) -> Unit,
    onGenerate: () -> Unit,
    onToggleArabic: (String) -> Unit,
    onGrade: (String, Int) -> Unit,
    onLookup: (String) -> Unit,
    onLoadChallenge: () -> Unit,
    onChallengeAnswer: (String, String) -> Unit,
    onCheckChallenge: () -> Unit,
    onStartQuiz: () -> Unit,
    onQuizGuess: (String) -> Unit,
    onSubmitSpelling: () -> Unit,
    onScorePronunciation: (Int) -> Unit,
    onNextQuiz: () -> Unit,
) {
    var extra by remember { mutableStateOf<String?>(null) }
    var showTools by remember { mutableStateOf(false) }
    LanguageFocusedVocabulary(
        vocabulary = vocabulary,
        onGenerate = onGenerate,
        onToggleArabic = onToggleArabic,
        onGrade = onGrade,
    )
    Box(modifier = Modifier.padding(top = Spacing.sm)) {
        GhostButton(text = stringResource(R.string.ln_deep_tools), onClick = { showTools = true })
        DropdownMenu(expanded = showTools, onDismissRequest = { showTools = false }) {
            DropdownMenuItem(text = { Text(stringResource(R.string.ln6b_tab_bank)) }, onClick = {
                showTools = false
                extra = "bank"
                onSelectTab(LanguageVocabularyTab.Bank)
            })
            DropdownMenuItem(text = { Text(stringResource(R.string.ln6b_lookup_word)) }, onClick = {
                showTools = false
                extra = "lookup"
                onLookup(vocabulary.lookup?.word ?: "practice")
            })
            DropdownMenuItem(text = { Text(stringResource(R.string.ln6b_daily_vocab_quiz)) }, onClick = {
                showTools = false
                extra = "quiz"
                onStartQuiz()
            })
            DropdownMenuItem(text = { Text(stringResource(R.string.ln6b_daily_challenge)) }, onClick = {
                showTools = false
                extra = "challenge"
                onLoadChallenge()
            })
        }
    }
    when (extra) {
        "bank" -> VocabularyBankPanel(vocabulary, filter, onSelectFilter, onToggleArabic, onGrade)
        "lookup" -> VocabularyLookupPanel(vocabulary = vocabulary, onLookup = onLookup)
        "quiz" -> DailyVocabularyQuizPanel(quiz = vocabulary.dailyQuiz, onStartQuiz = onStartQuiz, onGuess = onQuizGuess, onSubmitSpelling = onSubmitSpelling, onScorePronunciation = onScorePronunciation, onNext = onNextQuiz)
        "challenge" -> VocabularyChallengePanel(challenge = vocabulary.challenge, onLoad = onLoadChallenge, onAnswer = onChallengeAnswer, onCheck = onCheckChallenge)
    }
}

@Composable
private fun VocabularyDailyPanel(
    vocabulary: LanguageVocabularySnapshot,
    onGenerate: () -> Unit,
    onToggleArabic: (String) -> Unit,
    onGrade: (String, Int) -> Unit,
) {
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_vocab_generator), subtitle = stringResource(R.string.ln6b_vocab_generator_subtitle))
        PrimaryButton(text = stringResource(R.string.ln6b_generate_words), onClick = onGenerate, leadingIcon = Icons.Filled.AutoStories, modifier = Modifier.fillMaxWidth())
        Text(text = stringResource(R.string.ln6b_ai_words_left, vocabulary.metrics.remainingAiWordsToday), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xs))
        if (vocabulary.dailyGenerated) {
            val card = vocabulary.dailyWords.getOrNull(vocabulary.currentDailyIndex)
            if (card != null) {
                Text(text = stringResource(R.string.ln6b_today_index, vocabulary.currentDailyIndex + 1, vocabulary.dailyWords.size), style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.md))
                VocabularyWordCard(card = card, large = true, onToggleArabic = onToggleArabic, onGrade = onGrade)
            }
        } else {
            Text(text = stringResource(R.string.ln6b_vocab_generate_hint), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
        }
    }
}

@Composable
private fun VocabularyBankPanel(
    vocabulary: LanguageVocabularySnapshot,
    filter: LanguageVocabularyFilter,
    onSelectFilter: (LanguageVocabularyFilter) -> Unit,
    onToggleArabic: (String) -> Unit,
    onGrade: (String, Int) -> Unit,
) {
    EduCard {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            SkillMetricCard(label = stringResource(R.string.ln6b_total), value = vocabulary.metrics.totalWords.toString())
            SkillMetricCard(label = stringResource(R.string.ln6b_known), value = vocabulary.metrics.knownWords.toString())
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.sm)) {
            SkillMetricCard(label = stringResource(R.string.ln6b_due_today), value = vocabulary.metrics.dueToday.toString())
            SkillMetricCard(label = stringResource(R.string.ln6b_not_learned), value = vocabulary.metrics.newWords.toString())
        }
        Text(text = stringResource(R.string.ln6b_daily_goal, vocabulary.metrics.reviewedToday, vocabulary.metrics.dailyReviewGoal), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.md))
        EduLinearProgress(progress = vocabulary.metrics.reviewedToday.toFloat() / vocabulary.metrics.dailyReviewGoal.toFloat(), modifier = Modifier.padding(top = Spacing.xs))
        SkillSubTabs(labels = LanguageVocabularyFilter.entries.map { it to stringResource(it.titleRes()) }, selected = filter, onSelect = onSelectFilter)
    }
    val filtered = when (filter) {
        LanguageVocabularyFilter.All -> vocabulary.bankCards
        LanguageVocabularyFilter.Due -> vocabulary.bankCards.filter { it.due }
        LanguageVocabularyFilter.Difficult -> vocabulary.bankCards.filter { it.difficult }
    }
    filtered.forEach { card -> VocabularyWordCard(card = card, large = false, onToggleArabic = onToggleArabic, onGrade = onGrade) }
}

@Composable
private fun VocabularyWordCard(
    card: LanguageVocabularyCard,
    large: Boolean,
    onToggleArabic: (String) -> Unit,
    onGrade: (String, Int) -> Unit,
) {
    EduCard(borderColor = EduTheme.colors.success.copy(alpha = 0.25f)) {
        EduGroupedSurface {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                Box(contentAlignment = Alignment.Center, modifier = Modifier.size(if (large) 86.dp else 58.dp).background(EduTheme.colors.success.copy(alpha = 0.12f), RoundedCornerShape(Radius.sm))) {
                    Icon(Icons.Filled.School, contentDescription = null, tint = EduTheme.colors.success)
                }
                Column(modifier = Modifier.weight(1f)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically) {
                        Text(text = card.word.isolateBidi(), style = (if (large) EduTheme.typography.title else EduTheme.typography.bodyLg).copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(), color = EduTheme.colors.textPrimary)
                        CefrBadge(level = card.cefrLevel.code)
                    }
                    Text(text = card.partOfSpeech, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                    Text(text = card.example.isolateBidi(), style = EduTheme.typography.body.forEmbeddedRun(), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xs))
                }
            }
        }
        SecondaryButton(text = if (card.arabicRevealed) stringResource(R.string.ln6b_hide_arabic) else stringResource(R.string.ln6b_show_arabic), onClick = { onToggleArabic(card.id) }, modifier = Modifier.padding(top = Spacing.sm))
        if (card.arabicRevealed) {
            Text(text = card.translationAr, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
            Text(text = card.exampleAr, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            listOf(1 to R.string.ln6b_again, 3 to R.string.ln6b_hard, 4 to R.string.ln6b_good, 5 to R.string.ln6b_easy).forEach { (quality, label) ->
                GhostButton(text = stringResource(label), onClick = { onGrade(card.id, quality) }, modifier = Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun VocabularyLookupPanel(vocabulary: LanguageVocabularySnapshot, onLookup: (String) -> Unit) {
    var lookupDraft by remember { mutableStateOf(vocabulary.lookup?.word.orEmpty()) }
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_lookup_word), subtitle = stringResource(R.string.ln6b_lookup_subtitle))
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), verticalAlignment = Alignment.CenterVertically) {
            EduTextField(value = lookupDraft, onValueChange = { lookupDraft = it }, label = stringResource(R.string.ln6b_lookup_label), placeholder = stringResource(R.string.ln6b_lookup_placeholder), modifier = Modifier.weight(1f))
            PrimaryButton(text = stringResource(R.string.ln6b_analyze), onClick = { onLookup(lookupDraft.ifBlank { "practice" }) })
        }
        vocabulary.lookup?.let {
            EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
                Text(text = "${it.word} · ${it.partOfSpeech} · ${it.cefrLevel.code}", style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                Text(text = it.definition, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
                Text(text = it.exampleSentence, style = EduTheme.typography.caption, color = EduTheme.colors.primary)
                Text(text = it.pronunciationTip, style = EduTheme.typography.caption, color = EduTheme.colors.aiAccent)
            }
        }
    }
}

@Composable
private fun DailyVocabularyQuizPanel(
    quiz: LanguageDailyVocabQuiz,
    onStartQuiz: () -> Unit,
    onGuess: (String) -> Unit,
    onSubmitSpelling: () -> Unit,
    onScorePronunciation: (Int) -> Unit,
    onNext: () -> Unit,
) {
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_daily_vocab_quiz), subtitle = stringResource(R.string.ln6b_daily_vocab_quiz_subtitle))
        when {
            quiz.summary != null -> {
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    SkillMetricCard(label = stringResource(R.string.ln6b_spelling), value = "${quiz.summary.spellingCorrect}/${quiz.summary.spellingTotal}")
                    SkillMetricCard(label = stringResource(R.string.ln6b_pronunciation), value = "${quiz.summary.pronunciationAverage}%")
                }
            }
            !quiz.started -> PrimaryButton(text = if (quiz.alreadyCompletedToday) stringResource(R.string.ln6b_done_today) else stringResource(R.string.ln6b_start), onClick = onStartQuiz, enabled = !quiz.alreadyCompletedToday, modifier = Modifier.fillMaxWidth())
            else -> {
                val item = quiz.items.getOrNull(quiz.currentIndex)
                if (item != null) {
                    Text(text = stringResource(R.string.ln6b_word_count, quiz.currentIndex + 1, quiz.items.size), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                    if (quiz.phase == "spelling") {
                        Text(text = item.definition, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary)
                        Text(text = item.exampleMasked, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                        EduTextField(value = quiz.guess, onValueChange = onGuess, label = stringResource(R.string.ln6b_type_word), modifier = Modifier.padding(top = Spacing.sm))
                        PrimaryButton(text = stringResource(R.string.ln6b_check), onClick = onSubmitSpelling, enabled = quiz.guess.isNotBlank(), modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm))
                    } else {
                        Text(text = quiz.revealedWord, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
                        SecondaryButton(text = stringResource(R.string.ln6b_score_pronunciation), onClick = { onScorePronunciation(82) }, leadingIcon = Icons.Filled.VolumeUp)
                        PrimaryButton(text = if (quiz.currentIndex >= quiz.items.lastIndex) stringResource(R.string.ln6b_finish_quiz) else stringResource(R.string.common_next), onClick = onNext, modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm))
                    }
                }
            }
        }
    }
}

@Composable
private fun VocabularyChallengePanel(
    challenge: LanguageVocabularyChallenge?,
    onLoad: () -> Unit,
    onAnswer: (String, String) -> Unit,
    onCheck: () -> Unit,
) {
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_daily_challenge), subtitle = challenge?.contextHint ?: stringResource(R.string.ln6b_daily_challenge_subtitle))
        if (challenge == null) {
            PrimaryButton(text = stringResource(R.string.ln6b_start), onClick = onLoad, modifier = Modifier.fillMaxWidth())
            return@EduCard
        }
        Text(text = challenge.paragraphSegments.joinToString(" ____ "), style = EduTheme.typography.body, color = EduTheme.colors.textPrimary)
        challenge.blanks.forEach { blank ->
            SkillSubTabs(labels = challenge.optionsPool.map { it to it }, selected = challenge.answers[blank].orEmpty(), onSelect = { onAnswer(blank, it) })
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = Spacing.sm)) {
            PrimaryButton(text = stringResource(R.string.ln6b_check_answers), onClick = onCheck, modifier = Modifier.weight(1f))
            if (challenge.checked) {
                StatusPill(label = "${challenge.score}/${challenge.blanks.size}", contentColor = if (challenge.score == challenge.blanks.size) EduTheme.colors.success else EduTheme.colors.warning)
            }
        }
    }
}

@Composable
private fun <T> SkillSubTabs(
    labels: List<Pair<T, String>>,
    selected: T,
    onSelect: (T) -> Unit,
) {
    LazyRow(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        contentPadding = PaddingValues(vertical = Spacing.xs),
    ) {
        items(labels, key = { it.second }) { (value, label) ->
            EduChip(label = label, selected = value == selected, onClick = { onSelect(value) })
        }
    }
}

@Composable
private fun SkillSectionHeader(title: String, subtitle: String) {
    SectionHeader(title = title)
    if (subtitle.isNotBlank()) {
        Text(
            text = subtitle,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            modifier = Modifier.padding(bottom = Spacing.xs),
        )
    }
}

@Composable
private fun SkillJourneyHero(
    icon: ImageVector,
    title: String,
    level: String,
    stage: String,
    body: String,
    progress: Int,
    action: String,
    onAction: () -> Unit,
) {
    EduCard(borderColor = EduTheme.colors.aiAccent.copy(alpha = 0.25f)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.md)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(EduTheme.colors.aiAccent.copy(alpha = 0.14f), CircleShape),
            ) {
                Icon(icon, contentDescription = null, tint = EduTheme.colors.aiAccent, modifier = Modifier.size(Sizing.iconLg))
            }
            Column(modifier = Modifier.weight(1f)) {
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalAlignment = Alignment.CenterVertically) {
                    CefrBadge(level = level)
                    StatusPill(label = stage, contentColor = EduTheme.colors.primary)
                }
                Text(text = title, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xs))
                Text(text = body, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
            }
        }
        EduLinearProgress(progress = progress / 100f, modifier = Modifier.padding(top = Spacing.md))
        PrimaryButton(text = action, onClick = onAction, leadingIcon = Icons.Filled.PlayArrow, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
    }
}

@Composable
private fun SkillIntroCard(
    icon: ImageVector,
    title: String,
    body: String,
    action: String,
    onAction: () -> Unit,
) {
    EduCard {
        Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth()) {
            Icon(icon, contentDescription = null, tint = EduTheme.colors.aiAccent, modifier = Modifier.size(Sizing.avatarLg))
        }
        Text(text = title, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
        Text(text = body, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary, textAlign = TextAlign.Center, modifier = Modifier.padding(top = Spacing.xs))
        PrimaryButton(text = action, onClick = onAction, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
    }
}

@Composable
private fun SkillPromotionPanel(canStart: Boolean, progress: Int) {
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_promotion_title), subtitle = stringResource(R.string.ln6b_promotion_subtitle))
        EduLinearProgress(progress = progress / 100f, modifier = Modifier.padding(top = Spacing.sm))
        StatusPill(
            label = if (canStart) stringResource(R.string.ln6b_unlocked) else stringResource(R.string.ln6b_locked_more_practice),
            contentColor = if (canStart) EduTheme.colors.success else EduTheme.colors.warning,
            modifier = Modifier.padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun SkillMetricCard(label: String, value: String, modifier: Modifier = Modifier) {
    EduGroupedSurface(modifier = modifier) {
        Text(text = value, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary)
        Text(text = label, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
    }
}

@Composable
private fun LanguageBulletListCard(title: String, items: List<String>, tint: Color) {
    EduCard {
        LanguageBulletList(title = title, items = items, tint = tint)
    }
}

@Composable
private fun LanguageBulletList(title: String, items: List<String>, tint: Color) {
    if (items.isEmpty()) return
    Text(
        text = title,
        style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
        color = EduTheme.colors.textPrimary,
        modifier = Modifier.padding(top = Spacing.sm),
    )
    items.forEach { item ->
        Row(
            verticalAlignment = Alignment.Top,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.padding(top = Spacing.xs),
        ) {
            Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = tint, modifier = Modifier.size(Sizing.iconSm))
            Text(text = item, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun ChoiceList(
    choices: List<String>,
    selected: Int?,
    onSelect: (Int) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
        choices.forEachIndexed { index, choice ->
            EduChip(
                label = choice.isolateBidi(),
                selected = selected == index,
                onClick = { onSelect(index) },
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun ChoiceQuestionList(
    questions: List<LanguageChoiceQuestion>,
    answers: Map<String, Int>,
    onAnswer: (String, Int) -> Unit,
) {
    questions.forEachIndexed { index, question ->
        EduGroupedSurface(modifier = Modifier.padding(bottom = Spacing.sm)) {
            Text(text = stringResource(R.string.ln6b_question_number, index + 1), style = EduTheme.typography.caption, color = EduTheme.colors.primary)
            Text(text = question.stem.isolateBidi(), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold).forEmbeddedRun(), color = EduTheme.colors.textPrimary)
            ChoiceList(choices = question.choices, selected = answers[question.id], onSelect = { onAnswer(question.id, it) })
        }
    }
}

@Composable
private fun LanguageGoalPanel(activeGoalId: String, onSelectGoal: (String) -> Unit) {
    EduCard {
        SkillSectionHeader(title = stringResource(R.string.ln6b_goal_title), subtitle = stringResource(R.string.ln6b_goal_subtitle))
        SkillSubTabs(
            labels = listOf(
                "school" to stringResource(R.string.ln6b_goal_school),
                "travel" to stringResource(R.string.ln6b_goal_travel),
                "conversation" to stringResource(R.string.ln6b_goal_conversation),
            ),
            selected = activeGoalId,
            onSelect = onSelectGoal,
        )
    }
}

@Composable
private fun LanguageCorrectionRow(correction: LanguageCorrection, tint: Color) {
    EduGroupedSurface(modifier = Modifier.padding(top = Spacing.sm)) {
        Text(text = correction.original, style = EduTheme.typography.caption, color = EduTheme.colors.danger)
        Text(text = correction.corrected, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = tint)
        Text(text = correction.explanation, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
    }
}

@Composable
private fun PlacementIntroContent(
    access: LanguageAccess,
    selectedLevel: CefrLevel,
    isBusy: Boolean,
    onStartExam: () -> Unit,
    onSkipLevel: (CefrLevel) -> Unit,
    onSkipPlacement: () -> Unit,
    onOpenHistory: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
        LanguagePageHeader(
            eyebrow = stringResource(R.string.ln04_eyebrow),
            title = stringResource(R.string.ln04_title),
            subtitle = stringResource(R.string.ln04_subtitle),
            icon = Icons.Filled.Flag,
        )
        EduCard(borderColor = EduTheme.colors.primary.copy(alpha = 0.24f)) {
            Icon(
                Icons.Filled.School,
                contentDescription = null,
                tint = EduTheme.colors.primary,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .size(Sizing.stateIcon),
            )
            Text(
                text = stringResource(R.string.ln04_intro_title),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = EduTheme.colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                text = stringResource(R.string.ln04_intro_body),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.xs),
            )
            StatusPill(
                label = stringResource(R.string.ln04_timer_notice),
                icon = Icons.Filled.Timer,
                contentColor = EduTheme.colors.warning,
                containerColor = EduTheme.colors.highlightContainer,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(top = Spacing.md),
            )
            PlacementSkillPills(modifier = Modifier.padding(top = Spacing.md))
            PrimaryButton(
                text = stringResource(R.string.ln04_start_exam),
                onClick = onStartExam,
                isLoading = isBusy,
                leadingIcon = Icons.Filled.PlayArrow,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
        }
        PlacementInstructionsCard()
        PlacementSkipCard(
            selectedLevel = selectedLevel,
            isBusy = isBusy,
            onSkipLevel = onSkipLevel,
            onSkipPlacement = onSkipPlacement,
        )
        if (access.placementCompleted) {
            GhostButton(
                text = stringResource(R.string.ln01_results),
                onClick = onOpenHistory,
                leadingIcon = Icons.Filled.History,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun PlacementSkillPills(modifier: Modifier = Modifier) {
    val skills = listOf(LanguageSkill.Speaking, LanguageSkill.Listening, LanguageSkill.Reading, LanguageSkill.Writing)
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = modifier.fillMaxWidth()) {
        skills.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
                row.forEach { skill ->
                    EduGroupedSurface(modifier = Modifier.weight(1f), contentPadding = PaddingValues(Spacing.sm)) {
                        Icon(skill.icon(), contentDescription = null, tint = EduTheme.colors.primary)
                        Text(stringResource(skill.labelRes()), style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                        Text(stringResource(skill.placementHintRes()), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
                    }
                }
            }
        }
    }
}

@Composable
private fun PlacementInstructionsCard() {
    EduCard {
        Text(
            text = stringResource(R.string.ln04_instructions_title),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
        )
        Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.sm)) {
            InstructionRow(icon = Icons.Filled.School, text = stringResource(R.string.ln04_instruction_skills))
            InstructionRow(icon = Icons.Filled.TrendingUp, text = stringResource(R.string.ln04_instruction_adaptive))
            InstructionRow(icon = Icons.Filled.Mic, text = stringResource(R.string.ln04_instruction_speaking))
            InstructionRow(icon = Icons.Filled.Shield, text = stringResource(R.string.ln04_instruction_integrity))
        }
    }
}

@Composable
private fun InstructionRow(icon: ImageVector, text: String) {
    Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        Icon(icon, contentDescription = null, tint = EduTheme.colors.primary, modifier = Modifier.size(Sizing.icon))
        Text(text, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary, modifier = Modifier.weight(1f))
    }
}

@Composable
private fun PlacementSkipCard(
    selectedLevel: CefrLevel,
    isBusy: Boolean,
    onSkipLevel: (CefrLevel) -> Unit,
    onSkipPlacement: () -> Unit,
) {
    EduCard(borderColor = EduTheme.colors.border) {
        Text(
            text = stringResource(R.string.ln04_skip_title),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.ln04_skip_body),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            contentPadding = PaddingValues(vertical = Spacing.sm),
        ) {
            items(CefrLevel.entries, key = { it.code }) { level ->
                EduChip(
                    label = level.code,
                    selected = selectedLevel == level,
                    enabled = !isBusy,
                    onClick = { onSkipLevel(level) },
                )
            }
        }
        SecondaryButton(
            text = stringResource(R.string.ln04_skip_cta, selectedLevel.code),
            onClick = onSkipPlacement,
            enabled = !isBusy,
            isLoading = isBusy,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun PlacementExamRunner(
    attempt: LanguagePlacementAttempt?,
    answerDraft: String,
    playedAudioQuestionIds: Set<String>,
    onGoToQuestion: (Int) -> Unit,
    onAnswerChange: (String) -> Unit,
    onUseSampleSpeaking: () -> Unit,
    onPlayAudio: () -> Unit,
    onSubmitAnswer: () -> Unit,
    onStartFresh: () -> Unit,
) {
    if (attempt == null) {
        InlineLoader()
        return
    }
    val question = attempt.currentQuestion
    val answerReady = isAnswerReady(question, answerDraft, playedAudioQuestionIds)

    Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
        PlacementProgressCard(
            attempt = attempt,
            onGoToQuestion = onGoToQuestion,
        )
        PlacementQuestionCard(
            attempt = attempt,
            question = question,
            answerDraft = answerDraft,
            playedAudioQuestionIds = playedAudioQuestionIds,
            onAnswerChange = onAnswerChange,
            onUseSampleSpeaking = onUseSampleSpeaking,
            onPlayAudio = onPlayAudio,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
            GhostButton(text = stringResource(R.string.ln04_start_fresh), onClick = onStartFresh, modifier = Modifier.weight(1f))
            PrimaryButton(
                text = stringResource(if (attempt.isLastQuestion) R.string.ln04_submit_finish else R.string.ln04_submit_next),
                onClick = onSubmitAnswer,
                enabled = answerReady,
                leadingIcon = Icons.Filled.Send,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun PlacementProgressCard(
    attempt: LanguagePlacementAttempt,
    onGoToQuestion: (Int) -> Unit,
) {
    EduCard(contentPadding = PaddingValues(Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Text(
                text = stringResource(R.string.ln04_section_progress, numeral(attempt.answeredCount), numeral(attempt.questions.size)),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
            StatusPill(
                label = stringResource(R.string.ln04_time_remaining, numeral(attempt.totalMinutes)),
                icon = Icons.Filled.Timer,
                contentColor = EduTheme.colors.warning,
                containerColor = EduTheme.colors.highlightContainer,
            )
        }
        EduLinearProgress(progress = attempt.progress, modifier = Modifier.padding(top = Spacing.sm))
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            contentPadding = PaddingValues(top = Spacing.sm),
        ) {
            items(attempt.questions.size) { index ->
                val sectionQuestion = attempt.questions[index]
                val isAnswered = attempt.answers.containsKey(sectionQuestion.id)
                EduChip(
                    label = stringResource(sectionQuestion.section.skill().labelRes()),
                    selected = index == attempt.currentIndex,
                    onClick = { onGoToQuestion(index) },
                    leadingIcon = if (isAnswered) Icons.Filled.CheckCircle else sectionQuestion.section.skill().icon(),
                )
            }
        }
    }
}

@Composable
private fun PlacementQuestionCard(
    attempt: LanguagePlacementAttempt,
    question: LanguagePlacementQuestion,
    answerDraft: String,
    playedAudioQuestionIds: Set<String>,
    onAnswerChange: (String) -> Unit,
    onUseSampleSpeaking: () -> Unit,
    onPlayAudio: () -> Unit,
) {
    EduCard(borderColor = EduTheme.colors.primary.copy(alpha = 0.22f)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(40.dp)
                    .background(EduTheme.colors.primaryContainer, RoundedCornerShape(Radius.sm)),
            ) {
                Text(
                    text = numeral(attempt.currentIndex + 1),
                    style = EduTheme.typography.mono.copy(fontWeight = FontWeight.ExtraBold),
                    color = EduTheme.colors.primary,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(question.section.skill().labelRes()),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
                Text(
                    text = stringResource(R.string.ln04_question_count, numeral(attempt.currentIndex + 1), numeral(attempt.questions.size)),
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textPrimary,
                )
            }
            Icon(question.section.skill().icon(), contentDescription = null, tint = EduTheme.colors.primary)
        }
        Text(
            text = question.instructions,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.md),
        )
        when (question.type) {
            LanguagePlacementQuestionType.Speaking -> SpeakingQuestionBlock(
                question = question,
                answerDraft = answerDraft,
                onUseSampleSpeaking = onUseSampleSpeaking,
            )

            LanguagePlacementQuestionType.ListeningMcq -> ListeningQuestionBlock(
                question = question,
                selected = answerDraft.toIntOrNull(),
                hasPlayedAudio = playedAudioQuestionIds.contains(question.id),
                onPlayAudio = onPlayAudio,
                onAnswerChange = onAnswerChange,
            )

            LanguagePlacementQuestionType.ReadingMcq -> ReadingQuestionBlock(
                question = question,
                selected = answerDraft.toIntOrNull(),
                onAnswerChange = onAnswerChange,
            )

            LanguagePlacementQuestionType.Writing -> WritingQuestionBlock(
                question = question,
                answerDraft = answerDraft,
                onAnswerChange = onAnswerChange,
            )
        }
    }
}

@Composable
private fun SpeakingQuestionBlock(
    question: LanguagePlacementQuestion,
    answerDraft: String,
    onUseSampleSpeaking: () -> Unit,
) {
    Text(
        text = question.prompt,
        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
        color = EduTheme.colors.textPrimary,
        modifier = Modifier.padding(top = Spacing.sm),
    )
    EduGroupedSurface(modifier = Modifier.padding(top = Spacing.md)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(EduTheme.colors.aiAccentContainer, CircleShape),
            ) {
                Icon(Icons.Filled.Mic, contentDescription = null, tint = EduTheme.colors.aiAccent)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (answerDraft.isBlank()) stringResource(R.string.ln04_speaking_prompt) else stringResource(R.string.ln04_record_saved),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    color = EduTheme.colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.ln04_speaking_helper),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
            }
        }
        SecondaryButton(
            text = stringResource(R.string.ln04_record_answer),
            onClick = onUseSampleSpeaking,
            leadingIcon = Icons.Filled.Mic,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )
    }
}

@Composable
private fun ListeningQuestionBlock(
    question: LanguagePlacementQuestion,
    selected: Int?,
    hasPlayedAudio: Boolean,
    onPlayAudio: () -> Unit,
    onAnswerChange: (String) -> Unit,
) {
    EduGroupedSurface(modifier = Modifier.padding(top = Spacing.md)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Icon(Icons.Filled.VolumeUp, contentDescription = null, tint = EduTheme.colors.primary, modifier = Modifier.size(Sizing.iconLg))
            Column(modifier = Modifier.weight(1f)) {
                Text(stringResource(R.string.ln04_audio_title), style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                Text(question.audioSituation.orEmpty(), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
            }
        }
        SecondaryButton(
            text = stringResource(if (hasPlayedAudio) R.string.ln04_audio_unlocked else R.string.ln04_audio_cta),
            onClick = onPlayAudio,
            leadingIcon = Icons.Filled.Headphones,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
    }
    Text(
        text = if (hasPlayedAudio) question.prompt else stringResource(R.string.ln04_listen_first),
        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
        color = EduTheme.colors.textPrimary,
        modifier = Modifier.padding(top = Spacing.md),
    )
    OptionList(
        options = question.options,
        selected = selected,
        enabled = hasPlayedAudio,
        onSelect = { onAnswerChange(it.toString()) },
    )
}

@Composable
private fun ReadingQuestionBlock(
    question: LanguagePlacementQuestion,
    selected: Int?,
    onAnswerChange: (String) -> Unit,
) {
    question.passage?.let { passage ->
        EduGroupedSurface(modifier = Modifier.padding(top = Spacing.md)) {
            Text(stringResource(R.string.ln04_reading_passage), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
            Text(passage, style = EduTheme.typography.body, color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xs))
        }
    }
    Text(
        text = question.prompt,
        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
        color = EduTheme.colors.textPrimary,
        modifier = Modifier.padding(top = Spacing.md),
    )
    OptionList(options = question.options, selected = selected, onSelect = { onAnswerChange(it.toString()) })
}

@Composable
private fun WritingQuestionBlock(
    question: LanguagePlacementQuestion,
    answerDraft: String,
    onAnswerChange: (String) -> Unit,
) {
    Text(
        text = question.prompt,
        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold),
        color = EduTheme.colors.textPrimary,
        modifier = Modifier.padding(top = Spacing.md),
    )
    EduTextField(
        value = answerDraft,
        onValueChange = onAnswerChange,
        label = stringResource(R.string.ln04_write_answer),
        placeholder = stringResource(R.string.ln04_write_placeholder),
        singleLine = false,
        labelPlacement = FieldLabelPlacement.Above,
        supportingText = stringResource(
            R.string.ln04_words_count,
            numeral(wordCount(answerDraft)),
            numeral(question.minWords ?: 0),
            numeral(question.maxWords ?: 0),
        ),
        modifier = Modifier.padding(top = Spacing.md),
    )
}

@Composable
private fun OptionList(
    options: List<String>,
    selected: Int?,
    enabled: Boolean = true,
    onSelect: (Int) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
        options.forEachIndexed { index, option ->
            PlacementOptionRow(
                index = index,
                option = option,
                selected = selected == index,
                enabled = enabled,
                onSelect = { onSelect(index) },
            )
        }
    }
}

@Composable
private fun PlacementOptionRow(
    index: Int,
    option: String,
    selected: Boolean,
    enabled: Boolean,
    onSelect: () -> Unit,
) {
    val colors = EduTheme.colors
    EduCard(
        onClick = if (enabled) onSelect else null,
        borderColor = if (selected) colors.primary else colors.border,
        containerColor = when {
            selected -> colors.primaryContainer
            !enabled -> colors.neutralAlpha100
            else -> colors.surface
        },
        contentPadding = PaddingValues(Spacing.sm),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(32.dp)
                    .background(if (selected) colors.primary else colors.neutralAlpha100, RoundedCornerShape(Radius.sm)),
            ) {
                Text(
                    text = optionLetter(index),
                    style = EduTheme.typography.mono.copy(fontWeight = FontWeight.Bold),
                    color = if (selected) colors.onPrimary else colors.textSecondary,
                )
            }
            Text(option, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun PlacementEvaluatingCard() {
    EduCard {
        InlineLoader()
        Text(
            text = stringResource(R.string.ln04_evaluating_title),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.Bold),
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        Text(
            text = stringResource(R.string.ln04_evaluating_body),
            style = EduTheme.typography.body,
            color = EduTheme.colors.textSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun PlacementReportContent(
    report: LanguagePlacementReport,
    onReturnHome: () -> Unit,
    onOpenJourney: () -> Unit,
    onOpenIntro: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
        EduCard(borderColor = EduTheme.colors.primary.copy(alpha = 0.32f)) {
            Text(
                text = stringResource(R.string.ln05_overall_level),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(top = Spacing.xs)
                    .size(Sizing.heroBadge)
                    .background(EduTheme.colors.primary, RoundedCornerShape(Radius.md)),
            ) {
                Text(
                    text = report.overallLevel.code,
                    style = EduTheme.typography.display.copy(fontWeight = FontWeight.ExtraBold),
                    color = EduTheme.colors.onPrimary,
                )
            }
            StatusPill(
                label = stringResource(R.string.ln05_confidence, numeral(report.confidencePercent)),
                icon = Icons.Filled.Shield,
                contentColor = EduTheme.colors.success,
                containerColor = EduTheme.colors.success.copy(alpha = 0.13f),
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .padding(top = Spacing.sm),
            )
            Text(
                text = report.summary,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }

        PlacementSkillResultGrid(results = report.skillResults)
        PlacementReportHighlights(report = report)
        ReportTextSection(title = stringResource(R.string.ln05_strengths), items = report.strengths, tint = EduTheme.colors.success)
        ReportTextSection(title = stringResource(R.string.ln05_to_work_on), items = report.weaknesses, tint = EduTheme.colors.warning)
        ReportCorrections(corrections = report.corrections)
        ReportTextSection(title = stringResource(R.string.ln05_study_plan), items = report.recommendations, tint = EduTheme.colors.primary)
        EduCard(borderColor = EduTheme.colors.aiAccent.copy(alpha = 0.28f)) {
            Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                Icon(Icons.Filled.Lightbulb, contentDescription = null, tint = EduTheme.colors.aiAccent)
                Column(modifier = Modifier.weight(1f)) {
                    Text(stringResource(R.string.ln05_start_here), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                    Text(report.recommendedStartingTopic, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary)
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
            PrimaryButton(text = stringResource(R.string.ln05_go_home), onClick = onReturnHome, leadingIcon = Icons.Filled.Language, modifier = Modifier.weight(1f))
            SecondaryButton(text = stringResource(R.string.ln05_open_journey), onClick = onOpenJourney, leadingIcon = Icons.Filled.Flag, modifier = Modifier.weight(1f))
        }
        GhostButton(text = stringResource(R.string.ln05_retake), onClick = onOpenIntro, leadingIcon = Icons.Filled.History, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun PlacementSkillResultGrid(results: List<LanguagePlacementSkillResult>) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        results.chunked(2).forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
                row.forEach { result ->
                    SkillResultCard(result = result, modifier = Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun SkillResultCard(result: LanguagePlacementSkillResult, modifier: Modifier = Modifier) {
    EduCard(modifier = modifier, contentPadding = PaddingValues(Spacing.sm)) {
        Icon(result.skill.icon(), contentDescription = null, tint = EduTheme.colors.primary, modifier = Modifier.align(Alignment.CenterHorizontally))
        Text(
            text = stringResource(result.skill.labelRes()),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        Text(
            text = result.level.code,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        EduLinearProgress(progress = result.scorePercent / 100f, modifier = Modifier.padding(top = Spacing.xs))
        Text(
            text = stringResource(R.string.ln05_skill_score, numeral(result.scorePercent), result.evidence),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun PlacementReportHighlights(report: LanguagePlacementReport) {
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.fillMaxWidth()) {
        ReportMiniMetric(
            label = stringResource(R.string.ln05_strongest),
            value = stringResource(report.strongestSkill.labelRes()),
            tint = EduTheme.colors.success,
            modifier = Modifier.weight(1f),
        )
        ReportMiniMetric(
            label = stringResource(R.string.ln05_focus_skill),
            value = stringResource(report.weakestSkill.labelRes()),
            tint = EduTheme.colors.warning,
            modifier = Modifier.weight(1f),
        )
    }
    ReportMiniMetric(
        label = stringResource(R.string.ln05_eta),
        value = stringResource(R.string.ln05_eta_weeks, numeral(report.weeksToNextLevel)),
        tint = EduTheme.colors.primary,
    )
}

@Composable
private fun ReportMiniMetric(label: String, value: String, tint: Color, modifier: Modifier = Modifier) {
    EduCard(modifier = modifier, borderColor = tint.copy(alpha = 0.22f), contentPadding = PaddingValues(Spacing.sm)) {
        Text(label, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
        Text(value, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
    }
}

@Composable
private fun ReportTextSection(title: String, items: List<String>, tint: Color) {
    if (items.isEmpty()) return
    EduCard(borderColor = tint.copy(alpha = 0.22f)) {
        Text(title, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
        Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            items.forEachIndexed { index, item ->
                Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                    Text("${numeral(index + 1)}.", style = EduTheme.typography.mono, color = tint)
                    Text(item, style = EduTheme.typography.body, color = EduTheme.colors.textSecondary, modifier = Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun ReportCorrections(corrections: List<LanguageCorrection>) {
    if (corrections.isEmpty()) return
    EduCard(borderColor = EduTheme.colors.aiAccent.copy(alpha = 0.24f)) {
        Text(stringResource(R.string.ln05_language_feedback), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
        CorrectionList(corrections = corrections)
    }
}

@Composable
private fun CorrectionList(corrections: List<LanguageCorrection>) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
        corrections.forEach { correction ->
            EduGroupedSurface(contentPadding = PaddingValues(Spacing.sm)) {
                Text(correction.original, style = EduTheme.typography.body, color = EduTheme.colors.danger)
                Text(correction.corrected, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.success)
                Text(correction.explanation, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))
            }
        }
    }
}

@Composable
private fun PlacementHistoryContent(
    state: UiState<List<LanguagePlacementHistory>>,
    onOpenIntro: () -> Unit,
    onReturnHome: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.md)) {
        LanguagePageHeader(
            eyebrow = stringResource(R.string.ln04_eyebrow),
            title = stringResource(R.string.ln06_title),
            subtitle = stringResource(R.string.ln06_subtitle),
            icon = Icons.Filled.History,
        )
        when (state) {
            UiState.Loading -> {
                SkeletonCard()
                SkeletonListItem()
            }

            is UiState.Failure -> MessageState(
                icon = Icons.Filled.History,
                title = stringResource(R.string.state_error_unknown_title),
                body = stringResource(R.string.state_error_unknown_body),
            )

            is UiState.Empty -> MessageState(
                icon = Icons.Filled.History,
                title = stringResource(R.string.ln06_empty_title),
                body = stringResource(R.string.ln06_empty_body),
            )

            is UiState.Content -> {
                if (state.data.isEmpty()) {
                    MessageState(
                        icon = Icons.Filled.History,
                        title = stringResource(R.string.ln06_empty_title),
                        body = stringResource(R.string.ln06_empty_body),
                    )
                } else {
                    state.data.forEach { history ->
                        PlacementHistoryCard(history = history)
                    }
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.fillMaxWidth()) {
            PrimaryButton(text = stringResource(R.string.ln05_go_home), onClick = onReturnHome, modifier = Modifier.weight(1f))
            SecondaryButton(text = stringResource(R.string.ln05_retake), onClick = onOpenIntro, modifier = Modifier.weight(1f))
        }
    }
}

@Composable
private fun PlacementHistoryCard(history: LanguagePlacementHistory) {
    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Column(modifier = Modifier.weight(1f)) {
                Text(stringResource(R.string.ln06_result_title), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textPrimary)
                Text("${history.completedAtLabel} · ${history.source}", style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
            }
            CefrBadge(level = history.overallLevel.code)
        }
        Spacer(modifier = Modifier.height(Spacing.sm))
        PlacementSkillResultGrid(results = history.skillResults)
    }
}

@Composable
private fun LanguageFoundationSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        repeat(3) { SkeletonListItem() }
        SkeletonCard()
    }
}

@Composable
private fun LanguageAccessStatus.label(): String = when (this) {
    LanguageAccessStatus.Active -> stringResource(R.string.ln01_status_active)
    LanguageAccessStatus.ExpiringSoon -> stringResource(R.string.ln01_status_expiring)
    LanguageAccessStatus.Expired -> stringResource(R.string.ln01_status_expired)
    LanguageAccessStatus.Pending -> stringResource(R.string.ln01_status_inactive)
}

@Composable
private fun LanguageAccessStatus.color(): Color = when (this) {
    LanguageAccessStatus.Active -> EduTheme.colors.success
    LanguageAccessStatus.ExpiringSoon -> EduTheme.colors.warning
    LanguageAccessStatus.Expired -> EduTheme.colors.danger
    LanguageAccessStatus.Pending -> EduTheme.colors.warning
}

@StringRes
internal fun LanguageArea.titleRes(): Int = when (this) {
    LanguageArea.Home -> R.string.ln_area_home
    LanguageArea.Reading -> R.string.ln_area_reading
    LanguageArea.Listening -> R.string.ln_area_listening
    LanguageArea.Writing -> R.string.ln_area_writing
    LanguageArea.Speaking -> R.string.ln_area_speaking
    LanguageArea.Vocabulary -> R.string.ln_area_vocabulary
    LanguageArea.Journey -> R.string.ln_area_journey
    LanguageArea.Grammar -> R.string.ln_area_grammar
}

private fun LanguageListeningTab.titleRes(): Int = when (this) {
    LanguageListeningTab.Journey -> R.string.ln6b_tab_journey
    LanguageListeningTab.Practice -> R.string.ln6b_tab_practice
    LanguageListeningTab.Promotion -> R.string.ln6b_tab_promotion
}

private fun LanguageWritingTab.titleRes(): Int = when (this) {
    LanguageWritingTab.Journey -> R.string.ln6b_tab_journey
    LanguageWritingTab.Practice -> R.string.ln6b_tab_practice
    LanguageWritingTab.Promotion -> R.string.ln6b_tab_promotion
}

private fun LanguageSpeakingTab.titleRes(): Int = when (this) {
    LanguageSpeakingTab.Journey -> R.string.ln6b_tab_journey
    LanguageSpeakingTab.Lesson -> R.string.ln6b_tab_lesson
    LanguageSpeakingTab.Discussion -> R.string.ln6b_tab_discussion
    LanguageSpeakingTab.Alex -> R.string.ln6b_tab_alex
    LanguageSpeakingTab.Assessment -> R.string.ln6b_tab_assessment
}

private fun LanguageVocabularyTab.titleRes(): Int = when (this) {
    LanguageVocabularyTab.Daily -> R.string.ln6b_tab_daily
    LanguageVocabularyTab.Bank -> R.string.ln6b_tab_bank
}

private fun LanguageVocabularyFilter.titleRes(): Int = when (this) {
    LanguageVocabularyFilter.All -> R.string.ln6b_filter_all
    LanguageVocabularyFilter.Due -> R.string.ln6b_filter_due
    LanguageVocabularyFilter.Difficult -> R.string.ln6b_filter_difficult
}

@StringRes
private fun LanguageTrackStatus.statusLabelRes(): Int = when (this) {
    LanguageTrackStatus.Completed -> R.string.ln6c_status_completed
    LanguageTrackStatus.Current -> R.string.ln6c_status_current
    LanguageTrackStatus.Open -> R.string.ln6c_status_open
    LanguageTrackStatus.Locked -> R.string.ln6c_status_locked
}

@Composable
private fun LanguageTrackStatus.statusColor(): Color = when (this) {
    LanguageTrackStatus.Completed -> EduTheme.colors.success
    LanguageTrackStatus.Current -> EduTheme.colors.aiAccent
    LanguageTrackStatus.Open -> EduTheme.colors.primary
    LanguageTrackStatus.Locked -> EduTheme.colors.textSecondary
}

@StringRes
private fun LanguageGrammarLessonPhase.phaseLabelRes(): Int = when (this) {
    LanguageGrammarLessonPhase.Welcome -> R.string.ln6c_phase_welcome
    LanguageGrammarLessonPhase.Mission -> R.string.ln6c_phase_mission
    LanguageGrammarLessonPhase.Learn -> R.string.ln6c_phase_learn
    LanguageGrammarLessonPhase.Practice -> R.string.ln6c_phase_practice
    LanguageGrammarLessonPhase.Speaking -> R.string.ln6c_phase_speaking
    LanguageGrammarLessonPhase.Writing -> R.string.ln6c_phase_writing
    LanguageGrammarLessonPhase.Reflection -> R.string.ln6c_phase_reflection
    LanguageGrammarLessonPhase.Complete -> R.string.ln6c_phase_complete
}

@StringRes
private fun LanguageArea.subtitleRes(): Int = when (this) {
    LanguageArea.Home -> R.string.ln_area_home_subtitle
    LanguageArea.Reading -> R.string.ln_area_reading_subtitle
    LanguageArea.Listening -> R.string.ln_area_listening_subtitle
    LanguageArea.Writing -> R.string.ln_area_writing_subtitle
    LanguageArea.Speaking -> R.string.ln_area_speaking_subtitle
    LanguageArea.Vocabulary -> R.string.ln_area_vocabulary_subtitle
    LanguageArea.Journey -> R.string.ln_area_journey_subtitle
    LanguageArea.Grammar -> R.string.ln_area_grammar_subtitle
}

private fun LanguageArea.icon(): ImageVector = when (this) {
    LanguageArea.Home -> Icons.Filled.Language
    LanguageArea.Reading -> Icons.Filled.AutoStories
    LanguageArea.Listening -> Icons.Filled.Headphones
    LanguageArea.Writing -> Icons.Filled.Edit
    LanguageArea.Speaking -> Icons.Filled.Mic
    LanguageArea.Vocabulary -> Icons.Filled.School
    LanguageArea.Journey -> Icons.Filled.Flag
    LanguageArea.Grammar -> Icons.Filled.Insights
}

@Composable
private fun LanguageArea.tint(): Color = when (this) {
    LanguageArea.Home -> EduTheme.colors.aiAccent
    LanguageArea.Reading -> EduTheme.colors.primary
    LanguageArea.Listening -> EduTheme.colors.aiAccent
    LanguageArea.Writing -> EduTheme.colors.warning
    LanguageArea.Speaking -> EduTheme.colors.danger
    LanguageArea.Vocabulary -> EduTheme.colors.success
    LanguageArea.Journey -> EduTheme.colors.primary
    LanguageArea.Grammar -> EduTheme.colors.aiAccent
}

@StringRes
private fun LanguageSkill.labelRes(): Int = when (this) {
    LanguageSkill.Reading -> R.string.ln_skill_reading
    LanguageSkill.Listening -> R.string.ln_skill_listening
    LanguageSkill.Writing -> R.string.ln_skill_writing
    LanguageSkill.Speaking -> R.string.ln_skill_speaking
    LanguageSkill.Vocabulary -> R.string.ln_skill_vocabulary
    LanguageSkill.Journey -> R.string.ln_area_journey
    LanguageSkill.Grammar -> R.string.ln_skill_grammar
}

@StringRes
private fun LanguageSkill.placementHintRes(): Int = when (this) {
    LanguageSkill.Speaking -> R.string.ln04_skill_speaking_hint
    LanguageSkill.Listening -> R.string.ln04_skill_listening_hint
    LanguageSkill.Reading -> R.string.ln04_skill_reading_hint
    LanguageSkill.Writing -> R.string.ln04_skill_writing_hint
    LanguageSkill.Vocabulary -> R.string.ln04_skill_vocab_hint
    LanguageSkill.Journey -> R.string.ln_area_journey_subtitle
    LanguageSkill.Grammar -> R.string.ln04_skill_grammar_hint
}

private fun LanguageSkill.icon(): ImageVector = when (this) {
    LanguageSkill.Reading -> Icons.Filled.AutoStories
    LanguageSkill.Listening -> Icons.Filled.Headphones
    LanguageSkill.Writing -> Icons.Filled.Edit
    LanguageSkill.Speaking -> Icons.Filled.Mic
    LanguageSkill.Vocabulary -> Icons.Filled.School
    LanguageSkill.Journey -> Icons.Filled.Flag
    LanguageSkill.Grammar -> Icons.Filled.Insights
}

private fun LanguagePlacementSection.skill(): LanguageSkill = when (this) {
    com.rork.eduspark.data.model.LanguagePlacementSection.Speaking -> LanguageSkill.Speaking
    com.rork.eduspark.data.model.LanguagePlacementSection.Listening -> LanguageSkill.Listening
    com.rork.eduspark.data.model.LanguagePlacementSection.Reading -> LanguageSkill.Reading
    com.rork.eduspark.data.model.LanguagePlacementSection.Writing -> LanguageSkill.Writing
    com.rork.eduspark.data.model.LanguagePlacementSection.GrammarVocab -> LanguageSkill.Grammar
}

@Composable
private fun levelSummary(levels: List<LanguageSkillLevel>): String {
    val strength = levels.firstOrNull { it.isStrength }?.skill?.let { stringResource(it.labelRes()) }
    val focus = levels.firstOrNull { it.isFocus }?.skill?.let { stringResource(it.labelRes()) }
    return when {
        strength != null && focus != null -> stringResource(R.string.ln01_strength_focus, strength, focus)
        strength != null -> stringResource(R.string.ln01_strength_only, strength)
        focus != null -> stringResource(R.string.ln01_focus_only, focus)
        else -> stringResource(R.string.ln01_levels_subtitle)
    }
}

private fun isAnswerReady(
    question: LanguagePlacementQuestion,
    answerDraft: String,
    playedAudioQuestionIds: Set<String>,
): Boolean = when (question.type) {
    LanguagePlacementQuestionType.Speaking -> answerDraft.trim().isNotBlank()
    LanguagePlacementQuestionType.ListeningMcq ->
        playedAudioQuestionIds.contains(question.id) && answerDraft.toIntOrNull() in question.options.indices
    LanguagePlacementQuestionType.ReadingMcq -> answerDraft.toIntOrNull() in question.options.indices
    LanguagePlacementQuestionType.Writing -> wordCount(answerDraft) >= (question.minWords ?: 0)
}

private fun wordCount(value: String): Int = value.trim().split(Regex("\\s+")).count { it.isNotBlank() }

private fun optionLetter(index: Int): String = ('A'.code + index).toChar().toString()
