package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-01 · Projects Hub / PJ-02 · Project Detail / PJ-03 · Milestone Board.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit: Projects has no implemented backend contract — every field here is what
 * [com.rork.eduspark.data.repository.mock.MockProjectRepository] can honestly construct
 * from deterministic fixtures, not a guess at a future DTO. [Project] is the shared catalog
 * entity; [ActiveProject] is this student's own started instance of one — the split exists so
 * starting a project never mutates the catalog itself, only creates a new per-student record.
 *
 * Milestone/task *status* is intentionally not modelled as a manual field the repository could
 * forget to update — see [ProjectTask.status] and [ActiveProject]'s own doc comment for how
 * project progress derives from task state instead.
 *
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-04 · Task Detail / PJ-05 · Submission Composer / PJ-06 · AI Review & Rubric.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [ProjectTask.status] (above) stays the *only* thing PJ-01/PJ-03's spine/progress logic
 * reads — completely unchanged by this slice. [ProjectTask.workflowStatus] is a second,
 * finer-grained dimension for the *same* task, read/written only by PJ-04/05/06; the
 * repository is what keeps them in lockstep (`status` only ever becomes [ProjectTaskStatus.Completed]
 * once [TaskWorkflowStatus.Reviewed] AND the review is accepted — see [ProjectReview.isAcceptable]),
 * so there is never a second, independently-drifting progress copy.
 *
 * The rubric "criterion" and its "result" are deliberately merged into one [RubricResult] type
 * — nothing in this mock ever shows a criterion without its scored result, so a separate
 * criterion-definition record would just be a second copy of the same fields.
 *
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-10 · Project Portfolio / PJ-11 · Project Certificate / PJ-12 · Materials & Safety.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * No new models needed for PJ-10/PJ-11: the showcase composes [Project] + [ActiveProject] +
 * [ProjectReflection] the ViewModel layer already has, and the certificate itself reuses
 * [com.rork.eduspark.data.model.CertificateVerification] — the SAME model/repository A-12
 * already verifies through — extended with one optional [CertificateVerification.skills]
 * field rather than a parallel verification type. [ActiveProject.isFullyCompleted] is what
 * decides "does this project belong in the showcase", derived the same "never a stored flag
 * that can drift" way [ProjectMilestone.isCompleted] already is; [ActiveProject.completedAtLabel]
 * is the one genuinely-new stored field, because a completion *date* cannot be derived from
 * state the way a completion *boolean* can.
 *
 * PJ-12 extends [ProjectMaterial] with optional cost/sourcing/quantity fields (all default to
 * null/true, so every existing 2-arg construction elsewhere in this file keeps compiling) and
 * adds [ProjectSafetyNote]/[Project.safetyNotes] — PJ-12 is only ever shown for
 * [ProjectMedium.Physical] projects, gated at the navigation entry point, not by a field here.
 */
enum class ProjectDifficulty { Beginner, Intermediate, Advanced }

enum class ProjectMode { Solo, Team }

enum class ProjectMedium { Physical, Digital }

/**
 * A checklist item to prepare before starting — never a milestone/task, see
 * [com.rork.eduspark.data.repository.ProjectRepository.getCheckedMaterials]. The PJ-12
 * fields are all optional/defaulted so every existing `ProjectMaterial(id, label)` call
 * keeps compiling unchanged; [estimatedCostLabel]/[localSourcingNote] are informational MOCK
 * text only — never a live price or a real shopping integration.
 */
data class ProjectMaterial(
    val id: String,
    val label: String,
    val quantityLabel: String? = null,
    val isRequired: Boolean = true,
    val estimatedCostLabel: String? = null,
    val localSourcingNote: String? = null,
)

enum class SafetySeverity { Caution, Important }

/** PJ-12. Plain-language safety guidance for a physical project — never fear-heavy styling, but [Important] items must be visually unmistakable. */
data class ProjectSafetyNote(
    val id: String,
    val text: String,
    val severity: SafetySeverity,
)

enum class ProjectTaskStatus { Completed, Current, Blocked, Upcoming }

