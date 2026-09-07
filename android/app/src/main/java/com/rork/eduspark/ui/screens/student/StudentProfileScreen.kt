package com.rork.eduspark.ui.screens.student

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.PersonRemove
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Subscriptions
import androidx.compose.material.icons.filled.SupervisorAccount
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.ExplanationLength
import com.rork.eduspark.data.model.LearningGoal
import com.rork.eduspark.data.model.LearningInterest
import com.rork.eduspark.data.model.LinkedParent
import com.rork.eduspark.data.model.SubjectProgress
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.feedback.ConfirmDialog
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.progress.LevelBar
import com.rork.eduspark.ui.components.progress.StreakFlame
import com.rork.eduspark.ui.components.progress.XpChip
import com.rork.eduspark.ui.components.state.MessageState
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.components.surface.SkeletonListItem
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import androidx.compose.ui.window.Dialog
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-22 · Student Profile — the STUDENT_ME tab root.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The primary identity surface for the account area — replaces the old minimal
 * StudentAccountScreen stub. No [com.rork.eduspark.ui.components.scaffold.EduScaffold]: this
 * is a tab root, so RoleShell's own top/bottom chrome already wraps it, same convention
 * [StudentHomeScreen] uses. Settings/Security/Achievements/Subscriptions are reached from the
 * links section at the bottom — one hub, never a second one.
 */
@Composable
fun StudentProfileScreen(
    onOpenAchievements: () -> Unit,
    onOpenSubscriptions: () -> Unit,
    onOpenAccountSettings: () -> Unit,
    onOpenSecuritySettings: () -> Unit,
    onOpenLanguageDisplay: () -> Unit,
    onOpenNotifications: () -> Unit,
    onOpenLearningPreferences: () -> Unit,
    onOpenParentLinking: () -> Unit,
    onLogout: () -> Unit,
    localeLabel: String,
    appearanceLabel: String,
    modifier: Modifier = Modifier,
    viewModel: StudentProfileViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var showLogoutConfirm by remember { mutableStateOf(false) }

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
        loading = { ProfileSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        ProfileContent(
            data = data,
            onEdit = viewModel::openEditSheet,
            onRevokeParent = viewModel::requestRevokeParent,
            onOpenAchievements = onOpenAchievements,
            onOpenSubscriptions = onOpenSubscriptions,
            onOpenAccountSettings = onOpenAccountSettings,
            onOpenSecuritySettings = onOpenSecuritySettings,
            onOpenLanguageDisplay = onOpenLanguageDisplay,
            onOpenNotifications = onOpenNotifications,
            onOpenLearningPreferences = onOpenLearningPreferences,
            onOpenParentLinking = onOpenParentLinking,
            onLogout = { showLogoutConfirm = true },
            localeLabel = localeLabel,
            appearanceLabel = appearanceLabel,
        )
    }

    if (state.showEditSheet) {
        val data = (state.result as? UiState.Content)?.data
        if (data != null) {
            ProfileEditSheet(
                displayName = data.profile.displayName,
                grade = data.profile.grade,
                school = data.profile.school,
                isSaving = state.isSavingEdit,
                onDismiss = viewModel::dismissEditSheet,
                onSave = viewModel::saveProfile,
            )
        }
    }

    val pendingParentId = state.pendingRevokeParentId
    if (pendingParentId != null) {
        val parentName = (state.result as? UiState.Content)?.data?.linkedParents
            ?.firstOrNull { it.id == pendingParentId }?.name.orEmpty()
        ConfirmDialog(
            title = stringResource(R.string.st22_revoke_parent_title),
            body = stringResource(R.string.st22_revoke_parent_body, parentName),
            confirmLabel = stringResource(R.string.st22_revoke_confirm),
            onConfirm = viewModel::confirmRevokeParent,
            onDismiss = viewModel::cancelRevokeParent,
            isDestructive = true,
        )
    }
}

