package com.rork.eduspark.ui.screens.student

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.PlayArrow
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
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.format.isolateBidi
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.LanguageArea
import com.rork.eduspark.data.model.LanguageChoiceQuestion
import com.rork.eduspark.data.model.LanguageGrammarSnapshot
import com.rork.eduspark.data.model.LanguageJourneySnapshot
import com.rork.eduspark.data.model.LanguageListeningLesson
import com.rork.eduspark.data.model.LanguageReadingAttempt
import com.rork.eduspark.data.model.LanguageReadingQuestionType
import com.rork.eduspark.data.model.LanguageSkillWorkspace
import com.rork.eduspark.data.model.LanguageSpeakingSession
import com.rork.eduspark.data.model.LanguageTrackStatus
import com.rork.eduspark.data.model.LanguageVocabularySnapshot
import com.rork.eduspark.data.model.LanguageWritingLesson
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

@Composable
internal fun LanguageDeepChrome(
    area: LanguageArea,
    workspace: LanguageSkillWorkspace?,
    onBackHome: () -> Unit,
    onSelectArea: (LanguageArea) -> Unit,
    modifier: Modifier = Modifier,
) {
    var showMore by remember { mutableStateOf(false) }
    val progress = languageDeepProgress(area, workspace)
    Row(verticalAlignment = Alignment.CenterVertically, modifier = modifier.fillMaxWidth()) {
        EduIconButton(
            icon = Icons.AutoMirrored.Filled.ArrowBack,
            contentDescription = stringResource(R.string.ln_area_back_home),
            onClick = onBackHome,
        )
        Text(
            text = stringResource(area.titleRes()),
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.weight(1f),
        )
        if (progress != null) {
            Text(
                text = progress,
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(end = Spacing.xs),
            )
        }
        Box {
            EduIconButton(
                icon = Icons.Filled.MoreVert,
                contentDescription = stringResource(R.string.ln_deep_more),
                onClick = { showMore = true },
            )
            DropdownMenu(expanded = showMore, onDismissRequest = { showMore = false }) {
                LanguageArea.entries.filterNot { it == LanguageArea.Home || it == area }.forEach { destination ->
                    DropdownMenuItem(
                        text = { Text(stringResource(destination.titleRes())) },
                        onClick = {
                            showMore = false
                            onSelectArea(destination)
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun languageDeepProgress(area: LanguageArea, workspace: LanguageSkillWorkspace?): String? {
    val data = workspace ?: return null
    return when (area) {
        LanguageArea.Listening -> data.listeningLesson?.let {
            stringResource(R.string.ln_deep_progress, numeral(it.answeredCount.coerceAtLeast(1).coerceAtMost(it.questions.size)), numeral(it.questions.size))
        }
        LanguageArea.Reading -> data.readingAttempt?.let {
            stringResource(R.string.ln_deep_progress, numeral(it.answeredCount.coerceAtLeast(1).coerceAtMost(it.questions.size)), numeral(it.questions.size))
        }
        LanguageArea.Vocabulary -> if (data.vocabulary.dailyGenerated) {
            stringResource(R.string.ln_deep_progress, numeral(data.vocabulary.currentDailyIndex + 1), numeral(data.vocabulary.dailyWords.size.coerceAtLeast(1)))
        } else null
        LanguageArea.Grammar -> data.grammarLesson?.let {
            stringResource(R.string.ln_deep_progress, numeral(it.phaseIndex + 1), numeral(it.phaseTotal))
        }
        LanguageArea.Journey -> stringResource(R.string.ln_deep_progress, numeral(data.journey.stageIndex), numeral(data.journey.stageTotal))
        LanguageArea.Speaking -> data.speakingSession?.let {
            stringResource(R.string.ln_deep_progress, numeral(it.turns.count { turn -> turn.role == "user" }), numeral(3))
        }
        else -> null
    }
}

@Composable
internal fun LanguageDeepScene(text: String, area: LanguageArea, playing: Boolean = false) {
    val scene = remember(text, area) { resolveLanguageMissionScene(text, text, area) }
    val ink = EduTheme.colors.primary
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .fillMaxWidth()
                .height(132.dp)
                .background(ink.copy(alpha = 0.08f), RoundedCornerShape(Radius.md)),
        ) {
            if (area == LanguageArea.Grammar) {
                LanguageGrammarTimelineVisual(ink = ink)
            } else if (area == LanguageArea.Vocabulary) {
                LanguageVocabObjectVisual(hint = text, ink = ink)
            } else {
                LanguageHomeSceneVisual(scene = scene, area = area, ink = ink, dim = ink.copy(alpha = 0.42f))
            }
            if (playing) {
                LanguageHomeWaveformVisual(color = ink, modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = Spacing.xs))
            }
        }
    }
}

internal fun TextStyle.forEmbeddedRun(): TextStyle = copy(textDirection = TextDirection.Content)

@Composable
internal fun LanguageContextualHelp(label: String, hint: String) {
    if (hint.isBlank()) return
    var open by remember { mutableStateOf(false) }
    GhostButton(text = label, onClick = { open = !open }, modifier = Modifier.padding(top = Spacing.xs))
    if (open) {
        Text(text = hint.isolateBidi(), style = EduTheme.typography.caption.forEmbeddedRun(), color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))
    }
}

@Composable
internal fun LanguageGrammarTimelineVisual(ink: Color, modifier: Modifier = Modifier) {
    val dim = ink.copy(alpha = 0.42f)
    Canvas(modifier = modifier.size(132.dp)) {
        val w = size.width
        val h = size.height
        val sw = 2.6.dp.toPx()
        drawLine(dim, Offset(w * 0.12f, h * 0.62f), Offset(w * 0.88f, h * 0.62f), sw, StrokeCap.Round)
        drawCircle(ink, radius = 7.dp.toPx(), center = Offset(w * 0.22f, h * 0.62f))
        drawCircle(ink, radius = 7.dp.toPx(), center = Offset(w * 0.50f, h * 0.38f))
        drawCircle(dim, radius = 7.dp.toPx(), center = Offset(w * 0.78f, h * 0.62f), style = Stroke(width = sw))
        drawLine(ink, Offset(w * 0.22f, h * 0.62f), Offset(w * 0.50f, h * 0.38f), sw, StrokeCap.Round)
        drawLine(dim, Offset(w * 0.50f, h * 0.38f), Offset(w * 0.78f, h * 0.62f), sw, StrokeCap.Round)
    }
}

@Composable
private fun LanguageVocabObjectVisual(hint: String, ink: Color) {
    val dim = ink.copy(alpha = 0.42f)
    Canvas(modifier = Modifier.size(132.dp)) {
        val w = size.width
        val h = size.height
        val sw = 2.6.dp.toPx()
        val key = hint.lowercase()
        when {
            listOf("coffee", "cup", "order", "قهوة").any { it in key } -> {
                drawRoundRect(ink, Offset(w * 0.34f, h * 0.40f), Size(w * 0.28f, h * 0.32f), androidx.compose.ui.geometry.CornerRadius(8.dp.toPx()), style = Stroke(width = sw))
                drawArc(dim, -70f, 140f, false, Offset(w * 0.60f, h * 0.46f), Size(w * 0.14f, h * 0.18f), style = Stroke(width = sw, cap = StrokeCap.Round))
            }
            listOf("calendar", "schedule", "جدول").any { it in key } -> {
                drawRoundRect(ink, Offset(w * 0.28f, h * 0.28f), Size(w * 0.44f, h * 0.46f), androidx.compose.ui.geometry.CornerRadius(8.dp.toPx()), style = Stroke(width = sw))
                drawLine(dim, Offset(w * 0.28f, h * 0.40f), Offset(w * 0.72f, h * 0.40f), sw, StrokeCap.Round)
                drawCircle(ink, 3.dp.toPx(), Offset(w * 0.38f, h * 0.52f))
                drawCircle(ink, 3.dp.toPx(), Offset(w * 0.50f, h * 0.52f))
                drawCircle(dim, 3.dp.toPx(), Offset(w * 0.62f, h * 0.52f))
            }
            else -> {
                drawRoundRect(ink, Offset(w * 0.32f, h * 0.30f), Size(w * 0.36f, h * 0.42f), androidx.compose.ui.geometry.CornerRadius(10.dp.toPx()), style = Stroke(width = sw))
                drawLine(dim, Offset(w * 0.40f, h * 0.42f), Offset(w * 0.60f, h * 0.42f), sw, StrokeCap.Round)
                drawLine(dim, Offset(w * 0.40f, h * 0.52f), Offset(w * 0.56f, h * 0.52f), sw, StrokeCap.Round)
            }
        }
    }
}

@Composable
internal fun LanguageShortFeedback(correct: Boolean, reason: String, correctAnswer: String? = null) {
    val colors = EduTheme.colors
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xxs), modifier = Modifier.padding(top = Spacing.sm)) {
        Text(
            text = if (correct) stringResource(R.string.ln6b_correct) else stringResource(R.string.ln_deep_not_quite),
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
            color = if (correct) colors.success else colors.danger,
        )
        if (!correct && !correctAnswer.isNullOrBlank()) {
            Text(
                text = stringResource(R.string.ln_deep_answer_is, correctAnswer.isolateBidi()),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold).forEmbeddedRun(),
                color = colors.textPrimary,
            )
        }
        if (reason.isNotBlank()) {
            Text(text = reason.isolateBidi(), style = EduTheme.typography.caption.forEmbeddedRun(), color = colors.textSecondary)
        }
    }
}

