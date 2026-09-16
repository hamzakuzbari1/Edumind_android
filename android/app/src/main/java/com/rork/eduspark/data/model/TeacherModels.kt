package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-01 · Teacher Setup Wizard / TC-02 · Teacher Dashboard / TC-03 · Courses List.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Teacher setup identity, teaching selections, qualifications, and supported experience fields
 * can be backed by FastAPI. Documents, pricing, voice, and the broader teacher workspace remain
 * explicitly local/mock until their dedicated integration batches.
 *
 * [TeacherSetupState.completedStepIds] drives only the current visual wizard. Server data is
 * used to reconstruct a safe resume point, while [SessionUser.hasCompletedOnboarding] remains
 * authoritative for incomplete versus complete setup.
 */
enum class TeacherSetupStepId { Identity, SubjectsGrades, Qualifications, Experience, Documents, Pricing, VoiceSample }

/**
 * [bio]/[whyStudyWithMe] back TC-16's "About" section — added directly onto the same identity
 * record TC-01 already saves through [com.rork.eduspark.data.repository.TeacherRepository.saveIdentity],
 * rather than a second, disconnected profile-content model. TC-01's own wizard screen never
 * shows these two fields, so they simply start blank until a teacher first sets them from TC-16
 * — no TC-01 UI change required, and no field ever disagrees between the two screens because
 * there is only ever the one saved record.
 */
data class TeacherIdentityInfo(
    val displayName: String = "",
    val headline: String = "",
    val bio: String = "",
    val whyStudyWithMe: String = "",
    /** Absolute or relative avatar URL from setup status (`image_url` / `avatar_url`). */
    val photoUrl: String? = null,
)

/** Remote professional document from teacher portfolio (file_url may be private download path). */
data class TeacherProfessionalDocument(
    val id: String,
    val title: String,
    val documentType: String,
    /** Backend media reference — resolve via MediaUrlResolver at open time. */
    val fileUrl: String,
    val originalFilename: String? = null,
    val mimeType: String? = null,
    val sortOrder: Int = 0,
)

/** [grades] reuses [Grade] verbatim — the same Syrian-secondary taxonomy SO-01 already models — rather than a second grade concept for "which grades this teacher teaches". */
data class TeacherSubjectsGrades(
    val subjectIds: Set<String> = emptySet(),
    val grades: Set<Grade> = emptySet(),
)

/** TC-01 step 3. [year] is optional and never verified — no real document/credential check exists in this slice. */
data class TeacherQualification(
    val id: String,
    val title: String,
    val institution: String,
    val year: String? = null,
)

data class TeacherExperienceInfo(
    val yearsOfExperience: Int? = null,
    val description: String = "",
    val teachingModes: Set<String> = emptySet(),
)

enum class TeacherDocumentKind { Identity, Qualification }

/**
 * TC-01 step 5 — interaction shape only. [fileName] null means nothing has been mock-selected
 * yet; a non-null value is an honest MOCK label, never a real URI, and nothing here is ever
 * uploaded.
 */
data class TeacherSetupDocument(
    val id: String,
    val kind: TeacherDocumentKind,
    val labelHint: String,
    val fileName: String? = null,
)

data class TeacherPricingInfo(
    val sessionPriceLabel: String = "",
    val currencyLabel: String = "",
)

enum class VoiceSampleState { NotRecorded, Recorded }

/**
 * TC-01 step 7 — setup only, never a real recording; the real voice system connects later.
 * [durationLabel] is display metadata, the same MOCK convention [ProjectReflection.durationLabel]
 * already uses.
 */
data class TeacherVoiceSample(
    val state: VoiceSampleState = VoiceSampleState.NotRecorded,
    val durationLabel: String? = null,
)

data class TeacherSetupState(
    val teacherId: String,
    val identity: TeacherIdentityInfo = TeacherIdentityInfo(),
    val subjectsGrades: TeacherSubjectsGrades = TeacherSubjectsGrades(),
    val qualifications: List<TeacherQualification> = emptyList(),
    val experience: TeacherExperienceInfo = TeacherExperienceInfo(),
    val documents: List<TeacherSetupDocument> = emptyList(),
    /** Remote professional documents from portfolio (authenticated open via MediaUrlResolver). */
    val professionalDocuments: List<TeacherProfessionalDocument> = emptyList(),
    val pricing: TeacherPricingInfo = TeacherPricingInfo(),
    val voiceSample: TeacherVoiceSample = TeacherVoiceSample(),
    val completedStepIds: Set<TeacherSetupStepId> = emptySet(),
)

