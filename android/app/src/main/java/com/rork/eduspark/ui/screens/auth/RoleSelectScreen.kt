package com.rork.eduspark.ui.screens.auth

import androidx.activity.compose.BackHandler
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.outlined.AutoStories
import androidx.compose.material.icons.outlined.Groups
import androidx.compose.material.icons.outlined.Insights
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.foundation.mirrorInRtl
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.LocalReducedMotion
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * A-03 · Public Entry / Role Landing.
 *
 * Test-2SY's logged-out landing is a branded product promise before it is a form: EduMind,
 * intelligent learning, compact benefits, then a Student/Parent/Teacher fork. This mobile
 * version keeps that hierarchy while reusing Android's existing auth routes.
 */
private data class RoleChoice(
    val role: UserRole,
    val titleRes: Int,
    val lineRes: Int,
    val icon: ImageVector,
    val prominence: RoleProminence,
)

private enum class RoleProminence { Primary, Secondary }

private val RoleChoices = listOf(
    RoleChoice(
        role = UserRole.Student,
        titleRes = R.string.a03_role_student,
        lineRes = R.string.a03_role_student_line,
        icon = Icons.Outlined.AutoStories,
        prominence = RoleProminence.Primary,
    ),
    RoleChoice(
        role = UserRole.Parent,
        titleRes = R.string.a03_role_parent,
        lineRes = R.string.a03_role_parent_line,
        icon = Icons.Outlined.Person,
        prominence = RoleProminence.Secondary,
    ),
    RoleChoice(
        role = UserRole.Teacher,
        titleRes = R.string.a03_role_teacher,
        lineRes = R.string.a03_role_teacher_line,
        icon = Icons.Outlined.Groups,
        prominence = RoleProminence.Secondary,
    ),
)

private val BenefitLabels = listOf(
    R.string.a03_benefit_ai_tutor,
    R.string.a03_benefit_daily_plan,
    R.string.a03_benefit_progress,
)

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun RoleSelectScreen(
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
    onSelectRole: (UserRole) -> Unit,
    onLogin: () -> Unit,
    onBack: (() -> Unit)?,
    modifier: Modifier = Modifier,
) {
    val reducedMotion = LocalReducedMotion.current
    val scope = rememberCoroutineScope()
    var logoVisible by remember { mutableStateOf(false) }
    var copyVisible by remember { mutableStateOf(false) }
    var benefitsVisible by remember { mutableStateOf(false) }
    var rolesVisible by remember { mutableStateOf(false) }
    var selectedRole by remember { mutableStateOf<UserRole?>(null) }

    BackHandler(enabled = onBack != null) { onBack?.invoke() }

    LaunchedEffect(reducedMotion) {
        if (reducedMotion) {
            logoVisible = true
            copyVisible = true
            benefitsVisible = true
            rolesVisible = true
        } else {
            logoVisible = true
            delay(500)
            copyVisible = true
            delay(400)
            benefitsVisible = true
            delay(300)
            rolesVisible = true
        }
    }

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
        Column(
            verticalArrangement = Arrangement.spacedBy(Spacing.md),
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .verticalScroll(rememberScrollState()),
        ) {
            Spacer(modifier = Modifier.height(Spacing.xs))

            BrandWordmark(
                size = WordmarkSize.Compact,
                modifier = Modifier.publicEntryAnimated(
                    visible = logoVisible,
                    translate = 0.dp,
                    initialScale = 0.92f,
                ),
            )

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .fillMaxWidth()
                    .publicEntryAnimated(visible = copyVisible, translate = 14.dp),
            ) {
                Text(
                    text = stringResource(R.string.a03_entry_headline),
                    style = EduTheme.typography.display,
                    color = EduTheme.colors.textPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .semantics { heading() },
                )
                Text(
                    text = stringResource(R.string.a03_entry_subtitle),
                    style = EduTheme.typography.body,
                    color = EduTheme.colors.textSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
            }

            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs, Alignment.CenterHorizontally),
                verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.fillMaxWidth(),
            ) {
                BenefitLabels.forEachIndexed { index, labelRes ->
                    BenefitChip(
                        label = stringResource(labelRes),
                        modifier = Modifier.publicEntryAnimated(
                            visible = benefitsVisible,
                            delayMillis = index * 120,
                            translate = 8.dp,
                        ),
                    )
                }
            }

            RoleSelectionArea(
                choices = RoleChoices,
                selectedRole = selectedRole,
                onSelect = { role ->
                    if (selectedRole == null) {
                        selectedRole = role
                        scope.launch {
                            if (!reducedMotion) delay(180)
                            onSelectRole(role)
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs)
                    .publicEntryAnimated(visible = rolesVisible, translate = 16.dp),
            )

            Spacer(modifier = Modifier.height(Spacing.md))
        }
    }
}

