package com.rork.eduspark.ui.components.input

import androidx.annotation.StringRes
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.wrapContentSize
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.error
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Motion
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import com.rork.eduspark.ui.theme.reducedMotionAware

/**
 * Inputs — Design System §7.
 *
 * RTL-aware by construction: Compose resolves text alignment from the layout direction,
 * and mixed-direction content ("درس Python الأول") shapes correctly because we never
 * force an alignment. Errors are exposed to TalkBack via `semantics { error(...) }`
 * rather than colour alone.
 */

/**
 * Where a field's label sits.
 *
 * [Floating] is the Material default and stays the app-wide default.
 * [Above] is what the authentication flow uses — a static caption above the box — because
 * A-04…A-11 share one form shell in which every field is the same height and every failure
 * speaks in a single error region below the fields, not in a floating notch.
 */
enum class FieldLabelPlacement { Floating, Above }

@Composable
fun EduTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
    errorText: String? = null,
    supportingText: String? = null,
    enabled: Boolean = true,
    singleLine: Boolean = true,
    leadingIcon: ImageVector? = null,
    keyboardType: KeyboardType = KeyboardType.Text,
    imeAction: ImeAction = ImeAction.Next,
    labelPlacement: FieldLabelPlacement = FieldLabelPlacement.Floating,
    /**
     * When false the field still turns red and still announces its error to TalkBack, but
     * the message itself is rendered elsewhere — the auth flow's single error region.
     */
    showErrorText: Boolean = true,
) {
    val isError = errorText != null

    Column(modifier = modifier.fillMaxWidth()) {
        if (labelPlacement == FieldLabelPlacement.Above && label.isNotBlank()) {
            Text(
                text = label,
                style = EduTheme.typography.caption,
                color = if (isError) EduTheme.colors.danger else EduTheme.colors.textSecondary,
                modifier = Modifier.padding(bottom = Spacing.xxs),
            )
        }

        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            enabled = enabled,
            singleLine = singleLine,
            isError = isError,
            label = if (labelPlacement == FieldLabelPlacement.Floating && label.isNotBlank()) {
                { Text(text = label, style = EduTheme.typography.caption) }
            } else {
                null
            },
            placeholder = placeholder?.let { { Text(text = it, style = EduTheme.typography.body) } },
            leadingIcon = leadingIcon?.let {
                { Icon(imageVector = it, contentDescription = null, tint = EduTheme.colors.textSecondary) }
            },
            textStyle = EduTheme.typography.body,
            shape = RoundedCornerShape(Radius.sm),
            keyboardOptions = KeyboardOptions(keyboardType = keyboardType, imeAction = imeAction),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = EduTheme.colors.primary,
                unfocusedBorderColor = EduTheme.colors.border,
                errorBorderColor = EduTheme.colors.danger,
                focusedTextColor = EduTheme.colors.textPrimary,
                unfocusedTextColor = EduTheme.colors.textPrimary,
                cursorColor = EduTheme.colors.primary,
                focusedLabelColor = EduTheme.colors.primary,
                unfocusedLabelColor = EduTheme.colors.textSecondary,
                focusedContainerColor = EduTheme.colors.surface,
                unfocusedContainerColor = EduTheme.colors.surface,
            ),
            modifier = Modifier
                .fillMaxWidth()
                .defaultMinSize(minHeight = Sizing.touchTarget)
                .semantics { if (isError && errorText != null) error(errorText) },
        )

        // ONE error region per field, announced politely rather than only coloured red.
        val helper = (if (showErrorText) errorText else null) ?: supportingText
        if (helper != null) {
            Text(
                text = helper,
                style = EduTheme.typography.caption,
                color = if (isError) EduTheme.colors.danger else EduTheme.colors.textSecondary,
                modifier = Modifier
                    .padding(top = Spacing.xxs, start = Spacing.xs, end = Spacing.xs)
                    .semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
    }
}

