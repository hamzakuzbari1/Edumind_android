package com.rork.eduspark.ui.screens.teacher

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.rork.eduspark.R
import com.rork.eduspark.core.format.numeral
import com.rork.eduspark.data.model.AiPreReviewAvailability
import com.rork.eduspark.data.model.AiReviewStatus
import com.rork.eduspark.data.model.AtRiskReason
import com.rork.eduspark.data.model.AttendanceStatus
import com.rork.eduspark.data.model.FunnelStageKind
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.GradePublicationStatus
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.LessonInsightKind
import com.rork.eduspark.data.model.LessonProcessingStage
import com.rork.eduspark.data.model.LessonProcessingStageState
import com.rork.eduspark.data.model.LessonProcessingStageStatus
import com.rork.eduspark.data.model.LessonUploadStage
import com.rork.eduspark.data.model.ProjectReviewStatus
import com.rork.eduspark.data.model.QuestionType
import com.rork.eduspark.data.model.SafetySeverity
import com.rork.eduspark.data.model.StudentFlag
import com.rork.eduspark.data.model.StudentMonitoringStatus
import com.rork.eduspark.data.model.TeacherActivityKind
import com.rork.eduspark.data.model.TeacherCourseStatus
import com.rork.eduspark.data.model.TeacherLessonStatus
import com.rork.eduspark.data.model.TeacherProjectMediaKind
import com.rork.eduspark.data.model.TeacherProjectStatus
import com.rork.eduspark.data.model.TeacherQuizStatus
import com.rork.eduspark.data.model.VoiceProfileStatus
import com.rork.eduspark.data.model.VoiceSampleQualityStatus
import com.rork.eduspark.data.model.VoiceSampleSourceType
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.screens.auth.TeacherSubjectOptions
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import java.util.Locale

/**
 * The one honest boundary every not-yet-built Teacher destination in this slice shares —
 * tapping a TC-02 work item or a TC-03 course card shows this instead of a fake link, since
 * TC-04+ (course/lesson management, submission review, messaging) are not built yet. Single
 * acknowledgement action only — the same "dismiss/understand" shape [BlockedTaskDialog] (PJ-03)
 * and the certificate export MOCK dialog (PJ-11) already established, not a new dialog pattern.
 */
@Composable
fun TeacherComingSoonDialog(onDismiss: () -> Unit) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(text = stringResource(R.string.tc_coming_soon_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = { Text(text = stringResource(R.string.tc_coming_soon_body), style = EduTheme.typography.body, color = colors.textMuted) },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_done), onClick = onDismiss) },
        containerColor = colors.surface,
        titleContentColor = colors.textPrimary,
        textContentColor = colors.textMuted,
    )
}

/** Reuses A-07's own grade labels verbatim — the same [Grade] taxonomy, never a second set of strings for it. */
@Composable
fun teacherGradeLabel(grade: Grade): String = when (grade) {
    Grade.Grade10 -> stringResource(R.string.a07_grade_10)
    Grade.Grade11 -> stringResource(R.string.a07_grade_11)
    Grade.Baccalaureate -> stringResource(R.string.a07_grade_12)
}

@Composable
fun teacherSetupChipGradeLabel(grade: Grade): String = when (grade) {
    Grade.Grade10 -> stringResource(R.string.tc01_grade_10_short)
    Grade.Grade11 -> stringResource(R.string.tc01_grade_11_short)
    Grade.Baccalaureate -> stringResource(R.string.tc01_grade_12_short)
}

@Composable
fun teacherSubjectLabel(subjectId: String): String {
    val option = TeacherSubjectOptions.firstOrNull { it.id == subjectId }
    return option?.let { stringResource(it.labelRes) } ?: subjectId
}

@Composable
fun teacherSubjectsLine(subjectIds: Set<String>): String {
    val labels = mutableListOf<String>()
    for (option in TeacherSubjectOptions) {
        if (option.id in subjectIds) {
            labels += stringResource(option.labelRes)
        }
    }
    return labels.joinToString(" · ")
}

