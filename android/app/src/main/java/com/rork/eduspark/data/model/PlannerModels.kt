package com.rork.eduspark.data.model

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-10 · Planner / ST-11 · Planner AI Chat.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Source Audit §6/§7: the planner is genuinely **not** LLM-generated — "smart planner
 * generate" is a rule-based optimizer, and "planner chat" is regex parsing plus template
 * replies ("optional Claude augment"). [PlannerRepository]'s mock mirrors that shape
 * exactly: deterministic keyword parsing, canned replies — not a fake LLM integration.
 *
 * Deliberately separate from [com.rork.eduspark.data.model.PlannerItem] (ST-01's read-only
 * "today's plan" strip) and from Routine (`/student/routine/…`, ST-12/13, not built this
 * slice) — the planner is study content; the routine is the surrounding habit structure.
 */

enum class Weekday { Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday }

enum class SessionStatus { Upcoming, Completed, Missed }

data class PlannerSession(
    val id: String,
    val day: Weekday,
    val subjectId: String,
    val subjectTitle: String,
    val title: String,
    /** Pre-formatted, e.g. "17:00" — same convention as [LearningPath.lastUpdatedLabel]. */
    val startTime: String,
    val durationMinutes: Int,
    val status: SessionStatus,
    /** Why this landed where it did, shown when the student taps in — null when there isn't one. */
    val priorityReason: String? = null,
)

data class WeekPlan(
    val weekLabel: String,
    val today: Weekday,
    val sessions: List<PlannerSession>,
    val generatedAtLabel: String,
)

data class PlannerRecommendation(
    val id: String,
    val text: String,
    val priority: PlannerPriority,
    val reason: String,
)

enum class PlannerPriority {
    High,
    Medium,
    Low,
}

enum class PlannerChatSender { Student, Assistant }

data class PlannerChatMessage(
    val id: String,
    val sender: PlannerChatSender,
    val text: String,
    /** Set only on an Assistant message that proposes a concrete move — never applied on its own. */
    val proposedChange: PlannerChangeProposal? = null,
)

enum class ProposalStatus { Pending, Accepted, Rejected }

/** One proposed session move. [status] starts [ProposalStatus.Pending]; only Accept mutates the week plan. */
data class PlannerChangeProposal(
    val id: String,
    val sessionId: String,
    val subjectTitle: String,
    val oldDay: Weekday,
    val oldStartTime: String,
    val newDay: Weekday,
    val newStartTime: String,
    val reason: String,
    val status: ProposalStatus = ProposalStatus.Pending,
)