enum class TeacherWorkItemKind { LessonProcessingFailed, SubmissionAwaitingReview, DraftLesson, UnreadMessage }
enum class TeacherWorkItemUrgency { Urgent, Normal }

/**
 * TC-02. Most work items in this slice still have no built destination — see
 * [com.rork.eduspark.ui.screens.teacher.TeacherComingSoonDialog]'s own doc comment for why
 * tapping one falls back to that honest placeholder. The one exception: a
 * [TeacherWorkItemKind.LessonProcessingFailed] item that names a real, currently-Processing
 * lesson carries [courseId]/[lessonId] so the dashboard can open TC-06 directly instead —
 * never a fabricated link, only ever a genuine one.
 */
data class TeacherWorkItem(
    val id: String,
    val kind: TeacherWorkItemKind,
    val title: String,
    val reason: String,
    val contextLabel: String,
    val statusLabel: String,
    val urgency: TeacherWorkItemUrgency,
    val courseId: String? = null,
    val lessonId: String? = null,
)

/** TC-02. [headlineMetricLabel] is the one dominant number the Screen Inventory calls for — never one of several equally-loud stat cards. */
data class TeacherDashboardSummary(
    val headlineMetricLabel: String,
    val activeStudentsCount: Int,
    val lessonsProcessingCount: Int,
    val unreadMessagesCount: Int,
    val courseCount: Int,
    val workItems: List<TeacherWorkItem>,
)

enum class TeacherCourseStatus { Draft, Published, Archived }

data class TeacherCourseSummary(
    val id: String,
    val title: String,
    val subjectId: String,
    val subjectTitle: String,
    val grade: Grade,
    val studentCount: Int,
    val lessonCount: Int,
    val status: TeacherCourseStatus,
)

data class TeacherCourseFormSubject(
    val id: String,
    val name: String,
    val grade: Grade,
)

data class TeacherCourseCreateRequest(
    val title: String,
    val subjectId: String,
    val subjectTitle: String,
    val grade: Grade,
    val description: String? = null,
    val published: Boolean = true,
)

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-04 · Course Detail / TC-05 · Lesson Upload / TC-06 · Lesson Processing Status.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [TeacherLesson] is the one canonical lesson record every one of the three screens above
 * reads and, where they may, writes — never a per-screen copy. [TeacherLesson.status] is
 * always derived from real state: [TeacherLessonStatus.Draft] until a mock upload finishes,
 * [TeacherLessonStatus.Processing] from the moment it does until every stage
 * [TeacherLessonProcessingState] tracks finishes, then [TeacherLessonStatus.Published] — set
 * in exactly one place, [com.rork.eduspark.data.repository.mock.MockTeacherRepository], so
 * TC-04's list and TC-02's `lessonsProcessingCount` can never disagree about which lessons are
 * still processing.
 */
enum class LessonContentType { Pdf, Video }
enum class TeacherLessonStatus { Draft, Processing, Published }

data class TeacherLesson(
    val id: String,
    val courseId: String,
    val title: String,
    val order: Int,
    val contentType: LessonContentType,
    val status: TeacherLessonStatus,
    /** Video runtime or similar — display metadata only, never present for a PDF. */
    val durationLabel: String? = null,
    val updatedLabel: String? = null,
)

/** TC-06's five-stage pipeline, always evaluated in this order. Not every lesson runs every stage — see [LessonProcessingStageStatus.Skipped]. */
enum class LessonProcessingStage { Extract, Chunk, Index, Quiz, Narrate }

enum class LessonProcessingStageStatus { Pending, Running, Complete, Failed, Skipped }

data class LessonProcessingStageState(
    val stage: LessonProcessingStage,
    val status: LessonProcessingStageStatus,
    /** Only ever non-null when [status] is [LessonProcessingStageStatus.Failed] — a friendly, non-technical explanation, never a stack trace. */
    val errorLabel: String? = null,
)

enum class LessonProcessingOverallStatus { Running, Failed, Completed }