@Composable
fun teacherCourseSubjectLabel(courseTitle: String): String {
    val separators = listOf("—", "–", "-")
    val cut = separators.firstOrNull { courseTitle.contains(it) }?.let { courseTitle.substringBefore(it).trim() }
    return cut?.takeIf { it.isNotBlank() } ?: courseTitle
}

@Composable
fun teacherGradeShortLabel(grade: Grade): String = when (grade) {
    Grade.Grade10 -> stringResource(R.string.tc03_grade_short_10)
    Grade.Grade11 -> stringResource(R.string.tc03_grade_short_11)
    Grade.Baccalaureate -> stringResource(R.string.tc03_grade_short_bac)
}

@Composable
fun TeacherClassSubjectVisual(modifier: Modifier = Modifier.height(72.dp)) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .background(Brush.linearGradient(listOf(colors.primaryContainer, colors.primary.copy(alpha = 0.28f)))),
    ) {
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
                .padding(horizontal = 24.dp),
        ) {
            val path = Path().apply {
                moveTo(0f, size.height * 0.82f)
                quadraticTo(size.width / 2f, size.height * 0.08f, size.width, size.height * 0.82f)
            }
            drawPath(
                path = path,
                color = colors.primary,
                style = Stroke(width = 7f, cap = StrokeCap.Round),
            )
        }
    }
}

@Composable
fun TeacherStepSegmentBar(currentStep: Int, totalSteps: Int = 3, modifier: Modifier = Modifier) {
    val colors = EduTheme.colors
    Row(
        horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier.fillMaxWidth(),
    ) {
        repeat(totalSteps) { index ->
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(5.dp)
                    .background(
                        color = if (index < currentStep) colors.primary else colors.border,
                        shape = RoundedCornerShape(Radius.pill),
                    ),
            )
        }
    }
}

@Composable
fun TeacherVideoMediaWell(
    durationLabel: String? = null,
    modifier: Modifier = Modifier.height(148.dp),
) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .background(Brush.verticalGradient(listOf(colors.primary, colors.primary.copy(alpha = 0.82f)))),
    ) {
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp)
                .padding(horizontal = 28.dp),
        ) {
            val path = Path().apply {
                moveTo(0f, size.height * 0.82f)
                quadraticTo(size.width / 2f, size.height * 0.12f, size.width, size.height * 0.82f)
            }
            drawPath(
                path = path,
                color = colors.onPrimary.copy(alpha = 0.45f),
                style = Stroke(width = 5f, cap = StrokeCap.Round),
            )
        }
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(52.dp)
                .background(colors.surface, CircleShape),
        ) {
            Icon(
                imageVector = Icons.Filled.PlayArrow,
                contentDescription = null,
                tint = colors.primary,
                modifier = Modifier.size(Sizing.iconLg),
            )
        }
        if (!durationLabel.isNullOrBlank()) {
            Text(
                text = durationLabel,
                style = EduTheme.typography.caption,
                color = colors.onPrimary,
                modifier = Modifier
                    .align(Alignment.BottomStart)
                    .padding(Spacing.xs)
                    .background(colors.scrim, RoundedCornerShape(Radius.pill))
                    .padding(horizontal = Spacing.xs, vertical = Spacing.xxs),
            )
        }
    }
}

