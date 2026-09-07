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
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Workspaces
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.ProjectMode
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-10 · Project Portfolio — the public-artifact showcase.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deliberately calmer than PJ-01: no filters, no chips row, no "what do I do next" framing —
 * a header identity, an optional skills summary, and one card per completed project.
 * [shareProjectSummary] launches the real platform [Intent.ACTION_SEND] (`text/plain`) — genuinely safe, no
 * permission, no FileProvider — the honest, minimal Android share abstraction this slice needs;
 * see [ProjectShowcaseDetailScreen]'s own doc comment for why the certificate's *image* export
 * stays a MOCK boundary instead.
 */
@Composable
fun PortfolioScreen(
    onBack: () -> Unit,
    onOpenShowcaseDetail: (projectId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: PortfolioViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    EduScaffold(title = stringResource(R.string.pj10_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { PortfolioSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            PortfolioContent(
                data = data,
                onOpenProject = onOpenShowcaseDetail,
                onShareProject = { entry -> shareProjectSummary(context, entry) },
            )
        }
    }
}

@Composable
private fun PortfolioContent(
    data: PortfolioScreenData,
    onOpenProject: (String) -> Unit,
    onShareProject: (PortfolioEntry) -> Unit,
) {
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item { PortfolioHeader(data) }

        if (data.entries.isEmpty()) {
            item {
                MessageState(
                    icon = Icons.Filled.Workspaces,
                    title = stringResource(R.string.pj10_empty_title),
                    body = stringResource(R.string.pj10_empty_body),
                )
            }
        } else {
            items(data.entries, key = { it.project.id }) { entry ->
                PortfolioProjectCard(
                    entry = entry,
                    onOpen = { onOpenProject(entry.project.id) },
                    onShare = { onShareProject(entry) },
                )
                Spacer(modifier = Modifier.height(Spacing.sm))
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PortfolioHeader(data: PortfolioScreenData) {
    val colors = EduTheme.colors
    Column(modifier = Modifier.padding(bottom = Spacing.section)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(data.avatarInitial, style = EduTheme.typography.titleLg, color = colors.primary)
            }
            Column {
                Text(data.displayName, style = EduTheme.typography.titleLg, color = colors.textPrimary)
                Text(
                    text = stringResource(R.string.pj10_intro),
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        Text(
            text = stringResource(R.string.pj10_completed_count, numeral(data.entries.size)),
            style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textPrimary,
            modifier = Modifier.padding(top = Spacing.md),
        )
        if (data.skillsSummary.isNotEmpty()) {
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            ) {
                data.skillsSummary.take(6).forEach { skill -> EduChip(label = skill, selected = false, onClick = {}, enabled = false) }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun PortfolioProjectCard(entry: PortfolioEntry, onOpen: () -> Unit, onShare: () -> Unit) {
    val colors = EduTheme.colors
    val project = entry.project

    EduCard(onClick = onOpen) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .fillMaxWidth()
                .height(96.dp)
                .background(colors.primaryContainer, RoundedCornerShape(Radius.md)),
        ) {
            Icon(Icons.Filled.PhotoLibrary, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.stateIcon))
        }

        Row(
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.sm),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(project.subjectTitle, style = EduTheme.typography.caption, color = colors.primary)
                Text(
                    text = project.title,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            EduIconButton(
                icon = Icons.Filled.Share,
                contentDescription = stringResource(R.string.pj10_share),
                onClick = onShare,
            )
        }
        Text(project.deliverable, style = EduTheme.typography.body, color = colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))

        if (entry.active.completedAtLabel != null) {
            Text(
                text = stringResource(R.string.pj10_completed_on, entry.active.completedAtLabel),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        }

        if (project.skills.isNotEmpty()) {
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            ) {
                project.skills.take(3).forEach { skill -> EduChip(label = skill, selected = false, onClick = {}, enabled = false) }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs), modifier = Modifier.padding(top = Spacing.sm)) {
            ModeChip(icon = if (project.mode == ProjectMode.Solo) Icons.Filled.Person else Icons.Filled.Groups, label = projectModeLabel(project.mode))
        }
    }
}

@Composable
private fun ModeChip(label: String, icon: ImageVector) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = Modifier
            .background(colors.neutralAlpha100, RoundedCornerShape(Radius.pill))
            .padding(horizontal = Spacing.sm, vertical = Spacing.xxs),
    ) {
        Icon(icon, contentDescription = null, tint = colors.textSecondary, modifier = Modifier.size(Sizing.iconSm))
        Text(label, style = EduTheme.typography.caption, color = colors.textSecondary)
    }
}

@Composable
private fun PortfolioSkeleton() {
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

/**
 * The real, safe Android share abstraction (`ACTION_SEND`, `text/plain`) — no FileProvider, no
 * MediaStore, no storage permission, because plain-text sharing needs none. This is genuine
 * platform sharing, not a MOCK; only the certificate *image* export (PJ-11) stays a MOCK
 * boundary, since no real image-rendering pipeline exists for this slice.
 */
private fun shareProjectSummary(context: Context, entry: PortfolioEntry) {
    val project = entry.project
    val text = buildString {
        append(project.title)
        append(" — ")
        append(project.deliverable)
        if (project.skills.isNotEmpty()) {
            append("\n")
            append(project.skills.joinToString(", "))
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