@Composable
internal fun LanguageFocusedListening(
    lesson: LanguageListeningLesson?,
    onStartPractice: () -> Unit,
    onAnswer: (String, Int) -> Unit,
    onSubmit: () -> Unit,
    onRetry: () -> Unit,
    onNext: () -> Unit,
) {
    if (lesson == null) {
        LanguageStartCard(
            area = LanguageArea.Listening,
            context = stringResource(R.string.ln6b_listening_title),
            action = stringResource(R.string.ln6b_start_practice),
            onAction = onStartPractice,
        )
        return
    }
    if (lesson.result != null) {
        EduCard {
            Text(text = stringResource(R.string.ln6b_score_value, lesson.result.scorePercent), style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.success)
            Text(text = lesson.result.nextLessonTeaser, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xs))
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md)) {
                SecondaryButton(text = stringResource(R.string.ln6b_retry), onClick = onRetry, modifier = Modifier.weight(1f))
                PrimaryButton(text = stringResource(R.string.common_next), onClick = onNext, modifier = Modifier.weight(1f))
            }
        }
        return
    }
    var index by remember(lesson.lessonId) { mutableIntStateOf(0) }
    var playing by remember { mutableStateOf(false) }
    val question = lesson.questions.getOrNull(index) ?: return
    val selected = lesson.answers[question.id]
    val revealed = selected != null
    LanguageDeepScene(text = "${lesson.situation} ${lesson.goalLabel} ${lesson.audioSituation}", area = LanguageArea.Listening, playing = playing)
    Text(text = lesson.situation.isolateBidi(), style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .padding(top = Spacing.sm)
            .fillMaxWidth()
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .eduClickable(onClickLabel = stringResource(R.string.ln_deep_listen), onClick = { playing = !playing })
            .background(EduTheme.colors.primaryContainer, RoundedCornerShape(Radius.pill))
            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
    ) {
        Icon(Icons.Filled.PlayArrow, contentDescription = null, tint = EduTheme.colors.primary)
        Text(text = stringResource(R.string.ln_deep_listen), style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.primary, modifier = Modifier.padding(start = Spacing.xs))
        Spacer(modifier = Modifier.weight(1f))
        Text("0:18", style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
    }
    Text(text = question.stem.isolateBidi(), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.md))
    LanguageChoiceBlock(
        question = question,
        selected = selected,
        revealed = revealed,
        onSelect = { if (!revealed) onAnswer(question.id, it) },
    )
    LanguageContextualHelp(label = stringResource(R.string.ln_deep_explain_sentence), hint = if (revealed) question.explanation else lesson.audioInstructions)
    if (revealed) {
        LanguageShortFeedback(
            correct = selected == question.correctIndex,
            reason = question.explanation,
            correctAnswer = question.choices.getOrNull(question.correctIndex),
        )
        if (selected != question.correctIndex) {
            GhostButton(text = stringResource(R.string.ln_deep_replay), onClick = { playing = true }, modifier = Modifier.padding(top = Spacing.xs))
        }
        PrimaryButton(
            text = stringResource(R.string.common_next),
            onClick = {
                val last = index >= lesson.questions.lastIndex
                if (last) onSubmit() else index += 1
            },
            enabled = if (index >= lesson.questions.lastIndex) lesson.canSubmit else true,
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun LanguageChoiceBlock(
    question: LanguageChoiceQuestion,
    selected: Int?,
    revealed: Boolean,
    onSelect: (Int) -> Unit,
) {
    val colors = EduTheme.colors
    Column(verticalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
        question.choices.forEachIndexed { choiceIndex, label ->
            val isSelected = selected == choiceIndex
            val isCorrect = choiceIndex == question.correctIndex
            val border = when {
                revealed && isCorrect -> colors.success
                revealed && isSelected && !isCorrect -> colors.danger
                isSelected -> colors.primary
                else -> colors.border
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .defaultMinSize(minHeight = Sizing.touchTarget)
                    .border(1.5.dp, border, RoundedCornerShape(Radius.md))
                    .eduClickable(onClickLabel = label, onClick = { onSelect(choiceIndex) })
                    .padding(horizontal = Spacing.sm, vertical = Spacing.sm),
            ) {
                Text(
                    text = ('A' + choiceIndex).toString(),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                    color = border,
                    modifier = Modifier.padding(end = Spacing.sm),
                )
                Text(text = label.isolateBidi(), style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold).forEmbeddedRun(), color = colors.textPrimary)
            }
        }
    }
}

@Composable
internal fun LanguageFocusedSpeaking(
    session: LanguageSpeakingSession?,
    onOpenDiscussion: () -> Unit,
    onToggleRecording: () -> Unit,
    onTranscript: (String) -> Unit,
    onSubmitTurn: () -> Unit,
) {
    LaunchedEffect(session) {
        if (session == null) onOpenDiscussion()
    }
    val active = session
    if (active == null) {
        LanguageStartCard(
            area = LanguageArea.Speaking,
            context = stringResource(R.string.ln6b_speaking_title),
            action = stringResource(R.string.ln6b_start_session),
            onAction = onOpenDiscussion,
        )
        return
    }
    val prompt = active.turns.lastOrNull { it.role != "user" }?.content ?: active.setting
    val lastStudent = active.turns.lastOrNull { it.role == "user" }
    val lastCorrection = active.turns.lastOrNull { it.correction != null }?.correction
    var processing by remember { mutableStateOf(false) }
    LaunchedEffect(active.turns.size) { processing = false }
    val pulse = rememberInfiniteTransition(label = "speak-pulse")
    val scale by pulse.animateFloat(
        initialValue = 1f,
        targetValue = if (active.recording) 1.06f else 1f,
        animationSpec = infiniteRepeatable(animation = tween(700, easing = LinearEasing), repeatMode = RepeatMode.Reverse),
        label = "speak-scale",
    )
    val status = when {
        active.recording -> stringResource(R.string.ln_deep_recording)
        processing -> stringResource(R.string.ln_deep_processing)
        lastStudent != null -> stringResource(R.string.ln6b_correct)
        else -> stringResource(R.string.ln_deep_ready)
    }
    LanguageDeepScene(text = "${active.caseTitle} ${active.setting}", area = LanguageArea.Speaking)
    Text(text = status, style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
    Text(text = active.caseTitle, style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textSecondary)
    Text(text = prompt.isolateBidi(), style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs))
    Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md)) {
        PrimaryButton(
            text = if (active.recording) stringResource(R.string.ln6b_stop_recording) else stringResource(R.string.ln_deep_press_speak),
            onClick = onToggleRecording,
            leadingIcon = Icons.Filled.Mic,
            modifier = Modifier.scale(scale),
        )
    }
    if (active.transcriptDraft.isNotBlank() || lastStudent != null) {
        Text(
            text = active.transcriptDraft.ifBlank { lastStudent?.content.orEmpty() },
            style = EduTheme.typography.body,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.md),
        )
    }
    lastCorrection?.let {
        LanguageShortFeedback(correct = false, reason = it.explanation, correctAnswer = it.corrected)
    }
    LanguageContextualHelp(
        label = stringResource(R.string.ln_deep_say_simpler),
        hint = lastCorrection?.corrected ?: active.characterHooks.firstOrNull().orEmpty(),
    )
    if (!active.recording && active.transcriptDraft.isNotBlank()) {
        EduTextField(
            value = active.transcriptDraft,
            onValueChange = onTranscript,
            label = stringResource(R.string.ln6b_transcript),
            placeholder = stringResource(R.string.ln6b_transcript_placeholder),
            singleLine = false,
            modifier = Modifier.padding(top = Spacing.sm),
        )
    }
    if (!active.recording) {
        PrimaryButton(
            text = if (lastStudent != null) stringResource(R.string.ln_deep_next_turn) else stringResource(R.string.ln6b_send_voice),
            onClick = {
                processing = true
                onSubmitTurn()
            },
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
        )
    }
}

