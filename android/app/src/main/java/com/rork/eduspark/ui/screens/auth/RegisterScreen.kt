package com.rork.eduspark.ui.screens.auth

import androidx.activity.compose.BackHandler
import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.input.PasswordField
import com.rork.eduspark.ui.components.input.PasswordStrengthMeter
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-05 · Register — Student   ·   A-06 · Parent   ·   A-07 · Teacher
 * ══════════════════════════════════════════════════════════════════════════
 *
 * One screen, three roles. The Screen Inventory describes A-05, A-06 and A-07 as the same
 * form with one role-specific addition each, so this is literally the same composable with
 * a [role] parameter rather than three files that would drift apart by the second edit:
 *
 *  • **Student** — the form, nothing added.
 *  • **Parent**  — plus a note that linking a child is the step after this one.
 *  • **Teacher** — plus subjects and grades they intend to teach.
 *
 * The teaching intent is honest about where it goes. Registration sends name, email,
 * password and role — the only things the platform accepts — so the subjects and grades are
 * stored on the device for TC-01 Teacher Setup, and the screen says exactly that instead of
 * implying the server was told.
 *
 * Everything else is the shared auth shell: the same header, the same 48dp fields, the same
 * single error region, the same language toggle pinned to the bottom.
 */
@Composable
fun RegisterScreen(
    role: UserRole,
    locale: AppLocale,
    onSelectLocale: (AppLocale) -> Unit,
    onAuthenticated: (SessionUser) -> Unit,
    onEmailVerificationRequired: (String) -> Unit,
    onLogin: () -> Unit,
    onChangeAccountType: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: RegisterViewModel = koinViewModel(parameters = { parametersOf(role) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val focusManager = LocalFocusManager.current
    val presentation = presentationOf(role)

    BackHandler { onBack() }

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is RegisterEvent.Authenticated -> onAuthenticated(event.user)
                is RegisterEvent.EmailVerificationRequired ->
                    onEmailVerificationRequired(event.email)
            }
        }
    }

    val submit: () -> Unit = {
        focusManager.clearFocus()
        viewModel.submit()
    }

    AuthScaffold(
        modifier = modifier,
        onBack = onBack,
        bottomBlock = {
            AuthLanguageToggle(
                current = locale,
                onSelect = onSelectLocale,
                note = stringResource(R.string.a04_language_restart_note),
            )
        },
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .verticalScroll(rememberScrollState()),
        ) {
            AuthPageHeader(
                title = stringResource(presentation.titleRes),
                body = stringResource(presentation.bodyRes),
            )

            // A-06: the parent learns *before* typing that this account is theirs, and that
            // the child comes next. It is a note, not a warning — quiet tint, no alarm.
            if (role == UserRole.Parent) {
                RegisterNote(
                    text = stringResource(R.string.a06_link_child_note),
                    modifier = Modifier.padding(top = Spacing.md),
                )
            }

            Spacer(modifier = Modifier.height(Spacing.section))

            EduTextField(
                value = state.name,
                onValueChange = viewModel::onNameChange,
                label = stringResource(R.string.reg_name_label),
                placeholder = stringResource(R.string.reg_name_placeholder),
                errorText = state.nameError?.let { stringResource(it) },
                // The sentence belongs to the single region below, not under each field.
                showErrorText = false,
                labelPlacement = FieldLabelPlacement.Above,
                imeAction = ImeAction.Next,
                enabled = !state.isSubmitting,
            )

            Spacer(modifier = Modifier.height(Spacing.md))

            EduTextField(
                value = state.email,
                onValueChange = viewModel::onEmailChange,
                label = stringResource(R.string.a04_email_label),
                placeholder = stringResource(R.string.a04_email_placeholder),
                errorText = state.emailError?.let { stringResource(it) },
                showErrorText = false,
                labelPlacement = FieldLabelPlacement.Above,
                keyboardType = KeyboardType.Email,
                imeAction = ImeAction.Next,
                enabled = !state.isSubmitting,
            )

            Spacer(modifier = Modifier.height(Spacing.md))

            PasswordField(
                value = state.password,
                onValueChange = viewModel::onPasswordChange,
                label = stringResource(R.string.a04_password_label),
                placeholder = stringResource(R.string.reg_password_placeholder),
                errorText = state.passwordError?.let { stringResource(it) },
                // The requirement is stated up front, so nobody discovers it by failing.
                supportingText = stringResource(R.string.reg_password_hint),
                showErrorText = false,
                labelPlacement = FieldLabelPlacement.Above,
                revealAsText = true,
                imeAction = ImeAction.Next,
            )

            PasswordStrengthMeter(password = state.password)

            Spacer(modifier = Modifier.height(Spacing.md))

            PasswordField(
                value = state.passwordConfirmation,
                onValueChange = viewModel::onPasswordConfirmationChange,
                label = stringResource(R.string.reg_confirm_label),
                placeholder = stringResource(R.string.reg_confirm_placeholder),
                errorText = state.passwordConfirmationError?.let { stringResource(it) },
                showErrorText = false,
                labelPlacement = FieldLabelPlacement.Above,
                revealAsText = true,
                imeAction = ImeAction.Done,
                onImeAction = submit,
            )

            // A-07 · what they teach. Multi-select, because most Syrian teachers teach more
            // than one subject and more than one grade.
            if (role == UserRole.Teacher) {
                Spacer(modifier = Modifier.height(Spacing.section))

                ChipSection(
                    title = stringResource(R.string.a07_subjects_label),
                    options = TeacherSubjectOptions,
                    selectedIds = state.subjectIds,
                    onToggle = viewModel::toggleSubject,
                )

                Spacer(modifier = Modifier.height(Spacing.md))

                ChipSection(
                    title = stringResource(R.string.a07_grades_label),
                    options = TeacherGradeOptions,
                    selectedIds = state.gradeIds,
                    onToggle = viewModel::toggleGrade,
                )

                Text(
                    text = stringResource(R.string.a07_intent_note),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textMuted,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = Spacing.xs),
                )
            }

            Spacer(modifier = Modifier.height(Spacing.md))

            TermsRow(
                // Student and Parent affirm the 13+ age line the PDF specifies; Teacher's
                // checkbox stays the plain terms sentence — nothing to affirm about a minor.
                label = stringResource(
                    if (role == UserRole.Teacher) R.string.reg_terms else R.string.reg_terms_with_age
                ),
                accepted = state.acceptedTerms,
                onAcceptedChange = viewModel::onAcceptTermsChange,
            )

            // ── THE SINGLE ERROR REGION ──────────────────────────────────
            AuthErrorRegion {
                when {
                    state.isSubmitting -> AuthProgressRow(stringResource(R.string.reg_creating))

                    state.message != null -> RegisterMessageCard(
                        message = state.message!!,
                        isOnline = state.isOnline,
                        onLogin = onLogin,
                        onRetry = submit,
                    )
                }
            }

            PrimaryButton(
                text = stringResource(
                    if (state.isSubmitting) R.string.reg_submitting else R.string.reg_submit
                ),
                onClick = submit,
                enabled = state.canSubmit,
                isLoading = state.isSubmitting,
                modifier = Modifier.fillMaxWidth(),
            )

            // Says what happens next, before it happens — the verification code on A-08 is
            // then expected rather than a surprise.
            Text(
                text = stringResource(R.string.reg_next_step),
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs),
            )

            AuthFooterPrompt(
                question = stringResource(R.string.a03_have_account),
                actionLabel = stringResource(R.string.a03_login_action),
                onAction = onLogin,
            )

            GhostButton(
                text = stringResource(R.string.a03_change_account_type),
                onClick = onChangeAccountType,
                modifier = Modifier.fillMaxWidth(),
            )

            Spacer(modifier = Modifier.height(Spacing.md))
        }
    }
}