@Composable
private fun ProfileContent(
    data: ProfileScreenData,
    onEdit: () -> Unit,
    onRevokeParent: (String) -> Unit,
    onOpenAchievements: () -> Unit,
    onOpenSubscriptions: () -> Unit,
    onOpenAccountSettings: () -> Unit,
    onOpenSecuritySettings: () -> Unit,
    onOpenLanguageDisplay: () -> Unit,
    onOpenNotifications: () -> Unit,
    onOpenLearningPreferences: () -> Unit,
    onOpenParentLinking: () -> Unit,
    onLogout: () -> Unit,
    localeLabel: String,
    appearanceLabel: String,
) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        verticalArrangement = Arrangement.spacedBy(Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            EduCard(onClick = onEdit) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                    Box(
                        contentAlignment = Alignment.Center,
                        modifier = Modifier
                            .size(Sizing.avatarLg)
                            .background(colors.primaryContainer, CircleShape),
                    ) {
                        Text(data.profile.avatarInitial, style = EduTheme.typography.titleLg, color = colors.primary)
                    }
                    Text(
                        data.profile.displayName,
                        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                        color = colors.textPrimary,
                        modifier = Modifier.padding(top = Spacing.sm),
                    )
                    Text(
                        text = gradeLabel(data.profile.grade),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.xxs),
                    )
                }
            }
        }
        item {
            EduCard(contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xxs)) {
                AccountHubRow(Icons.Filled.AutoAwesome, stringResource(R.string.st_lp_title), onClick = onOpenLearningPreferences)
                AccountHubRow(Icons.Filled.EmojiEvents, stringResource(R.string.st15_title), onClick = onOpenAchievements)
                AccountHubRow(Icons.Filled.Subscriptions, stringResource(R.string.st16_title), onClick = onOpenSubscriptions)
            }
        }
        item {
            EduCard(contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xxs)) {
                AccountHubRow(Icons.Filled.Language, stringResource(R.string.st22_row_language), status = localeLabel, onClick = onOpenLanguageDisplay)
                AccountHubRow(Icons.Filled.Settings, stringResource(R.string.st22_row_appearance), status = appearanceLabel, onClick = onOpenLanguageDisplay)
                AccountHubRow(Icons.Filled.Notifications, stringResource(R.string.st26_title), onClick = onOpenNotifications)
            }
        }
        item {
            EduCard(contentPadding = PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xxs)) {
                AccountHubRow(
                    Icons.Filled.SupervisorAccount,
                    stringResource(R.string.st_parent_link_title),
                    status = if (data.linkedParents.isEmpty()) stringResource(R.string.st22_parent_unlinked) else stringResource(R.string.st22_parent_linked),
                    onClick = onOpenParentLinking,
                )
                AccountHubRow(Icons.Filled.Security, stringResource(R.string.st24_title), onClick = onOpenSecuritySettings)
            }
        }
        item {
            TextButton(
                onClick = onLogout,
                colors = ButtonDefaults.textButtonColors(contentColor = colors.danger),
                modifier = Modifier.fillMaxWidth().defaultMinSize(minHeight = Sizing.touchTarget),
            ) {
                Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null, modifier = Modifier.size(Sizing.icon))
                Text(
                    text = stringResource(R.string.drawer_logout),
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(start = Spacing.xs),
                )
            }
        }
    }
}

@Composable
private fun AccountHubRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    onClick: () -> Unit,
    status: String? = null,
) {
    ListRow(
        title = title,
        supporting = status,
        leading = icon,
        showChevron = true,
        onClick = onClick,
    )
}

@Composable
private fun IdentityCard(data: ProfileScreenData, onEdit: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(data.profile.avatarInitial, style = EduTheme.typography.display, color = colors.primary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(data.profile.displayName, style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold), color = colors.textPrimary)
                if (data.email.isNotBlank()) {
                    Text(data.email, style = EduTheme.typography.caption, color = colors.textSecondary, modifier = Modifier.padding(top = Spacing.xxs))
                }
                Text(
                    text = stringResource(R.string.st22_grade_school_format, gradeLabel(data.profile.grade), data.profile.school),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
        }
        SecondaryButton(
            text = stringResource(R.string.st22_edit_profile),
            onClick = onEdit,
            leadingIcon = Icons.Filled.Edit,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.md),
        )
    }
}