@Composable
internal fun LanguageFocusedReading(
    attempt: LanguageReadingAttempt?,
    onStartPractice: () -> Unit,
    onAnswer: (String, String) -> Unit,
    onSubmit: () -> Unit,
) {
    if (attempt == null) {
        LanguageStartCard(
            area = LanguageArea.Reading,
            context = stringResource(R.string.ln6b_reading_stage),
            action = stringResource(R.string.ln6b_start_practice),
            onAction = onStartPractice,
        )
        return
    }
    var index by remember(attempt.attemptId) { mutableIntStateOf(0) }
    var revealedGap by remember(attempt.attemptId, index) { mutableStateOf(false) }
    val question = attempt.questions.getOrNull(index) ?: return
    val answer = attempt.answers[question.id].orEmpty()
    val choiceRevealed = question.type == LanguageReadingQuestionType.Mcq || question.type == LanguageReadingQuestionType.TrueFalse
    val revealed = if (choiceRevealed) answer.isNotBlank() else revealedGap
    LanguageDeepScene(text = "${attempt.topic} ${attempt.title} ${attempt.passage}", area = LanguageArea.Reading)
    Text(text = stringResource(R.string.ln_deep_read), style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.sm))
    Text(text = readingChunk(attempt.passage, index).isolateBidi(), style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold).forEmbeddedRun(), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.xxs))
    Text(
        text = (if (question.type == LanguageReadingQuestionType.GapFill) question.sentenceWithBlank.orEmpty() else question.stem).isolateBidi(),
        style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(),
        color = EduTheme.colors.textPrimary,
        modifier = Modifier.padding(top = Spacing.md),
    )
    when (question.type) {
        LanguageReadingQuestionType.Mcq -> LanguageChoiceBlock(
            question = LanguageChoiceQuestion(question.id, question.stem, question.choices, question.choices.indexOf(question.correctAnswer).coerceAtLeast(0), question.explanation),
            selected = answer.toIntOrNull(),
            revealed = answer.isNotBlank(),
            onSelect = { if (answer.isBlank()) onAnswer(question.id, it.toString()) },
        )
        LanguageReadingQuestionType.TrueFalse -> LanguageChoiceBlock(
            question = LanguageChoiceQuestion(question.id, question.stem, question.choices, question.choices.indexOfFirst { it.equals(question.correctAnswer, true) }.coerceAtLeast(0), question.explanation),
            selected = question.choices.indexOfFirst { it.equals(answer, true) }.takeIf { it >= 0 },
            revealed = answer.isNotBlank(),
            onSelect = { if (answer.isBlank()) onAnswer(question.id, question.choices[it].lowercase()) },
        )
        LanguageReadingQuestionType.GapFill,
        LanguageReadingQuestionType.ShortAnswer -> EduTextField(
            value = answer,
            onValueChange = { onAnswer(question.id, it) },
            label = stringResource(R.string.ln6b_your_answer),
            singleLine = question.type != LanguageReadingQuestionType.ShortAnswer,
            modifier = Modifier.padding(top = Spacing.sm),
        )
    }
    LanguageContextualHelp(
        label = stringResource(R.string.ln_deep_word_meaning),
        hint = question.subskill.ifBlank { attempt.grammarFocus.orEmpty() },
    )
    if (answer.isNotBlank() && !revealed && !choiceRevealed) {
        PrimaryButton(
            text = stringResource(R.string.ln6b_check),
            onClick = { revealedGap = true },
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
        )
    }
    if (revealed) {
        val correct = when (question.type) {
            LanguageReadingQuestionType.Mcq -> answer.toIntOrNull() == question.choices.indexOf(question.correctAnswer)
            else -> answer.equals(question.correctAnswer, ignoreCase = true)
        }
        LanguageShortFeedback(correct = correct, reason = question.explanation, correctAnswer = question.correctAnswer)
        PrimaryButton(
            text = stringResource(R.string.common_next),
            onClick = {
                if (index >= attempt.questions.lastIndex) onSubmit() else {
                    revealedGap = false
                    index += 1
                }
            },
            enabled = if (index >= attempt.questions.lastIndex) attempt.canSubmit else true,
            modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
        )
    }
}

