package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ActiveSession
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

@Composable
fun ParentMeScreen(
    onOpenLinkStudent: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ParentMeViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { ParentMeSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        ParentMeContent(data = data, onOpenLinkStudent = onOpenLinkStudent)
    }
}

@Composable
private fun ParentMeContent(
    data: ParentMeData,
    onOpenLinkStudent: () -> Unit,
) {
    val colors = EduTheme.colors
    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
                ) {
                    ParentAvatar(initial = data.account.avatarInitial, modifier = Modifier.size(Sizing.avatarLg))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = data.account.displayName,
                            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                            color = colors.textPrimary,
                        )
                        Text(
                            text = stringResource(R.string.pr13_account_status_parent),
                            style = EduTheme.typography.caption,
                            color = colors.textSecondary,
                        )
                        Text(
                            text = data.account.email,
                            style = EduTheme.typography.caption,
                            color = colors.textTertiary,
                        )
                    }
                }
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pr13_account_security_section))
            EduCard {
                ListRow(
                    title = stringResource(R.string.pr13_password_title),
                    supporting = stringResource(R.string.pr13_password_supporting),
                    leading = Icons.Filled.Key,
                    leadingTint = colors.primary,
                    showChevron = true,
                )
                EduDivider()
                ListRow(
                    title = stringResource(R.string.pr13_verification_title),
                    supporting = stringResource(R.string.pr13_verification_supporting),
                    leading = Icons.Filled.VerifiedUser,
                    leadingTint = colors.accent,
                    trailingContent = {
                        StatusPill(
                            label = stringResource(if (data.twoFactorEnabled) R.string.st24_status_enabled else R.string.st24_status_disabled),
                            contentColor = if (data.twoFactorEnabled) colors.success else colors.textSecondary,
                            containerColor = if (data.twoFactorEnabled) colors.success.copy(alpha = 0.14f) else colors.neutralAlpha100,
                        )
                    },
                    showChevron = true,
                )
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pr13_devices_section))
            EduCard {
                data.sessions.forEachIndexed { index, session ->
                    ParentSessionRow(session = session)
                    if (index != data.sessions.lastIndex) EduDivider()
                }
            }
        }

        item {
            SectionHeader(title = stringResource(R.string.pr13_linked_students_section))
        }

        if (data.linkedStudents.isEmpty()) {
            item {
                EduCard(borderColor = colors.warning.copy(alpha = 0.36f)) {
                    Text(
                        text = stringResource(R.string.pr13_no_students_title),
                        style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                        color = colors.textPrimary,
                    )
                    Text(
                        text = stringResource(R.string.pr13_no_students_body),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                    )
                }
            }
        } else {
            items(data.linkedStudents, key = { it.id }) { student ->
                ParentLinkedStudentCard(student = student)
            }
        }

        item {
            SecondaryButton(
                text = stringResource(R.string.pr13_link_another_student),
                onClick = onOpenLinkStudent,
                leadingIcon = Icons.Filled.Link,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(Spacing.section))
        }
    }
}

@Composable
private fun ParentSessionRow(session: ActiveSession) {
    val colors = EduTheme.colors
    ListRow(
        title = session.deviceLabel,
        supporting = session.lastSeenLabel,
        leading = if (session.isCurrentDevice) Icons.Filled.PhoneAndroid else Icons.Filled.Computer,
        leadingTint = if (session.isCurrentDevice) colors.success else colors.primary,
        trailingContent = {
            if (session.isCurrentDevice) {
                StatusPill(
                    label = stringResource(R.string.st24_current_device),
                    contentColor = colors.success,
                    containerColor = colors.success.copy(alpha = 0.14f),
                )
            }
        },
        showChevron = !session.isCurrentDevice,
    )
}

@Composable
private fun ParentMeSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
        repeat(2) { SkeletonListItem() }
    }
}
