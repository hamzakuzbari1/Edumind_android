package com.rork.eduspark.ui.components.feedback

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.action.DestructiveButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.theme.EduTheme

/**
 * Confirmation dialog.
 *
 * Copy rule (§9): the confirm button repeats the *same verb* as the action that opened it,
 * so "Delete account" → "Delete account", never "OK". Users should never have to infer
 * what "Yes" refers to.
 */
@Composable
fun ConfirmDialog(
    title: String,
    body: String,
    confirmLabel: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    isDestructive: Boolean = false,
    dismissLabel: String = stringResource(R.string.common_cancel),
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = title,
                style = EduTheme.typography.title,
                color = EduTheme.colors.textPrimary,
            )
        },
        text = {
            Text(
                text = body,
                style = EduTheme.typography.body,
                color = EduTheme.colors.textSecondary,
            )
        },
        confirmButton = {
            if (isDestructive) {
                DestructiveButton(text = confirmLabel, onClick = onConfirm)
            } else {
                PrimaryButton(text = confirmLabel, onClick = onConfirm)
            }
        },
        dismissButton = {
            GhostButton(text = dismissLabel, onClick = onDismiss)
        },
        containerColor = EduTheme.colors.surface,
        titleContentColor = EduTheme.colors.textPrimary,
        textContentColor = EduTheme.colors.textSecondary,
        modifier = modifier,
    )
}