@Composable
fun TeacherPdfMediaWell(modifier: Modifier = Modifier.height(150.dp)) {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .background(colors.background, RoundedCornerShape(Radius.sm))
            .border(Sizing.hairline, colors.border, RoundedCornerShape(Radius.sm))
            .padding(Spacing.sm),
    ) {
        Canvas(modifier = Modifier.size(92.dp, 100.dp)) {
            val page = Path().apply {
                addRoundRect(
                    RoundRect(
                        left = size.width * 0.18f,
                        top = size.height * 0.08f,
                        right = size.width * 0.82f,
                        bottom = size.height * 0.88f,
                        radiusX = 8.dp.toPx(),
                        radiusY = 8.dp.toPx(),
                    ),
                )
            }
            drawPath(page, color = colors.surface)
            drawPath(page, color = colors.border, style = Stroke(width = 2.dp.toPx()))
            val fold = Path().apply {
                moveTo(size.width * 0.58f, size.height * 0.08f)
                lineTo(size.width * 0.82f, size.height * 0.08f)
                lineTo(size.width * 0.82f, size.height * 0.26f)
                close()
            }
            drawPath(fold, color = colors.primaryContainer)
        }
        Text(
            text = stringResource(R.string.tc04_content_type_pdf),
            style = EduTheme.typography.caption.copy(fontWeight = FontWeight.ExtraBold),
            color = colors.primary,
            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = Spacing.sm),
        )
    }
}

@Composable
fun TeacherAiPipelineVisual(
    stages: List<LessonProcessingStageState>,
    modifier: Modifier = Modifier.height(110.dp),
) {
    val colors = EduTheme.colors
    val complete = stages.count {
        it.status == LessonProcessingStageStatus.Complete || it.status == LessonProcessingStageStatus.Skipped
    }
    val failed = stages.any { it.status == LessonProcessingStageStatus.Failed }
    val filled = when {
        failed -> complete.coerceAtMost(2)
        complete >= 4 -> 3
        complete >= 2 -> 2
        complete >= 1 -> 1
        else -> 0
    }
    val outlined = if (!failed && filled < 3) filled else -1
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .background(colors.aiAccentContainer, RoundedCornerShape(Radius.md)),
    ) {
        Canvas(modifier = Modifier.fillMaxWidth().height(50.dp).padding(horizontal = 36.dp)) {
            val cy = size.height / 2f
            val r = 8.dp.toPx()
            val xs = listOf(size.width * 0.12f, size.width * 0.5f, size.width * 0.88f)
            for (i in 0 until 2) {
                drawLine(
                    color = colors.aiAccent,
                    start = Offset(xs[i] + r, cy),
                    end = Offset(xs[i + 1] - r, cy),
                    strokeWidth = 2.dp.toPx(),
                    cap = StrokeCap.Round,
                )
            }
            xs.forEachIndexed { index, x ->
                val center = Offset(x, cy)
                when {
                    failed && index == filled -> drawCircle(color = colors.danger, radius = r, center = center)
                    index < filled -> drawCircle(color = colors.aiAccent, radius = r, center = center)
                    index == outlined -> drawCircle(
                        color = colors.aiAccent,
                        radius = r,
                        center = center,
                        style = Stroke(width = 2.dp.toPx()),
                    )
                    else -> drawCircle(
                        color = colors.border,
                        radius = r,
                        center = center,
                        style = Stroke(width = 2.dp.toPx()),
                    )
                }
            }
        }
    }
}

@Composable
fun teacherCourseStatusLabel(status: TeacherCourseStatus): String = when (status) {
    TeacherCourseStatus.Draft -> stringResource(R.string.tc03_status_draft)
    TeacherCourseStatus.Published -> stringResource(R.string.tc03_status_published)
    TeacherCourseStatus.Archived -> stringResource(R.string.tc03_status_archived)
}

/** TC-04/05/06. [TeacherLessonStatus] deliberately reuses none of [TeacherCourseStatus]'s labels — a lesson's own three states read differently from a course's Draft/Published/Archived. */
@Composable
fun teacherLessonStatusLabel(status: TeacherLessonStatus): String = when (status) {
    TeacherLessonStatus.Draft -> stringResource(R.string.tc04_lesson_status_draft)
    TeacherLessonStatus.Processing -> stringResource(R.string.tc04_lesson_status_processing)
    TeacherLessonStatus.Published -> stringResource(R.string.tc04_lesson_status_published)
}

