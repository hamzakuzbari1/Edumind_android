package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Stop
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.text.style.TextAlign
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.TeacherDocumentKind
import com.rork.eduspark.data.model.TeacherExperienceInfo
import com.rork.eduspark.data.model.TeacherIdentityInfo
import com.rork.eduspark.data.model.TeacherPricingInfo
import com.rork.eduspark.data.model.TeacherQualification
import com.rork.eduspark.data.model.TeacherSetupDocument
import com.rork.eduspark.data.model.TeacherSetupState
import com.rork.eduspark.data.model.TeacherSetupStepId
import com.rork.eduspark.data.model.TeacherSubjectsGrades
import com.rork.eduspark.data.model.TeacherVoiceSample
import com.rork.eduspark.data.model.VoiceSampleState
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.GhostButton
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.progress.HorizontalSpine
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SectionHeader
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.screens.auth.TeacherSubjectOptions
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-01 · Teacher Setup Wizard.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Reuses [HorizontalSpine] as-is — the SAME horizontal Progress Spine SO-01…SO-04's own shell,
 * ST-06's quiz runner and A-13's transition already use — never a new progress primitive.
 * There is no exit affordance on step 1: [TeacherSetupScreen] is only ever reached with
 * nothing meaningful behind it in the back stack (same shape as SO-01), so the back arrow
 * only appears from step 2 onward, moving between steps rather than leaving the wizard.
 */
@Composable
fun TeacherSetupScreen(
    onFinished: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherSetupViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                TeacherSetupEvent.SetupCompleted -> onFinished()
            }
        }
    }

    ScreenStateHost(
        state = state.result,
        onRetry = viewModel::retry,
        isOffline = !state.isOnline,
        loading = { TeacherSetupSkeleton() },
        modifier = modifier.fillMaxSize(),
    ) { data ->
        TeacherSetupWizard(
            data = data,
            isSaving = state.isSaving,
            isFinishing = state.isFinishing,
            showValidationError = state.showValidationError,
            onUpdateIdentity = viewModel::updateIdentity,
            onUpdateSubjectsGrades = viewModel::updateSubjectsGrades,
            onUpdateQualifications = viewModel::updateQualifications,
            onUpdateExperience = viewModel::updateExperience,
            onUpdateDocuments = viewModel::updateDocuments,
            onUpdatePricing = viewModel::updatePricing,
            onUpdateVoiceSample = viewModel::updateVoiceSample,
            onBack = viewModel::goBack,
            onNext = viewModel::saveCurrentStepAndAdvance,
            onFinish = viewModel::finishSetup,
        )
    }
}

private val STEP_ORDER = TeacherSetupStepId.entries

