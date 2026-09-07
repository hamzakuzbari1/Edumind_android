package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.LessonUploadStage
import com.rork.eduspark.data.model.TeacherLessonUploadDraft
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-05 · Lesson Upload — Teacher content flow (PDF pages 07–09).
 * ══════════════════════════════════════════════════════════════════════════
 *
 * MOCK interaction only — no real file picker, no storage permission, no backend upload
 * (see [TeacherLessonUploadViewModel]). Three local steps share one ViewModel and the same
 * [TeacherRepository.startLessonUpload] pipeline; they are not separate destinations.
 */
@Composable
fun TeacherLessonUploadScreen(
    courseId: String,
    onBack: () -> Unit,
    onUploaded: (lessonId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherLessonUploadViewModel = koinViewModel(parameters = { parametersOf(courseId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherLessonUploadEvent.Uploaded -> onUploaded(event.lessonId)
            }
        }
    }

    EduScaffold(
        title = stringResource(R.string.tc05_title),
        onBack = {
            if (!viewModel.consumeBack()) onBack()
        },
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherLessonUploadSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            val activeUpload = state.activeUpload
            if (activeUpload != null) {
                UploadProgressContent(
                    draft = activeUpload,
                    onPause = viewModel::pauseUpload,
                    onResume = viewModel::resumeUpload,
                    onCancel = viewModel::requestCancelUpload,
                )
            } else {
                Column(modifier = Modifier.fillMaxSize()) {
                    UploadWizardContent(
                        form = state.form,
                        step = state.step,
                        maxOrder = data.maxOrder,
                        showValidationError = state.showValidationError,
                        onSelectSourceKind = viewModel::selectSourceKind,
                        onSelectMockFile = viewModel::selectMockFile,
                        onRemoveMockFile = viewModel::removeMockFile,
                        onUpdateVideoLink = viewModel::updateVideoLink,
                        onUpdateTitle = viewModel::updateTitle,
                        onUpdateOrder = viewModel::updateOrder,
                        modifier = Modifier.weight(1f),
                    )
                    UploadActionBar(
                        step = state.step,
                        isStartingUpload = state.isStartingUpload,
                        onAction = viewModel::goNext,
                    )
                }
            }
        }

        if (state.showCancelConfirm) {
            ConfirmDialog(
                title = stringResource(R.string.tc05_cancel_confirm_title),
                body = stringResource(R.string.tc05_cancel_confirm_body),
                confirmLabel = stringResource(R.string.tc05_cancel_confirm_action),
                onConfirm = viewModel::confirmCancelUpload,
                onDismiss = viewModel::dismissCancelUpload,
                isDestructive = true,
            )
        }
    }
}

@Composable
private fun UploadWizardContent(
    form: TeacherLessonUploadFormState,
    step: Int,
    maxOrder: Int,
    showValidationError: Boolean,
    onSelectSourceKind: (TeacherLessonSourceKind) -> Unit,
    onSelectMockFile: () -> Unit,
    onRemoveMockFile: () -> Unit,
    onUpdateVideoLink: (String) -> Unit,
    onUpdateTitle: (String) -> Unit,
    onUpdateOrder: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        Text(
            text = when (step) {
                1 -> stringResource(R.string.tc05_step_details)
                2 -> stringResource(R.string.tc05_step_content)
                else -> stringResource(R.string.tc05_step_review)
            },
            style = EduTheme.typography.caption,
            color = colors.textTertiary,
        )
        TeacherStepSegmentBar(
            currentStep = step,
            modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.sm),
        )
        if (step > 1 && form.title.isNotBlank()) {
            Text(
                text = form.title,
                style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
        }

        when (step) {
            1 -> DetailsStep(
                form = form,
                maxOrder = maxOrder,
                showValidationError = showValidationError,
                onUpdateTitle = onUpdateTitle,
                onUpdateOrder = onUpdateOrder,
            )
            2 -> ContentStep(
                form = form,
                showValidationError = showValidationError,
                onSelectSourceKind = onSelectSourceKind,
                onSelectMockFile = onSelectMockFile,
                onRemoveMockFile = onRemoveMockFile,
                onUpdateVideoLink = onUpdateVideoLink,
            )
            else -> ReviewStep(form = form)
        }

        Spacer(modifier = Modifier.height(Spacing.xl))
    }
}

