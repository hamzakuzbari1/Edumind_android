package com.rork.eduspark.ui.screens.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.foundation.mirrorInRtl
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-03 · Role Select
 * ══════════════════════════════════════════════════════════════════════════
 *
 * "A fork, not a form." Three cards, one line of explanation each, and nothing else on the
 * screen except the back affordance, the login cross-link, and the language toggle. No
 * radio buttons, no confirm button, no "continue" — tapping a card *is* the decision, so
 * adding a second step would only slow down the one choice this screen exists to make.
 *
 * Each card carries a monogram tile (ط / م / و in Arabic, S / T / P in English) rather than
 * an icon: three role icons would be arbitrary pictograms, whereas the first letter of the
 * word is unambiguous in both scripts and costs nothing to render.
 *
 * The chevron is the only directional glyph here and it mirrors automatically.
 */
private data class RoleChoice(
    val role: UserRole,
    val monogramRes: Int,
    val titleRes: Int,
    val lineRes: Int,
)

private val RoleChoices = listOf(
    RoleChoice(
        role = UserRole.Student,
        monogramRes = R.string.a03_role_student_monogram,
        titleRes = R.string.a03_role_student,
        lineRes = R.string.a03_role_student_line,
    ),
    RoleChoice(
        role = UserRole.Teacher,
        monogramRes = R.string.a03_role_teacher_monogram,
        titleRes = R.string.a03_role_teacher,
        lineRes = R.string.a03_role_teacher_line,
    ),
    RoleChoice(
        role = UserRole.Parent,
        monogramRes = R.string.a03_role_parent_monogram,
        titleRes = R.string.a03_role_parent,
        lineRes = R.string.a03_role_parent_line,
    ),
)

@Composable
fun RoleSelectScreen(
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
    onSelectRole: (UserRole) -> Unit,
    onLogin: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    AuthScaffold(
        modifier = modifier,
        onBack = onBack,
        bottomBlock = {
            AuthFooterPrompt(
                question = stringResource(R.string.a03_have_account),
                actionLabel = stringResource(R.string.a03_login_action),
                onAction = onLogin,
            )
            AuthLanguageToggle(
                current = locale,
                onSelect = onSelectLocale,
                modifier = Modifier.padding(top = Spacing.sm),
            )
        },
    ) {
        Box(modifier = Modifier.weight(0.6f))

        Text(
            text = stringResource(R.string.a03_title),
            style = EduTheme.typography.display,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.fillMaxWidth(),
        )
        Text(
            text = stringResource(R.string.a03_body),
            style = EduTheme.typography.body,
            color = EduTheme.colors.textMuted,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        )

        Column(
            verticalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.section),
        ) {
            RoleChoices.forEach { choice ->
                RoleCard(
                    monogram = stringResource(choice.monogramRes),
                    title = stringResource(choice.titleRes),
                    line = stringResource(choice.lineRes),
                    onClick = { onSelectRole(choice.role) },
                )
            }
        }

        Box(modifier = Modifier.weight(1f))
    }
}

@Composable
private fun RoleCard(
    monogram: String,
    title: String,
    line: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val shape = RoundedCornerShape(Radius.md)
    val colors = EduTheme.colors

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier
            .fillMaxWidth()
            .background(colors.surface, shape)
            .border(Sizing.hairline, colors.border, shape)
            // The whole card is the target — comfortably past the 48dp floor.
            .eduClickable(onClickLabel = title, onClick = onClick)
            .padding(Spacing.card),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(MonogramTileSize)
                .background(colors.zaytounSoft, RoundedCornerShape(Radius.sm)),
        ) {
            Text(
                text = monogram,
                style = EduTheme.typography.title,
                color = colors.zaytoun,
            )
        }

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = EduTheme.typography.bodyLg.copy(
                    fontWeight = androidx.compose.ui.text.font.FontWeight.SemiBold
                ),
                color = colors.textPrimary,
            )
            Text(
                text = line,
                style = EduTheme.typography.caption,
                color = colors.textMuted,
            )
        }

        Icon(
            imageVector = Icons.AutoMirrored.Filled.ArrowForward,
            contentDescription = null,
            tint = colors.textMuted,
            modifier = Modifier
                .size(Sizing.icon)
                .mirrorInRtl(),
        )
    }
}

private val MonogramTileSize = 40.dp
