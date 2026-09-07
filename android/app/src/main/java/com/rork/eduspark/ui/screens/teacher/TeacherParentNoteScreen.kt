package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.TeacherParentNote
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * Parent Note — PDF page 28.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Not the Messages / Parent Chat redesign. Uses [TeacherRepository.getParentNotes] /
 * [TeacherRepository.sendParentNote] only. Category/priority chips are omitted because
 * [TeacherParentNote] has no such fields.
 */
@Composable
fun TeacherParentNoteScreen(
    studentId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherParentNoteViewModel = koinViewModel(parameters = { parametersOf(studentId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.tc13n_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherParentNoteSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .imePadding(),
            ) {
                LazyColumn(
                    contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
                    modifier = Modifier.weight(1f),
                ) {
                    if (data.notes.isEmpty()) {
                        item {
                            Text(
                                text = stringResource(R.string.tc13n_empty),
                                style = EduTheme.typography.body,
                                color = EduTheme.colors.textMuted,
                            )
                        }
                    } else {
                        items(data.notes, key = { it.id }) { note ->
                            ParentNoteBubble(note = note)
                        }
                    }
                }
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(EduTheme.colors.surface)
                        .padding(Spacing.gutter),
                ) {
                    EduTextField(
                        value = state.draft,
                        onValueChange = viewModel::updateDraft,
                        label = "",
                        placeholder = stringResource(R.string.tc13n_reply_hint),
                        labelPlacement = FieldLabelPlacement.Above,
                        singleLine = false,
                        imeAction = ImeAction.Default,
                        modifier = Modifier.padding(bottom = Spacing.sm),
                    )
                    PrimaryButton(
                        text = stringResource(R.string.tc13_send),
                        onClick = viewModel::sendReply,
                        enabled = state.draft.isNotBlank(),
                        isLoading = state.isSending,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}

@Composable
private fun ParentNoteBubble(note: TeacherParentNote) {
    val colors = EduTheme.colors
    EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
        Text(
            text = stringResource(R.string.tc13n_you, note.sentLabel),
            style = EduTheme.typography.caption,
            color = colors.textMuted,
        )
        Text(
            text = note.message,
            style = EduTheme.typography.body,
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun TeacherParentNoteSkeleton() {
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
