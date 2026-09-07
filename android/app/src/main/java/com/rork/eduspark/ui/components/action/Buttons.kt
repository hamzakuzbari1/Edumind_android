package com.rork.eduspark.ui.components.action

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Elevation
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * Actions — new identity.
 *
 * All buttons are pill-shaped, min 48dp tall, and label the *outcome* rather than the
 * mechanism ("Start lesson", not "Submit"). Highlight (formerly barq) is never a button
 * colour.
 *
 * [PrimaryButton] is the one component in this batch that carries the new identity's
 * "soft coloured shadow, but only on primary actions" rule (see [Elevation]) — every other
 * button/surface in the app stays flat (tint + hairline), matching the old system's
 * low-end-GPU discipline.
 */

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isLoading: Boolean = false,
    leadingIcon: ImageVector? = null,
) {
    Button(
        onClick = onClick,
        enabled = enabled && !isLoading,
        shape = RoundedCornerShape(Radius.pill),
        colors = ButtonDefaults.buttonColors(
            containerColor = EduTheme.colors.primary,
            contentColor = EduTheme.colors.onPrimary,
            disabledContainerColor = EduTheme.colors.neutralAlpha100,
            disabledContentColor = EduTheme.colors.textSecondary,
        ),
        contentPadding = ButtonDefaults.ContentPadding,
        modifier = modifier
            .defaultMinSize(minHeight = Sizing.touchTarget)
            .then(
                if (enabled && !isLoading) {
                    Modifier.shadow(
                        elevation = Elevation.action,
                        shape = RoundedCornerShape(Radius.pill),
                        ambientColor = EduTheme.colors.primary.copy(alpha = Elevation.actionTint),
                        spotColor = EduTheme.colors.primary.copy(alpha = Elevation.actionTint),
                    )
                } else {
                    Modifier
                }
            ),
    ) {
        ButtonContent(text = text, isLoading = isLoading, leadingIcon = leadingIcon)
    }
}

@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isLoading: Boolean = false,
    leadingIcon: ImageVector? = null,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled && !isLoading,
        shape = RoundedCornerShape(Radius.pill),
        border = BorderStroke(Sizing.hairline, EduTheme.colors.primary),
        colors = ButtonDefaults.outlinedButtonColors(
            contentColor = EduTheme.colors.primary,
            disabledContentColor = EduTheme.colors.textSecondary,
        ),
        modifier = modifier.defaultMinSize(minHeight = Sizing.touchTarget),
    ) {
        ButtonContent(text = text, isLoading = isLoading, leadingIcon = leadingIcon)
    }
}

@Composable
fun GhostButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: ImageVector? = null,
) {
    TextButton(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(Radius.pill),
        colors = ButtonDefaults.textButtonColors(
            contentColor = EduTheme.colors.primary,
            disabledContentColor = EduTheme.colors.textSecondary,
        ),
        modifier = modifier.defaultMinSize(minHeight = Sizing.touchTarget),
    ) {
        ButtonContent(text = text, isLoading = false, leadingIcon = leadingIcon)
    }
}

/** Destructive actions are always confirmed — pair with `ConfirmDialog`. */
@Composable
fun DestructiveButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isLoading: Boolean = false,
) {
    Button(
        onClick = onClick,
        enabled = enabled && !isLoading,
        shape = RoundedCornerShape(Radius.pill),
        colors = ButtonDefaults.buttonColors(
            containerColor = EduTheme.colors.danger,
            contentColor = EduTheme.colors.onDanger,
            disabledContainerColor = EduTheme.colors.neutralAlpha100,
            disabledContentColor = EduTheme.colors.textSecondary,
        ),
        modifier = modifier.defaultMinSize(minHeight = Sizing.touchTarget),
    ) {
        ButtonContent(text = text, isLoading = isLoading, leadingIcon = null)
    }
}

/**
 * Icon-only action. [contentDescription] is mandatory — an unlabelled icon button is
 * invisible to TalkBack, and the accessibility floor treats that as a defect.
 */
@Composable
fun EduIconButton(
    icon: ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    tint: Color = EduTheme.colors.textPrimary,
) {
    IconButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .size(Sizing.touchTarget)
            .semantics {
                role = Role.Button
                this.contentDescription = contentDescription
            },
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = if (enabled) tint else EduTheme.colors.textSecondary,
            modifier = Modifier.size(Sizing.iconLg),
        )
    }
}

@Composable
private fun ButtonContent(
    text: String,
    isLoading: Boolean,
    leadingIcon: ImageVector?,
) {
    Box(contentAlignment = Alignment.Center) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            verticalAlignment = Alignment.CenterVertically,
            modifier = if (isLoading) Modifier.clearAndSetSemantics { } else Modifier,
        ) {
            if (leadingIcon != null) {
                Icon(
                    imageVector = leadingIcon,
                    contentDescription = null,
                    modifier = Modifier.size(Sizing.icon),
                )
            }
            // The label stays laid out while the spinner overlays it, so the button
            // never changes width mid-request.
            Text(text = text, style = EduTheme.typography.label)
        }
        if (isLoading) {
            CircularProgressIndicator(
                strokeWidth = 2.dp,
                color = EduTheme.colors.onPrimary,
                modifier = Modifier.size(Sizing.icon),
            )
        }
    }
}