@Composable
private fun TeacherSetupWizard(
    data: TeacherSetupScreenData,
    isSaving: Boolean,
    isFinishing: Boolean,
    showValidationError: Boolean,
    onUpdateIdentity: (TeacherIdentityInfo) -> Unit,
    onUpdateSubjectsGrades: (TeacherSubjectsGrades) -> Unit,
    onUpdateQualifications: (List<TeacherQualification>) -> Unit,
    onUpdateExperience: (TeacherExperienceInfo) -> Unit,
    onUpdateDocuments: (List<TeacherSetupDocument>) -> Unit,
    onUpdatePricing: (TeacherPricingInfo) -> Unit,
    onUpdateVoiceSample: (TeacherVoiceSample) -> Unit,
    onBack: () -> Unit,
    onNext: () -> Unit,
    onFinish: () -> Unit,
) {
    val colors = EduTheme.colors
    val step = data.currentStepId
    val stepIndex = step?.let { STEP_ORDER.indexOf(it) } ?: STEP_ORDER.size
    val isApprovedSetupChrome = step == TeacherSetupStepId.Identity || step == TeacherSetupStepId.SubjectsGrades
    val approvedProgressIndex = if (step == TeacherSetupStepId.Identity) 1 else 2

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(colors.background)
            .safeDrawingPadding()
            .imePadding(),
    ) {
        if (isApprovedSetupChrome) {
            ApprovedSetupTopBar(
                title = stringResource(
                    if (step == TeacherSetupStepId.Identity) R.string.tc01_setup_title else R.string.tc01_teaching_question,
                ),
                showBack = step == TeacherSetupStepId.SubjectsGrades,
                onBack = onBack,
            )
        } else {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(Sizing.topBarHeight)
                    .padding(horizontal = Spacing.xs),
            ) {
                if (stepIndex > 0) {
                    EduIconButton(
                        icon = Icons.AutoMirrored.Filled.ArrowBack,
                        contentDescription = stringResource(R.string.a11y_back),
                        onClick = onBack,
                    )
                } else {
                    Spacer(modifier = Modifier.size(Sizing.touchTarget))
                }
                Box(modifier = Modifier.weight(1f))
                Text(
                    text = stringResource(R.string.tc01_step_label, numeral(stepIndex + 1), numeral(STEP_ORDER.size + 1)),
                    style = EduTheme.typography.caption,
                    color = colors.textMuted,
                    modifier = Modifier.padding(end = Spacing.gutter),
                )
            }

            HorizontalSpine(
                total = STEP_ORDER.size + 1,
                currentIndex = stepIndex,
                contentDescription = stringResource(R.string.tc01_step_label, numeral(stepIndex + 1), numeral(STEP_ORDER.size + 1)),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = Spacing.gutter),
            )
        }

        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = Spacing.gutter),
        ) {
            if (isApprovedSetupChrome) {
                // Numeric "١ / ٣" must stay LTR so RTL does not reverse it to "٣ / ١".
                CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) {
                    Text(
                        text = stringResource(R.string.tc01_progress, numeral(approvedProgressIndex), numeral(3)),
                        style = EduTheme.typography.caption,
                        color = colors.textTertiary,
                        textAlign = if (step == TeacherSetupStepId.Identity) TextAlign.Center else TextAlign.Start,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = Spacing.xs, bottom = Spacing.sm),
                    )
                }
            } else {
                Spacer(modifier = Modifier.height(Spacing.section))
            }
            when (step) {
                TeacherSetupStepId.Identity -> IdentityStep(data.draft.identity, onUpdateIdentity)
                TeacherSetupStepId.SubjectsGrades -> SubjectsGradesStep(data.draft.subjectsGrades, onUpdateSubjectsGrades)
                TeacherSetupStepId.Qualifications -> QualificationsStep(data.draft.qualifications, onUpdateQualifications)
                TeacherSetupStepId.Experience -> ExperienceStep(data.draft.experience, onUpdateExperience)
                TeacherSetupStepId.Documents -> DocumentsStep(data.draft.documents, onUpdateDocuments)
                TeacherSetupStepId.Pricing -> PricingStep(data.draft.pricing, onUpdatePricing)
                TeacherSetupStepId.VoiceSample -> VoiceSampleStep(data.draft.voiceSample, onUpdateVoiceSample)
                null -> ReviewStep(data.draft)
            }
            if (showValidationError) {
                Text(
                    text = stringResource(R.string.tc01_validation_error),
                    style = EduTheme.typography.caption,
                    color = colors.danger,
                    modifier = Modifier.padding(top = Spacing.sm),
                )
            }
            Spacer(modifier = Modifier.height(Spacing.section))
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter)
                .padding(top = Spacing.sm, bottom = Spacing.md),
        ) {
            if (step == null) {
                PrimaryButton(
                    text = stringResource(R.string.tc01_finish_setup),
                    onClick = onFinish,
                    isLoading = isFinishing,
                    modifier = Modifier.fillMaxWidth(),
                )
            } else {
                PrimaryButton(
                    text = stringResource(if (isApprovedSetupChrome) R.string.tc01_save else R.string.tc01_next),
                    onClick = onNext,
                    isLoading = isSaving,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

// ── STEP 1 · Identity ──────────────────────────────────────────────────────────
@Composable
private fun IdentityStep(identity: TeacherIdentityInfo, onUpdate: (TeacherIdentityInfo) -> Unit) {
    val colors = EduTheme.colors
    var photoAdded by rememberSaveable { mutableStateOf(false) }
    val initial = identity.displayName.trim().firstOrNull()?.toString().orEmpty()

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(Sizing.heroBadge)
                .background(colors.primaryContainer, CircleShape)
                .eduClickable(onClickLabel = stringResource(R.string.tc01_add_photo)) {
                    photoAdded = !photoAdded
                },
        ) {
            if (photoAdded) {
                Icon(
                    imageVector = Icons.Filled.Person,
                    contentDescription = null,
                    tint = colors.primary,
                    modifier = Modifier.size(Sizing.iconLg),
                )
            } else {
                Text(
                    text = if (initial.isNotBlank()) initial else "س",
                    style = EduTheme.typography.titleLg.copy(fontWeight = FontWeight.ExtraBold),
                    color = colors.primary,
                )
            }
        }
        Text(
            text = stringResource(R.string.tc01_add_photo),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.SemiBold),
            color = colors.textTertiary,
            modifier = Modifier
                .padding(top = Spacing.sm, bottom = Spacing.md)
                .eduClickable(onClickLabel = stringResource(R.string.tc01_add_photo)) {
                    photoAdded = !photoAdded
                },
        )
    }

    EduTextField(
        value = identity.displayName,
        onValueChange = { onUpdate(identity.copy(displayName = it)) },
        label = stringResource(R.string.tc01_name_label),
        labelPlacement = FieldLabelPlacement.Above,
        modifier = Modifier.padding(bottom = Spacing.sm),
    )
    EduTextField(
        value = identity.headline,
        onValueChange = { onUpdate(identity.copy(headline = it)) },
        label = stringResource(R.string.tc01_bio_label),
        placeholder = stringResource(R.string.tc01_bio_placeholder),
        labelPlacement = FieldLabelPlacement.Above,
        singleLine = false,
    )
}