/** Which headline the shared form wears. */
private data class RolePresentation(
    @param:StringRes val titleRes: Int,
    @param:StringRes val bodyRes: Int,
)

private fun presentationOf(role: UserRole): RolePresentation = when (role) {
    UserRole.Student -> RolePresentation(R.string.a05_title, R.string.a05_body)
    UserRole.Parent -> RolePresentation(R.string.a06_title, R.string.a06_body)
    UserRole.Teacher -> RolePresentation(R.string.a07_title, R.string.a07_body)
}

/** A teaching-intent option: a stable id for storage, a translated label for the screen. */
data class IntentOption(val id: String, @param:StringRes val labelRes: Int)

/**
 * Subjects and grades offered on A-07.
 *
 * A fixed local list, not a fetched catalogue. The authoritative catalogue lives behind the
 * platform's catalog routes, which need a session — and registration happens before there
 * is one. Rather than invent a public endpoint, the screen offers the Syrian secondary
 * curriculum's own vocabulary — the exact same [TeacherSubjectOptions] TC-01's own Subjects &
 * Grades step reuses verbatim once the teacher is signed in (see
 * [com.rork.eduspark.ui.screens.teacher.TeacherSetupViewModel]'s own doc comment), so there is
 * only ever one subject-id vocabulary, never a second one to reconcile against.
 */
