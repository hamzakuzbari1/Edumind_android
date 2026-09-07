package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddCircle
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.data.model.ExamEntry
import com.rork.eduspark.data.model.OcrConfidence
import com.rork.eduspark.data.model.SimpleDate
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-14 · Exam Schedule Capture.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * No camera, no gallery picker, no OCR engine — [CaptureStage.Processing] is a deterministic
 * delay standing in for both, and correction is chip-based throughout (subject, date, time)
 * rather than free text, matching "quick-reply / date-like affordances" instead of a form.
 * None of the extracted text is aiAccent-marked — OCR output is not AI-generated content.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ExamCaptureScreen(
    onBack: () -> Unit,
    onConfirmed: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ExamCaptureViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var editingEntry by remember { mutableStateOf<ExamEntry?>(null) }

    EduScaffold(title = stringResource(R.string.st14_title), onBack = onBack, modifier = modifier) { _ ->
        when (state.stage) {
            CaptureStage.NoImage -> NoImageState(error = state.error, onCapture = viewModel::capture)
            CaptureStage.Processing -> ProcessingState()
            CaptureStage.Reviewing -> ReviewingState(
                entries = state.entries,
                isConfirming = state.isConfirming,
                error = state.error,
                onEdit = { editingEntry = it },
                onRemove = viewModel::removeEntry,
                onAddManual = viewModel::addManualEntry,
                onConfirm = viewModel::confirm,
            )
            CaptureStage.Confirmed -> ConfirmedState(entryCount = state.entries.size, onDone = onConfirmed)
        }
    }

    val current = editingEntry
    if (current != null) {
        EditExamEntryDialog(
            entry = current,
            onDismiss = { editingEntry = null },
            onSave = { updated -> viewModel.updateEntry(updated); editingEntry = null },
        )
    }
}

@Composable
private fun NoImageState(error: AppError?, onCapture: () -> Unit) {
    val colors = EduTheme.colors
    MessageState(
        icon = Icons.Filled.CameraAlt,
        title = stringResource(R.string.st14_no_image_title),
        body = if (error != null) stringResource(R.string.st14_capture_error) else stringResource(R.string.st14_no_image_body),
        iconTint = if (error != null) colors.warning else colors.textSecondary,
        primaryActionLabel = stringResource(R.string.st14_take_photo),
        onPrimaryAction = onCapture,
        secondaryActionLabel = stringResource(R.string.st14_import_gallery),
        onSecondaryAction = onCapture,
        modifier = Modifier.fillMaxSize(),
    )
}

@Composable
private fun ProcessingState() {
    val colors = EduTheme.colors
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm, Alignment.CenterVertically),
        modifier = Modifier
            .fillMaxSize()
            .padding(Spacing.gutter),
    ) {
        CircularProgressIndicator(color = colors.primary)
        Text(text = stringResource(R.string.st14_processing_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)
        Text(text = stringResource(R.string.st14_processing_body), style = EduTheme.typography.body, color = colors.textSecondary)
    }
}