// ── STEP 2 · Subjects & Grades ─────────────────────────────────────────────────
// Reuses [TeacherSubjectOptions] from A-07 verbatim — the exact same subject-id vocabulary
// the registration screen already offers, never a second catalog to keep in sync. See
// [TeacherSetupViewModel]'s own doc comment for why this is the "one source of truth" fix.
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SubjectsGradesStep(subjectsGrades: TeacherSubjectsGrades, onUpdate: (TeacherSubjectsGrades) -> Unit) {
    val colors = EduTheme.colors

    Text(
        text = stringResource(R.string.tc01_grades_section),
        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
        color = colors.textPrimary,
        modifier = Modifier.padding(bottom = Spacing.xs),
    )
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = Spacing.md),
    ) {
        Grade.entries.forEach { grade ->
            val selected = grade in subjectsGrades.grades
            EduChip(
                label = teacherSetupGradeLabel(grade),
                selected = selected,
                onClick = {
                    val updated = if (selected) subjectsGrades.grades - grade else subjectsGrades.grades + grade
                    onUpdate(subjectsGrades.copy(grades = updated))
                },
            )
        }
    }

    Text(
        text = stringResource(R.string.tc01_subjects_section),
        style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
        color = colors.textPrimary,
        modifier = Modifier.padding(bottom = Spacing.xs),
    )
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        TeacherSubjectOptions.forEach { option ->
            val selected = option.id in subjectsGrades.subjectIds
            EduChip(
                label = stringResource(option.labelRes),
                selected = selected,
                onClick = {
                    val updated = if (selected) subjectsGrades.subjectIds - option.id else subjectsGrades.subjectIds + option.id
                    onUpdate(subjectsGrades.copy(subjectIds = updated))
                },
            )
        }
    }
}