@Composable
fun lessonContentTypeLabel(type: LessonContentType): String = when (type) {
    LessonContentType.Pdf -> stringResource(R.string.tc04_content_type_pdf)
    LessonContentType.Video -> stringResource(R.string.tc04_content_type_video)
}

/** TC-06's five pipeline stages, in their one fixed order. */
@Composable
fun processingStageLabel(stage: LessonProcessingStage): String = when (stage) {
    LessonProcessingStage.Extract -> stringResource(R.string.tc06_stage_extract)
    LessonProcessingStage.Chunk -> stringResource(R.string.tc06_stage_chunk)
    LessonProcessingStage.Index -> stringResource(R.string.tc06_stage_index)
    LessonProcessingStage.Quiz -> stringResource(R.string.tc06_stage_quiz)
    LessonProcessingStage.Narrate -> stringResource(R.string.tc06_stage_narrate)
}

@Composable
fun processingStageStatusLabel(status: LessonProcessingStageStatus): String = when (status) {
    LessonProcessingStageStatus.Pending -> stringResource(R.string.tc06_stage_status_pending)
    LessonProcessingStageStatus.Running -> stringResource(R.string.tc06_stage_status_running)
    LessonProcessingStageStatus.Complete -> stringResource(R.string.tc06_stage_status_complete)
    LessonProcessingStageStatus.Failed -> stringResource(R.string.tc06_stage_status_failed)
    LessonProcessingStageStatus.Skipped -> stringResource(R.string.tc06_stage_status_skipped)
}

/** TC-04's compact "what's happening right now" caption for a Processing lesson row — e.g. "جارٍ الفهرسة" or, once failed, the stage's own error label. */
@Composable
fun processingActiveStageCaption(stage: LessonProcessingStage, status: LessonProcessingStageStatus): String =
    if (status == LessonProcessingStageStatus.Failed) {
        stringResource(R.string.tc04_lesson_processing_failed_caption)
    } else {
        stringResource(R.string.tc04_lesson_processing_active_caption, processingStageLabel(stage))
    }

/** TC-05. A mock byte count, formatted as MB — never a real file size, but expressed the same way a real one would be. */
@Composable
fun megabytesLabel(bytes: Long): String {
    val formatted = String.format(Locale.US, "%.1f", bytes / 1_000_000.0)
    return stringResource(R.string.tc05_size_mb, numeral(formatted))
}

@Composable
fun lessonUploadStageLabel(stage: LessonUploadStage): String = when (stage) {
    LessonUploadStage.Preparing -> stringResource(R.string.tc05_upload_stage_preparing)
    LessonUploadStage.Uploading -> stringResource(R.string.tc05_upload_stage_uploading)
    LessonUploadStage.Paused -> stringResource(R.string.tc05_upload_stage_paused)
    LessonUploadStage.Completed -> stringResource(R.string.tc05_upload_stage_completed)
}

/** TC-07. */
@Composable
fun aiReviewStatusLabel(status: AiReviewStatus): String = when (status) {
    AiReviewStatus.Unreviewed -> stringResource(R.string.tc07_review_unreviewed)
    AiReviewStatus.Accepted -> stringResource(R.string.tc07_review_accepted)
    AiReviewStatus.Rejected -> stringResource(R.string.tc07_review_rejected)
}

@Composable
fun lessonInsightKindLabel(kind: LessonInsightKind): String = when (kind) {
    LessonInsightKind.DifficultConcept -> stringResource(R.string.tc07_insight_kind_difficult)
    LessonInsightKind.PrerequisiteReminder -> stringResource(R.string.tc07_insight_kind_prerequisite)
    LessonInsightKind.MisconceptionWarning -> stringResource(R.string.tc07_insight_kind_misconception)
}