@Composable
private fun ReviewingState(
    entries: List<ExamEntry>,
    isConfirming: Boolean,
    error: AppError?,
    onEdit: (ExamEntry) -> Unit,
    onRemove: (String) -> Unit,
    onAddManual: () -> Unit,
    onConfirm: () -> Unit,
) {
    val colors = EduTheme.colors
    Column(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.weight(1f).fillMaxWidth(),
        ) {
            item {
                Text(text = stringResource(R.string.st14_review_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)
                Text(
                    text = stringResource(R.string.st14_review_body),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
                )
            }
            items(entries, key = { it.id }) { entry ->
                ExamEntryCard(entry = entry, onEdit = { onEdit(entry) }, onRemove = { onRemove(entry.id) })
            }
            item {
                GhostButton(
                    text = stringResource(R.string.st14_add_manual),
                    onClick = onAddManual,
                    leadingIcon = Icons.Filled.AddCircle,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.surface)
                .padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
        ) {
            if (error != null) {
                Text(
                    text = stringResource(R.string.st14_confirm_error),
                    style = EduTheme.typography.caption,
                    color = colors.danger,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )
            }
            PrimaryButton(
                text = stringResource(R.string.st14_confirm),
                onClick = onConfirm,
                isLoading = isConfirming,
                enabled = entries.isNotEmpty(),
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun ExamEntryCard(entry: ExamEntry, onEdit: () -> Unit, onRemove: () -> Unit) {
    val colors = EduTheme.colors
    val borderColor = when (entry.confidence) {
        OcrConfidence.High -> colors.border
        OcrConfidence.Medium -> colors.warning
        OcrConfidence.Low -> colors.danger
    }

    EduCard(onClick = onEdit, borderColor = borderColor) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = entry.subjectTitle.ifBlank { stringResource(R.string.st14_unknown_subject) },
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = examDateTimeLabel(entry),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                ConfidencePill(entry.confidence, modifier = Modifier.padding(top = Spacing.xs))
            }
            EduIconButton(icon = Icons.Filled.Edit, contentDescription = stringResource(R.string.st14_edit_entry), onClick = onEdit)
            EduIconButton(icon = Icons.Filled.Delete, contentDescription = stringResource(R.string.st14_remove_entry), onClick = onRemove, tint = colors.danger)
        }
        if (entry.confidence == OcrConfidence.Low) {
            Text(
                text = stringResource(R.string.st14_low_confidence_hint),
                style = EduTheme.typography.caption,
                color = colors.danger,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun examDateTimeLabel(entry: ExamEntry): String {
    val date = entry.date
    val dateText = if (date != null) simpleDateLabel(date) else stringResource(R.string.st14_no_date)
    return if (entry.time != null) "$dateText · ${entry.time}" else dateText
}

@Composable
private fun simpleDateLabel(date: SimpleDate): String =
    numeral("%02d/%02d/%04d".format(date.day, date.month, date.year))

@Composable
private fun ConfidencePill(confidence: OcrConfidence, modifier: Modifier = Modifier) {
    val (labelRes, contentColor, containerColor) = when (confidence) {
        OcrConfidence.High -> Triple(R.string.st14_confidence_high, EduTheme.colors.success, EduTheme.colors.success.copy(alpha = 0.12f))
        OcrConfidence.Medium -> Triple(R.string.st14_confidence_medium, EduTheme.colors.warning, EduTheme.colors.warning.copy(alpha = 0.14f))
        OcrConfidence.Low -> Triple(R.string.st14_confidence_low, EduTheme.colors.danger, EduTheme.colors.danger.copy(alpha = 0.12f))
    }
    StatusPill(label = stringResource(labelRes), contentColor = contentColor, containerColor = containerColor, modifier = modifier)
}

@Composable
private fun ConfirmedState(entryCount: Int, onDone: () -> Unit) {
    MessageState(
        icon = Icons.Filled.CheckCircle,
        iconTint = EduTheme.colors.success,
        title = stringResource(R.string.st14_confirmed_title),
        body = stringResource(R.string.st14_confirmed_body, entryCount),
        primaryActionLabel = stringResource(R.string.st14_back_to_planner),
        onPrimaryAction = onDone,
        modifier = Modifier.fillMaxSize(),
    )
}

private val EDIT_SUBJECTS = listOf("math" to "الرياضيات", "physics" to "الفيزياء", "chemistry" to "الكيمياء")
private val EDIT_DATES = listOf(
    SimpleDate(2026, 9, 12), SimpleDate(2026, 9, 14), SimpleDate(2026, 9, 16),
    SimpleDate(2026, 9, 18), SimpleDate(2026, 9, 20), SimpleDate(2026, 9, 22),
)
private val EDIT_TIMES = listOf("08:00", "09:00", "10:00", "13:00")

@Composable
private fun EditExamEntryDialog(entry: ExamEntry, onDismiss: () -> Unit, onSave: (ExamEntry) -> Unit) {
    val colors = EduTheme.colors
    var subjectId by remember { mutableStateOf(entry.subjectId) }
    var subjectTitle by remember { mutableStateOf(entry.subjectTitle) }
    var date by remember { mutableStateOf(entry.date) }
    var time by remember { mutableStateOf(entry.time) }
    val unknownSubjectLabel = stringResource(R.string.st14_unknown_subject)

    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.surface, RoundedCornerShape(Radius.lg))
                .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.lg))
                .padding(Spacing.card),
        ) {
            Text(text = stringResource(R.string.st14_edit_title), style = EduTheme.typography.titleLg, color = colors.textPrimary)

            Text(
                text = stringResource(R.string.st14_edit_subject_label),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xxs),
            )
            FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                EDIT_SUBJECTS.forEach { (id, title) ->
                    EduChip(label = title, selected = subjectId == id, onClick = { subjectId = id; subjectTitle = title })
                }
            }

            Text(
                text = stringResource(R.string.st14_edit_date_label),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xxs),
            )
            FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                EDIT_DATES.forEach { option ->
                    EduChip(label = simpleDateLabel(option), selected = date == option, onClick = { date = option })
                }
            }

            Text(
                text = stringResource(R.string.st14_edit_time_label),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xxs),
            )
            FlowRow(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), verticalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                EduChip(label = stringResource(R.string.st14_no_time), selected = time == null, onClick = { time = null })
                EDIT_TIMES.forEach { option ->
                    EduChip(label = option, selected = time == option, onClick = { time = option })
                }
            }

            PrimaryButton(
                text = stringResource(R.string.st14_save_entry),
                onClick = {
                    onSave(
                        entry.copy(
                            subjectId = subjectId,
                            subjectTitle = subjectTitle.ifBlank { unknownSubjectLabel },
                            date = date,
                            time = time,
                            confidence = OcrConfidence.High,
                        ),
                    )
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
            GhostButton(text = stringResource(R.string.st14_close), onClick = onDismiss, modifier = Modifier.fillMaxWidth())
        }
    }
}
