package com.rork.eduspark.ui.components.foundation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.semantics.Role
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing

/**
 * The app's single tap affordance.
 *
 * Enforces three foundation rules in one place so no screen has to remember them:
 *  1. **Ripple feedback** — the Android convention (Design System §5b). When iOS is added
 *     this is the one place to swap for an opacity press, instead of auditing every screen.
 *  2. **48×48 minimum touch target**, always. Shrink the visual, never the target.
 *  3. **A TalkBack label for the action**, announced in the active locale.
 */
@Composable
fun Modifier.eduClickable(
    enabled: Boolean = true,
    onClickLabel: String? = null,
    role: Role = Role.Button,
    onClick: () -> Unit,
): Modifier {
    val interactionSource = remember { MutableInteractionSource() }
    val indication = ripple(color = EduTheme.colors.primary)
    return this
        .sizeIn(minWidth = Sizing.touchTarget, minHeight = Sizing.touchTarget)
        .clickable(
            interactionSource = interactionSource,
            indication = indication,
            enabled = enabled,
            onClickLabel = onClickLabel,
            role = role,
            onClick = onClick,
        )
}

/**
 * Haptic confirmation for the moments that deserve it: completing a lesson, unlocking a
 * bead, submitting an answer. Not for ordinary navigation.
 */
@Composable
fun rememberConfirmHaptic(): () -> Unit {
    val haptics = LocalHapticFeedback.current
    return remember(haptics) {
        { haptics.performHapticFeedback(HapticFeedbackType.LongPress) }
    }
}