// ── STEP 3 · Qualifications ────────────────────────────────────────────────────
@Composable
private fun QualificationsStep(qualifications: List<TeacherQualification>, onUpdate: (List<TeacherQualification>) -> Unit) {
    val colors = EduTheme.colors
    StepHeader(R.string.tc01_qualifications_title, R.string.tc01_qualifications_body)

    qualifications.forEach { qualification ->
        EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(qualification.title, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = colors.textPrimary)
                    Text(
                        text = if (qualification.year != null) "${qualification.institution} · ${qualification.year}" else qualification.institution,
                        style = EduTheme.typography.caption,
                        color = colors.textMuted,
                    )
                }
                EduIconButton(
                    icon = Icons.Filled.Close,
                    contentDescription = stringResource(R.string.tc01_remove_qualification),
                    tint = colors.danger,
                    onClick = { onUpdate(qualifications - qualification) },
                )
            }
        }
    }

    var title by remember { mutableStateOf("") }
    var institution by remember { mutableStateOf("") }
    var year by remember { mutableStateOf("") }

    EduCard {
        EduTextField(
            value = title,
            onValueChange = { title = it },
            label = stringResource(R.string.tc01_qualification_title_label),
            modifier = Modifier.padding(bottom = Spacing.sm),
        )
        EduTextField(
            value = institution,
            onValueChange = { institution = it },
            label = stringResource(R.string.tc01_qualification_institution_label),
            modifier = Modifier.padding(bottom = Spacing.sm),
        )
        EduTextField(
            value = year,
            onValueChange = { year = it },
            label = stringResource(R.string.tc01_qualification_year_label),
            keyboardType = KeyboardType.Number,
            modifier = Modifier.padding(bottom = Spacing.sm),
        )
        SecondaryButton(
            text = stringResource(R.string.tc01_add_qualification),
            leadingIcon = Icons.Filled.Add,
            enabled = title.isNotBlank() && institution.isNotBlank(),
            onClick = {
                onUpdate(
                    qualifications + TeacherQualification(
                        id = "q-${System.currentTimeMillis()}",
                        title = title,
                        institution = institution,
                        year = year.ifBlank { null },
                    )
                )
                title = ""
                institution = ""
                year = ""
            },
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

// ── STEP 4 · Experience ────────────────────────────────────────────────────────
private val TEACHING_MODE_OPTIONS = listOf(
    R.string.tc01_mode_individual to "individual",
    R.string.tc01_mode_small_group to "small_group",
    R.string.tc01_mode_online to "online",
)

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ExperienceStep(experience: TeacherExperienceInfo, onUpdate: (TeacherExperienceInfo) -> Unit) {
    StepHeader(R.string.tc01_experience_title, R.string.tc01_experience_body)

    EduTextField(
        value = experience.yearsOfExperience?.toString().orEmpty(),
        onValueChange = { text -> onUpdate(experience.copy(yearsOfExperience = text.toIntOrNull())) },
        label = stringResource(R.string.tc01_experience_years_label),
        keyboardType = KeyboardType.Number,
        modifier = Modifier.padding(bottom = Spacing.section),
    )
    EduTextField(
        value = experience.description,
        onValueChange = { onUpdate(experience.copy(description = it)) },
        label = stringResource(R.string.tc01_experience_description_label),
        singleLine = false,
        modifier = Modifier.padding(bottom = Spacing.section),
    )

    SectionHeader(title = stringResource(R.string.tc01_experience_modes_section))
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
        modifier = Modifier.fillMaxWidth(),
    ) {
        TEACHING_MODE_OPTIONS.forEach { (labelRes, id) ->
            val selected = id in experience.teachingModes
            EduChip(
                label = stringResource(labelRes),
                selected = selected,
                onClick = {
                    val updated = if (selected) experience.teachingModes - id else experience.teachingModes + id
                    onUpdate(experience.copy(teachingModes = updated))
                },
            )
        }
    }
}

// ── STEP 5 · Documents ─────────────────────────────────────────────────────────
@Composable
private fun DocumentsStep(documents: List<TeacherSetupDocument>, onUpdate: (List<TeacherSetupDocument>) -> Unit) {
    val colors = EduTheme.colors
    val identityDocumentHint = stringResource(R.string.tc01_document_identity_hint)
    val qualificationDocumentHint = stringResource(R.string.tc01_document_qualification_hint)
    StepHeader(R.string.tc01_documents_title, R.string.tc01_documents_body)

    documents.forEach { document ->
        EduCard(modifier = Modifier.padding(bottom = Spacing.sm)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
                Icon(Icons.Filled.AttachFile, contentDescription = null, tint = colors.zaytoun, modifier = Modifier.size(Sizing.icon))
                Column(modifier = Modifier.weight(1f)) {
                    Text(document.labelHint, style = EduTheme.typography.body, color = colors.textPrimary)
                    Text(document.fileName ?: "", style = EduTheme.typography.caption, color = colors.textMuted)
                }
                EduIconButton(
                    icon = Icons.Filled.Close,
                    contentDescription = stringResource(R.string.tc01_remove_document),
                    tint = colors.danger,
                    onClick = { onUpdate(documents - document) },
                )
            }
        }
    }

    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        SecondaryButton(
            text = stringResource(R.string.tc01_add_identity_document),
            onClick = {
                onUpdate(
                    documents + TeacherSetupDocument(
                        id = "doc-${System.currentTimeMillis()}",
                        kind = TeacherDocumentKind.Identity,
                        labelHint = identityDocumentHint,
                        fileName = "id_scan_${documents.count { it.kind == TeacherDocumentKind.Identity } + 1}.jpg",
                    )
                )
            },
        )
        SecondaryButton(
            text = stringResource(R.string.tc01_add_qualification_document),
            onClick = {
                onUpdate(
                    documents + TeacherSetupDocument(
                        id = "doc-${System.currentTimeMillis()}",
                        kind = TeacherDocumentKind.Qualification,
                        labelHint = qualificationDocumentHint,
                        fileName = "qualification_${documents.count { it.kind == TeacherDocumentKind.Qualification } + 1}.pdf",
                    )
                )
            },
        )
    }
    Text(
        text = stringResource(R.string.tc01_documents_mock_notice),
        style = EduTheme.typography.caption,
        color = EduTheme.colors.textMuted,
        modifier = Modifier.padding(top = Spacing.sm),
    )
}