/** TC-09. */
@Composable
fun voiceProfileStatusLabel(status: VoiceProfileStatus): String = when (status) {
    VoiceProfileStatus.NotReady -> stringResource(R.string.tc09_status_not_ready)
    VoiceProfileStatus.ReadyToGenerate -> stringResource(R.string.tc09_status_ready_to_generate)
    VoiceProfileStatus.Processing -> stringResource(R.string.tc09_status_processing)
    VoiceProfileStatus.Ready -> stringResource(R.string.tc09_status_ready)
    VoiceProfileStatus.Failed -> stringResource(R.string.tc09_status_failed)
}

@Composable
fun voiceSampleQualityLabel(status: VoiceSampleQualityStatus): String = when (status) {
    VoiceSampleQualityStatus.Good -> stringResource(R.string.tc09_quality_good)
    VoiceSampleQualityStatus.NeedsImprovement -> stringResource(R.string.tc09_quality_needs_improvement)
}

@Composable
fun voiceSampleSourceTypeLabel(type: VoiceSampleSourceType): String = when (type) {
    VoiceSampleSourceType.Recorded -> stringResource(R.string.tc09_source_recorded)
    VoiceSampleSourceType.Uploaded -> stringResource(R.string.tc09_source_uploaded)
}

/** TC-10. */
@Composable
fun teacherQuizStatusLabel(status: TeacherQuizStatus): String = when (status) {
    TeacherQuizStatus.Draft -> stringResource(R.string.tc04_lesson_status_draft)
    TeacherQuizStatus.Published -> stringResource(R.string.tc04_lesson_status_published)
}

/** Only the three types TC-10 actually supports this slice — [QuestionType.GapFill] has no builder UI yet. */
@Composable
fun questionTypeLabel(type: QuestionType): String = when (type) {
    QuestionType.MultipleChoice -> stringResource(R.string.tc10_type_multiple_choice)
    QuestionType.TrueFalse -> stringResource(R.string.tc10_type_true_false)
    QuestionType.ShortAnswer -> stringResource(R.string.tc10_type_short_answer)
    QuestionType.GapFill -> stringResource(R.string.tc10_type_gap_fill)
}

/** TC-12. */
@Composable
fun studentMonitoringStatusLabel(status: StudentMonitoringStatus): String = when (status) {
    StudentMonitoringStatus.Active -> stringResource(R.string.tc12_status_active)
    StudentMonitoringStatus.NeedsAttention -> stringResource(R.string.tc12_status_needs_attention)
    StudentMonitoringStatus.Inactive -> stringResource(R.string.tc12_status_inactive)
}

@Composable
fun studentFlagLabel(flag: StudentFlag): String = when (flag) {
    StudentFlag.LowProgress -> stringResource(R.string.tc12_flag_low_progress)
    StudentFlag.QuizRisk -> stringResource(R.string.tc12_flag_quiz_risk)
    StudentFlag.MissingWork -> stringResource(R.string.tc12_flag_missing_work)
}

/** TC-13. */
@Composable
fun attendanceStatusLabel(status: AttendanceStatus): String = when (status) {
    AttendanceStatus.Present -> stringResource(R.string.tc13_attendance_present)
    AttendanceStatus.Absent -> stringResource(R.string.tc13_attendance_absent)
    AttendanceStatus.Late -> stringResource(R.string.tc13_attendance_late)
}

@Composable
fun activityKindLabel(kind: TeacherActivityKind): String = when (kind) {
    TeacherActivityKind.LessonCompleted -> stringResource(R.string.tc13_activity_lesson_completed)
    TeacherActivityKind.QuizSubmitted -> stringResource(R.string.tc13_activity_quiz_submitted)
    TeacherActivityKind.CourseOpened -> stringResource(R.string.tc13_activity_course_opened)
    TeacherActivityKind.AssignmentMissed -> stringResource(R.string.tc13_activity_assignment_missed)
    TeacherActivityKind.ProjectSubmitted -> stringResource(R.string.tc13_activity_project_submitted)
}

