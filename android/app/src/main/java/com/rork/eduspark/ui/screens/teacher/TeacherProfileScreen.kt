package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.screens.auth.TeacherSubjectOptions
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * Teacher Edit Profile (الملف الشخصي) — the existing identity/subjects destination,
 * visually aligned to the approved Account editor. Saves back through Teacher Setup state.
 */
@Composable
fun TeacherProfileScreen(
    onBack: () -> Unit,
    onSaved: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherProfileViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                TeacherProfileEvent.Saved -> onSaved()
            }
        }
    }

    EduScaffold(
        title = stringResource(R.string.tc16_row_profile),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherProfileSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) {
            TeacherProfileEditor(
                state = state,
                onUpdateName = viewModel::updateNameDraft,
                onUpdateBio = viewModel::updateBioDraft,
                onToggleGrade = viewModel::toggleGrade,
                onToggleSubject = viewModel::toggleSubject,
                onSave = viewModel::saveProfile,
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TeacherProfileEditor(
    state: TeacherProfileUiState,
    onUpdateName: (String) -> Unit,
    onUpdateBio: (String) -> Unit,
    onToggleGrade: (Grade) -> Unit,
    onToggleSubject: (String) -> Unit,
    onSave: () -> Unit,
) {
    val colors = EduTheme.colors
    var photoAdded by rememberSaveable { mutableStateOf(false) }
    val initial = state.nameDraft.trim().firstOrNull()?.toString().orEmpty()

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.md),
            ) {
                Box(
                    contentAlignment = Alignment.Center,
                    modifier = Modifier
                        .size(Sizing.heroBadge)
                        .background(colors.primaryContainer, CircleShape)
                        .eduClickable(onClickLabel = stringResource(R.string.tc16_change_photo)) {
                            photoAdded = !photoAdded
                        },
                ) {
                    if (photoAdded) {
                        Icon(
                            imageVector = Icons.Filled.Person,
                            contentDescription = null,
                            tint = colors.primary,
                            modifier = Modifier.size(Sizing.iconLg),
                        )
                    } else {
                        Text(
                            text = if (initial.isNotBlank()) initial else "س",
                            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.primary,
                        )
                    }
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .align(Alignment.BottomStart)
                            .offset(x = (-2).dp, y = 2.dp)
                            .size(Sizing.iconLg)
                            .background(colors.primary, CircleShape),
                    ) {
                        Icon(
                            imageVector = Icons.Filled.Add,
                            contentDescription = null,
                            tint = colors.onPrimary,
                            modifier = Modifier.size(Sizing.iconSm),
                        )
                    }
                }
                Text(
                    text = stringResource(R.string.tc16_change_photo),
                    style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textTertiary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .padding(top = Spacing.xs)
                        .eduClickable(onClickLabel = stringResource(R.string.tc16_change_photo)) {
                            photoAdded = !photoAdded
                        },
                )
                Text(
                    text = state.email,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }

        item {
            EduTextField(
                value = state.nameDraft,
                onValueChange = onUpdateName,
                label = stringResource(R.string.tc01_name_label),
                labelPlacement = FieldLabelPlacement.Above,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
            EduTextField(
                value = state.bioDraft,
                onValueChange = onUpdateBio,
                label = stringResource(R.string.tc16_bio_field),
                placeholder = stringResource(R.string.tc01_bio_placeholder),
                labelPlacement = FieldLabelPlacement.Above,
                singleLine = false,
                modifier = Modifier.padding(bottom = Spacing.sm),
            )
        }

        item {
            Text(
                text = stringResource(R.string.tc01_grades_section),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(bottom = Spacing.xxs),
            )
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                verticalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.sm),
            ) {
                Grade.entries.forEach { grade ->
                    CompactSelectChip(
                        label = teacherSetupChipGradeLabel(grade),
                        selected = grade in state.gradesDraft,
                        onClick = { onToggleGrade(grade) },
                    )
                }
            }
        }

        item {
            Text(
                text = stringResource(R.string.tc01_subjects_section),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(bottom = Spacing.xxs),
            )
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                verticalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = Spacing.md),
            ) {
                TeacherSubjectOptions.forEach { option ->
                    CompactSelectChip(
                        label = stringResource(option.labelRes),
                        selected = option.id in state.subjectIdsDraft,
                        onClick = { onToggleSubject(option.id) },
                    )
                }
            }
        }

        item {
            PrimaryButton(
                text = stringResource(R.string.tc01_save),
                onClick = onSave,
                isLoading = state.isSaving,
                enabled = state.nameDraft.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

/** Local Edit Profile chip — quieter unselected catalog, dominant selected. Does not restyle shared EduChip. */
@Composable
private fun CompactSelectChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val colors = EduTheme.colors
    val shape = RoundedCornerShape(Radius.pill)
    val selectedLabel = stringResource(R.string.a11y_selected)
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .background(if (selected) colors.primaryContainer else colors.neutralAlpha100, shape)
            .then(
                if (selected) Modifier.border(Sizing.hairline, colors.primary, shape)
                else Modifier
            )
            .eduClickable(role = Role.Checkbox, onClick = onClick)
            .defaultMinSize(minHeight = 36.dp)
            .padding(horizontal = Spacing.sm, vertical = Spacing.xxs)
            .semantics {
                this.selected = selected
                if (selected) stateDescription = selectedLabel
            },
    ) {
        Text(
            text = label,
            style = EduTheme.typography.caption.copy(
                fontWeight = if (selected) FontWeight.ExtraBold else FontWeight.Medium,
            ),
            color = if (selected) colors.primary else colors.textTertiary,
        )
    }
}

@Composable
private fun TeacherProfileSkeleton() {
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