/**
 * TC-06. One live record per lesson, held by
 * [com.rork.eduspark.data.repository.mock.MockTeacherRepository] rather than any screen's
 * ViewModel, so leaving TC-06 and reopening it (or reaching the same lesson from TC-02's work
 * queue) always shows the true current pipeline state, not a restarted one.
 *
 * [overallStatus] is computed, never stored redundantly: a lesson is
 * [LessonProcessingOverallStatus.Failed] the moment any stage fails, otherwise
 * [LessonProcessingOverallStatus.Completed] once every non-skipped stage is complete,
 * otherwise still [LessonProcessingOverallStatus.Running]. This is the one place that
 * decision is made — never re-derived differently on another screen.
 */
data class TeacherLessonProcessingState(
    val lessonId: String,
    val courseId: String,
    val stages: List<LessonProcessingStageState>,
    /** Whether this pipeline's one possible deterministic failure has already been retried past — internal bookkeeping, never read by UI. */
    val hasRetried: Boolean = false,
) {
    val overallStatus: LessonProcessingOverallStatus
        get() {
            val relevant = stages.filter { it.status != LessonProcessingStageStatus.Skipped }
            return when {
                stages.any { it.status == LessonProcessingStageStatus.Failed } -> LessonProcessingOverallStatus.Failed
                relevant.isNotEmpty() && relevant.all { it.status == LessonProcessingStageStatus.Complete } -> LessonProcessingOverallStatus.Completed
                else -> LessonProcessingOverallStatus.Running
            }
        }
}

enum class LessonUploadStage { Preparing, Uploading, Paused, Completed }

/**
 * TC-05. At most one in-flight mock upload per course, held by
 * [com.rork.eduspark.data.repository.mock.MockTeacherRepository] — never inside TC-05's own
 * ViewModel — precisely so the upload keeps its place if the teacher navigates away and the
 * ViewModel is recreated; a new instance simply reads whatever [stage]/[uploadedBytes] this
 * record is already at and resumes ticking from there. Nothing here is a real file: [mockFileName]
 * and [mockTotalBytes] are honest MOCK labels, never a real URI or a real byte stream.
 */
data class TeacherLessonUploadDraft(
    val courseId: String,
    val contentType: LessonContentType,
    val mockFileName: String,
    val mockTotalBytes: Long,
    val title: String,
    val order: Int,
    val generateQuiz: Boolean,
    val generateNarration: Boolean,
    val indexForTutor: Boolean,
    val uploadedBytes: Long = 0L,
    val stage: LessonUploadStage = LessonUploadStage.Preparing,
    /** Set the moment [stage] becomes [LessonUploadStage.Completed] — the id TC-05 hands to TC-06, never invented client-side. */
    val createdLessonId: String? = null,
)

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-07 · Lesson Editor / TC-08 · Lesson Preview.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Nothing here duplicates an existing model. Quiz questions reuse [QuizQuestion]/[QuizOption]
 * verbatim — the exact shape ST-06…ST-09's [com.rork.eduspark.data.repository.QuizRepository]
 * already uses — because "a generated question awaiting teacher review" is the same question
 * shape a student later answers, plus one field that's genuinely new: [AiReviewStatus].
 */

/** One editable segment of a lesson's extracted text — nothing else in the app models this yet. */
data class TeacherLessonChunk(
    val id: String,
    val order: Int,
    val text: String,
)

/**
 * Whether a teacher has looked at one piece of AI output and decided. Never silently implied
 * by "not rejected" — [TeacherLessonEditorState]'s publish gate requires every generated
 * question/insight to have explicitly left [Unreviewed], Accepted or Rejected, never assumed.
 */
enum class AiReviewStatus { Unreviewed, Accepted, Rejected }

/**
 * TC-07's generated-quiz row. [reviewStatus] is the only new field over plain [QuizQuestion] —
 * editing [question]'s text/options/answer/explanation replaces it in place and leaves
 * [reviewStatus] untouched, so a teacher's correction to AI-authored wording is never itself
 * re-marked as freshly AI-generated or silently reset to unreviewed.
 */
data class TeacherGeneratedQuestion(
    val question: QuizQuestion,
    val reviewStatus: AiReviewStatus = AiReviewStatus.Unreviewed,
)

enum class LessonInsightKind { DifficultConcept, PrerequisiteReminder, MisconceptionWarning }

/** TC-07. A short generated observation about the lesson — no editing UI in this slice, only Accept/Reject (see TC-07's own screen doc comment for why). */
data class TeacherLessonInsight(
    val id: String,
    val kind: LessonInsightKind,
    val text: String,
    val reviewStatus: AiReviewStatus = AiReviewStatus.Unreviewed,
)

