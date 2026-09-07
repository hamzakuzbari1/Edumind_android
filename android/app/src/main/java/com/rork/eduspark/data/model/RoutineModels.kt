package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-12 · Routine Builder / ST-13 · Routine Week View.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit §6: "Daily routine — Implemented", `/student/routine/…`, and "Routine AI
 * chat" is a separate documented capability from "Planner chat". The client mirrors that
 * split: [RoutineProfile]/[RoutineSlot] describe recurring habit structure (wake, school,
 * commitments, sleep) and never share a shape with [WeekPlan]/[PlannerSession] (dated study
 * content), even though both key off the same [Weekday] calendar primitive.
 */

/** Deliberately its own enum, not [SessionStatus] — Routine and Planner never share a status type either. */
enum class RoutineSlotStatus { Upcoming, Completed, Missed }

enum class RoutineSlotType { Wake, School, Commitment, StudyWindow, Sleep }

data class RoutineSlot(
    val id: String,
    val day: Weekday,
    val type: RoutineSlotType,
    val title: String,
    val startTime: String,
    /** Null for a point-in-time anchor (wake, sleep) rather than a span (school, a commitment). */
    val endTime: String? = null,
    val status: RoutineSlotStatus,
)

data class RoutineProfile(
    val weekLabel: String,
    val today: Weekday,
    val slots: List<RoutineSlot>,
    val lastConfirmedLabel: String,
    /** Drives ST-13's weekly renewal/review prompt. */
    val needsRenewal: Boolean = false,
)

enum class RoutineBuildStep {
    Onboarding,
    AiBuild,
    SuggestionReview,
    FinalWeek,
}

data class RoutineBuildMessage(
    val id: String,
    val sender: PlannerChatSender,
    val text: String,
)

data class RoutineDayDraft(
    val day: Weekday,
    val slots: List<RoutineSlot>,
    val confirmed: Boolean,
    val reasoning: String,
)

data class RoutineSuggestion(
    val id: String,
    val title: String,
    val description: String,
    val priority: PlannerPriority,
    val accepted: Boolean? = null,
)

data class RoutineDraft(
    val answers: RoutineBuilderAnswers,
    val messages: List<RoutineBuildMessage>,
    val dayDrafts: List<RoutineDayDraft>,
    val currentDay: Weekday,
    val suggestions: List<RoutineSuggestion> = emptyList(),
    val reviewText: String = "",
) {
    val confirmedCount: Int get() = dayDrafts.count { it.confirmed }
    val totalDays: Int get() = dayDrafts.size
    val readyForReview: Boolean get() = dayDrafts.isNotEmpty() && dayDrafts.all { it.confirmed }
}

/**
 * ST-12's six setup topics. Every answer is quick-reply-shaped — a time string ("6:30"), a
 * preset id, or a small tag set — never a raw text field, matching "this is not a form".
 */
data class RoutineBuilderAnswers(
    val wakeTime: String? = null,
    val schoolHoursId: String? = null,
    val commitmentIds: Set<String> = emptySet(),
    /** Approved design's nested detail card (RoutineBuilder.dc.html) — per-commitment days
     *  and start/end time, additive to [commitmentIds]. A commitment id with no entry here
     *  falls back to [com.rork.eduspark.data.repository.mock.MockRoutineRepository]'s default
     *  days/time for it, so this never blocks confirming without customizing every commitment. */
    val commitmentSchedules: Map<String, CommitmentSchedule> = emptyMap(),
    val studyWindowIds: Set<String> = emptySet(),
    val energyPattern: StudyTimeOfDay? = null,
    val sleepTime: String? = null,
)

/** One commitment's student-chosen days + time span — see [RoutineBuilderAnswers.commitmentSchedules]. */
data class CommitmentSchedule(
    val days: Set<Weekday> = emptySet(),
    val startTime: String? = null,
    val endTime: String? = null,
)
