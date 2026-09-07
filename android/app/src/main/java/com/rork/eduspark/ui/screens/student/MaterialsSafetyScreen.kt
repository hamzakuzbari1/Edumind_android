package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ProjectMaterial
import com.rork.eduspark.data.model.ProjectSafetyNote
import com.rork.eduspark.data.model.SafetySeverity
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
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
 * PJ-12 · Materials & Safety Sheet.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Practical and scannable, not decorative — materials first (with the same checklist
 * [ProjectDetailScreen]'s own `MaterialsSection` already uses), a plain cost estimate, then
 * safety guidance grouped by [SafetySeverity]. [SafetySeverity.Important] rows use
 * [EduTheme.colors.danger] and [SafetySeverity.Caution] rows use [EduTheme.colors.warning] — a
 * tinted card, never a solid fear-heavy red fill, but still visually unmistakable next to a
 * plain material row. Entirely static [com.rork.eduspark.data.repository.mock.MockProjectRepository]
 * fixture data — [ScreenStateHost]'s [isOffline] only ever adds the banner on top; it never
 * gates whether this content loads.
 */
@Composable
fun MaterialsSafetyScreen(
    projectId: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: MaterialsSafetyViewModel = koinViewModel(parameters = { parametersOf(projectId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    EduScaffold(title = stringResource(R.string.pj12_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { MaterialsSafetySkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            MaterialsSafetyContent(data = data, onToggleMaterial = viewModel::toggleMaterial)
        }
    }
}

@Composable
private fun MaterialsSafetyContent(data: MaterialsSafetyScreenData, onToggleMaterial: (String, Boolean) -> Unit) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Text(data.projectTitle, style = EduTheme.typography.titleLg, color = colors.textPrimary)
            SectionHeader(title = stringResource(R.string.pj12_materials_section))
        }
        items(data.materials, key = { it.id }) { material ->
            MaterialRow(
                material = material,
                checked = material.id in data.checkedMaterialIds,
                onToggle = { checked -> onToggleMaterial(material.id, checked) },
            )
        }

        if (data.estimatedTotalCostLabel != null) {
            item {
                SectionHeader(title = stringResource(R.string.pj12_cost_section))
                EduCard {
                    Text(
                        text = data.estimatedTotalCostLabel,
                        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                    )
                    Text(
                        text = stringResource(R.string.pj12_cost_estimate_note),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                }
            }
        }

        if (data.safetyNotes.isNotEmpty()) {
            item { SectionHeader(title = stringResource(R.string.pj12_safety_section)) }
            items(data.safetyNotes, key = { it.id }) { note -> SafetyNoteRow(note) }
        }
    }
}

@Composable
private fun MaterialRow(material: ProjectMaterial, checked: Boolean, onToggle: (Boolean) -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(
                checked = checked,
                onCheckedChange = onToggle,
                colors = CheckboxDefaults.colors(checkedColor = colors.primary, checkmarkColor = colors.onPrimary),
            )
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                    Text(
                        text = material.label,
                        style = EduTheme.typography.body,
                        color = if (checked) colors.textSecondary else colors.textPrimary,
                    )
                    if (!material.isRequired) {
                        StatusPill(
                            label = stringResource(R.string.pj12_optional),
                            contentColor = colors.textSecondary,
                            containerColor = colors.neutralAlpha100,
                        )
                    }
                }
                if (material.quantityLabel != null) {
                    Text(
                        text = stringResource(R.string.pj12_quantity_format, material.quantityLabel),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
                if (material.localSourcingNote != null) {
                    Text(
                        text = material.localSourcingNote,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                }
            }
            if (material.estimatedCostLabel != null) {
                Text(material.estimatedCostLabel, style = EduTheme.typography.body, color = colors.textSecondary)
            }
        }
    }
}

@Composable
private fun SafetyNoteRow(note: ProjectSafetyNote) {
    val colors = EduTheme.colors
    val tint = if (note.severity == SafetySeverity.Important) colors.danger else colors.warning
    val icon = if (note.severity == SafetySeverity.Important) Icons.Filled.ErrorOutline else Icons.Filled.WarningAmber

    Row(
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .background(tint.copy(alpha = 0.12f), RoundedCornerShape(Radius.md))
            .padding(Spacing.card)
            .padding(bottom = Spacing.xs),
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(Sizing.icon))
        Text(note.text, style = EduTheme.typography.body, color = colors.textPrimary)
    }
}

@Composable
private fun MaterialsSafetySkeleton() {
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