/**
 * TC-07/TC-08's one canonical per-lesson editorial record, held by
 * [com.rork.eduspark.data.repository.mock.MockTeacherRepository] exactly like
 * [TeacherSetupState] is — never only in a ViewModel, so it survives navigating to TC-08 and
 * back, and ViewModel recreation.
 *
 * Publish gate (enforced by [com.rork.eduspark.data.repository.TeacherRepository.submitLessonForPublish],
 * mirrored client-side so TC-07 can show why publish is disabled): [extractedText] non-blank
 * (has been saved at least once), at least one [chunks] entry with non-blank
 * [TeacherLessonChunk.text], and every [generatedQuestions]/[insights] entry has left
 * [AiReviewStatus.Unreviewed] — Accepted or Rejected, never requiring universal acceptance.
 * TC-08 renders only [AiReviewStatus.Accepted] questions/insights.
 */
data class TeacherLessonEditorState(
    val lessonId: String,
    val courseId: String,
    val extractedText: String = "",
    val chunks: List<TeacherLessonChunk> = emptyList(),
    val generatedQuestions: List<TeacherGeneratedQuestion> = emptyList(),
    val insights: List<TeacherLessonInsight> = emptyList(),
)

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-09 · Voice Profile.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [TeacherVoiceProfile] is deliberately a different model from [TeacherVoiceSample] (TC-01's
 * single-flag "has this teacher recorded anything yet" step field) rather than a competing
 * one — TC-01 keeps using [TeacherVoiceSample] completely unchanged, and
 * [com.rork.eduspark.data.repository.mock.MockTeacherRepository.saveVoiceSample] (TC-01's own
 * write path) is what keeps this profile's sample list in sync with it, so the two screens
 * never disagree about whether this teacher has a recording.
 */
enum class VoiceSampleSourceType { Recorded, Uploaded }
enum class VoiceSampleQualityStatus { Good, NeedsImprovement }

data class TeacherVoiceProfileSample(
    val id: String,
    val sourceType: VoiceSampleSourceType,
    /** Only ever set for [VoiceSampleSourceType.Uploaded] — an honest MOCK label, never a real URI. */
    val fileName: String? = null,
    val durationLabel: String,
    val qualityStatus: VoiceSampleQualityStatus,
    val qualityFeedback: String,
)

enum class VoiceProfileStatus { NotReady, ReadyToGenerate, Processing, Ready, Failed }

/** TC-09. One profile per teacher, held by [com.rork.eduspark.data.repository.mock.MockTeacherRepository]. */
data class TeacherVoiceProfile(
    val teacherId: String,
    val consentGranted: Boolean = false,
    val samples: List<TeacherVoiceProfileSample> = emptyList(),
    val profileStatus: VoiceProfileStatus = VoiceProfileStatus.NotReady,
    val clonedNarrationEnabled: Boolean = false,
    /** Internal bookkeeping only, same shape as [TeacherLessonProcessingState.hasRetried] — whether this profile's one deterministic generation failure has already been retried past. */
    val hasRetriedGeneration: Boolean = false,
)

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-10 · Quiz Builder / TC-11 · Quiz Results.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [TeacherQuizQuestion] wraps [QuizQuestion] verbatim rather than inventing a second,
 * incompatible question shape — the exact same [QuizQuestion]/[QuizOption]/[QuestionType]
 * ST-06…ST-09's [com.rork.eduspark.data.repository.QuizRepository] already uses. Only
 * [TeacherQuizQuestion.points] and [TeacherQuizQuestion.isAiOrigin] are genuinely new: neither
 * points nor per-question AI provenance exists anywhere else in the quiz domain, because a
 * student-facing [Quiz] never needed either. A teacher-authored [TeacherQuiz] is a distinct
 * model from [Quiz] on purpose — [Quiz] is inherently one-lesson-scoped (`lessonId`,
 * `feedbackMode`, `timerSeconds`, ST-06 runner concerns) while [TeacherQuiz] is course-scoped
 * and has none of those; forcing it into [Quiz]'s shape would mean faking fields that don't
 * apply, not genuine reuse.
 */
enum class TeacherQuizStatus { Draft, Published }

/**
 * [isAiOrigin] is set once, at creation (accepted from an AI bulk-import candidate, or typed by
 * the teacher), and never changes afterward — editing [question]'s text/options/answer later
 * never clears it and never sets it, so provenance survives an edit exactly as the spec
 * requires, and a teacher-authored question can never accidentally acquire it.
 */
