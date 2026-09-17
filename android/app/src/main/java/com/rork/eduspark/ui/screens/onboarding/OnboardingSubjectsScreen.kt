package com.rork.eduspark.ui.screens.onboarding

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.SubjectGroup
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.surface.SkeletonBlock
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * SO-02 · Onboarding: Subjects
 * ══════════════════════════════════════════════════════════════════════════
 *
 * "Chips grouped by track, so a science student sees their core group first and the
 * electives second — the grouping does the filtering instead of a dropdown." Groups come
 * from [OnboardingCatalog.groupsFor], keyed off the track chosen on SO-01.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun OnboardingSubjectsScreen(
    onBack: () -> Unit,
    onContinue: () -> Unit,
    viewModel: OnboardingViewModel,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showValidation by remember { mutableStateOf(false) }

    BackHandler { onBack() }

    LaunchedEffect(viewModel) {
        viewModel.loadSubjectsIfNeeded()
        viewModel.events.collect { event ->
            if (event == OnboardingEvent.SubjectsSaved) onContinue()
        }
    }

    OnboardingStepScaffold(
        step = 2,
        onBack = onBack,
        bottomBar = {
            when {
                state.subjectsSaveFailed -> Text(
                    text = stringResource(R.string.state_error_unknown_body),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.danger,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )

                state.subjectIds.isNotEmpty() -> Text(
                    text = pluralStringResource(
                        R.plurals.so02_selected_count,
                        state.subjectIds.size,
                        state.subjectIds.size,
                    ),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textMuted,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )

                showValidation -> Text(
                    text = stringResource(R.string.so02_error_min_one),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.danger,
                    modifier = Modifier.padding(bottom = Spacing.xs),
                )
            }
            PrimaryButton(
                text = stringResource(R.string.so02_continue),
                onClick = { if (state.canContinueFromSubjects) viewModel.saveSubjects() else showValidation = true },
                isLoading = state.isSavingSubjects,
                modifier = Modifier.fillMaxWidth(),
            )
        },
    ) {
        Text(
            text = stringResource(R.string.so02_title),
            style = EduTheme.typography.titleLg,
            color = EduTheme.colors.textPrimary,
        )
        Text(
            text = stringResource(R.string.so02_body),
            style = EduTheme.typography.body,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.padding(top = Spacing.xs),
        )

        when (val subjectsState = state.availableSubjects) {
            UiState.Loading -> Column(
                verticalArrangement = Arrangement.spacedBy(Spacing.sm),
                modifier = Modifier.padding(top = Spacing.section),
            ) {
                repeat(3) { SkeletonBlock(widthFraction = 1f) }
            }

            is UiState.Failure -> Column(modifier = Modifier.padding(top = Spacing.section)) {
                Text(
                    text = stringResource(R.string.state_error_network_body),
                    style = EduTheme.typography.body,
                    color = EduTheme.colors.textMuted,
                )
                SecondaryButton(
                    text = stringResource(R.string.common_retry),
                    onClick = viewModel::retrySubjects,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }

            is UiState.Empty -> Text(
                text = stringResource(R.string.state_empty_default_body),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textMuted,
                modifier = Modifier.padding(top = Spacing.section),
            )

            is UiState.Content -> listOf(
                SubjectGroup.Core to R.string.so02_group_science_core,
                SubjectGroup.LanguagesAndGeneral to R.string.so02_group_languages_general,
            ).forEach { (group, groupTitleRes) ->
                val subjects = subjectsState.data.filter { it.group == group }
                if (subjects.isNotEmpty()) {
                    Text(
                        text = stringResource(groupTitleRes),
                        style = EduTheme.typography.caption,
                        color = EduTheme.colors.textMuted,
                        modifier = Modifier.padding(top = Spacing.section),
                    )
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = Spacing.xs),
                    ) {
                        subjects.forEach { subject ->
                            EduChip(
                                label = subject.name,
                                selected = subject.id in state.subjectIds,
                                onClick = { viewModel.toggleSubject(subject.id) },
                            )
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(Spacing.xxs))
    }
}
