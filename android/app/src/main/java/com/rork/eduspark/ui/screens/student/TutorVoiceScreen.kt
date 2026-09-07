package com.rork.eduspark.ui.screens.student

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.tween
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MicOff
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.onClick
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ChatSender
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.ai.AiMessageBubble
import com.rork.eduspark.ui.components.ai.AiTypingIndicator
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Elevation
import com.rork.eduspark.ui.theme.LocalReducedMotion
import com.rork.eduspark.ui.theme.Motion
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-05 · AI Tutor Voice Mode.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Shares [TutorChatViewModel] with ST-04 (graph-scoped in AppNavigation) so a voice
 * exchange is still in the transcript when the student backs out to the typed chat — this
 * screen only owns its own ephemeral recording/permission/waveform state, which has no
 * reason to survive navigation.
 *
 * No real Whisper/Hume/TTS, no microphone upload, no streaming: [micGranted] simulates a
 * permission grant, transcription cycles a small fixed set of deterministic questions, and
 * "every third attempt" deliberately fails so the retry path is reachable by hand.
 *
 * The reply is AI-generated, so it renders through the same aiAccent-marked [AiMessageBubble]
 * ST-04 uses — voice mode does not get a different trust rule.
 */
@Composable
fun TutorVoiceScreen(
    onBack: () -> Unit,
    viewModel: TutorChatViewModel,
    modifier: Modifier = Modifier,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var micGranted by rememberSaveable { mutableStateOf(false) }
    var voiceStep by remember { mutableStateOf<VoiceStep>(VoiceStep.Idle) }
    var attemptCount by rememberSaveable { mutableStateOf(0) }
    var lastTranscript by rememberSaveable { mutableStateOf("") }
    var isPlayingResponse by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val lastTutorMessage = state.messages.lastOrNull { it.sender == ChatSender.Tutor }

    LaunchedEffect(isPlayingResponse) {
        if (isPlayingResponse) {
            delay(2500L)
            isPlayingResponse = false
        }
    }

    EduScaffold(
        title = stringResource(R.string.st05_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxSize()
                .padding(Spacing.gutter),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            ) {
                when {
                    !micGranted -> MicPermissionPrompt(onGrant = { micGranted = true })
                    voiceStep is VoiceStep.Failed -> MessageState(
                        icon = Icons.Filled.MicOff,
                        title = stringResource(R.string.st05_failed_title),
                        body = stringResource(R.string.st05_failed_body),
                        primaryActionLabel = stringResource(R.string.common_retry),
                        onPrimaryAction = { voiceStep = VoiceStep.Idle },
                    )
                    lastTranscript.isNotBlank() -> VoiceExchange(
                        transcript = lastTranscript,
                        isSending = state.isSending,
                        replyText = lastTutorMessage?.text,
                        isPlayingResponse = isPlayingResponse,
                        onTogglePlayResponse = { isPlayingResponse = !isPlayingResponse },
                    )
                    voiceStep is VoiceStep.Recording -> VoiceWaveform()
                    voiceStep is VoiceStep.Resolving -> Text(
                        text = stringResource(R.string.st05_resolving),
                        style = EduTheme.typography.body,
                        color = EduTheme.colors.textSecondary,
                    )
                    else -> Text(
                        text = stringResource(R.string.st05_hold_to_speak),
                        style = EduTheme.typography.body,
                        color = EduTheme.colors.textSecondary,
                        textAlign = TextAlign.Center,
                    )
                }
            }

            VoiceMicButton(
                step = voiceStep,
                enabled = micGranted,
                onPressStart = { if (micGranted) voiceStep = VoiceStep.Recording },
                onPressEnd = {
                    if (micGranted && voiceStep is VoiceStep.Recording) {
                        voiceStep = VoiceStep.Resolving
                        scope.launch {
                            delay(900L)
                            attemptCount += 1
                            if (attemptCount % 3 == 0) {
                                voiceStep = VoiceStep.Failed
                            } else {
                                val transcript = MockTranscripts[(attemptCount - 1) % MockTranscripts.size]
                                lastTranscript = transcript
                                voiceStep = VoiceStep.Idle
                                viewModel.sendMessage(transcript, isVoice = true)
                            }
                        }
                    }
                },
            )
        }
    }
}

private sealed interface VoiceStep {
    data object Idle : VoiceStep
    data object Recording : VoiceStep
    data object Resolving : VoiceStep
    data object Failed : VoiceStep
}

private val MockTranscripts = listOf(
    "كيف أفهم المشتقة الثانية بشكل أوضح؟",
    "أعطني مثالاً على المشتقة الثانية",
    "اشرح لي بشكل أبسط من فضلك",
)