data class TeacherQuizQuestion(
    val question: QuizQuestion,
    val points: Int,
    val isAiOrigin: Boolean = false,
)

/**
 * [totalPoints] is always derived from [questions] — never a second stored number that could
 * disagree with the questions actually in the quiz.
 */
data class TeacherQuiz(
    val id: String,
    val courseId: String,
    val courseTitle: String,
    val title: String,
    val instructions: String = "",
    val status: TeacherQuizStatus = TeacherQuizStatus.Draft,
    val questions: List<TeacherQuizQuestion> = emptyList(),
    /** Local mock duration. `15`, `30`, or `null` for unlimited. */
    val durationMinutes: Int? = 15,
    val passMarkPercent: Int = 60,
    val singleAttempt: Boolean = true,
) {
    val totalPoints: Int get() = questions.sumOf { it.points }
}

enum class TeacherQuizAttemptStatus { Completed, NotSubmitted }

/**
 * Teacher-manual essay grade attached to an existing [TeacherQuizAttempt].
 * Auto-scored question types still use [TeacherQuizAttempt.answers] only.
 */
data class TeacherEssayResponse(
    val questionId: String,
    val studentText: String,
    val pending: Boolean = true,
    val assignedMark: Int? = null,
    val teacherFeedback: String = "",
)

/**
 * TC-11. Auto-scored items still live in [answers]. Essay / ShortAnswer items that the Teacher
 * frontend grades by hand live in [essayResponses] — same attempt, not a second store.
 */
data class TeacherQuizAttempt(
    val studentId: String,
    val studentName: String,
    val status: TeacherQuizAttemptStatus,
    /** Null only for [TeacherQuizAttemptStatus.NotSubmitted]. */
    val submittedLabel: String? = null,
    /** questionId → whether this student answered it correctly. Empty for [TeacherQuizAttemptStatus.NotSubmitted]. */
    val answers: Map<String, Boolean> = emptyMap(),
    /** questionId → student essay text + teacher grade. Empty when the attempt has no essay items. */
    val essayResponses: Map<String, TeacherEssayResponse> = emptyMap(),
    /** Backend attempt id for essay grading API; null in pure mock fixtures. */
    val attemptId: String? = null,
) {
    val pendingEssayCount: Int get() = essayResponses.values.count { it.pending }
    val hasPendingEssay: Boolean get() = pendingEssayCount > 0

    fun firstPendingQuestionId(): String? = essayResponses.entries.firstOrNull { it.value.pending }?.key

    fun earnedPoints(questions: List<TeacherQuizQuestion>): Int {
        if (status != TeacherQuizAttemptStatus.Completed) return 0
        return questions.sumOf { row ->
            val essay = essayResponses[row.question.id]
            when {
                essay != null && essay.pending -> 0
                essay != null -> (essay.assignedMark ?: 0).coerceIn(0, row.points)
                answers[row.question.id] == true -> row.points
                else -> 0
            }
        }
    }

    fun scorePercent(quiz: TeacherQuiz): Int? {
        if (status != TeacherQuizAttemptStatus.Completed || hasPendingEssay || quiz.totalPoints <= 0) return null
        return (earnedPoints(quiz.questions) * 100) / quiz.totalPoints
    }
}

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-12 · Students List.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A lightweight wrapper, not a duplicated student profile — there is no existing "many
 * students, one teacher's roster" model anywhere else in the app to reuse ([StudentProfile] is
 * always the CURRENT student's own single record). [studentId]/[displayName] intentionally use
 * the same fixture identities [TeacherQuizAttempt] seeds for TC-11, so the two screens agree on
 * who a given student is — see [com.rork.eduspark.data.repository.mock.MockTeacherRepository]'s
 * own doc comment for the shared persona list this prepares TC-13 to key off later.
 */
enum class StudentMonitoringStatus { Active, NeedsAttention, Inactive }

enum class StudentFlag { LowProgress, QuizRisk, MissingWork }

data class TeacherStudentSummary(
    val studentId: String,
    val displayName: String,
    val courseId: String,
    val courseTitle: String,
    val grade: Grade,
    val progressPercent: Float,
    val lastActiveLabel: String,
    val status: StudentMonitoringStatus,
    val flags: Set<StudentFlag> = emptySet(),
)

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-13 · Student Profile — Teacher View.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deliberately NOT one big persisted "student detail" model — the header/overview/quiz-history
 * sections are all derived at read time from [TeacherStudentSummary] (TC-12), [TeacherQuiz]/
 * [TeacherQuizAttempt] (TC-10/TC-11) and attendance/activity below, never a second copy of any
 * of those numbers. Only the genuinely mutable, teacher-authored pieces — private notes, sent
 * parent notes — get their own persisted model.
 */