// ── STEP 6 · Pricing ───────────────────────────────────────────────────────────
@Composable
private fun PricingStep(pricing: TeacherPricingInfo, onUpdate: (TeacherPricingInfo) -> Unit) {
    StepHeader(R.string.tc01_pricing_title, R.string.tc01_pricing_body)

    Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm)) {
        EduTextField(
            value = pricing.sessionPriceLabel,
            onValueChange = { onUpdate(pricing.copy(sessionPriceLabel = it)) },
            label = stringResource(R.string.tc01_pricing_amount_label),
            keyboardType = KeyboardType.Number,
            modifier = Modifier.weight(1f),
        )
        EduTextField(
            value = pricing.currencyLabel,
            onValueChange = { onUpdate(pricing.copy(currencyLabel = it)) },
            label = stringResource(R.string.tc01_pricing_currency_label),
            modifier = Modifier.weight(1f),
        )
    }
}

// ── STEP 7 · Voice Sample ──────────────────────────────────────────────────────
@Composable
private fun VoiceSampleStep(voiceSample: TeacherVoiceSample, onUpdate: (TeacherVoiceSample) -> Unit) {
    val colors = EduTheme.colors
    var consentGiven by remember { mutableStateOf(voiceSample.state == VoiceSampleState.Recorded) }
    var isRecording by remember { mutableStateOf(false) }

    StepHeader(R.string.tc01_voice_title, R.string.tc01_voice_body)

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = Spacing.section)
            .eduClickable(onClickLabel = stringResource(R.string.tc01_voice_consent)) { consentGiven = !consentGiven },
    ) {
        Checkbox(
            checked = consentGiven,
            onCheckedChange = { consentGiven = it },
            colors = CheckboxDefaults.colors(checkedColor = colors.zaytoun, checkmarkColor = colors.onZaytoun),
        )
        Text(stringResource(R.string.tc01_voice_consent), style = EduTheme.typography.body, color = colors.textPrimary, modifier = Modifier.weight(1f))
    }

    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
        when {
            isRecording -> Text(stringResource(R.string.tc01_voice_recording), style = EduTheme.typography.body, color = colors.danger)
            voiceSample.state == VoiceSampleState.Recorded -> {
                Text(
                    text = stringResource(R.string.tc01_voice_recorded, voiceSample.durationLabel.orEmpty()),
                    style = EduTheme.typography.body,
                    color = colors.textPrimary,
                    modifier = Modifier.padding(bottom = Spacing.sm),
                )
            }
        }

        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .padding(top = Spacing.md, bottom = Spacing.sm)
                .size(Sizing.heroBadge)
                .background(if (consentGiven) (if (isRecording) colors.danger else colors.zaytoun) else colors.hajar300, CircleShape)
                .eduClickable(
                    enabled = consentGiven,
                    onClickLabel = stringResource(if (isRecording) R.string.tc01_voice_stop else R.string.tc01_voice_record),
                ) {
                    if (isRecording) {
                        isRecording = false
                        onUpdate(TeacherVoiceSample(state = VoiceSampleState.Recorded, durationLabel = "٠٠:٣٠"))
                    } else {
                        isRecording = true
                    }
                },
        ) {
            Icon(
                imageVector = if (isRecording) Icons.Filled.Stop else Icons.Filled.Mic,
                contentDescription = null,
                tint = colors.onZaytoun,
                modifier = Modifier.size(Sizing.iconLg * 1.2f),
            )
        }

        if (voiceSample.state == VoiceSampleState.Recorded && !isRecording) {
            GhostButton(
                text = stringResource(R.string.tc01_voice_rerecord),
                onClick = { onUpdate(TeacherVoiceSample()) },
            )
        }
    }
}

