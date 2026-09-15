package com.rork.eduspark.data.remote.planner

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
internal data class PlannerStateDto(
    val profile: JsonObject? = null,
    @SerialName("life_events") val lifeEvents: List<PlannerLifeEventDto> = emptyList(),
    val schedule: List<PlannerScheduleSlotDto> = emptyList(),
    @SerialName("chat_history") val chatHistory: List<PlannerChatHistoryDto> = emptyList(),
    val reasoning: List<String> = emptyList(),
    val insights: List<String> = emptyList(),
    @SerialName("weekly_plan") val weeklyPlan: List<PlannerWeeklyDayDto> = emptyList(),
    @SerialName("subject_analytics") val subjectAnalytics: List<JsonObject> = emptyList(),
    val recommendations: List<PlannerRecommendationDto> = emptyList(),
    val streak: JsonObject? = null,
    @SerialName("dashboard_snapshot") val dashboardSnapshot: JsonObject? = null,
    @SerialName("plan_stats") val planStats: JsonObject? = null,
)

@Serializable
internal data class PlannerScheduleSlotDto(
    val id: Int,
    val subject: String,
    @SerialName("scheduled_at") val scheduledAt: String,
    @SerialName("duration_minutes") val durationMinutes: Int,
    val priority: Int,
    val status: String,
    val reasoning: String? = null,
    @SerialName("priority_tier") val priorityTier: String? = null,
    @SerialName("priority_label") val priorityLabel: String? = null,
    @SerialName("priority_icon") val priorityIcon: String? = null,
    @SerialName("task_label") val taskLabel: String? = null,
)

@Serializable
internal data class PlannerWeeklyDayDto(
    @SerialName("day_name") val dayName: String,
    @SerialName("day_offset") val dayOffset: Int,
    val tasks: List<PlannerWeeklyTaskDto> = emptyList(),
)

@Serializable
internal data class PlannerWeeklyTaskDto(
    val subject: String,
    val time: String? = null,
    val duration: Int? = null,
    val priority: Int? = null,
    val reasoning: String? = null,
)

@Serializable
internal data class PlannerRecommendationDto(
    val text: String,
    @SerialName("priority_tier") val priorityTier: String? = null,
    @SerialName("priority_label") val priorityLabel: String? = null,
    @SerialName("priority_icon") val priorityIcon: String? = null,
    val subject: String? = null,
)

@Serializable
internal data class PlannerLifeEventDto(
    val id: Int? = null,
    @SerialName("event_type") val eventType: String? = null,
    val title: String? = null,
    @SerialName("event_date") val eventDate: String? = null,
    @SerialName("start_time") val startTime: String? = null,
    @SerialName("end_time") val endTime: String? = null,
    val subject: String? = null,
    val source: String? = null,
    val confidence: Double? = null,
)

@Serializable
internal data class PlannerChatHistoryDto(
    val id: Int,
    val role: String,
    val content: String,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
internal data class PlannerChatRequestDto(
    val message: String,
)

@Serializable
internal data class PlannerChatResponseDto(
    val reply: String = "",
    @SerialName("extracted_events") val extractedEvents: List<JsonObject> = emptyList(),
    val profile: JsonObject? = null,
    @SerialName("life_events") val lifeEvents: List<PlannerLifeEventDto> = emptyList(),
    val schedule: List<PlannerScheduleSlotDto> = emptyList(),
    @SerialName("chat_history") val chatHistory: List<PlannerChatHistoryDto> = emptyList(),
    val reasoning: List<String> = emptyList(),
    val insights: List<String> = emptyList(),
    @SerialName("weekly_plan") val weeklyPlan: List<PlannerWeeklyDayDto> = emptyList(),
    @SerialName("subject_analytics") val subjectAnalytics: List<JsonObject> = emptyList(),
    val recommendations: List<PlannerRecommendationDto> = emptyList(),
    val streak: JsonObject? = null,
    @SerialName("dashboard_snapshot") val dashboardSnapshot: JsonObject? = null,
    @SerialName("plan_stats") val planStats: JsonObject? = null,
)

@Serializable
internal data class PlannerCompleteSessionRequestDto(
    @SerialName("slot_id") val slotId: Int,
)
