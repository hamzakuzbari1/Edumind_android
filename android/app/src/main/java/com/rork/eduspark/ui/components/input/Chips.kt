package com.rork.eduspark.ui.components.input

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * Selectable chip — subject pickers (SO-02), filters, quick-reply chips in the
 * conversational routine builder, suggested tutor questions.
 *
 * Selection is never signalled by colour alone (Design System §3): a checkmark appears
 * and the state is exposed to TalkBack through `selected` + `stateDescription`.
 */
@Composable
fun EduChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: ImageVector? = null,
) {
    val shape = RoundedCornerShape(Radius.pill)
    val container = if (selected) EduTheme.colors.zaytounSoft else EduTheme.colors.surface
    val border = if (selected) EduTheme.colors.zaytoun else EduTheme.colors.border
    val content = when {
        !enabled -> EduTheme.colors.textMuted
        selected -> EduTheme.colors.zaytoun
        else -> EduTheme.colors.textPrimary
    }
    val selectedLabel = stringResource(R.string.a11y_selected)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier
            .background(container, shape)
            .border(Sizing.hairline, border, shape)
            .eduClickable(enabled = enabled, role = Role.Checkbox, onClick = onClick)
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .padding(horizontal = Spacing.md, vertical = Spacing.xs)
            .semantics {
                this.selected = selected
                if (selected) stateDescription = selectedLabel
            },
    ) {
        if (selected) {
            // Not mirrored: a checkmark is not directional.
            Icon(
                imageVector = Icons.Filled.Check,
                contentDescription = null,
                tint = content,
                modifier = Modifier.size(Sizing.iconSm),
            )
        } else if (leadingIcon != null) {
            Icon(
                imageVector = leadingIcon,
                contentDescription = null,
                tint = content,
                modifier = Modifier.size(Sizing.iconSm),
            )
        }
        Text(text = label, style = EduTheme.typography.caption, color = content)
    }
}
