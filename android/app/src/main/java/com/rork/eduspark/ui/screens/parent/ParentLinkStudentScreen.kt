package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.PersonAdd
import androidx.compose.material.icons.filled.School
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun ParentLinkStudentScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentLinkStudentViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(
        title = stringResource(R.string.pr01_title),
        onBack = onBack,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ParentLinkStudentSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ParentLinkStudentContent(
                data = data,
                state = state,
                onCodeChange = viewModel::updateCode,
                onSubmit = viewModel::submit,
                onDone = onBack,
            )
        }
    }
}

@Composable
private fun ParentLinkStudentContent(
    data: ParentLinkStudentData,
    state: ParentLinkStudentUiState,
    onCodeChange: (String) -> Unit,
    onSubmit: () -> Unit,
    onDone: () -> Unit,
) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(
                containerColor = colors.primary,
                borderColor = colors.primary,
            ) {
                Text(
                    text = stringResource(R.string.pr01_hero_eyebrow),
                    style = EduTheme.typography.caption,
                    color = colors.onPrimary.copy(alpha = 0.82f),
                )
                Text(
                    text = stringResource(R.string.pr01_hero_title),
                    style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.onPrimary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
                Text(
                    text = stringResource(R.string.pr01_hero_body),
                    style = EduTheme.typography.body,
                    color = colors.onPrimary.copy(alpha = 0.86f),
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }

        item {
            EduCard {
                EduTextField(
                    value = state.code,
                    onValueChange = onCodeChange,
                    label = stringResource(R.string.pr01_code_label),
                    placeholder = stringResource(R.string.pr01_code_placeholder),
                    supportingText = stringResource(R.string.pr01_code_help),
                    errorText = if (state.invalidCode) stringResource(R.string.pr01_invalid_code) else null,
                    leadingIcon = Icons.Filled.Link,
                    imeAction = ImeAction.Done,
                    labelPlacement = FieldLabelPlacement.Above,
                )
                PrimaryButton(
                    text = stringResource(R.string.pr01_submit),
                    onClick = onSubmit,
                    enabled = state.code.isNotBlank(),
                    isLoading = state.isSubmitting,
                    leadingIcon = Icons.Filled.PersonAdd,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.md),
                )
            }
        }

        state.linkedStudentName?.let { name ->
            item {
                EduCard(
                    containerColor = colors.success.copy(alpha = 0.12f),
                    borderColor = colors.success.copy(alpha = 0.32f),
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                    ) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = colors.success)
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = stringResource(R.string.pr01_success_title),
                                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                                color = colors.textPrimary,
                            )
                            Text(
                                text = stringResource(R.string.pr01_success_body, name),
                                style = EduTheme.typography.caption,
                                color = colors.textSecondary,
                            )
                        }
                    }
                    SecondaryButton(
                        text = stringResource(R.string.pr01_view_account),
                        onClick = onDone,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = Spacing.sm),
                    )
                }
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pr01_linked_students_section))
        }

        if (data.linkedStudents.isEmpty()) {
            item {
                EduCard {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                    ) {
                        Icon(Icons.Filled.School, contentDescription = null, tint = colors.textSecondary)
                        Column {
                            Text(
                                text = stringResource(R.string.pr01_no_students_title),
                                style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                                color = colors.textPrimary,
                            )
                            Text(
                                text = stringResource(R.string.pr01_no_students_body),
                                style = EduTheme.typography.caption,
                                color = colors.textSecondary,
                            )
                        }
                    }
                }
            }
        } else {
            items(data.linkedStudents, key = { it.id }) { student ->
                ParentLinkedStudentCard(student = student)
            }
        }

        item {
            Spacer(modifier = Modifier.height(Spacing.section))
        }
    }
}

@Composable
private fun ParentLinkStudentSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        repeat(2) { SkeletonListItem() }
    }
}