enum class AttendanceStatus { Present, Absent, Late }

data class AttendanceRecord(val dateLabel: String, val status: AttendanceStatus)

/**
 * MOCK, deterministic per student — no real attendance system exists. [attendancePercent]
 * counts a [AttendanceStatus.Late] day as half credit, the same "not a strict pass/fail"
 * convention this app already applies to quiz partial credit; it is always derived from
 * [records], never a second stored figure.
 */
data class TeacherStudentAttendance(
    val studentId: String,
    val records: List<AttendanceRecord>,
) {
    val presentCount: Int get() = records.count { it.status == AttendanceStatus.Present }
    val absentCount: Int get() = records.count { it.status == AttendanceStatus.Absent }
    val lateCount: Int get() = records.count { it.status == AttendanceStatus.Late }
    val attendancePercent: Float
        get() = if (records.isEmpty()) 0f else (presentCount + lateCount * 0.5f) / records.size
}

enum class TeacherActivityKind { LessonCompleted, QuizSubmitted, CourseOpened, AssignmentMissed, ProjectSubmitted }

/**
 * TC-13's activity timeline row. Where an item genuinely happened — a quiz submission — it is
 * built from the same [TeacherQuizAttempt] TC-11 already reads, not a re-invented fact; only
 * the remaining lesson/course-open entries are deterministic MOCK filler with no other source
 * of truth to reuse.
 */
data class TeacherActivityItem(
    val id: String,
    val kind: TeacherActivityKind,
    val title: String,
    val dateLabel: String,
)

/** TC-13 private teacher notes — never exposed to any student/parent flow; see [com.rork.eduspark.data.repository.TeacherRepository.getPrivateNotes]'s own doc comment. */
data class TeacherPrivateNote(
    val id: String,
    val studentId: String,
    val text: String,
    val createdLabel: String,
)

/**
 * TC-13 "Send note to parent" — a distinct concept from [TeacherPrivateNote] on purpose: a
 * parent note is sent (mock), never edited/deleted afterward, and never silently folded into
 * the private-notes list.
 */
data class TeacherParentNote(
    val id: String,
    val studentId: String,
    val message: String,
    val sentLabel: String,
)

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-14 · Grades.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * A gradebook entry per (student, course) — distinct from [TeacherQuizAttempt]/TC-11 on
 * purpose (TC-11 stays quiz-specific analytics; this is the course-level gradebook). Only
 * [courseworkScore] is teacher-entered and persisted here; the quiz component of a student's
 * grade is always read fresh from [TeacherQuizAttempt] (see
 * [com.rork.eduspark.ui.screens.teacher.TeacherGradebookViewModel]'s own doc comment for the
 * derivation), never duplicated into this model.
 */
enum class GradePublicationStatus { Draft, Published }

data class TeacherGradeEntry(
    val studentId: String,
    val courseId: String,
    /** 0-100, teacher-entered; null means nothing entered yet — never defaulted to 0. */
    val courseworkScore: Int? = null,
    val comment: String = "",
    val publicationStatus: GradePublicationStatus = GradePublicationStatus.Draft,
)

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-15 · Teacher Analytics.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * No persisted analytics model — every field below is computed fresh, per request, from the
 * same [TeacherStudentSummary]/[TeacherQuiz]/[TeacherQuizAttempt]/attendance fixtures TC-12/
 * TC-11/TC-13 already read, filtered by [courseId]/[period]. See
 * [com.rork.eduspark.data.repository.mock.MockTeacherRepository.getAnalyticsSnapshot]'s own doc
 * comment for exactly how each figure is derived — nothing here is a hand-picked number.
 */
enum class AnalyticsPeriod { SevenDays, ThirtyDays, Term }

data class EngagementPoint(val label: String, val activeCount: Int)

enum class FunnelStageKind { Enrolled, Started, LessonsProgressed, QuizAttempted, CourseCompleted }

data class FunnelStage(val kind: FunnelStageKind, val count: Int)

enum class AtRiskReason { LowProgress, LowQuizPerformance, MissingWork, Inactivity, PoorAttendance }

data class AtRiskStudent(val student: TeacherStudentSummary, val reasons: Set<AtRiskReason>)

