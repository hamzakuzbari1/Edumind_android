package com.rork.eduspark.ui.components.progress

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing

/**
 * PJ-01's compact horizontal milestone-bead preview (ProjectsHub.dc.html's `.milestonerow`).
 *
 * Deliberately its own small component, not a reuse of the vertical [ProgressSpine]/[SpineRow]
 * — that component's rendering shape (a continuous rail, one bead per row, virtualised for long
 * lists) doesn't fit a compact single-row summary on a project card. It reuses [SpineNodeState]
 * (the same Completed/Current/Locked vocabulary) purely as data, not as a rendering dependency,
 * so a milestone's state reads identically wherever it's shown — this preview, and PJ-03's own
 * full board — without inventing a second three-state enum.
 *
 * The current bead's amber [EduTheme.colors.highlight] fill matches the one other sanctioned
 * "current" bead in the app (the vertical spine's own ring) — a real, already-shipped precedent,
 * not a new use of highlight.
 */
@Composable
fun HorizontalMilestoneBeads(states: List<SpineNodeState>, modifier: Modifier = Modifier) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = modifier.fillMaxWidth()) {
        states.forEachIndexed { index, state ->
            MilestoneBead(state)
            if (index != states.lastIndex) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(2.dp)
                        .background(if (state == SpineNodeState.Completed) EduTheme.colors.primary else EduTheme.colors.border),
                )
            }
        }
    }
}

@Composable
private fun MilestoneBead(state: SpineNodeState) {
    val colors = EduTheme.colors
    val beadSize = 22.dp

    when (state) {
        SpineNodeState.Completed -> Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.size(beadSize).background(colors.primary, CircleShape),
        ) {
            Icon(Icons.Filled.Check, contentDescription = null, tint = colors.onPrimary, modifier = Modifier.size(Sizing.iconSm))
        }

        SpineNodeState.Current -> Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.size(beadSize).background(colors.highlight, CircleShape),
        ) {
            Icon(Icons.Filled.PlayArrow, contentDescription = null, tint = colors.onHighlight, modifier = Modifier.size(Sizing.iconSm))
        }

        SpineNodeState.Locked -> Box(modifier = Modifier.size(beadSize).background(colors.neutralAlpha100, CircleShape))
    }
}