@Composable
private fun DetailsStep(
    form: TeacherLessonUploadFormState,
    maxOrder: Int,
    showValidationError: Boolean,
    onUpdateTitle: (String) -> Unit,
    onUpdateOrder: (Int) -> Unit,
) {
    EduTextField(
        value = form.title,
        onValueChange = onUpdateTitle,
        label = stringResource(R.string.tc05_lesson_title_label),
        errorText = if (showValidationError && form.title.isBlank()) {
            stringResource(R.string.tc05_lesson_title_required)
        } else {
            null
        },
        modifier = Modifier.padding(bottom = Spacing.sm),
    )
    OrderStepper(order = form.order, maxOrder = maxOrder, onUpdateOrder = onUpdateOrder)
}

@Composable
private fun ContentStep(
    form: TeacherLessonUploadFormState,
    showValidationError: Boolean,
    onSelectSourceKind: (TeacherLessonSourceKind) -> Unit,
    onSelectMockFile: () -> Unit,
    onRemoveMockFile: () -> Unit,
    onUpdateVideoLink: (String) -> Unit,
) {
    val colors = EduTheme.colors
    SourceKindSelector(selected = form.sourceKind, onSelect = onSelectSourceKind)

    when (form.sourceKind) {
        TeacherLessonSourceKind.Video -> VideoSourceSurface(
            fileName = form.mockFileName,
            fileBytes = form.mockFileBytes,
            onSelect = onSelectMockFile,
            onRemove = onRemoveMockFile,
        )
        TeacherLessonSourceKind.Pdf -> PdfSourceSurface(
            fileName = form.mockFileName,
            fileBytes = form.mockFileBytes,
            onSelect = onSelectMockFile,
        )
        TeacherLessonSourceKind.VideoLink -> VideoLinkSurface(
            link = form.videoLink,
            showError = showValidationError && form.videoLink.isBlank(),
            onUpdate = onUpdateVideoLink,
        )
    }

    if (showValidationError && form.sourceKind != TeacherLessonSourceKind.VideoLink && form.mockFileName == null) {
        Text(
            text = stringResource(R.string.tc05_file_required),
            style = EduTheme.typography.caption,
            color = colors.danger,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun SourceKindSelector(
    selected: TeacherLessonSourceKind,
    onSelect: (TeacherLessonSourceKind) -> Unit,
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = Spacing.sm),
    ) {
        SourceKindOption(
            kind = TeacherLessonSourceKind.Video,
            icon = Icons.Filled.PlayArrow,
            label = stringResource(R.string.tc05_source_video),
            selected = selected == TeacherLessonSourceKind.Video,
            onSelect = onSelect,
            modifier = Modifier.weight(1f),
        )
        SourceKindOption(
            kind = TeacherLessonSourceKind.VideoLink,
            icon = Icons.Filled.Link,
            label = stringResource(R.string.tc05_source_link),
            selected = selected == TeacherLessonSourceKind.VideoLink,
            onSelect = onSelect,
            modifier = Modifier.weight(1f),
        )
        SourceKindOption(
            kind = TeacherLessonSourceKind.Pdf,
            icon = Icons.Filled.Description,
            label = stringResource(R.string.tc05_source_pdf),
            selected = selected == TeacherLessonSourceKind.Pdf,
            onSelect = onSelect,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun SourceKindOption(
    kind: TeacherLessonSourceKind,
    icon: ImageVector,
    label: String,
    selected: Boolean,
    onSelect: (TeacherLessonSourceKind) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.md)
    val container = if (selected) colors.primary else colors.surface
    val content = if (selected) colors.onPrimary else colors.textPrimary
    val border = if (selected) colors.primary else colors.border
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = modifier
            .background(container, shape)
            .border(Sizing.hairline, border, shape)
            .eduClickable(role = Role.RadioButton, onClickLabel = label) { onSelect(kind) }
            .padding(vertical = Spacing.xs, horizontal = Spacing.xxs),
    ) {
        Icon(imageVector = icon, contentDescription = null, tint = content, modifier = Modifier.size(Sizing.iconLg))
        Text(
            text = label,
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
            color = content,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

@Composable
private fun VideoSourceSurface(
    fileName: String?,
    fileBytes: Long,
    onSelect: () -> Unit,
    onRemove: () -> Unit,
) {
    val colors = EduTheme.colors
    if (fileName == null) {
        EduCard {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                TeacherVideoMediaWell(modifier = Modifier.fillMaxWidth().height(120.dp).clip(RoundedCornerShape(Radius.sm)))
                Text(
                    text = stringResource(R.string.tc05_no_file_selected),
                    style = EduTheme.typography.caption,
                    color = colors.textMuted,
                    modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.sm),
                )
                PrimaryButton(text = stringResource(R.string.tc05_select_file), onClick = onSelect)
            }
        }
    } else {
        EduCard(contentPadding = PaddingValues(0.dp)) {
            TeacherVideoMediaWell(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(148.dp)
                    .clip(RoundedCornerShape(topStart = Radius.md, topEnd = Radius.md)),
            )
            Column(modifier = Modifier.padding(Spacing.card)) {
                Text(
                    text = fileName,
                    style = EduTheme.typography.title.copy(fontWeight = FontWeight.Bold),
                    color = colors.textPrimary,
                )
                Text(
                    text = "${megabytesLabel(fileBytes)} · ${stringResource(R.string.tc05_selected_ready)}",
                    style = EduTheme.typography.caption,
                    color = colors.textMuted,
                    modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                    SecondaryButton(
                        text = stringResource(R.string.tc05_replace_file),
                        onClick = onSelect,
                        modifier = Modifier.weight(1f),
                    )
                    GhostButton(
                        text = stringResource(R.string.tc05_delete_file),
                        onClick = onRemove,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

@Composable
private fun PdfSourceSurface(
    fileName: String?,
    fileBytes: Long,
    onSelect: () -> Unit,
) {
    val colors = EduTheme.colors
    if (fileName == null) {
        EduCard {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                TeacherPdfMediaWell()
                Text(
                    text = stringResource(R.string.tc05_no_file_selected),
                    style = EduTheme.typography.caption,
                    color = colors.textMuted,
                    modifier = Modifier.padding(top = Spacing.sm, bottom = Spacing.sm),
                )
                PrimaryButton(text = stringResource(R.string.tc05_select_file), onClick = onSelect)
            }
        }
    } else {
        EduCard {
            TeacherPdfMediaWell()
            Text(
                text = fileName,
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.Bold),
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = "${megabytesLabel(fileBytes)} · ${stringResource(R.string.tc05_selected_ready)}",
                style = EduTheme.typography.caption,
                color = colors.textMuted,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.sm),
            )
            SecondaryButton(
                text = stringResource(R.string.tc05_replace_file),
                onClick = onSelect,
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun VideoLinkSurface(
    link: String,
    showError: Boolean,
    onUpdate: (String) -> Unit,
) {
    EduCard {
        EduTextField(
            value = link,
            onValueChange = onUpdate,
            label = stringResource(R.string.tc05_link_label),
            keyboardType = KeyboardType.Uri,
            errorText = if (showError) stringResource(R.string.tc05_link_required) else null,
        )
    }
}

@Composable
private fun ReviewStep(form: TeacherLessonUploadFormState) {
    val colors = EduTheme.colors
    val sourceTitle = when (form.sourceKind) {
        TeacherLessonSourceKind.Video -> stringResource(R.string.tc05_teacher_video)
        TeacherLessonSourceKind.Pdf -> stringResource(R.string.tc05_teacher_pdf)
        TeacherLessonSourceKind.VideoLink -> stringResource(R.string.tc05_teacher_link)
    }
    val sourceSummary = when (form.sourceKind) {
        TeacherLessonSourceKind.VideoLink -> form.videoLink.trim()
        TeacherLessonSourceKind.Video, TeacherLessonSourceKind.Pdf ->
            listOfNotNull(form.mockFileName, form.mockFileBytes.takeIf { it > 0L }?.let { megabytesLabel(it) })
                .joinToString(" · ")
    }
    val sourceIcon = when (form.sourceKind) {
        TeacherLessonSourceKind.Pdf -> Icons.Filled.Description
        TeacherLessonSourceKind.VideoLink -> Icons.Filled.Link
        TeacherLessonSourceKind.Video -> Icons.Filled.PlayArrow
    }

    EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Icon(imageVector = sourceIcon, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.iconLg))
            Column(modifier = Modifier.weight(1f)) {
                Text(sourceTitle, style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold), color = colors.textPrimary)
                if (sourceSummary.isNotBlank()) {
                    Text(sourceSummary, style = EduTheme.typography.caption, color = colors.textMuted)
                }
            }
            StatusPill(
                label = stringResource(R.string.tc05_selected_ready),
                contentColor = colors.success,
                containerColor = colors.success.copy(alpha = 0.14f),
            )
        }
    }

    Text(
        text = stringResource(R.string.tc05_one_source),
        style = EduTheme.typography.caption,
        color = colors.textMuted,
        modifier = Modifier.padding(bottom = Spacing.sm),
    )

    EduCard(
        borderColor = colors.aiAccent,
        modifier = Modifier.padding(bottom = Spacing.md),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            Icon(
                imageVector = Icons.Filled.AutoAwesome,
                contentDescription = null,
                tint = colors.aiAccent,
                modifier = Modifier.size(Sizing.icon),
            )
            Text(
                text = stringResource(R.string.tc05_after_save_label),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.aiAccent,
            )
        }
        Text(
            text = stringResource(R.string.tc05_after_save_body),
            style = EduTheme.typography.body,
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun OrderStepper(order: Int, maxOrder: Int, onUpdateOrder: (Int) -> Unit) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.padding(bottom = Spacing.sm),
    ) {
        Text(
            text = stringResource(R.string.tc05_order_label),
            style = EduTheme.typography.body,
            color = colors.textPrimary,
            modifier = Modifier.weight(1f),
        )
        EduIconButton(
            icon = Icons.Filled.Remove,
            contentDescription = stringResource(R.string.tc05_order_decrease),
            enabled = order > 1,
            onClick = { onUpdateOrder(order - 1) },
        )
        Text(numeral(order), style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
        EduIconButton(
            icon = Icons.Filled.Add,
            contentDescription = stringResource(R.string.tc05_order_increase),
            enabled = order < maxOrder,
            onClick = { onUpdateOrder(order + 1) },
        )
    }
}

@Composable
private fun UploadActionBar(
    step: Int,
    isStartingUpload: Boolean,
    onAction: () -> Unit,
) {
    val colors = EduTheme.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(Spacing.gutter),
    ) {
        PrimaryButton(
            text = if (step >= 3) stringResource(R.string.tc05_save_lesson) else stringResource(R.string.tc05_next),
            onClick = onAction,
            isLoading = isStartingUpload,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
private fun UploadProgressContent(
    draft: TeacherLessonUploadDraft,
    onPause: () -> Unit,
    onResume: () -> Unit,
    onCancel: () -> Unit,
) {
    val colors = EduTheme.colors
    val progress = if (draft.mockTotalBytes > 0) draft.uploadedBytes.toFloat() / draft.mockTotalBytes else 0f

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxSize()
            .padding(Spacing.gutter),
    ) {
        Spacer(modifier = Modifier.height(Spacing.section))
        Text(draft.mockFileName, style = EduTheme.typography.titleLg, color = colors.textPrimary)
        Text(
            text = lessonUploadStageLabel(draft.stage),
            style = EduTheme.typography.body,
            color = colors.primary,
            modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.section),
        )

        EduLinearProgress(progress = progress, modifier = Modifier.fillMaxWidth())
        Row(
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        ) {
            Text(stringResource(R.string.progress_percent, (progress * 100).toInt()), style = EduTheme.typography.caption, color = colors.textMuted)
            Text(
                text = stringResource(R.string.tc05_bytes_progress, megabytesLabel(draft.uploadedBytes), megabytesLabel(draft.mockTotalBytes)),
                style = EduTheme.typography.caption,
                color = colors.textMuted,
            )
        }

        Spacer(modifier = Modifier.height(Spacing.section))
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            when (draft.stage) {
                LessonUploadStage.Uploading, LessonUploadStage.Preparing ->
                    SecondaryButton(text = stringResource(R.string.tc05_pause), onClick = onPause)

                LessonUploadStage.Paused ->
                    PrimaryButton(text = stringResource(R.string.tc05_resume), onClick = onResume)

                LessonUploadStage.Completed -> Unit
            }
            if (draft.stage != LessonUploadStage.Completed) {
                GhostButton(text = stringResource(R.string.tc05_cancel), onClick = onCancel)
            }
        }
    }
}

@Composable
private fun TeacherLessonUploadSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
    }
}