/**
 * PJ-04's own finer lifecycle for a task that has a submission workflow — null for tasks that
 * don't (e.g. this slice's other fixture tasks, which have no [ProjectTask.acceptedSubmissionTypes]).
 * [Reviewed] with a rejected [ProjectReview] loops back to [InProgress] via
 * [com.rork.eduspark.data.repository.ProjectRepository.beginResubmission] — never straight to
 * [ProjectTaskStatus.Completed], which only [ProjectRepository.getReview] reaching an
 * *accepted* review is allowed to set.
 */
enum class TaskWorkflowStatus { NotStarted, InProgress, ReadyToSubmit, Submitted, Reviewed }

/**
 * A progressively-revealed hint. [xpCost] preserves the Screen Inventory's "hints available at
 * cost" vocabulary for display only — nothing in this slice deducts real XP; there is no
 * existing shared contract for spending it (see [com.rork.eduspark.data.repository.LearningRepository],
 * which only ever reads [GamificationSnapshot]).
 */
data class TaskHint(
    val id: String,
    val text: String,
    val xpCost: Int,
)

data class ProjectTask(
    val id: String,
    val title: String,
    val status: ProjectTaskStatus,
    /** Only ever set when [status] is [ProjectTaskStatus.Blocked]. */
    val blockerLabel: String? = null,
    // ── PJ-04 additions — all null/empty for tasks with no submission workflow ──────────
    val workflowStatus: TaskWorkflowStatus? = null,
    val objective: String? = null,
    val instructions: List<String> = emptyList(),
    val safetyNote: String? = null,
    val whatGoodLooksLike: List<String> = emptyList(),
    val hints: List<TaskHint> = emptyList(),
    val acceptedSubmissionTypes: Set<SubmissionType> = emptySet(),
)

/**
 * One bead on the Progress Spine. Deliberately carries no status field of its own — a
 * milestone's [com.rork.eduspark.ui.components.progress.SpineNodeState] is always derived from
 * [tasks] (all completed → Completed; any task Current or Blocked → Current; otherwise Locked),
 * so there is never a manual milestone status that can drift from its own tasks.
 */
data class ProjectMilestone(
    val id: String,
    val title: String,
    val tasks: List<ProjectTask>,
)

/** An honest, non-social placeholder — never a real student identity, like, or comment. */
data class ProjectShowcaseSample(
    val id: String,
    val caption: String,
)

/** The shared catalog entity — the same object PJ-01's Discover list and PJ-02 both read. */
data class Project(
    val id: String,
    val title: String,
    /** The HERO line — sells the outcome ("a working water-level alarm"), never the lesson topic. */
    val deliverable: String,
    val description: String,
    val subjectId: String,
    val subjectTitle: String,
    val skills: List<String>,
    val estimatedDurationLabel: String,
    val difficulty: ProjectDifficulty,
    val mode: ProjectMode,
    val medium: ProjectMedium,
    val materials: List<ProjectMaterial>,
    val showcaseSamples: List<ProjectShowcaseSample>,
    /** The template milestones every student starting this project gets their own copy of. */
    val milestones: List<ProjectMilestone>,
    /** PJ-12. Only ever populated for [ProjectMedium.Physical] projects; empty for Digital ones by construction, not by a screen-side filter. */
    val safetyNotes: List<ProjectSafetyNote> = emptyList(),
    /** PJ-12. A pre-authored MOCK estimate string (e.g. "≈16$") — never summed at runtime from [ProjectMaterial.estimatedCostLabel], and never implied to be a live price. */
    val estimatedTotalCostLabel: String? = null,
)

/**
 * This student's own started instance of a [Project]. [milestones] starts as a copy of the
 * project template's — nothing in this slice mutates a task's status yet (that is PJ-04's
 * job), so today it is always identical to the template, but the field lives here because
 * task progress belongs to the student's instance, never the shared catalog entity.
 *
 * Deliberately carries no materials-checklist state — [com.rork.eduspark.data.repository.ProjectRepository.getCheckedMaterials]
 * is ticked *before* a project is even started, so it is tracked independently of whether an
 * [ActiveProject] exists at all, never as a field here.
 */
