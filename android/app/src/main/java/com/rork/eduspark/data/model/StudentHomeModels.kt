package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-01 · Student Home — client domain models.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit §2/§8: student dashboard and course lists are READY backend capabilities.
 * [hasActiveProject] and [englishAvailable] are gates only — Projects and the Language
 * module have no backend yet (Source Audit: Projects ❌, Language Phase 5) — so this slice
 * never fabricates project or CEFR data, only whether their teaser cards should show.
 */
data class StudentHomeSnapshot(
    val studentName: String,
    val grade: Grade,
    val streakDays: Int,
    val gamification: GamificationSnapshot,
    /** Null is the legitimate "first day, nothing to continue yet" empty state. */
    val continueItem: ContinueLearningItem?,
    val todayPlan: List<PlannerItem>,
    val subjects: List<SubjectProgress>,
    val hasActiveProject: Boolean,
    val englishAvailable: Boolean,
    /** ST-01's compact report row — Test-2SY's `MyReportSection` parity. Reuses [subjects].size for
     *  "active subjects" rather than a redundant count field; these two are the only stats that
     *  genuinely don't exist anywhere else in the snapshot. */
    val completedLessonsTotal: Int = 0,
    /** Null when the student hasn't taken a quiz yet — the report row hides that tile rather than showing a fake 0%. */
    val lastQuizScorePercent: Int? = null,
)

data class ContinueLearningItem(
    val lessonId: String,
    val courseId: String,
    val lessonTitle: String,
    val subjectTitle: String,
    val subjectSubtitle: String,
    val minutesLeft: Int,
    val lessonIndex: Int,
    val lessonTotal: Int,
    val mediaTypes: Set<LessonMediaType>,
    /** Test-2SY's `NextMissionSection` shows the teacher on the mission card; reuses [com.rork.eduspark.R.string.st02_locked_teacher_name]'s "مع %1$s" pattern at the call site rather than a second format string. */
    val teacherName: String,
)

/** One row of the "today's plan" strip — a read-only reflection of the planner, not the planner itself. */
data class PlannerItem(
    val time: String,
    val title: String,
    val durationMinutes: Int,
)

data class SubjectProgress(
    val courseId: String,
    val title: String,
    val progress: Float,
    val currentLabel: String,
    /** Approved design's subject card shows "teacher · X%", not the unit/lesson label —
     *  [currentLabel] stays for callers that still need it (e.g. the completed-state override). */
    val teacherName: String = "",
)
