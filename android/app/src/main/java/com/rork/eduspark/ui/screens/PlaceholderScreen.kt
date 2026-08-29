package com.rork.eduspark.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.ai.AiMarker
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing

/**
 * Honest placeholder for a destination that exists in the navigation graph but whose
 * screen has not been designed or built yet.
 *
 * It names the screen ID and the phase, so walking the app during the foundation review
 * shows exactly what is scheduled where — rather than a blank screen or, worse, a
 * fabricated UI that implies work that has not happened.
 *
 * @param screenId the Screen Inventory identifier, e.g. "ST-01 · Student Home".
 * @param phase the phase label, e.g. "Phase 1".
 * @param backendPending true for features with no backend at all (Projects, push,
 * real payments) — surfaces the pending-integration note.
 */
@Composable
fun PlaceholderScreen(
    screenId: String,
    phase: String,
    modifier: Modifier = Modifier,
    backendPending: Boolean = false,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(Spacing.sm, Alignment.CenterVertically),
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter),
    ) {
        Text(
            text = stringResource(R.string.placeholder_title),
            style = EduTheme.typography.brandTitle,
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Center,
        )
        Text(
            text = stringResource(R.string.placeholder_body, screenId, phase),
            style = EduTheme.typography.body,
            color = EduTheme.colors.textMuted,
            textAlign = TextAlign.Center,
        )
        if (backendPending) {
            EduCard(modifier = Modifier.padding(top = Spacing.sm)) {
                AiMarker()
                Text(
                    text = stringResource(R.string.placeholder_backend_pending),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textMuted,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }
    }
}