data class ActiveProject(
    val projectId: String,
    val milestones: List<ProjectMilestone>,
    /**
     * PJ-10. Set only once, the moment every milestone completes — a genuine event timestamp,
     * not something [isFullyCompleted] could derive on its own. Null for every in-progress
     * project (including the water-alarm/ecosystem-model QA fixtures — this slice never marks
     * either "falsely completed" just to populate the showcase).
     */
    val completedAtLabel: String? = null,
) {
    val completedMilestoneCount: Int get() = milestones.count { it.isCompleted }
    val totalMilestoneCount: Int get() = milestones.size

    /** The first milestone that isn't fully completed — "what do I do next?". Null once every milestone is done. */
    val currentMilestone: ProjectMilestone? get() = milestones.firstOrNull { !it.isCompleted }
}

val ProjectMilestone.isCompleted: Boolean get() = tasks.isNotEmpty() && tasks.all { it.status == ProjectTaskStatus.Completed }
val ProjectMilestone.isCurrent: Boolean get() = !isCompleted && tasks.any { it.status == ProjectTaskStatus.Current || it.status == ProjectTaskStatus.Blocked }

/** PJ-10. Whether this project belongs in the showcase — derived from [ProjectMilestone.isCompleted], the same "never a stored flag that can drift" rule the milestone/task status hierarchy already follows. */
val ActiveProject.isFullyCompleted: Boolean get() = milestones.isNotEmpty() && milestones.all { it.isCompleted }

/**
 * PJ-05. [Video] exists in the enum for completeness with the Screen Inventory but this slice
 * seeds no task that accepts it — no media-recording infrastructure is added just to exercise
 * a case no fixture needs (see [MockProjectRepository][com.rork.eduspark.data.repository.mock.MockProjectRepository]'s own doc comment).
 * [WrittenReflection]/[Link] are plain text fields; [Photo]/[File] become [SubmissionAttachment]s
 * — never real captures, always an honest MOCK selection.
 */
enum class SubmissionType { WrittenReflection, Photo, File, Link, Video }

/** A MOCK-selected photo/file — never a real URI, camera capture, or upload. */
data class SubmissionAttachment(
    val id: String,
    val type: SubmissionType,
    val label: String,
)

/**
 * The student's in-progress work on one task, saved locally before submitting. Deliberately
 * has no status of its own — see [ProjectTask.workflowStatus] for where "has this become
 * ready to submit" actually lives, kept in lockstep by [ProjectRepository.saveDraft][com.rork.eduspark.data.repository.ProjectRepository.saveDraft].
 */
data class SubmissionDraft(
    val taskId: String,
    val writtenReflection: String = "",
    val link: String = "",
    val attachments: List<SubmissionAttachment> = emptyList(),
) {
    val hasContent: Boolean get() = writtenReflection.isNotBlank() || link.isNotBlank() || attachments.isNotEmpty()
}

/** The submitted, immutable record PJ-06 reviews. Created once — see [ProjectRepository.submitTask][com.rork.eduspark.data.repository.ProjectRepository.submitTask]'s own doc comment for its idempotency guarantee. */
data class ProjectSubmission(
    val taskId: String,
    val writtenReflection: String,
    val link: String,
    val attachments: List<SubmissionAttachment>,
    val submittedAtLabel: String,
)

/** One scored rubric row. [score]/[maxScore] is always a small integer scale (e.g. 0/2, 1/2, 2/2) — never a fabricated percentage. */
data class RubricResult(
    val criterionId: String,
    val criterionTitle: String,
    val score: Int,
    val maxScore: Int,
    val reason: String,
)

/**
 * PJ-06. Machine-generated — see [com.rork.eduspark.ui.components.ai.AiMessageBubble]'s own
 * doc comment for the jouri trust contract this review must render under. [strengths] is
 * shown before [improvement] on purpose (Screen Inventory: "strengths first, then one
 * specific improvement"). [isAcceptable] is derived from [rubricResults], never a separately
 * authored flag that could disagree with the scores actually shown.
 */