val TeacherSubjectOptions = listOf(
    IntentOption("math", R.string.a07_subject_math),
    IntentOption("physics", R.string.a07_subject_physics),
    IntentOption("chemistry", R.string.a07_subject_chemistry),
    IntentOption("biology", R.string.a07_subject_biology),
    IntentOption("arabic", R.string.a07_subject_arabic),
    IntentOption("english", R.string.a07_subject_english),
    IntentOption("informatics", R.string.a07_subject_informatics),
    IntentOption("philosophy", R.string.a07_subject_philosophy),
)

/** Grade ids match the string form [com.rork.eduspark.ui.screens.teacher.mapRegistrationGradeId] converts to [com.rork.eduspark.data.model.Grade] for TC-01's own typed representation. */
val TeacherGradeOptions = listOf(
    IntentOption("grade_10", R.string.a07_grade_10),
    IntentOption("grade_11", R.string.a07_grade_11),
    IntentOption("grade_12", R.string.a07_grade_12),
)

/**
 * A labelled wrap of chips.
 *
 * [FlowRow] rather than a horizontal scroller: every option must be visible at once on a
 * decision screen, and Arabic subject names vary enough in length that a fixed grid would
 * leave ragged holes.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ChipSection(
    title: String,
    options: List<IntentOption>,
    selectedIds: Set<String>,
    onToggle: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier.fillMaxWidth()) {
        Text(
            text = title,
            style = EduTheme.typography.caption,
            color = EduTheme.colors.textMuted,
            modifier = Modifier.semantics { heading() },
        )
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            verticalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = Spacing.xs),
        ) {
            options.forEach { option ->
                EduChip(
                    label = stringResource(option.labelRes),
                    selected = selectedIds.contains(option.id),
                    onClick = { onToggle(option.id) },
                )
            }
        }
    }
}

/**
 * Terms acceptance.
 *
 * Never pre-ticked, and the whole row is the target so the sentence is as tappable as the
 * box. Not accepting is not an error state on the field — it speaks in the single region
 * like every other unmet condition.
 */
@Composable
private fun TermsRow(
    label: String,
    accepted: Boolean,
    onAcceptedChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier
            .fillMaxWidth()
            .eduClickable(role = Role.Checkbox, onClickLabel = label) {
                onAcceptedChange(!accepted)
            },
    ) {
        Checkbox(
            checked = accepted,
            onCheckedChange = null,
            colors = CheckboxDefaults.colors(
                checkedColor = EduTheme.colors.zaytoun,
                checkmarkColor = EduTheme.colors.onZaytoun,
                uncheckedColor = EduTheme.colors.border,
            ),
        )
        Text(
            text = label,
            style = EduTheme.typography.body,
            color = EduTheme.colors.textPrimary,
            modifier = Modifier.weight(1f),
        )
    }
}

/** A quiet, non-blocking note. Deliberately not the error surface — nothing is wrong. */
@Composable
private fun RegisterNote(
    text: String,
    modifier: Modifier = Modifier,
) {
    EduCard(
        containerColor = EduTheme.colors.zaytounSoft,
        borderColor = EduTheme.colors.border,
        modifier = modifier,
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
            Icon(
                imageVector = Icons.Outlined.Info,
                contentDescription = null,
                tint = EduTheme.colors.zaytoun,
                modifier = Modifier.size(Sizing.icon),
            )
            Text(
                text = text,
                style = EduTheme.typography.caption,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

/** All five register outcomes, in the one region, through the one shared surface. */
@Composable
private fun RegisterMessageCard(
    message: RegisterMessage,
    isOnline: Boolean,
    onLogin: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors

    when (message) {
        is RegisterMessage.Invalid -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = colors.danger,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(message.messageRes),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
        }

        RegisterMessage.EmailAlreadyRegistered -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = colors.danger,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(R.string.reg_error_email_taken),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
            // The useful action is not "try again" — it is "you already have an account".
            SecondaryButton(
                text = stringResource(R.string.a03_login_action),
                onClick = onLogin,
                modifier = Modifier.padding(top = Spacing.xs),
            )
        }

        RegisterMessage.Offline -> AuthMessageSurface(
            icon = Icons.Filled.WifiOff,
            accent = colors.warning,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(
                    if (isOnline) R.string.reg_offline_back_online else R.string.reg_error_offline
                ),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
            if (isOnline) {
                SecondaryButton(
                    text = stringResource(R.string.common_retry),
                    onClick = onRetry,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
            }
        }

        RegisterMessage.ServerProblem -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = colors.danger,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(R.string.state_error_server_body),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
        }

        RegisterMessage.Unknown -> AuthMessageSurface(
            icon = Icons.Filled.ErrorOutline,
            accent = colors.danger,
            modifier = modifier,
        ) {
            Text(
                text = stringResource(R.string.state_error_unknown_body),
                style = EduTheme.typography.caption,
                color = colors.textPrimary,
            )
        }
    }
}