@Composable
private fun LearningProfileCard(data: ProfileScreenData, onOpenLearningPreferences: () -> Unit) {
    EduCard {
        LevelBar(level = data.gamification.level, progressToNextLevel = data.gamification.progressToNextLevel)
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
            modifier = Modifier.padding(top = Spacing.sm),
        ) {
            XpChip(xp = data.gamification.xp)
            StreakFlame(days = data.gamification.streakDays)
        }
        ListRow(
            title = stringResource(R.string.st_lp_title),
            supporting = preferencesSummary(data.learningPreferences.goal, data.learningPreferences.explanationLength, data.learningPreferences.interests),
            leading = Icons.Filled.AutoAwesome,
            showChevron = true,
            onClick = onOpenLearningPreferences,
            modifier = Modifier.padding(top = Spacing.sm),
        )
        if (data.subjects.isNotEmpty()) {
            SectionHeader(title = stringResource(R.string.st22_quick_stats_section))
            data.subjects.take(3).forEach { subject -> SubjectQuickStatRow(subject) }
        }
    }
}

@Composable
private fun RelationshipsCard(
    linkedParents: List<LinkedParent>,
    parentLinkCode: String,
    onOpenParentLinking: () -> Unit,
    onRevokeParent: (String) -> Unit,
) {
    EduCard {
        ListRow(
            title = stringResource(R.string.st_parent_link_title),
            supporting = if (linkedParents.isEmpty()) {
                stringResource(R.string.st_parent_link_hub_empty, parentLinkCode)
            } else {
                pluralStringResource(R.plurals.st_parent_link_hub_linked, linkedParents.size, linkedParents.size, parentLinkCode)
            },
            leading = Icons.Filled.Link,
            showChevron = true,
            onClick = onOpenParentLinking,
        )
        if (linkedParents.isNotEmpty()) {
            linkedParents.take(1).forEach { parent ->
                LinkedParentRow(parent = parent, onRevoke = { onRevokeParent(parent.id) })
            }
        } else {
            Text(
                text = stringResource(R.string.st22_no_parents_body),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun SubjectQuickStatRow(subject: SubjectProgress) {
    val colors = EduTheme.colors
    Column(modifier = Modifier.padding(vertical = Spacing.xxs)) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Text(subject.title, style = EduTheme.typography.body, color = colors.textPrimary)
            Text(
                text = stringResource(R.string.st22_progress_percent, (subject.progress * 100).toInt().toString()),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
        }
        EduLinearProgress(progress = subject.progress, modifier = Modifier.padding(top = Spacing.xxs))
    }
}

@Composable
private fun LinkedParentRow(parent: LinkedParent, onRevoke: () -> Unit) {
    val colors = EduTheme.colors
    EduCard {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatar)
                    .background(colors.neutralAlpha100, CircleShape),
            ) {
                Icon(Icons.Filled.SupervisorAccount, contentDescription = null, tint = colors.textSecondary)
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(parent.name, style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                Text(
                    text = stringResource(R.string.st22_parent_relationship_format, parent.relationship, parent.email),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
            EduIconButton(
                icon = Icons.Filled.PersonRemove,
                contentDescription = stringResource(R.string.st22_revoke_parent_action),
                tint = colors.danger,
                onClick = onRevoke,
            )
        }
    }
}

@Composable
private fun ProfileEditSheet(
    displayName: String,
    grade: Grade,
    school: String,
    isSaving: Boolean,
    onDismiss: () -> Unit,
    onSave: (String, Grade, String) -> Unit,
) {
    val colors = EduTheme.colors
    var name by remember { mutableStateOf(displayName) }
    var selectedGrade by remember { mutableStateOf(grade) }
    var schoolValue by remember { mutableStateOf(school) }

    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(colors.surface, RoundedCornerShape(Radius.lg))
                .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.lg))
                .padding(Spacing.card),
        ) {
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(colors.primaryContainer, CircleShape)
                    .align(Alignment.CenterHorizontally),
            ) {
                Text(name.take(1).ifEmpty { "؟" }, style = EduTheme.typography.titleLg, color = colors.primary)
            }
            Text(
                text = stringResource(R.string.st22_edit_sheet_title),
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier
                    .padding(top = Spacing.sm)
                    .align(Alignment.CenterHorizontally),
            )

            EduTextField(
                value = name,
                onValueChange = { name = it },
                label = stringResource(R.string.st22_edit_name_label),
                modifier = Modifier.padding(top = Spacing.md),
            )

            Text(
                text = stringResource(R.string.st22_edit_grade_label),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.md, bottom = Spacing.xxs),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
                GradeOption(Grade.Grade10, selectedGrade) { selectedGrade = it }
                GradeOption(Grade.Grade11, selectedGrade) { selectedGrade = it }
                GradeOption(Grade.Baccalaureate, selectedGrade) { selectedGrade = it }
            }

            EduTextField(
                value = schoolValue,
                onValueChange = { schoolValue = it },
                label = stringResource(R.string.st22_edit_school_label),
                modifier = Modifier.padding(top = Spacing.md),
            )

            PrimaryButton(
                text = stringResource(R.string.common_save),
                onClick = { onSave(name, selectedGrade, schoolValue) },
                enabled = name.isNotBlank() && schoolValue.isNotBlank(),
                isLoading = isSaving,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md),
            )
            SecondaryButton(
                text = stringResource(R.string.common_cancel),
                onClick = onDismiss,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            )
        }
    }
}