data class ProjectReview(
    val taskId: String,
    val rubricResults: List<RubricResult>,
    val strengths: List<String>,
    val improvement: String,
) {
    val isAcceptable: Boolean get() = rubricResults.isNotEmpty() && rubricResults.all { it.score == it.maxScore }
}

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-07 · Peer Review / PJ-08 · Team Workspace / PJ-09 · Reflection Log.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * All three are deterministic MOCK — no real peer network, no real-time team sync, no real
 * microphone/transcription. PJ-07/PJ-08 deliberately never carry a real student's name or
 * photo; every identity field here is either an anonymized label ([PeerSubmissionPreview])
 * or a fixed, fictional demo member ([TeamMember]).
 */

/** PJ-07/PJ-08. A criterion from a task's rubric, unscored — the same criteria [ProjectReview] scores via [RubricResult], before any score exists. */
data class RubricCriterion(
    val id: String,
    val title: String,
    val maxScore: Int,
)

/**
 * PJ-07. The submission a peer reviews. [anonymizedLabel] is the only identity ever shown —
 * never a real name or photo. [submission] reuses [ProjectSubmission] verbatim, since that
 * model never carried a student identity field to begin with, so nothing needs stripping.
 */
data class PeerSubmissionPreview(
    val taskId: String,
    val anonymizedLabel: String,
    val submission: ProjectSubmission,
    val criteria: List<RubricCriterion>,
)

/** PJ-07's local, in-progress rating — [scores] keyed by [RubricCriterion.id]. */
data class PeerReviewDraft(
    val taskId: String,
    val scores: Map<String, Int> = emptyMap(),
    val comment: String = "",
)

/**
 * PJ-07's submitted review. [ratings] reuses [RubricResult]'s shape — same rubric, same 0/2
 * scale PJ-06 uses — but [RubricResult.reason] is left blank per row, since PJ-07 collects one
 * overall [comment] rather than a per-criterion reason the way PJ-06's AI review does.
 */
data class PeerReview(
    val taskId: String,
    val ratings: List<RubricResult>,
    val comment: String,
    val submittedAtLabel: String,
)

enum class TeamRole { Leader, Member }

/**
 * PJ-08. A fixed, fictional demo member — never a real student. [isCurrentStudent] marks the
 * viewer's own row; decided entirely by this MOCK fixture, with no session/auth coupling (same
 * "no cross-repository mutation" boundary [ProfileRepository] already keeps).
 */
data class TeamMember(
    val id: String,
    val displayName: String,
    val role: TeamRole,
    val isCurrentStudent: Boolean,
)

/**
 * PJ-08. Maps one of the project's own tasks to a team member — kept separate from
 * [ProjectTask] so the canonical task list PJ-01/PJ-03 render from is never duplicated. A null
 * [assigneeMemberId] is the explicit "unassigned" state, not an absent record.
 */
data class TeamTaskAssignment(
    val taskId: String,
    val assigneeMemberId: String?,
)

data class TeamMessage(
    val id: String,
    val senderMemberId: String,
    val text: String,
    val sentAtLabel: String,
)

/** PJ-08. Never a real file upload — [referenceLabel] is an honest MOCK placeholder, the same boundary [SubmissionAttachment] already draws for PJ-05. */
data class SharedDeliverable(
    val title: String,
    val stateLabel: String,
    val lastUpdatedByMemberId: String,
    val lastUpdatedAtLabel: String,
    val referenceLabel: String? = null,
)

/** PJ-08. One per [ProjectMode.Team] project — deterministic MOCK membership and messages, never a real peer network or real-time sync. */
data class ProjectTeam(
    val projectId: String,
    val teamName: String,
    val members: List<TeamMember>,
    val taskAssignments: List<TeamTaskAssignment>,
    val messages: List<TeamMessage>,
    val deliverable: SharedDeliverable,
)

/**
 * PJ-09. Repository/session-level, keyed by ([projectId], [milestoneId]) — PJ-10 Portfolio
 * (not this slice) is meant to read these back later, so nothing here is view-only state.
 * [durationLabel] is optional display metadata only, never a real recording length.
 */
data class ProjectReflection(
    val projectId: String,
    val milestoneId: String,
    val milestoneTitle: String,
    val projectTitle: String,
    val sessionLabel: String,
    val transcript: String,
    val durationLabel: String? = null,
)