// ── Review / Finish ────────────────────────────────────────────────────────────
@Composable
private fun ReviewStep(draft: TeacherSetupState) {
    val colors = EduTheme.colors
    StepHeader(R.string.tc01_review_title, R.string.tc01_review_body)

    EduCard {
        ReviewRow(stringResource(R.string.tc01_review_name), draft.identity.displayName)
        ReviewRow(stringResource(R.string.tc01_review_subjects), numeral(draft.subjectsGrades.subjectIds.size))
        ReviewRow(stringResource(R.string.tc01_review_qualifications), numeral(draft.qualifications.size))
        ReviewRow(stringResource(R.string.tc01_review_documents), numeral(draft.documents.size))
        ReviewRow(
            stringResource(R.string.tc01_review_pricing),
            if (draft.pricing.sessionPriceLabel.isNotBlank()) "${draft.pricing.sessionPriceLabel} ${draft.pricing.currencyLabel}" else "—",
        )
        ReviewRow(
            stringResource(R.string.tc01_review_voice),
            if (draft.voiceSample.state == VoiceSampleState.Recorded) stringResource(R.string.tc01_voice_recorded_short) else stringResource(R.string.tc01_voice_not_recorded),
        )
    }
    Text(
        text = stringResource(R.string.tc01_review_hint),
        style = EduTheme.typography.caption,
        color = colors.textMuted,
        modifier = Modifier.padding(top = Spacing.sm),
    )
}

@Composable
private fun ReviewRow(label: String, value: String) {
    Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth().padding(vertical = Spacing.xxs)) {
        Text(label, style = EduTheme.typography.body, color = EduTheme.colors.textMuted)
        Text(value, style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold), color = EduTheme.colors.textPrimary)
    }
}

@Composable
private fun ApprovedSetupTopBar(
    title: String,
    showBack: Boolean,
    onBack: () -> Unit,
) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .background(colors.surface)
            .border(Sizing.hairline, colors.border)
            .height(Sizing.topBarHeight)
            .padding(horizontal = Spacing.xs),
    ) {
        if (showBack) {
            EduIconButton(
                icon = Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = stringResource(R.string.a11y_back),
                onClick = onBack,
            )
        } else {
            Spacer(modifier = Modifier.size(Sizing.touchTarget))
        }
        Text(
            text = title,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier.weight(1f),
        )
        Spacer(modifier = Modifier.size(Sizing.touchTarget))
    }
}

@Composable
private fun teacherSetupGradeLabel(grade: Grade): String = when (grade) {
    Grade.Grade10 -> stringResource(R.string.tc01_grade_10_short)
    Grade.Grade11 -> stringResource(R.string.tc01_grade_11_short)
    Grade.Baccalaureate -> stringResource(R.string.tc01_grade_12_short)
}

@Composable
private fun StepHeader(titleRes: Int, bodyRes: Int) {
    Text(text = stringResource(titleRes), style = EduTheme.typography.titleLg, color = EduTheme.colors.textPrimary)
    Text(
        text = stringResource(bodyRes),
        style = EduTheme.typography.body,
        color = EduTheme.colors.textMuted,
        modifier = Modifier.padding(top = Spacing.xs, bottom = Spacing.section),
    )
}

@Composable
private fun TeacherSetupSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
        SkeletonCard()
    }
}
