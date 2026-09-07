package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.TeacherVoiceProfile
import com.rork.eduspark.data.model.TeacherVoiceProfileSample
import com.rork.eduspark.data.model.VoiceProfileStatus
import com.rork.eduspark.data.model.VoiceSampleQualityStatus
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * Teacher Voice Clone (الصوت) — same TC-09 route/ViewModel. Default composition matches
 * the approved simple landing; consent, generate, preview, and narration stay available
 * through progressive disclosure.
 */
@Composable
fun TeacherVoiceProfileScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherVoiceProfileViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.tc09_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherVoiceProfileSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { profile ->
            TeacherVoiceProfileContent(
                profile = profile,
                isGenerating = state.isGenerating,
                isPreviewPlaying = state.isPreviewPlaying,
                onSetConsent = viewModel::setConsent,
                onAddRecordedSample = viewModel::addRecordedSample,
                onAddUploadedSample = viewModel::addUploadedSample,
                onRemoveSample = viewModel::removeSample,
                onGenerate = viewModel::generateProfile,
                onTogglePreview = viewModel::togglePreview,
                onSetNarrationEnabled = viewModel::setNarrationEnabled,
            )
        }
    }
}

@Composable
private fun TeacherVoiceProfileContent(
    profile: TeacherVoiceProfile,
    isGenerating: Boolean,
    isPreviewPlaying: Boolean,
    onSetConsent: (Boolean) -> Unit,
    onAddRecordedSample: () -> Unit,
    onAddUploadedSample: () -> Unit,
    onRemoveSample: (String) -> Unit,
    onGenerate: () -> Unit,
    onTogglePreview: () -> Unit,
    onSetNarrationEnabled: (Boolean) -> Unit,
) {
    val colors = EduTheme.colors
    val processing = isGenerating || profile.profileStatus == VoiceProfileStatus.Processing
    val needsConsent = !profile.consentGranted
    val needsGenerate = profile.profileStatus == VoiceProfileStatus.ReadyToGenerate
    val needsRetry = profile.profileStatus == VoiceProfileStatus.Failed && !isGenerating
    var showAdvanced by rememberSaveable { mutableStateOf(false) }

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Text(
                text = stringResource(R.string.tc09_intro),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.padding(bottom = Spacing.md),
            )
            VoiceWaveformWell(processing = processing)
        }

        if (profile.samples.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.tc09_no_samples),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.sm),
                )
            }
        } else {
            itemsIndexed(profile.samples, key = { _, sample -> sample.id }) { index, sample ->
                VoiceSampleRow(
                    index = index,
                    sample = sample,
                    processing = processing && index == profile.samples.lastIndex && profile.profileStatus == VoiceProfileStatus.Processing,
                    onRemove = { onRemoveSample(sample.id) },
                    modifier = Modifier.padding(top = if (index == 0) Spacing.md else Spacing.xs),
                )
            }
        }

        if (needsConsent) {
            item {
                ConsentRow(
                    consentGranted = profile.consentGranted,
                    onSetConsent = onSetConsent,
                    modifier = Modifier.padding(top = Spacing.md),
                )
            }
        }

        item {
            PrimaryButton(
                text = stringResource(R.string.tc09_record_sample),
                onClick = onAddRecordedSample,
                enabled = profile.consentGranted,
                leadingIcon = Icons.Filled.Mic,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
            GhostButton(
                text = stringResource(R.string.tc09_upload_sample),
                onClick = onAddUploadedSample,
                enabled = profile.consentGranted,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        if (processing) {
            item {
                StatusPill(
                    label = stringResource(R.string.tc09_sample_processing),
                    contentColor = colors.aiAccent,
                    containerColor = colors.aiAccentContainer,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
        }

        if (needsGenerate || needsRetry) {
            item {
                if (needsRetry) {
                    Text(
                        text = stringResource(R.string.tc09_generate_failed_hint),
                        style = EduTheme.typography.caption,
                        color = colors.danger,
                        modifier = Modifier.padding(top = Spacing.sm),
                    )
                }
                PrimaryButton(
                    text = stringResource(if (needsRetry) R.string.tc09_retry_generate else R.string.tc09_generate),
                    onClick = onGenerate,
                    isLoading = isGenerating,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
            }
        }

        item {
            GhostButton(
                text = stringResource(R.string.tc09_more),
                onClick = { showAdvanced = !showAdvanced },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs, bottom = if (showAdvanced) 0.dp else Spacing.md),
            )
        }

        if (showAdvanced) {
            item {
                if (!needsConsent) {
                    ConsentRow(
                        consentGranted = profile.consentGranted,
                        onSetConsent = onSetConsent,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                }
                if (profile.profileStatus == VoiceProfileStatus.Ready) {
                    SecondaryButton(
                        text = stringResource(R.string.tc09_regenerate),
                        onClick = onGenerate,
                        isLoading = isGenerating,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = Spacing.sm),
                    )
                    PreviewCard(
                        isPlaying = isPreviewPlaying,
                        onTogglePreview = onTogglePreview,
                        modifier = Modifier.padding(top = Spacing.sm),
                    )
                    NarrationToggleCard(
                        profile = profile,
                        onSetNarrationEnabled = onSetNarrationEnabled,
                        modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.md),
                    )
                } else {
                    NarrationToggleCard(
                        profile = profile,
                        onSetNarrationEnabled = onSetNarrationEnabled,
                        modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.md),
                    )
                }
            }
        }
    }
}

@Composable
private fun VoiceWaveformWell(processing: Boolean) {
    val colors = EduTheme.colors
    val strokeColor = if (processing) colors.aiAccent else colors.primary
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .fillMaxWidth()
            .height(110.dp)
            .background(
                if (processing) colors.aiAccentContainer else colors.primaryContainer,
                RoundedCornerShape(Radius.md),
            ),
    ) {
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
                .padding(horizontal = Spacing.lg),
        ) {
            val mid = size.height / 2f
            val amps = floatArrayOf(0f, -14f, 28f, -20f, 12f, -18f, 22f, -10f, 4f, -16f, 12f, 0f)
            val path = Path()
            val step = size.width / (amps.size - 1).toFloat()
            amps.forEachIndexed { index, amp ->
                val x = step * index
                val y = mid + amp.dp.toPx()
                if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            drawPath(
                path = path,
                color = strokeColor,
                style = Stroke(width = 2.4.dp.toPx(), cap = StrokeCap.Round),
            )
        }
    }
}