data class TeacherAnalyticsSnapshot(
    val totalEnrolled: Int,
    val engagement: List<EngagementPoint>,
    val funnel: List<FunnelStage>,
    val atRiskStudents: List<AtRiskStudent>,
)

/**
 * ══════════════════════════════════════════════════════════════════════════
 * TC-17 · Project Authoring / TC-18 · Project Review Queue.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [TeacherProject] is deliberately a NEW, distinct model from the student-facing [Project] —
 * the exact same "teacher-authored vs. student-facing shape" split [TeacherQuiz] already draws
 * from [Quiz]. [Project] has no Draft/Published state, no rubric, no team-size field and is
 * keyed to a fixed catalog a repository swap could not safely reshape; [TeacherProject] needs
 * all of those. Where [ProjectMedium]/[SafetySeverity] already model exactly what is needed —
 * physical-vs-digital, caution-vs-important — they are reused verbatim, never re-declared.
 *
 * The one fixture below that mirrors an existing student-facing project ("منبّه مستوى الماء" /
 * Water Alarm System) reuses the SAME id, `"water-alarm"`, as [com.rork.eduspark.data.repository.mock.MockProjectRepository]'s
 * own `CATALOG` entry — identity continuity only; this is a genuinely separate
 * [TeacherProject] row in [com.rork.eduspark.data.repository.mock.MockTeacherRepository], never
 * a shared mutable row with the student [Project] catalog, which this slice does not touch.
 */
enum class TeacherProjectStatus { Draft, Published }

data class TeacherProjectTask(
    val id: String,
    val order: Int,
    val title: String,
    val description: String = "",
)

/**
 * [contextLabel] is optional free-text ("الأسبوع الأول", "قبل العرض النهائي") — a due/context
 * hint only, never a real calendar date, matching every other MOCK date-ish label this app uses.
 */
data class TeacherProjectMilestone(
    val id: String,
    val order: Int,
    val title: String,
    val description: String = "",
    val contextLabel: String? = null,
    val tasks: List<TeacherProjectTask> = emptyList(),
)

/**
 * A project-level, weight-percentage rubric — deliberately NOT [RubricCriterion]/[RubricResult]
 * (PJ-06/PJ-07's task-scoped, small-integer-scale rubric, whose own doc comment explicitly says
 * a score there is "never a fabricated percentage"). [weightPercent] doubles as this
 * criterion's max point value in TC-18's /100 scoring — a criterion weighted 40% is worth 40
 * points, so [TeacherProject.rubricWeightTotal] and a submission's max score are always the
 * same number, never two independently-maintained ones.
 */
data class TeacherProjectRubricCriterion(
    val id: String,
    val title: String,
    val description: String = "",
    val weightPercent: Int,
)

/** Deliberately a distinct, simpler shape from [ProjectMaterial] — no live-cost/local-sourcing fields, since those are PJ-12 student-facing conveniences a teacher authoring a brand-new project has no fixture for yet. */
data class TeacherProjectMaterial(
    val id: String,
    val label: String,
    val quantityLabel: String? = null,
    val note: String? = null,
)

/** Reuses [SafetySeverity] verbatim — the exact Caution/Important scale PJ-12 already defines. */
data class TeacherProjectSafetyNote(
    val id: String,
    val text: String,
    val severity: SafetySeverity,
)

enum class TeacherProjectMediaKind { Image, Document, Video }

/** MOCK reference only — [label] is an honest placeholder filename, never a real URI or upload, the same boundary [SubmissionAttachment] already draws. */
data class TeacherProjectMediaItem(
    val id: String,
    val kind: TeacherProjectMediaKind,
    val label: String,
)

/**
 * [rubricWeightTotal] is always derived from [rubric] — never a second stored number. Publish
 * requires it to equal exactly 100 when [rubric] is non-empty; see
 * [com.rork.eduspark.data.repository.mock.MockTeacherRepository.canPublishTeacherProject]'s own
 * doc comment for the full gate.
 */