private fun readingChunk(passage: String, index: Int): String {
    val sentences = passage.split(Regex("(?<=[.!?])\\s+")).filter { it.isNotBlank() }
    if (sentences.isEmpty()) return passage
    val start = (index * 2).coerceAtMost(sentences.lastIndex)
    return sentences.drop(start).take(2).joinToString(" ")
}

@Composable
internal fun LanguageFocusedWriting(
    lesson: LanguageWritingLesson?,
    onStartPractice: () -> Unit,
    onDraft: (String) -> Unit,
    onSubmitDraft: () -> Unit,
    onComplete: () -> Unit,
) {
    if (lesson == null) {
        LanguageStartCard(
            area = LanguageArea.Writing,
            context = stringResource(R.string.ln6b_writing_title),
            action = stringResource(R.string.ln6b_start_practice),
            onAction = onStartPractice,
        )
        return
    }
    if (lesson.completed) {
        EduCard {
            Text(text = stringResource(R.string.ln6b_writing_completed), style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.success)
            PrimaryButton(text = stringResource(R.string.ln6b_new_lesson), onClick = onStartPractice, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
        }
        return
    }
    LanguageDeepScene(text = "${lesson.missionTitle} ${lesson.writingContext} ${lesson.prompt}", area = LanguageArea.Writing)
    Text(text = lesson.prompt.isolateBidi(), style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    EduTextField(
        value = lesson.draftText,
        onValueChange = onDraft,
        label = stringResource(R.string.ln6b_editor_label),
        placeholder = stringResource(R.string.ln04_write_placeholder),
        singleLine = false,
        modifier = Modifier.padding(top = Spacing.sm),
    )
    Text(text = stringResource(R.string.ln04_words_count, lesson.wordCount, lesson.minWords, lesson.maxWords), style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))
    PrimaryButton(
        text = if (lesson.revisionNumber > 0) stringResource(R.string.ln_deep_revise) else stringResource(R.string.ln6b_submit_draft),
        onClick = onSubmitDraft,
        enabled = lesson.canSubmit,
        modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm),
    )
    LanguageContextualHelp(
        label = stringResource(R.string.ln_deep_fix_sentence),
        hint = lesson.evaluation?.afterExample?.ifBlank { lesson.expectedOutput } ?: lesson.expectedOutput,
    )
    lesson.evaluation?.let { evaluation ->
        AnimatedVisibility(visible = true, enter = fadeIn() + slideInVertically()) {
            Column {
                val ok = evaluation.strengths.firstOrNull().orEmpty()
                val fix = evaluation.improvements.firstOrNull() ?: evaluation.mainIssue
                if (ok.isNotBlank()) {
                    Text(text = "✓ $ok", style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.success, modifier = Modifier.padding(top = Spacing.md))
                }
                Text(text = "△ $fix", style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold), color = EduTheme.colors.warning, modifier = Modifier.padding(top = Spacing.xxs))
                if (evaluation.readyToComplete) {
                    PrimaryButton(text = stringResource(R.string.ln6b_complete), onClick = onComplete, leadingIcon = Icons.Filled.CheckCircle, modifier = Modifier.fillMaxWidth().padding(top = Spacing.sm))
                }
            }
        }
    }
}