/** TC-14. Deliberately reuses none of [teacherQuizStatusLabel]'s Draft/Published strings — a grade's publication state reads differently from a quiz's. */
@Composable
fun gradePublicationStatusLabel(status: GradePublicationStatus): String = when (status) {
    GradePublicationStatus.Draft -> stringResource(R.string.tc14_status_draft)
    GradePublicationStatus.Published -> stringResource(R.string.tc14_status_published)
}

/** TC-15. */
@Composable
fun funnelStageLabel(kind: FunnelStageKind): String = when (kind) {
    FunnelStageKind.Enrolled -> stringResource(R.string.tc15_funnel_enrolled)
    FunnelStageKind.Started -> stringResource(R.string.tc15_funnel_started)
    FunnelStageKind.LessonsProgressed -> stringResource(R.string.tc15_funnel_lessons_progressed)
    FunnelStageKind.QuizAttempted -> stringResource(R.string.tc15_funnel_quiz_attempted)
    FunnelStageKind.CourseCompleted -> stringResource(R.string.tc15_funnel_course_completed)
}

@Composable
fun atRiskReasonLabel(reason: AtRiskReason): String = when (reason) {
    AtRiskReason.LowProgress -> stringResource(R.string.tc15_risk_low_progress)
    AtRiskReason.LowQuizPerformance -> stringResource(R.string.tc15_risk_low_quiz)
    AtRiskReason.MissingWork -> stringResource(R.string.tc15_risk_missing_work)
    AtRiskReason.Inactivity -> stringResource(R.string.tc15_risk_inactivity)
    AtRiskReason.PoorAttendance -> stringResource(R.string.tc15_risk_poor_attendance)
}

/** TC-17. Deliberately reuses none of [teacherQuizStatusLabel]'s/[gradePublicationStatusLabel]'s Draft/Published strings — a project's own publication state reads differently again. */
@Composable
fun teacherProjectStatusLabel(status: TeacherProjectStatus): String = when (status) {
    TeacherProjectStatus.Draft -> stringResource(R.string.tc17_status_draft)
    TeacherProjectStatus.Published -> stringResource(R.string.tc17_status_published)
}

@Composable
fun teacherProjectMediaKindLabel(kind: TeacherProjectMediaKind): String = when (kind) {
    TeacherProjectMediaKind.Image -> stringResource(R.string.tc17_media_image)
    TeacherProjectMediaKind.Document -> stringResource(R.string.tc17_media_document)
    TeacherProjectMediaKind.Video -> stringResource(R.string.tc17_media_video)
}

/** Reuses [SafetySeverity] verbatim (PJ-12's own Caution/Important scale) — only the short text label is new, since PJ-12 itself only ever shows severity via icon/color. */
@Composable
fun teacherSafetySeverityLabel(severity: SafetySeverity): String = when (severity) {
    SafetySeverity.Caution -> stringResource(R.string.tc17_safety_caution)
    SafetySeverity.Important -> stringResource(R.string.tc17_safety_important)
}

/** TC-18. Kept entirely separate from [aiPreReviewAvailabilityLabel] — see [ProjectReviewStatus]'s own doc comment for why teacher-review state and AI availability never mix. */
@Composable
fun projectReviewStatusLabel(status: ProjectReviewStatus): String = when (status) {
    ProjectReviewStatus.AwaitingReview -> stringResource(R.string.tc18_status_awaiting)
    ProjectReviewStatus.InReview -> stringResource(R.string.tc18_status_in_review)
    ProjectReviewStatus.Reviewed -> stringResource(R.string.tc18_status_reviewed)
}

@Composable
fun aiPreReviewAvailabilityLabel(availability: AiPreReviewAvailability): String = when (availability) {
    AiPreReviewAvailability.Ready -> stringResource(R.string.tc18_ai_ready)
    AiPreReviewAvailability.Unavailable -> stringResource(R.string.tc18_ai_unavailable)
}
