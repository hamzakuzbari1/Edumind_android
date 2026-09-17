package com.rork.eduspark.ui.screens.auth

import androidx.activity.compose.BackHandler
import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing

/**
 * Role-specific auth hub: Login, Register, or change account type.
 *
 * The role is already chosen. Registration is never asked to pick it again.
 */
@Composable
fun RoleAuthScreen(
    role: UserRole,
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
    onLogin: () -> Unit,
    onRegister: () -> Unit,
    onChangeAccountType: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val copy = roleAuthCopy(role)

    BackHandler { onChangeAccountType() }

    AuthScaffold(
        modifier = modifier,
        onBack = onChangeAccountType,
        bottomBlock = {
            AuthLanguageToggle(
                current = locale,
                onSelect = onSelectLocale,
                note = stringResource(R.string.a04_language_restart_note),
            )
        },
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .verticalScroll(rememberScrollState()),
        ) {
            Spacer(modifier = Modifier.height(Spacing.section))

            BrandLogo(height = 64.dp)

            Text(
                text = stringResource(copy.titleRes),
                style = EduTheme.typography.titleLg,
                color = EduTheme.colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md)
                    .semantics { heading() },
            )
            Text(
                text = stringResource(copy.bodyRes),
                style = EduTheme.typography.body,
                color = EduTheme.colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(modifier = Modifier.height(Spacing.lg))

            PrimaryButton(
                text = stringResource(R.string.a04_submit),
                onClick = onLogin,
                modifier = Modifier.fillMaxWidth(),
            )
            SecondaryButton(
                text = stringResource(R.string.a04_create_account),
                onClick = onRegister,
                modifier = Modifier.fillMaxWidth(),
            )
            GhostButton(
                text = stringResource(R.string.a03_change_account_type),
                onClick = onChangeAccountType,
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(modifier = Modifier.height(Spacing.section))
        }
    }
}

private data class RoleAuthCopy(
    @param:StringRes val titleRes: Int,
    @param:StringRes val bodyRes: Int,
)

private fun roleAuthCopy(role: UserRole): RoleAuthCopy = when (role) {
    UserRole.Student -> RoleAuthCopy(R.string.a04_auth_title_student, R.string.a04_auth_body_student)
    UserRole.Teacher -> RoleAuthCopy(R.string.a04_auth_title_teacher, R.string.a04_auth_body_teacher)
    UserRole.Parent -> RoleAuthCopy(R.string.a04_auth_title_parent, R.string.a04_auth_body_parent)
}