@Composable
private fun GradeOption(option: Grade, selected: Grade, onSelect: (Grade) -> Unit) {
    val colors = EduTheme.colors
    val isSelected = option == selected
    val label = gradeLabel(option)
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .background(if (isSelected) colors.primary else colors.neutralAlpha100, RoundedCornerShape(Radius.pill))
            .eduClickable(onClickLabel = label) { onSelect(option) }
            .padding(horizontal = Spacing.sm, vertical = Spacing.xs),
    ) {
        Text(
            text = label,
            style = EduTheme.typography.caption,
            color = if (isSelected) colors.onPrimary else colors.textSecondary,
        )
    }
}

@Composable
private fun gradeLabel(grade: Grade): String = when (grade) {
    Grade.Grade10 -> stringResource(R.string.a07_grade_10)
    Grade.Grade11 -> stringResource(R.string.a07_grade_11)
    Grade.Baccalaureate -> stringResource(R.string.a07_grade_12)
}

@Composable
private fun preferencesSummary(goal: LearningGoal, length: ExplanationLength, interests: Set<LearningInterest>): String {
    val interestText = interests.firstOrNull()?.let { " · ${interestLabel(it)}" }.orEmpty()
    return "${goalLabel(goal)} · ${lengthLabel(length)}$interestText"
}

@Composable
private fun goalLabel(goal: LearningGoal): String = when (goal) {
    LearningGoal.ImproveGrades -> stringResource(R.string.st_lp_goal_improve_grades)
    LearningGoal.PrepareForBaccalaureate -> stringResource(R.string.st_lp_goal_prepare_bac)
    LearningGoal.DeeperUnderstanding -> stringResource(R.string.st_lp_goal_deeper_understanding)
}

@Composable
private fun lengthLabel(length: ExplanationLength): String = when (length) {
    ExplanationLength.Brief -> stringResource(R.string.st_lp_length_brief)
    ExplanationLength.Balanced -> stringResource(R.string.st_lp_length_balanced)
    ExplanationLength.Detailed -> stringResource(R.string.st_lp_length_detailed)
}

@Composable
private fun interestLabel(interest: LearningInterest): String = when (interest) {
    LearningInterest.Football -> stringResource(R.string.st_lp_interest_football)
    LearningInterest.Gaming -> stringResource(R.string.st_lp_interest_gaming)
    LearningInterest.Music -> stringResource(R.string.st_lp_interest_music)
    LearningInterest.Drawing -> stringResource(R.string.st_lp_interest_drawing)
}

@Composable
private fun ProfileSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        repeat(2) { SkeletonListItem() }
    }
}