@Composable
private fun VoiceSampleRow(
    index: Int,
    sample: TeacherVoiceProfileSample,
    processing: Boolean,
    onRemove: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val isGood = sample.qualityStatus == VoiceSampleQualityStatus.Good
    val border = when {
        processing -> colors.aiAccent
        else -> colors.border
    }
    EduCard(
        borderColor = border,
        contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xs),
        modifier = modifier,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.tc09_sample_n, numeral(index + 1)),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                )
                Text(sample.durationLabel, style = EduTheme.typography.caption, color = colors.textSecondary)
            }
            when {
                processing -> StatusPill(
                    label = stringResource(R.string.tc09_sample_processing),
                    contentColor = colors.aiAccent,
                    containerColor = colors.aiAccentContainer,
                )
                isGood -> StatusPill(
                    label = stringResource(R.string.tc09_sample_ready),
                    contentColor = colors.success,
                    containerColor = colors.success.copy(alpha = 0.14f),
                )
                else -> StatusPill(
                    label = voiceSampleQualityLabel(sample.qualityStatus),
                    contentColor = colors.warning,
                    containerColor = colors.warning.copy(alpha = 0.14f),
                )
            }
            EduIconButton(
                icon = Icons.Filled.Close,
                contentDescription = stringResource(R.string.tc09_remove_sample),
                tint = colors.danger,
                onClick = onRemove,
            )
        }
    }
}

@Composable
private fun ConsentRow(
    consentGranted: Boolean,
    onSetConsent: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val label = stringResource(R.string.tc09_consent_label)
    EduCard(
        modifier = modifier,
        contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xs),
    ) {
        Row(
            verticalAlignment = Alignment.Top,
            modifier = Modifier
                .fillMaxWidth()
                .eduClickable(onClickLabel = label) { onSetConsent(!consentGranted) },
        ) {
            Checkbox(
                checked = consentGranted,
                onCheckedChange = onSetConsent,
                colors = CheckboxDefaults.colors(checkedColor = colors.primary, checkmarkColor = colors.onPrimary),
            )
            Text(
                text = label,
                style = EduTheme.typography.body,
                color = colors.textPrimary,
                modifier = Modifier
                    .weight(1f)
                    .padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun PreviewCard(
    isPlaying: Boolean,
    onTogglePreview: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    EduCard(modifier = modifier) {
        Text(
            text = stringResource(R.string.tc09_preview_paragraph),
            style = EduTheme.typography.body,
            color = colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.tc09_preview_disclosure),
            style = EduTheme.typography.caption,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.sm),
        )
        SecondaryButton(
            text = stringResource(if (isPlaying) R.string.tc09_stop_preview else R.string.tc09_play_preview),
            onClick = onTogglePreview,
            leadingIcon = if (isPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun NarrationToggleCard(
    profile: TeacherVoiceProfile,
    onSetNarrationEnabled: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val canEnable = profile.consentGranted && profile.profileStatus == VoiceProfileStatus.Ready
    EduCard(modifier = modifier) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = stringResource(R.string.tc09_narration_toggle_label),
                style = EduTheme.typography.body,
                color = colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
            Switch(
                checked = profile.clonedNarrationEnabled,
                onCheckedChange = onSetNarrationEnabled,
                enabled = canEnable || profile.clonedNarrationEnabled,
                colors = SwitchDefaults.colors(checkedThumbColor = colors.onPrimary, checkedTrackColor = colors.primary),
            )
        }
        if (!canEnable) {
            Text(
                text = stringResource(R.string.tc09_narration_disabled_hint),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun TeacherVoiceProfileSkeleton() {
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
