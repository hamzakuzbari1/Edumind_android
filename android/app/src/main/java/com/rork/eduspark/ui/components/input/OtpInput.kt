package com.rork.eduspark.ui.components.input

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * Six-cell OTP input, shared by A-08 Verify Email and A-09 Two-Factor Verify.
 *
 * Two RTL details that are easy to get wrong, handled here once:
 *  1. **The code itself is LTR even in Arabic.** A one-time code is a digit sequence;
 *     laying the cells out right-to-left would make the user type it backwards. The cell
 *     row is pinned to LTR while the surrounding screen stays RTL.
 *  2. The value is always *stored* in Western digits; only the display honours the
 *     user's numeral preference.
 *
 * A single hidden field owns the value, so paste, SMS autofill and hardware keyboards all
 * work — six separate fields break all three.
 */
@Composable
fun OtpInput(
    value: String,
    onValueChange: (String) -> Unit,
    contentDescription: String,
    modifier: Modifier = Modifier,
    length: Int = 6,
    isError: Boolean = false,
    enabled: Boolean = true,
) {
    val focusRequester = remember { FocusRequester() }

    Box(modifier = modifier) {
        BasicTextField(
            value = value,
            onValueChange = { input -> onValueChange(input.filter { it.isDigit() }.take(length)) },
            enabled = enabled,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
            cursorBrush = SolidColor(Color.Transparent),
            modifier = Modifier
                .focusRequester(focusRequester)
                .width(1.dp)
                .height(1.dp),
            decorationBox = { },
        )

        CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.semantics {
                    this.contentDescription = contentDescription
                },
            ) {
                repeat(length) { index ->
                    OtpCell(
                        character = value.getOrNull(index),
                        isFocused = index == value.length.coerceAtMost(length - 1) && enabled,
                        isError = isError,
                        onClick = { focusRequester.requestFocus() },
                    )
                }
            }
        }
    }
}

@Composable
private fun OtpCell(
    character: Char?,
    isFocused: Boolean,
    isError: Boolean,
    onClick: () -> Unit,
) {
    val borderColor = when {
        isError -> EduTheme.colors.danger
        isFocused -> EduTheme.colors.primary
        else -> EduTheme.colors.border
    }
    val shape = RoundedCornerShape(Radius.sm)

    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .width(Sizing.touchTarget)
            .height(Sizing.touchTarget + Spacing.xs)
            .background(EduTheme.colors.surface, shape)
            .border(
                width = if (isFocused || isError) Sizing.hairline * 2 else Sizing.hairline,
                color = borderColor,
                shape = shape,
            )
            .eduClickable(onClick = onClick),
    ) {
        Text(
            // Codes use the mono face — §4: "scores, timers, codes, IDs".
            text = character?.let { numeral(it.toString()) }.orEmpty(),
            style = EduTheme.typography.mono,
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Center,
        )
    }
}