@Composable
private fun MicPermissionPrompt(onGrant: () -> Unit) {
    MessageState(
        icon = Icons.Filled.MicOff,
        title = stringResource(R.string.st05_mic_permission_title),
        body = stringResource(R.string.st05_mic_permission_body),
        primaryActionLabel = stringResource(R.string.st05_mic_permission_action),
        onPrimaryAction = onGrant,
    )
}

@Composable
private fun VoiceExchange(
    transcript: String,
    isSending: Boolean,
    replyText: String?,
    isPlayingResponse: Boolean,
    onTogglePlayResponse: () -> Unit,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = stringResource(R.string.st05_your_question),
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textSecondary,
        )
        Text(
            text = transcript,
            style = EduTheme.typography.bodyLg,
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Center,
        )
        when {
            isSending -> AiTypingIndicator()
            replyText != null -> AiMessageBubble(
                text = replyText,
                footer = {
                    EduIconButton(
                        icon = if (isPlayingResponse) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                        contentDescription = stringResource(R.string.st05_play_response),
                        onClick = onTogglePlayResponse,
                        tint = EduTheme.colors.aiAccent,
                    )
                },
            )
        }
    }
}

@Composable
private fun VoiceMicButton(
    step: VoiceStep,
    enabled: Boolean,
    onPressStart: () -> Unit,
    onPressEnd: () -> Unit,
) {
    val colors = EduTheme.colors
    val isRecording = step is VoiceStep.Recording
    val isBusy = step is VoiceStep.Resolving
    val container = if (isRecording) colors.danger else colors.primary
    val label = stringResource(
        when {
            isRecording -> R.string.st05_recording
            else -> R.string.st05_hold_to_speak
        }
    )

    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .padding(top = Spacing.md, bottom = Spacing.sm)
            .size(Sizing.heroBadge)
            // The other primary/floating action carrying the approved "soft coloured shadow"
            // rule (Batch 1's PrimaryButton was the first) — idle glows primary, recording
            // glows danger, approximating the reference's red pulse ring without a real
            // animated shadow loop (banned on the device floor — see Motion.kt's own doc).
            .then(
                if (enabled && !isBusy) {
                    Modifier.shadow(
                        elevation = Elevation.action,
                        shape = CircleShape,
                        ambientColor = container.copy(alpha = Elevation.actionTint),
                        spotColor = container.copy(alpha = Elevation.actionTint),
                    )
                } else {
                    Modifier
                }
            )
            .background(if (enabled && !isBusy) container else colors.border, CircleShape)
            .pointerInput(enabled, isBusy) {
                if (enabled && !isBusy) {
                    detectTapGestures(
                        onPress = {
                            onPressStart()
                            tryAwaitRelease()
                            onPressEnd()
                        },
                    )
                }
            }
            .semantics {
                contentDescription = label
                role = Role.Button
                // Press-and-hold has no TalkBack equivalent — a double-tap still triggers a
                // full (near-instant) record/release cycle rather than leaving this control
                // unreachable to screen-reader users.
                onClick {
                    if (enabled && !isBusy) {
                        onPressStart()
                        onPressEnd()
                    }
                    true
                }
            },
    ) {
        Icon(
            imageVector = Icons.Filled.Mic,
            contentDescription = null,
            // Paired to whichever container is actually showing (primary vs danger) rather
            // than a single static "on primary" — the two have different dark-mode values.
            tint = if (isRecording) colors.onDanger else colors.onPrimary,
            modifier = Modifier.size(Sizing.iconLg * 1.4f),
        )
    }
}

@Composable
private fun VoiceWaveform(modifier: Modifier = Modifier) {
    val reduced = LocalReducedMotion.current
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier,
    ) {
        repeat(5) { index -> WaveformBar(index = index, animate = !reduced) }
    }
}

@Composable
private fun WaveformBar(index: Int, animate: Boolean) {
    val height = if (animate) {
        val transition = rememberInfiniteTransition(label = "waveform")
        val value by transition.animateFloat(
            initialValue = 8f,
            targetValue = 28f,
            animationSpec = infiniteRepeatable(
                animation = tween(durationMillis = Motion.SPINE_FILL_MS, delayMillis = index * 90),
                repeatMode = RepeatMode.Reverse,
            ),
            label = "waveformBar$index",
        )
        value
    } else {
        16f
    }
    Box(
        modifier = Modifier
            .width(6.dp)
            .height(height.dp)
            .background(EduTheme.colors.primary, RoundedCornerShape(Radius.sm))
    )
}
