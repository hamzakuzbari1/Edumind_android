package com.rork.eduspark.ui.components.nav

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.foundation.mirrorInRtl
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing

/**
 * TopBar — title, leading back, and up to two trailing actions (Design System §5b).
 *
 * **The back affordance is always visible.** Android's hardware/gesture back is handled
 * separately in [com.rork.eduspark.ui.components.scaffold.EduScaffold], but it is never
 * the only way back, because iOS has no hardware back button and the same screens ship
 * there later.
 *
 * The back arrow uses the auto-mirrored icon *and* [mirrorInRtl] is unnecessary for it —
 * `Icons.AutoMirrored` already flips. Non-auto-mirrored directional glyphs must use the
 * modifier explicitly.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EduTopBar(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    onBack: (() -> Unit)? = null,
    showBrandMark: Boolean = false,
    navigationIcon: (@Composable () -> Unit)? = null,
    actions: @Composable RowScope.() -> Unit = {},
) {
    CenterAlignedTopAppBar(
        title = {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    if (showBrandMark) {
                        TopBarBrandMark()
                    }
                    Text(
                        text = title,
                        style = EduTheme.typography.title,
                        color = EduTheme.colors.textPrimary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                if (!subtitle.isNullOrBlank()) {
                    Text(
                        text = subtitle,
                        style = EduTheme.typography.caption,
                        color = EduTheme.colors.textSecondary,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        },
        navigationIcon = {
            if (navigationIcon != null) {
                navigationIcon()
            } else if (onBack != null) {
                EduIconButton(
                    icon = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = stringResource(R.string.a11y_back),
                    onClick = onBack,
                )
            }
        },
        actions = actions,
        colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
            containerColor = EduTheme.colors.background,
            titleContentColor = EduTheme.colors.textPrimary,
            navigationIconContentColor = EduTheme.colors.textPrimary,
            actionIconContentColor = EduTheme.colors.textPrimary,
        ),
        modifier = modifier,
    )
}

@Composable
private fun TopBarBrandMark(modifier: Modifier = Modifier) {
    val shape = RoundedCornerShape(Radius.sm)

    Image(
        painter = painterResource(R.drawable.ic_launcher_foreground),
        contentDescription = null,
        contentScale = ContentScale.Fit,
        modifier = modifier
            .size(Sizing.avatarSm)
            .clip(shape),
    )
}

/**
 * TopBar action carrying an unread count.
 *
 * Messages and Notifications live here on every root screen rather than costing a tab
 * (Screen Inventory · Navigation shells). The badge count is announced as part of the
 * action's label so TalkBack users hear "Messages, 3 unread" rather than just "Messages".
 */
@Composable
fun BadgedTopBarAction(
    icon: ImageVector,
    contentDescription: String,
    count: Int,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(modifier = modifier) {
        EduIconButton(
            icon = icon,
            contentDescription = contentDescription,
            onClick = onClick,
        )
        if (count > 0) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .offset(x = (-6).dp, y = 6.dp)
                    .size(Sizing.iconSm)
                    .background(EduTheme.colors.danger, RoundedCornerShape(Radius.pill)),
            ) {
                Text(
                    text = numeral(if (count > 9) 9 else count),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.surface,
                )
            }
        }
    }
}

/** Grab handle for bottom sheets — Design System §5: "bottom-sheet first". */
@Composable
fun SheetHandle(modifier: Modifier = Modifier) {
    Row(
        horizontalArrangement = androidx.compose.foundation.layout.Arrangement.Center,
        modifier = modifier.then(Modifier),
    ) {
        Box(
            modifier = Modifier
                .size(width = 36.dp, height = 4.dp)
                .background(EduTheme.colors.border, RoundedCornerShape(Radius.pill))
        )
    }
}
