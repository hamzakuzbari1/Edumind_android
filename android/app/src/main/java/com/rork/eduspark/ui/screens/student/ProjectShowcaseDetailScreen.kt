package com.rork.eduspark.ui.screens.student

import android.content.Context
import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CardMembership
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.ActiveProject
import com.rork.eduspark.data.model.Project
import com.rork.eduspark.data.model.ProjectReflection
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.progress.ProgressSpine
import com.rork.eduspark.ui.components.progress.SpineNode
import com.rork.eduspark.ui.components.progress.SpineNodeState
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-10 · Project Showcase Detail — the polished, single-project artifact view.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Every section reuses data this app already has — [ProgressSpine] for the milestone summary
 * (every bead [SpineNodeState.Completed] by construction, since this screen only ever loads
 * for [com.rork.eduspark.data.model.ActiveProject.isFullyCompleted]), [ProjectReflection] from
 * PJ-09 verbatim, and the certificate entry point only appears when
 * [ShowcaseDetailScreenData.certificateCode] is non-null. Sharing is the same real
 * `text/plain` [Intent.ACTION_SEND] [PortfolioScreen] uses — see that file's own doc comment
 * for why this is genuine platform sharing, not a MOCK.
 */
@Composable
fun ProjectShowcaseDetailScreen(
    projectId: String,
    onBack: () -> Unit,
    onOpenCertificate: (projectId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ProjectShowcaseDetailViewModel = koinViewModel(parameters = { parametersOf(projectId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    EduScaffold(
        title = stringResource(R.string.pj10_detail_title),
        onBack = onBack,
        actions = {
            val data = (state.result as? UiState.Content)?.data
            if (data != null) {
                EduIconButton(
                    icon = Icons.Filled.Share,
                    contentDescription = stringResource(R.string.pj10_share),
                    onClick = { shareShowcaseDetail(context, data.project, data.active) },
                )
            }
        },
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { ShowcaseDetailSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            ShowcaseDetailContent(
                data = data,
                onOpenCertificate = { onOpenCertificate(projectId) },
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ShowcaseDetailContent(data: ShowcaseDetailScreenData, onOpenCertificate: () -> Unit) {
    val colors = EduTheme.colors
    val project = data.project

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(160.dp)
                    .background(colors.primaryContainer, RoundedCornerShape(Radius.md)),
            ) {
                Icon(Icons.Filled.PhotoLibrary, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.stateIcon))
            }

            Text(project.subjectTitle, style = EduTheme.typography.caption, color = colors.primary, modifier = Modifier.padding(top = Spacing.md))
            Text(
                text = project.title,
                style = EduTheme.typography.brandTitle,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
            if (data.active.completedAtLabel != null) {
                Text(
                    text = stringResource(R.string.pj10_completed_on, data.active.completedAtLabel),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pj10_what_was_built_section))
            Text(project.deliverable, style = EduTheme.typography.body, color = colors.textPrimary)
            Text(
                text = project.description,
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }

        if (project.skills.isNotEmpty()) {
            item {
                SectionHeader(title = stringResource(R.string.pj10_skills_section))
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                    verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    project.skills.forEach { skill -> EduChip(label = skill, selected = false, onClick = {}, enabled = false) }
                }
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pj10_milestones_section))
            val nodes = data.active.milestones.map { SpineNode(id = it.id, state = SpineNodeState.Completed) }
            ProgressSpine(nodes = nodes) { index, _ ->
                Text(
                    text = data.active.milestones[index].title,
                    style = EduTheme.typography.body,
                    color = colors.textPrimary,
                    modifier = Modifier.padding(start = Spacing.xs, end = Spacing.xs, top = Spacing.xs),
                )
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pj10_final_deliverable_section))
            EduCard {
                Text(project.deliverable, style = EduTheme.typography.body, color = colors.textPrimary)
            }
        }

        if (data.reflections.isNotEmpty()) {
            item { SectionHeader(title = stringResource(R.string.pj10_reflections_section)) }
            items(data.reflections, key = { it.milestoneId }) { reflection -> ReflectionCard(reflection) }
        }

        if (data.certificateCode != null) {
            item {
                SectionHeader(title = stringResource(R.string.pj10_certificate_section))
                EduCard(onClick = onOpenCertificate, borderColor = colors.primary) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                        Icon(Icons.Filled.CardMembership, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.icon))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = stringResource(R.string.pj10_certificate_available_title),
                                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                                color = colors.textPrimary,
                            )
                            Text(
                                text = stringResource(R.string.pj10_certificate_available_body),
                                style = EduTheme.typography.caption,
                                color = colors.textSecondary,
                            )
                        }
                    }
                }
                PrimaryButton(
                    text = stringResource(R.string.pj10_view_certificate),
                    onClick = onOpenCertificate,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.sm),
                )
            }
        }
    }
}

@Composable
private fun ReflectionCard(reflection: ProjectReflection) {
    val colors = EduTheme.colors
    EduCard {
        Text(
            text = reflection.milestoneTitle,
            style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
        )
        Text(
            text = reflection.transcript,
            style = EduTheme.typography.body,
            color = colors.textSecondary,
            modifier = Modifier.padding(top = Spacing.xs),
        )
    }
}

@Composable
private fun ShowcaseDetailSkeleton() {
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

private fun shareShowcaseDetail(context: Context, project: Project, active: ActiveProject) {
    val text = buildString {
        append(project.title)
        append(" — ")
        append(project.deliverable)
        if (project.skills.isNotEmpty()) {
            append("\n")
            append(project.skills.joinToString(", "))
        }
        if (active.completedAtLabel != null) {
            append("\n")
            append(active.completedAtLabel)
        }
        append("\n")
        append("EduMind")
    }
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, text)
    }
    context.startActivity(Intent.createChooser(intent, null))
}

