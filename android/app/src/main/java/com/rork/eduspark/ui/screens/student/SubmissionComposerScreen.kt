package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.InsertDriveFile
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ProjectTask
import com.rork.eduspark.data.model.SubmissionAttachment
import com.rork.eduspark.data.model.SubmissionDraft
import com.rork.eduspark.data.model.SubmissionType
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-05 · Submission Composer.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Only the submission types [ProjectTask.acceptedSubmissionTypes] declares are ever shown —
 * this composer never assumes every task supports every type. Photo/file "attachment" buttons
 * are honest MOCK boundaries (see [SubmissionComposerViewModel]'s own doc comment) — no
 * CameraX, no gallery picker, no file provider. Back always saves the draft first.
 */
@Composable
fun SubmissionComposerScreen(
    projectId: String,
    taskId: String,
    onBack: () -> Unit,
    onSubmitted: (taskId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: SubmissionComposerViewModel = koinViewModel(parameters = { parametersOf(projectId, taskId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                SubmissionComposerEvent.Submitted -> onSubmitted(taskId)
            }
        }
    }

    val handleBack: () -> Unit = {
        viewModel.saveDraft()
        onBack()
    }

    EduScaffold(title = stringResource(R.string.pj05_title), onBack = handleBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ComposerSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            Column(modifier = Modifier.fillMaxSize()) {
                ComposerContent(
                    task = data.task,
                    draft = data.draft,
                    showValidationError = state.showValidationError,
                    onUpdateReflection = viewModel::updateReflection,
                    onUpdateLink = viewModel::updateLink,
                    onAddAttachment = viewModel::addMockAttachment,
                    onRemoveAttachment = viewModel::removeAttachment,
                    modifier = Modifier.weight(1f),
                )
                ComposerActionBar(
                    phase = state.phase,
                    onSaveDraft = viewModel::saveDraft,
                    onSubmit = viewModel::submit,
                )
            }
        }
    }
}

@Composable
private fun ComposerContent(
    task: ProjectTask,
    draft: SubmissionDraft,
    showValidationError: Boolean,
    onUpdateReflection: (String) -> Unit,
    onUpdateLink: (String) -> Unit,
    onAddAttachment: (SubmissionType) -> Unit,
    onRemoveAttachment: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val accepted = task.acceptedSubmissionTypes

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = modifier.fillMaxSize(),
    ) {
        item {
            Text(task.title, style = EduTheme.typography.titleLg, color = colors.textPrimary)
            Text(
                text = stringResource(R.string.pj05_intro),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs, bottom = Spacing.section),
            )
        }

        if (SubmissionType.WrittenReflection in accepted) {
            item {
                SectionHeader(title = stringResource(R.string.pj05_reflection_section))
                EduTextField(
                    value = draft.writtenReflection,
                    onValueChange = onUpdateReflection,
                    label = stringResource(R.string.pj05_reflection_label),
                    singleLine = false,
                    modifier = Modifier.padding(bottom = Spacing.section),
                )
            }
        }

        if (SubmissionType.Photo in accepted || SubmissionType.File in accepted) {
            item {
                SectionHeader(title = stringResource(R.string.pj05_attachments_section))
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    if (SubmissionType.Photo in accepted) {
                        SecondaryButton(
                            text = stringResource(R.string.pj05_add_photo),
                            onClick = { onAddAttachment(SubmissionType.Photo) },
                            leadingIcon = Icons.Filled.PhotoCamera,
                        )
                    }
                    if (SubmissionType.File in accepted) {
                        SecondaryButton(
                            text = stringResource(R.string.pj05_add_file),
                            onClick = { onAddAttachment(SubmissionType.File) },
                            leadingIcon = Icons.Filled.AttachFile,
                        )
                    }
                }
            }
            items(draft.attachments, key = { it.id }) { attachment ->
                AttachmentRow(attachment = attachment, onRemove = { onRemoveAttachment(attachment.id) })
                Spacer(modifier = Modifier.height(Spacing.xs))
            }
            item { Spacer(modifier = Modifier.height(Spacing.section - Spacing.xs)) }
        }

        if (SubmissionType.Link in accepted) {
            item {
                SectionHeader(title = stringResource(R.string.pj05_link_section))
                EduTextField(
                    value = draft.link,
                    onValueChange = onUpdateLink,
                    label = stringResource(R.string.pj05_link_label),
                    leadingIcon = Icons.Filled.Link,
                    modifier = Modifier.padding(bottom = Spacing.section),
                )
            }
        }

        if (showValidationError) {
            item {
                Text(
                    text = stringResource(R.string.pj05_validation_error),
                    style = EduTheme.typography.caption,
                    color = colors.danger,
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
            }
        }
    }
}

@Composable
private fun AttachmentRow(attachment: SubmissionAttachment, onRemove: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Icon(
                    imageVector = if (attachment.type == SubmissionType.Photo) Icons.Filled.PhotoCamera else Icons.Filled.InsertDriveFile,
                    contentDescription = null,
                    tint = colors.primary,
                )
            }
            Text(attachment.label, style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.weight(1f))
            EduIconButton(
                icon = Icons.Filled.Close,
                contentDescription = stringResource(R.string.pj05_remove_attachment),
                tint = colors.danger,
                onClick = onRemove,
            )
        }
    }
}

@Composable
private fun ComposerActionBar(phase: ComposerPhase, onSaveDraft: () -> Unit, onSubmit: () -> Unit) {
    val colors = EduTheme.colors
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .padding(Spacing.gutter),
    ) {
        SecondaryButton(
            text = stringResource(R.string.pj05_save_draft),
            onClick = onSaveDraft,
            isLoading = phase == ComposerPhase.SavingDraft,
            modifier = Modifier.weight(1f),
        )
        PrimaryButton(
            text = stringResource(R.string.pj05_submit),
            onClick = onSubmit,
            isLoading = phase == ComposerPhase.Submitting,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun ComposerSkeleton() {
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