@Composable
private fun RoleSelectionArea(
    choices: List<RoleChoice>,
    selectedRole: UserRole?,
    onSelect: (UserRole) -> Unit,
    modifier: Modifier = Modifier,
) {
    val primary = choices.first { it.prominence == RoleProminence.Primary }
    val secondary = choices.filter { it.prominence == RoleProminence.Secondary }

    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = modifier,
    ) {
        Text(
            text = stringResource(R.string.a03_role_section_title),
            style = EduTheme.typography.title,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.semantics { heading() },
        )

        PublicRoleCard(
            choice = primary,
            selected = selectedRole == primary.role,
            selectionLocked = selectedRole != null,
            onClick = { onSelect(primary.role) },
        )

        BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
            if (maxWidth >= SecondaryCardsTwoColumnMinWidth) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    secondary.forEach { choice ->
                        PublicRoleCard(
                            choice = choice,
                            selected = selectedRole == choice.role,
                            selectionLocked = selectedRole != null,
                            onClick = { onSelect(choice.role) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                    secondary.forEach { choice ->
                        PublicRoleCard(
                            choice = choice,
                            selected = selectedRole == choice.role,
                            selectionLocked = selectedRole != null,
                            onClick = { onSelect(choice.role) },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun PublicRoleCard(
    choice: RoleChoice,
    selected: Boolean,
    selectionLocked: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val reducedMotion = LocalReducedMotion.current
    val isPrimary = choice.prominence == RoleProminence.Primary
    val container by animateColorAsState(
        targetValue = if (selected) colors.primaryContainer else colors.surface,
        animationSpec = if (reducedMotion) snap() else tween(180, easing = FastOutSlowInEasing),
        label = "role-card-container",
    )
    val border by animateColorAsState(
        targetValue = when {
            selected -> colors.primary
            isPrimary -> colors.primary.copy(alpha = 0.36f)
            else -> colors.border
        },
        animationSpec = if (reducedMotion) snap() else tween(180, easing = FastOutSlowInEasing),
        label = "role-card-border",
    )
    val scale by animateFloatAsState(
        targetValue = if (selected && !reducedMotion) 0.985f else 1f,
        animationSpec = if (reducedMotion) snap() else tween(150, easing = FastOutSlowInEasing),
        label = "role-card-scale",
    )
    val iconContainer = if (isPrimary || selected) colors.primaryContainer else colors.aiAccentContainer
    val iconTint = if (isPrimary || selected) colors.primary else colors.aiAccent

    Surface(
        shape = RoundedCornerShape(Radius.md),
        color = container,
        border = BorderStroke(Sizing.hairline, border),
        modifier = modifier
            .fillMaxWidth()
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .clip(RoundedCornerShape(Radius.md))
            .eduClickable(
                enabled = !selectionLocked || selected,
                onClickLabel = stringResource(choice.titleRes),
                onClick = onClick,
            ),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier
                .fillMaxWidth()
                .defaultMinSize(minHeight = if (isPrimary) 104.dp else 96.dp)
                .padding(if (isPrimary) PaddingValues(Spacing.card) else PaddingValues(Spacing.md)),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(if (isPrimary) 52.dp else 44.dp)
                    .background(iconContainer, RoundedCornerShape(Radius.sm)),
            ) {
                Icon(
                    imageVector = choice.icon,
                    contentDescription = null,
                    tint = iconTint,
                    modifier = Modifier.size(if (isPrimary) Sizing.iconLg else Sizing.icon),
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(choice.titleRes),
                    style = if (isPrimary) EduTheme.typography.titleLg else EduTheme.typography.bodyLg,
                    color = colors.textPrimary,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = stringResource(choice.lineRes),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    maxLines = if (isPrimary) 2 else 3,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }

            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                contentDescription = null,
                tint = if (selected) colors.primary else colors.textTertiary,
                modifier = Modifier
                    .size(Sizing.icon)
                    .mirrorInRtl(),
            )
        }
    }
}

@Composable
private fun BenefitChip(
    label: String,
    modifier: Modifier = Modifier,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier
            .background(EduTheme.colors.aiAccentContainer, RoundedCornerShape(Radius.pill))
            .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
    ) {
        Icon(
            imageVector = Icons.Outlined.Insights,
            contentDescription = null,
            tint = EduTheme.colors.aiAccent,
            modifier = Modifier.size(Sizing.iconSm),
        )
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textPrimary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun Modifier.publicEntryAnimated(
    visible: Boolean,
    delayMillis: Int = 0,
    translate: Dp = 12.dp,
    initialScale: Float = 1f,
): Modifier {
    val reducedMotion = LocalReducedMotion.current
    val density = LocalDensity.current
    val alpha by animateFloatAsState(
        targetValue = if (visible || reducedMotion) 1f else 0f,
        animationSpec = if (reducedMotion) snap() else tween(
            durationMillis = 420,
            delayMillis = delayMillis,
            easing = LinearOutSlowInEasing,
        ),
        label = "public-entry-alpha",
    )
    val translatePx = with(density) { translate.toPx() }
    val offset by animateFloatAsState(
        targetValue = if (visible || reducedMotion) 0f else translatePx,
        animationSpec = if (reducedMotion) snap() else tween(
            durationMillis = 420,
            delayMillis = delayMillis,
            easing = FastOutSlowInEasing,
        ),
        label = "public-entry-offset",
    )
    val scale by animateFloatAsState(
        targetValue = if (visible || reducedMotion) 1f else initialScale,
        animationSpec = if (reducedMotion) snap() else tween(
            durationMillis = 500,
            delayMillis = delayMillis,
            easing = FastOutSlowInEasing,
        ),
        label = "public-entry-scale",
    )

    return graphicsLayer {
        this.alpha = alpha
        translationY = offset
        scaleX = scale
        scaleY = scale
    }
}

private val SecondaryCardsTwoColumnMinWidth = 340.dp