data class TeacherProject(
    val id: String,
    val title: String,
    val description: String = "",
    val courseId: String,
    val courseTitle: String,
    val grade: Grade,
    val deliverable: String = "",
    /** 1 = solo project; >1 = team-sized. No separate [ProjectMode] flag — the number itself carries that meaning. */
    val teamSize: Int = 1,
    val medium: ProjectMedium,
    val status: TeacherProjectStatus = TeacherProjectStatus.Draft,
    val milestones: List<TeacherProjectMilestone> = emptyList(),
    val rubric: List<TeacherProjectRubricCriterion> = emptyList(),
    val materials: List<TeacherProjectMaterial> = emptyList(),
    val safetyNotes: List<TeacherProjectSafetyNote> = emptyList(),
    val media: List<TeacherProjectMediaItem> = emptyList(),
) {
    val rubricWeightTotal: Int get() = rubric.sumOf { it.weightPercent }
}

/**
 * TC-18. [aiSuggestedScore] never changes once seeded — it is the AI's one-time MOCK suggestion,
 * advisory only. [isTeacherConfirmed] is the one explicit signal that the teacher has actually
 * acted on this criterion — via [com.rork.eduspark.data.repository.TeacherRepository.saveCriterionOverride]
 * ("Accept AI suggestion" passes [aiSuggestedScore] back in; "Override" passes the teacher's own
 * value) — and is never set any other way, including by
 * [com.rork.eduspark.data.repository.TeacherRepository.finalizeReview]: an untouched criterion
 * stays unconfirmed forever, Finalize included. [teacherScore] is only ever non-null alongside
 * [isTeacherConfirmed] = true; [TeacherProjectSubmission.finalScore] requires every criterion to
 * be confirmed, so a finalized review's total is always genuinely derived from teacher-confirmed
 * numbers, never a silently-defaulted AI one.
 */
data class TeacherCriterionReview(
    val criterionId: String,
    val criterionTitle: String,
    /** Max points for this criterion — always equal to its authored [TeacherProjectRubricCriterion.weightPercent]. */
    val maxScore: Int,
    val aiSuggestedScore: Int,
    val teacherScore: Int? = null,
    val isTeacherConfirmed: Boolean = false,
)

enum class ProjectReviewStatus { AwaitingReview, InReview, Reviewed }

/** Kept entirely separate from [ProjectReviewStatus] — see this file's own TC-18 doc comment for why AI availability is never folded into the teacher's own review state. */
enum class AiPreReviewAvailability { Ready, Unavailable }

/**
 * TC-18's one queue row / review record. [studentName] carries either a solo student's name or
 * a team label — this slice does not build a full [TeamMember]-style roster for teacher-authored
 * projects (out of scope; see this file's own TC-17 doc comment), so a single display string is
 * the honest minimum. [studentId] still matches a real TC-12/TC-13 persona id so a reviewer can
 * navigate to that student's profile.
 *
 * [aiStrengths]/[aiConcerns]/[aiSuggestedFeedback] are Jouri-marked, one-time MOCK content — see
 * [com.rork.eduspark.ui.screens.teacher.TeacherReviewDetailScreen]'s own doc comment for exactly
 * where the Jouri boundary is drawn. [teacherFeedback]/[teacherPrivateComment] are teacher-authored
 * and never Jouri-marked, even after being pre-filled from an AI suggestion the teacher accepted
 * unedited.
 */
data class TeacherProjectSubmission(
    val id: String,
    val projectId: String,
    val projectTitle: String,
    val studentId: String,
    val studentName: String,
    val milestoneTitle: String,
    val submittedLabel: String,
    val artifactSummary: String,
    val studentComment: String = "",
    val reviewStatus: ProjectReviewStatus = ProjectReviewStatus.AwaitingReview,
    val aiAvailability: AiPreReviewAvailability = AiPreReviewAvailability.Ready,
    val criteria: List<TeacherCriterionReview> = emptyList(),
    val aiStrengths: List<String> = emptyList(),
    val aiConcerns: List<String> = emptyList(),
    val aiSuggestedFeedback: String = "",
    val teacherFeedback: String = "",
    val teacherPrivateComment: String = "",
) {
    val maxScore: Int get() = criteria.sumOf { it.maxScore }

    /** True only once every criterion is explicitly [TeacherCriterionReview.isTeacherConfirmed] — Finalize's own gate, never inferred from [reviewStatus]. */
    val allCriteriaConfirmed: Boolean
        get() = criteria.isNotEmpty() && criteria.all { it.isTeacherConfirmed && it.teacherScore != null }

    /** Null until [allCriteriaConfirmed] — a finalized review's total, always derived from teacher-confirmed numbers, never a second stored figure and never an AI value the teacher never acted on. */
    val finalScore: Int?
        get() = if (allCriteriaConfirmed) criteria.sumOf { it.teacherScore!! } else null
}
