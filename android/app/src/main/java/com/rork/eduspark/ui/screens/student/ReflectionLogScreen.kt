package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.InlineLoader
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-09 · Reflection Log.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Voice-first, one large record button — see [ReflectionLogViewModel]'s own doc comment for
 * the deterministic MOCK recording/transcription flow behind it. The SAME button drives every
 * state this screen has: start, stop, and retry after a failed attempt all read from
 * [RecordButtonBar] — no second button anywhere, which is the entire point of "low friction."
 * An existing saved reflection loads straight into the same editable transcript view a fresh
 * recording lands on, so "already recorded" and "just finished recording" are one surface.
 */
@Composable
fun ReflectionLogScreen(
    projectId: String,
    milestoneId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ReflectionLogViewModel = koinViewModel(parameters = { parametersOf(projectId, milestoneId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.pj09_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ReflectionLogSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ReflectionLogContent(
                data = data,
                state = state,
                onStartRecording = viewModel::startRecording,
                onStopRecording = viewModel::stopRecording,
                onUpdateTranscript = viewModel::updateTranscript,
                onSave = viewModel::saveReflection,
            )
        }
    }
}

@Composable
private fun ReflectionLogContent(
    data: ReflectionLogScreenData,
    state: ReflectionLogUiState,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onUpdateTranscript: (String) -> Unit,
    onSave: (String?) -> Unit,
) {
    val colors = EduTheme.colors
    val freshDurationLabel = state.recordedDurationSeconds?.let { numeral(formatMmSs(it)) }

    Column(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
        ) {
            Text(data.milestoneTitle, style = EduTheme.typography.titleLg, color = colors.textPrimary)
            Text(
                text = data.projectTitle,
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.section),
            )

            when {
                state.recordingState == RecordingState.Processing -> ProcessingContent()
                state.recordingState == RecordingState.Failed -> FailedContent()
                state.recordingState == RecordingState.Recording -> RecordingContent(elapsedSeconds = state.elapsedSeconds)
                state.transcript.isNotBlank() -> TranscriptEditor(
                    transcript = state.transcript,
                    sessionLabel = data.sessionLabel,
                    durationLabel = freshDurationLabel ?: data.existingDurationLabel,
                    isSaving = state.isSaving,
                    onUpdateTranscript = onUpdateTranscript,
                    onSave = { onSave(freshDurationLabel) },
                )
                else -> NoReflectionYetPrompt()
            }
        }

        RecordButtonBar(
            recordingState = state.recordingState,
            onToggle = { if (state.recordingState == RecordingState.Recording) onStopRecording() else onStartRecording() },
        )
    }
}

@Composable
private fun NoReflectionYetPrompt() {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.section),
    ) {
        Icon(Icons.Filled.Mic, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.stateIcon))
        Text(
            text = stringResource(R.string.pj09_empty_title),
            style = EduTheme.typography.brandTitle,
            color = colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        Text(
            text = stringResource(R.string.pj09_empty_body),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun RecordingContent(elapsedSeconds: Int) {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.section),
    ) {
        Text(
            text = numeral(formatMmSs(elapsedSeconds)),
            style = EduTheme.typography.brandTitle,
            color = colors.danger,
        )
        Text(
            text = stringResource(R.string.pj09_recording),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ProcessingContent() {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = Spacing.section),
    ) {
        InlineLoader()
        Text(
            text = stringResource(R.string.pj09_processing),
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun FailedContent() {
    MessageState(
        icon = Icons.Filled.ErrorOutline,
        title = stringResource(R.string.pj09_failed_title),
        body = stringResource(R.string.pj09_failed_body),
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun TranscriptEditor(
    transcript: String,
    sessionLabel: String?,
    durationLabel: String?,
    isSaving: Boolean,
    onUpdateTranscript: (String) -> Unit,
    onSave: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            if (sessionLabel != null) {
                StatusPill(label = sessionLabel, contentColor = colors.primary, containerColor = colors.primaryContainer)
            }
            if (durationLabel != null) {
                StatusPill(label = durationLabel, contentColor = colors.textSecondary, containerColor = colors.neutralAlpha100)
            }
        }
        EduTextField(
            value = transcript,
            onValueChange = onUpdateTranscript,
            label = stringResource(R.string.pj09_transcript_label),
            singleLine = false,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
        PrimaryButton(
            text = stringResource(R.string.pj09_save),
            onClick = onSave,
            isLoading = isSaving,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        )
    }
}

@Composable
private fun RecordButtonBar(recordingState: RecordingState, onToggle: () -> Unit) {
    val colors = EduTheme.colors
    val isRecording = recordingState == RecordingState.Recording
    val isBusy = recordingState == RecordingState.Processing
    val container = if (isRecording) colors.danger else colors.primary
    val icon = if (isRecording) Icons.Filled.Stop else Icons.Filled.Mic
    val label = stringResource(
        when {
            isRecording -> R.string.pj09_stop_recording
            recordingState == RecordingState.Failed -> R.string.pj09_record_retry
            else -> R.string.pj09_record
        }
    )

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(vertical = Spacing.md),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(Sizing.heroBadge)
                .background(if (!isBusy) container else colors.border, CircleShape)
                .eduClickable(enabled = !isBusy, onClickLabel = label, onClick = onToggle),
        ) {
            Icon(icon, contentDescription = null, tint = colors.onPrimary, modifier = Modifier.size(Sizing.iconLg * 1.4f))
        }
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

private fun formatMmSs(totalSeconds: Int): String {
    val minutes = totalSeconds / 60
    val seconds = totalSeconds % 60
    return "%02d:%02d".format(minutes, seconds)
}

@Composable
private fun ReflectionLogSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
    }
}

