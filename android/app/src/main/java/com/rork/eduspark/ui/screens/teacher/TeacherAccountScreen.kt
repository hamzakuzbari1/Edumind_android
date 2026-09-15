package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * Teacher Account hub (حسابي) — identity snapshot plus grouped destinations.
 * RoleShell owns the chrome. Nested Profile / Voice / Teaching Page are pushed screens.
 */
@Composable
fun TeacherAccountScreen(
    onOpenProfile: () -> Unit,
    onOpenVoice: () -> Unit,
    onOpenTeachingPage: () -> Unit,
    onLogout: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherAccountViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showLogoutConfirm by rememberSaveable { mutableStateOf(false) }

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.retry()
    }

    if (showLogoutConfirm) {
        ConfirmDialog(
            title = stringResource(R.string.drawer_logout_confirm_title),
            body = stringResource(R.string.drawer_logout_confirm_body),
            confirmLabel = stringResource(R.string.drawer_logout),
            onConfirm = {
                showLogoutConfirm = false
                onLogout()
            },
            onDismiss = { showLogoutConfirm = false },
            isDestructive = true,
        )
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { TeacherAccountSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        TeacherAccountContent(
            data = data,
            onOpenProfile = onOpenProfile,
            onOpenVoice = onOpenVoice,
            onOpenTeachingPage = onOpenTeachingPage,
            onLogout = { showLogoutConfirm = true },
        )
    }
}

@Composable
private fun TeacherAccountContent(
    data: TeacherAccountScreenData,
    onOpenProfile: () -> Unit,
    onOpenVoice: () -> Unit,
    onOpenTeachingPage: () -> Unit,
    onLogout: () -> Unit,
) {
    val colors = EduTheme.colors
    val name = data.identity.displayName.ifBlank { stringResource(R.string.tc16_no_name) }
    val initial = data.identity.displayName.trim().firstOrNull()?.toString().orEmpty().ifBlank { "؟" }
    val subjectsLine = teacherSubjectsLine(data.subjectsGrades.subjectIds)

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(Sizing.avatarLg)
                            .background(colors.primaryContainer, CircleShape),
                    ) {
                        Text(
                            text = initial,
                            style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.primary,
                        )
                    }
                    Text(
                        text = name,
                        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textPrimary,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(top = Spacing.xs),
                    )
                    Text(
                        text = data.email,
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                    if (subjectsLine.isNotBlank()) {
                        Text(
                            text = subjectsLine,
                            style = EduTheme.typography.caption,
                            color = colors.textSecondary,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                    }
                }
            }
        }

        item {
            AccountHubGroup {
                AccountHubRow(
                    title = stringResource(R.string.tc16_row_profile),
                    onClick = onOpenProfile,
                )
                AccountHubDivider()
                AccountHubRow(
                    title = stringResource(R.string.tc16_row_voice),
                    onClick = onOpenVoice,
                )
                AccountHubDivider()
                AccountHubRow(
                    title = stringResource(R.string.tc16_row_phrases),
                    enabled = false,
                    soon = true,
                )
                AccountHubDivider()
                AccountHubRow(
                    title = stringResource(R.string.tc16_row_teaching),
                    soon = true,
                    onClick = onOpenTeachingPage,
                )
            }
        }

        item {
            AccountHubGroup(modifier = Modifier.padding(top = Spacing.sm)) {
                AccountHubRow(
                    title = stringResource(R.string.tc16_row_settings),
                    enabled = false,
                    soon = true,
                )
            }
        }

        item {
            Text(
                text = stringResource(R.string.drawer_logout),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.danger,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.section)
                    .eduClickable(onClickLabel = stringResource(R.string.drawer_logout), onClick = onLogout)
                    .padding(vertical = Spacing.sm),
            )
        }
    }
}

@Composable
private fun AccountHubGroup(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    EduCard(
        modifier = modifier,
        contentPadding = PaddingValues(horizontal = Spacing.card, vertical = Spacing.xxs),
    ) {
        content()
    }
}

@Composable
private fun AccountHubDivider() {
    HorizontalDivider(color = EduTheme.colors.border)
}

@Composable
private fun AccountHubRow(
    title: String,
    enabled: Boolean = true,
    soon: Boolean = false,
    onClick: (() -> Unit)? = null,
) {
    val colors = EduTheme.colors
    ListRow(
        title = title,
        showChevron = enabled && onClick != null && !soon,
        onClick = if (enabled) onClick else null,
        modifier = if (enabled) Modifier else Modifier.alpha(0.55f),
        trailingContent = if (soon) {
            {
                Text(
                    text = stringResource(R.string.tc_coming_soon_title),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
        } else {
            null
        },
    )
}

@Composable
private fun TeacherAccountSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        SkeletonCard()
    }
}