@Composable
internal fun LanguageFocusedVocabulary(
    vocabulary: LanguageVocabularySnapshot,
    onGenerate: () -> Unit,
    onToggleArabic: (String) -> Unit,
    onGrade: (String, Int) -> Unit,
) {
    LaunchedEffect(vocabulary.dailyGenerated) {
        if (!vocabulary.dailyGenerated) onGenerate()
    }
    val card = vocabulary.dailyWords.getOrNull(vocabulary.currentDailyIndex)
    if (card == null) {
        LanguageStartCard(
            area = LanguageArea.Vocabulary,
            context = stringResource(R.string.ln6b_vocab_generator),
            action = stringResource(R.string.ln6b_generate_words),
            onAction = onGenerate,
        )
        return
    }
    LanguageDeepScene(text = "${card.word} ${card.imageHint} ${card.example}", area = LanguageArea.Vocabulary)
    Text(text = card.word.isolateBidi(), style = EduTheme.typography.display.copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    Text(text = card.example.isolateBidi(), style = EduTheme.typography.body.forEmbeddedRun(), color = EduTheme.colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))
    GhostButton(
        text = if (card.arabicRevealed) card.translationAr else stringResource(R.string.ln_deep_show_meaning),
        onClick = { onToggleArabic(card.id) },
        modifier = Modifier.padding(top = Spacing.sm),
    )
    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.md).fillMaxWidth()) {
        SecondaryButton(text = stringResource(R.string.ln_deep_know), onClick = { onGrade(card.id, 5) }, modifier = Modifier.weight(1f))
        SecondaryButton(text = stringResource(R.string.ln_deep_hard_word), onClick = { onGrade(card.id, 3) }, modifier = Modifier.weight(1f))
        PrimaryButton(text = stringResource(R.string.ln_deep_new_word), onClick = { onGrade(card.id, 1) }, modifier = Modifier.weight(1f))
    }
}