@Composable
fun PasswordField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
    errorText: String? = null,
    supportingText: String? = null,
    imeAction: ImeAction = ImeAction.Done,
    labelPlacement: FieldLabelPlacement = FieldLabelPlacement.Floating,
    showErrorText: Boolean = true,
    /**
     * Auth screens spell the toggle out («إظهار» / "Show") instead of using an eye glyph:
     * it is unambiguous for the low-tech-confidence parent audience, and it reads at a
     * glance in both scripts.
     */
    revealAsText: Boolean = false,
    onImeAction: (() -> Unit)? = null,
) {
    var revealed by rememberSaveable { mutableStateOf(false) }
    val isError = errorText != null
    val toggleLabel = stringResource(
        if (revealed) R.string.a11y_password_hide else R.string.a11y_password_show
    )

    Column(modifier = modifier.fillMaxWidth()) {
        if (labelPlacement == FieldLabelPlacement.Above) {
            Text(
                text = label,
                style = EduTheme.typography.caption,
                color = if (isError) EduTheme.colors.danger else EduTheme.colors.textSecondary,
                modifier = Modifier.padding(bottom = Spacing.xxs),
            )
        }

        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            singleLine = true,
            isError = isError,
            label = if (labelPlacement == FieldLabelPlacement.Floating) {
                { Text(text = label, style = EduTheme.typography.caption) }
            } else {
                null
            },
            placeholder = placeholder?.let { { Text(text = it, style = EduTheme.typography.body) } },
            textStyle = EduTheme.typography.body,
            shape = RoundedCornerShape(Radius.sm),
            visualTransformation = if (revealed) {
                VisualTransformation.None
            } else {
                PasswordVisualTransformation()
            },
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Password,
                imeAction = imeAction,
            ),
            keyboardActions = KeyboardActions(onDone = { onImeAction?.invoke() }),
            trailingIcon = {
                if (revealAsText) {
                    Text(
                        text = stringResource(if (revealed) R.string.a04_conceal else R.string.a04_reveal),
                        style = EduTheme.typography.caption,
                        color = EduTheme.colors.primary,
                        modifier = Modifier
                            .padding(end = Spacing.sm)
                            // eduClickable keeps the 48dp target even though the glyph is small.
                            .eduClickable(onClickLabel = toggleLabel) { revealed = !revealed }
                            .wrapContentSize(),
                    )
                } else {
                    EduIconButton(
                        icon = if (revealed) Icons.Filled.VisibilityOff else Icons.Filled.Visibility,
                        contentDescription = toggleLabel,
                        tint = EduTheme.colors.textSecondary,
                        onClick = { revealed = !revealed },
                    )
                }
            },
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = EduTheme.colors.primary,
                unfocusedBorderColor = EduTheme.colors.border,
                errorBorderColor = EduTheme.colors.danger,
                focusedTextColor = EduTheme.colors.textPrimary,
                unfocusedTextColor = EduTheme.colors.textPrimary,
                cursorColor = EduTheme.colors.primary,
                focusedLabelColor = EduTheme.colors.primary,
                unfocusedLabelColor = EduTheme.colors.textSecondary,
                focusedContainerColor = EduTheme.colors.surface,
                unfocusedContainerColor = EduTheme.colors.surface,
            ),
            modifier = Modifier
                .fillMaxWidth()
                .defaultMinSize(minHeight = Sizing.touchTarget)
                .semantics { if (isError && errorText != null) error(errorText) },
        )

        val helper = (if (showErrorText) errorText else null) ?: supportingText
        if (helper != null) {
            Text(
                text = helper,
                style = EduTheme.typography.caption,
                color = if (isError) EduTheme.colors.danger else EduTheme.colors.textSecondary,
                modifier = Modifier
                    .padding(top = Spacing.xxs, start = Spacing.xs, end = Spacing.xs)
                    .semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
    }
}

@Composable
fun SearchField(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String = stringResource(R.string.common_search_hint),
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        singleLine = true,
        placeholder = { Text(text = placeholder, style = EduTheme.typography.body) },
        textStyle = EduTheme.typography.body,
        shape = RoundedCornerShape(Radius.pill),
        leadingIcon = {
            // Not mirrored: a magnifier is not a directional glyph.
            Icon(
                imageVector = Icons.Filled.Search,
                contentDescription = null,
                tint = EduTheme.colors.textSecondary,
            )
        },
        trailingIcon = {
            if (value.isNotEmpty()) {
                EduIconButton(
                    icon = Icons.Filled.Close,
                    contentDescription = stringResource(R.string.common_clear),
                    tint = EduTheme.colors.textSecondary,
                    onClick = { onValueChange("") },
                )
            }
        },
        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = EduTheme.colors.primary,
            unfocusedBorderColor = EduTheme.colors.border,
            focusedTextColor = EduTheme.colors.textPrimary,
            unfocusedTextColor = EduTheme.colors.textPrimary,
            cursorColor = EduTheme.colors.primary,
            focusedContainerColor = EduTheme.colors.surface,
            unfocusedContainerColor = EduTheme.colors.surface,
        ),
        modifier = modifier
            .fillMaxWidth()
            .defaultMinSize(minHeight = Sizing.touchTarget),
    )
}