@Composable
internal fun LanguageFocusedGrammarRoadmap(
    grammar: LanguageGrammarSnapshot,
    onStartLesson: (String?) -> Unit,
) {
    LanguageDeepScene(text = grammar.currentName, area = LanguageArea.Grammar)
    Text(text = grammar.currentName.isolateBidi(), style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold).forEmbeddedRun(), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    Text(text = grammar.recommendation, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary, maxLines = 2, modifier = Modifier.padding(top = Spacing.xxs))
    PrimaryButton(text = stringResource(R.string.ln6c_start_lesson), onClick = { onStartLesson(grammar.currentGrammarId) }, leadingIcon = Icons.Filled.PlayArrow, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
}

@Composable
internal fun LanguageFocusedJourney(
    journey: LanguageJourneySnapshot,
    onStartSession: () -> Unit,
) {
    val current = journey.levels.firstOrNull { it.status == LanguageTrackStatus.Current } ?: journey.levels.firstOrNull()
    LanguageDeepScene(text = journey.todayMission.title + " " + journey.todayMission.scenario, area = LanguageArea.Journey)
    Text(text = journey.currentLevel.code, style = EduTheme.typography.display.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.primary, modifier = Modifier.padding(top = Spacing.sm))
    current?.stages.orEmpty().forEach { stage ->
        val mark = when (stage.status) {
            LanguageTrackStatus.Completed -> "✓"
            LanguageTrackStatus.Current -> "●"
            else -> "○"
        }
        Text(
            text = "$mark  ${stage.title}",
            style = EduTheme.typography.body.copy(fontWeight = if (stage.status == LanguageTrackStatus.Current) FontWeight.ExtraBold else FontWeight.SemiBold),
            color = when (stage.status) {
                LanguageTrackStatus.Completed -> EduTheme.colors.success
                LanguageTrackStatus.Current -> EduTheme.colors.textPrimary
                else -> EduTheme.colors.textTertiary
            },
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
    PrimaryButton(text = stringResource(R.string.ln6c_start_today_session), onClick = onStartSession, leadingIcon = Icons.Filled.PlayArrow, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
}

@Composable
private fun LanguageStartCard(
    area: LanguageArea,
    context: String,
    action: String,
    onAction: () -> Unit,
) {
    LanguageDeepScene(text = context, area = area)
    Text(text = context, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = EduTheme.colors.textPrimary, modifier = Modifier.padding(top = Spacing.sm))
    PrimaryButton(text = action, onClick = onAction, leadingIcon = Icons.Filled.PlayArrow, modifier = Modifier.fillMaxWidth().padding(top = Spacing.md))
}