/** Password strength, used by A-05/A-06/A-07 register and A-11 reset. */
enum class PasswordStrength { Weak, Fair, Strong }

/** The only length the client enforces. The server stays the authority on password policy. */
const val PASSWORD_MIN_LENGTH = 8

/**
 * Pure, testable strength heuristic kept out of the composable so it can be unit-tested
 * and reused by form validation without a composition.
 */
fun passwordStrengthOf(password: String): PasswordStrength {
    val classes = listOf(
        password.any { it.isLowerCase() },
        password.any { it.isUpperCase() },
        password.any { it.isDigit() },
        password.any { !it.isLetterOrDigit() },
    ).count { it }

    return when {
        password.length >= 12 && classes >= 3 -> PasswordStrength.Strong
        password.length >= PASSWORD_MIN_LENGTH && classes >= 2 -> PasswordStrength.Fair
        else -> PasswordStrength.Weak
    }
}

/**
 * The single next thing that would strengthen [password], or null once there is nothing
 * left worth suggesting.
 *
 * Checked in a fixed priority — digit, then uppercase, then symbol, then length — so the
 * meter always names *one* concrete, achievable change rather than restating the whole
 * policy at once. This mirrors the approved copy ("Strong — add a number to make it very
 * strong"): a specific next step, not a rescored grade.
 */
@StringRes
fun passwordGuidanceOf(password: String): Int? {
    if (password.isEmpty()) return null
    val hasDigit = password.any { it.isDigit() }
    val hasUpper = password.any { it.isUpperCase() }
    val hasSymbol = password.any { !it.isLetterOrDigit() }

    return when {
        !hasDigit -> R.string.reg_strength_hint_add_number
        !hasUpper -> R.string.reg_strength_hint_add_uppercase
        !hasSymbol -> R.string.reg_strength_hint_add_symbol
        password.length < 12 -> R.string.reg_strength_hint_add_length
        else -> null
    }
}

/**
 * Password strength meter — three segments, a word, and one actionable next step.
 *
 * Guidance, not a gate: the form only requires the minimum length, because refusing a
 * password the server would happily accept means inventing policy on the client. The meter
 * reports how strong the typed password actually is, in words as well as colour, so the
 * meaning survives colour-blindness and a bright bus window — and it *names* the single
 * thing that would improve it next, via [passwordGuidanceOf], rather than only scoring what
 * was typed.
 *
 * The block keeps its height whether or not anything has been typed, so nothing below it
 * shifts while the user types.
 */
@Composable
fun PasswordStrengthMeter(
    password: String,
    modifier: Modifier = Modifier,
) {
    val strength = passwordStrengthOf(password)
    val hasInput = password.isNotEmpty()
    val filledSegments = if (hasInput) strength.ordinal + 1 else 0
    val guidanceRes = passwordGuidanceOf(password)

    val accent = when {
        !hasInput -> EduTheme.colors.border
        strength == PasswordStrength.Weak -> EduTheme.colors.danger
        strength == PasswordStrength.Fair -> EduTheme.colors.warning
        else -> EduTheme.colors.success
    }
    val label = stringResource(
        when (strength) {
            PasswordStrength.Weak -> R.string.reg_strength_weak
            PasswordStrength.Fair -> R.string.reg_strength_fair
            PasswordStrength.Strong -> R.string.reg_strength_strong
        }
    )
    val guidance = guidanceRes?.let { stringResource(it) }
    val readout = stringResource(R.string.a11y_password_strength, label) +
        (guidance?.let { ". $it" } ?: "")

    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(top = Spacing.xxs)
            // One merged node: TalkBack says "Password strength: fair. Add a number to
            // make it stronger" — the guidance, not just three unlabeled bars.
            .clearAndSetSemantics { if (hasInput) contentDescription = readout },
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier.weight(1f),
            ) {
                repeat(StrengthSegments) { index ->
                    val segmentColor by animateColorAsState(
                        targetValue = if (index < filledSegments) accent else EduTheme.colors.neutralAlpha100,
                        animationSpec = reducedMotionAware(tween(Motion.QUICK_MS)),
                        label = "strengthSegment",
                    )
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(StrengthBarHeight)
                            .background(segmentColor, RoundedCornerShape(Radius.pill)),
                    )
                }
            }
            Text(
                text = if (hasInput) label else "",
                style = EduTheme.typography.caption,
                color = if (hasInput) accent else EduTheme.colors.textSecondary,
            )
        }
        if (guidance != null) {
            Text(
                text = guidance,
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

private const val StrengthSegments = 3
private val StrengthBarHeight = 4.dp
