package com.rork.eduspark.data.remote.parent

import com.rork.eduspark.data.model.ParentActionItem
import com.rork.eduspark.data.model.ParentFeatureSnapshot
import com.rork.eduspark.data.model.ParentLessonDetails
import com.rork.eduspark.data.model.ParentLessonProgressSnapshot
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.data.model.ParentMetric
import com.rork.eduspark.data.model.ParentNotificationSnapshot
import com.rork.eduspark.data.model.ParentSubjectsTeachersSnapshot
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.floatOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive

internal fun ParentLinkedStudent.toDashboardSummary(
    courses: List<com.rork.eduspark.data.model.ParentCourseProgress>,
    activity: List<com.rork.eduspark.data.model.ParentActivity>,
    notes: com.rork.eduspark.data.model.ParentNotesFeed?,
) = ParentFeatureSnapshot(
    title = name,
    subtitle = gradeLabel.ifBlank { academicStatusLabel },
    metrics = listOf(
        ParentMetric("المواد", courses.size.toString(), "مواد مرتبطة"),
        ParentMetric("التقدم", "${courses.averagePercent()}%", "متوسط إنجاز"),
        ParentMetric("النشاط", activity.size.toString(), "آخر تحديثات"),
        ParentMetric("تنبيهات", (notes?.unreadCount ?: 0).toString(), "غير مقروء"),
    ),
    items = activity.take(4).map {
        ParentActionItem(
            id = it.id,
            title = it.title,
            subtitle = it.description.orEmpty(),
            status = it.relativeTime,
        )
    },
)

internal fun List<com.rork.eduspark.data.model.ParentCourseProgress>.toPerformanceSnapshot() =
    ParentFeatureSnapshot(
        title = "التقدم الأكاديمي",
        subtitle = "ملخص حقيقي من تقدم المواد المرتبطة بالطالب",
        metrics = listOf(
            ParentMetric("المواد", size.toString()),
            ParentMetric("متوسط التقدم", "${averagePercent()}%"),
            ParentMetric("متوسط العلامات", averageScoreLabel()),
        ),
        items = map {
            ParentActionItem(
                id = it.courseId,
                title = it.courseTitle,
                subtitle = it.subjectName,
                value = "${(it.completionPercentage * 100).toInt()}%",
                status = it.averageScore?.let { score -> "متوسط ${score.toInt()}%" }.orEmpty(),
            )
        },
    )

internal fun JsonElement.toFeatureSnapshot(title: String, subtitle: String): ParentFeatureSnapshot {
    if (this is JsonArray) {
        return ParentFeatureSnapshot(
            title = title,
            subtitle = subtitle,
            items = toActionItems(),
        )
    }
    val root = asObject()
    val metrics = root.collectMetrics()
    val items = root.firstArrayItems(
        "today_plan",
        "upcoming_tasks",
        "weekly_calendar",
        "recent_records",
        "subjects",
        "weekly",
        "items",
    ).toActionItems()
    return ParentFeatureSnapshot(title = title, subtitle = subtitle, metrics = metrics, items = items)
}

internal fun JsonElement.toInsightsSnapshot(academic: JsonElement?): ParentFeatureSnapshot {
    val insightItems = when (this) {
        is JsonArray -> toActionItems()
        else -> asObject().firstArrayItems("items", "insights").toActionItems()
    }
    val academicRoot = academic?.asObject() ?: JsonObject(emptyMap())
    val metrics = listOfNotNull(
        academicRoot.stringAny("overall_average")?.let { ParentMetric("المعدل", it) },
        academicRoot.stringAny("performance_label")?.let { ParentMetric("المستوى", it) },
    )
    val subjects = academicRoot.firstArrayItems("subjects").mapIndexed { index, item ->
        val obj = item.asObject()
        ParentActionItem(
            id = obj.stringAny("course_id", "subject_id") ?: "subject-$index",
            title = obj.stringAny("subject_name", "course_title") ?: "مادة ${index + 1}",
            subtitle = obj.stringAny("performance_label", "course_title").orEmpty(),
            value = obj.stringAny("composite_score", "quiz_average", "completion_rate").orEmpty(),
            status = obj.stringAny("performance_indicator").orEmpty(),
        )
    }
    return ParentFeatureSnapshot(
        title = "رؤى ذكية",
        subtitle = academicRoot.stringAny("summary")
            ?: "ملخصات وتحليلات مبنية على أداء الطالب",
        metrics = metrics,
        items = insightItems + subjects,
    )
}

internal fun JsonElement.toLessonProgressSnapshot(): ParentLessonProgressSnapshot {
    val root = asObject()
    val lessons = root.flattenLessons().mapIndexed { index, item ->
        val obj = item.asObject()
        ParentActionItem(
            id = obj.stringAny("id", "lesson_id") ?: "lesson-$index",
            title = obj.stringAny("title", "lesson_title", "topic", "course_title") ?: "درس ${index + 1}",
            subtitle = obj.stringAny("course_title", "subject_name", "unit_title").orEmpty(),
            value = obj.stringAny("progress_percent", "completion_percentage", "percent", "completion_percent").orEmpty(),
            status = obj.stringAny("status_label", "status", "completed_at").orEmpty(),
        )
    }
    val summary = root["summary"]?.asObject()
    val completed = summary?.intAny("completed_lessons", "completed", "done")
        ?: root.intAny("completed_lessons", "completed", "done")
        ?: lessons.count {
            it.status.contains("complete", ignoreCase = true) || it.status.contains("مكتمل")
        }
    val total = summary?.intAny("total_lessons", "total")
        ?: root.intAny("total_lessons", "total")
        ?: lessons.size
    return ParentLessonProgressSnapshot(completedLessons = completed, totalLessons = total, lessons = lessons)
}

internal fun JsonElement.toLessonDetailsSnapshot(lessonId: String): ParentLessonDetails {
    val root = asObject()
    val lesson = root["lesson"]?.asObject() ?: root
    val timeline = root.firstArrayItems("timeline", "activity", "events").mapIndexed { index, item ->
        val obj = item.asObject()
        ParentActionItem(
            id = obj.stringAny("id") ?: "event-$index",
            title = obj.stringAny("title", "label", "event_type", "type") ?: "نشاط ${index + 1}",
            subtitle = obj.stringAny("description", "datetime", "created_at", "time", "date").orEmpty(),
            status = obj.stringAny("status").orEmpty(),
        )
    }
    return ParentLessonDetails(
        lessonId = lesson.stringAny("id", "lesson_id") ?: lessonId,
        title = lesson.stringAny("title", "lesson_title", "topic") ?: "تفاصيل الدرس",
        subtitle = lesson.stringAny("course_title", "subject_name", "unit_title").orEmpty(),
        metrics = root.collectMetrics().ifEmpty { lesson.collectMetrics() },
        timeline = timeline,
    )
}

internal fun JsonElement.toSubjectsTeachersSnapshot(): ParentSubjectsTeachersSnapshot {
    val root = asObject()
    val enrolled = root["enrolled"] as? JsonArray
    val available = root["available"] as? JsonArray
    val source = when {
        enrolled != null || available != null -> (enrolled ?: JsonArray(emptyList())) +
            (available ?: JsonArray(emptyList()))
        else -> root.firstArrayItems("items", "subjects", "teachers")
    }
    return ParentSubjectsTeachersSnapshot(
        items = source.mapIndexed { index, item ->
            val obj = item.asObject()
            val teacher = obj["teacher"]?.asObject()
            ParentActionItem(
                id = obj.stringAny("id", "subject_id", "course_id") ?: "subject-$index",
                title = obj.stringAny("subject", "subject_name", "course_title", "title") ?: "مادة ${index + 1}",
                subtitle = teacher?.stringAny("name", "display_name")
                    ?: obj.stringAny("teacher_name", "teacher")
                    ?: "المعلم",
                value = obj.stringAny("progress_percent", "completion_percentage").orEmpty(),
                status = obj.stringAny("subscription_status", "status", "availability").orEmpty().ifBlank {
                    if (obj.booleanAny("enrolled") == true) "مسجل" else ""
                },
            )
        },
    )
}

internal fun JsonElement.toNotificationSnapshot(settings: JsonElement?): ParentNotificationSnapshot {
    val root = asObject()
    val notifications = root.firstArrayItems("notifications", "items", "results").mapIndexed { index, item ->
        val obj = item.asObject()
        ParentActionItem(
            id = obj.stringAny("id", "notification_id") ?: "notification-$index",
            title = obj.stringAny("title", "message") ?: "تنبيه",
            subtitle = obj.stringAny("body", "description", "created_at").orEmpty(),
            status = if (obj.booleanAny("is_read", "read") == false) "جديد" else "",
        )
    }
    val settingsRoot = settings?.asObject()
    val preferences = settingsRoot?.firstArrayItems("preferences", "items")?.mapIndexed { index, item ->
        val obj = item.asObject()
        ParentActionItem(
            id = obj.stringAny("id", "category") ?: "preference-$index",
            title = obj.stringAny("title", "category_label", "category") ?: "إعداد ${index + 1}",
            status = if (obj.booleanAny("enabled", "is_enabled") == false) "متوقف" else "مفعل",
        )
    }.orEmpty().ifEmpty { settingsRoot?.booleanPreferenceItems().orEmpty() }
    return ParentNotificationSnapshot(
        unreadCount = root.intAny("unread_count", "unread") ?: notifications.count { it.status == "جديد" },
        notifications = notifications,
        preferences = preferences,
    )
}

private fun List<com.rork.eduspark.data.model.ParentCourseProgress>.averagePercent(): Int =
    if (isEmpty()) 0 else map { (it.completionPercentage * 100).toInt() }.average().toInt()

private fun List<com.rork.eduspark.data.model.ParentCourseProgress>.averageScoreLabel(): String {
    val scores = mapNotNull { it.averageScore }
    return if (scores.isEmpty()) "غير متاح" else "${scores.average().toInt()}%"
}

private fun JsonElement.asObject(): JsonObject = this as? JsonObject ?: JsonObject(emptyMap())

private fun JsonArray.toActionItems(): List<ParentActionItem> = mapIndexed { index, item ->
    val obj = item.asObject()
    ParentActionItem(
        id = obj.stringAny("id", "lesson_id", "course_id") ?: "item-$index",
        title = obj.stringAny(
            "title",
            "text",
            "task_name",
            "name",
            "subject",
            "subject_name",
            "course_title",
            "lesson_title",
            "message",
            "day_label",
            "date",
            "label",
        ) ?: "عنصر ${index + 1}",
        subtitle = obj.stringAny(
            "description",
            "subtitle",
            "summary",
            "teacher_name",
            "status_label",
            "status",
            "planned_at",
        ).orEmpty(),
        value = obj.stringAny(
            "value",
            "progress",
            "completion_percentage",
            "completion_percent",
            "score",
            "study_minutes",
            "adherence_rate",
        ).orEmpty(),
        status = obj.stringAny("status_label", "status", "created_at", "relative_time", "updated_at").orEmpty(),
    )
}

private fun List<JsonElement>.toActionItems(): List<ParentActionItem> =
    JsonArray(this).toActionItems()

private operator fun JsonArray.plus(other: JsonArray): List<JsonElement> = this + other.toList()

private fun JsonObject.flattenLessons(): List<JsonElement> {
    val courses = get("courses") as? JsonArray
    if (courses != null) {
        return courses.flatMap { course ->
            val nested = course.asObject()["lessons"] as? JsonArray
            nested?.toList() ?: listOf(course)
        }
    }
    return firstArrayItems("lessons", "items", "progress")
}

private fun JsonObject.firstArrayItems(vararg preferredKeys: String): List<JsonElement> {
    preferredKeys.forEach { key ->
        val direct = get(key) as? JsonArray
        if (direct != null) return direct
    }
    values.forEach { value ->
        if (value is JsonArray) return value
        val nested = value as? JsonObject
        val nestedArray = nested?.values?.firstOrNull { it is JsonArray } as? JsonArray
        if (nestedArray != null) return nestedArray
    }
    return emptyList()
}

private fun JsonObject.collectMetrics(): List<ParentMetric> {
    metricPairs().takeIf { it.isNotEmpty() }?.let { return it }
    listOf("commitment", "attendance_history", "lesson_history", "comparison", "weekly_consistency").forEach { key ->
        val nested = get(key) as? JsonObject ?: return@forEach
        nested.metricPairs().takeIf { it.isNotEmpty() }?.let { return it }
    }
    return listOfNotNull(
        percentMetric("الحضور", "attendance_percentage"),
        percentMetric("الالتزام", "commitment_percent"),
        numberMetric("جلسات", "completed_sessions"),
        numberMetric("ساعات", "study_hours"),
        numberMetric("دقائق", "total_study_minutes_week"),
    )
}

private fun JsonObject.metricPairs(): List<ParentMetric> {
    val keys = listOf(
        "average_score" to "متوسط العلامات",
        "overall_average" to "المعدل",
        "attendance_percentage" to "الحضور",
        "completion_percentage" to "الإنجاز",
        "completion_percent" to "الإنجاز",
        "video_progress_percent" to "الفيديو",
        "quiz_score_percent" to "الاختبار",
        "study_hours" to "ساعات الدراسة",
        "total_study_hours" to "ساعات الدراسة",
        "total_study_minutes_week" to "دقائق الأسبوع",
        "completed_sessions" to "جلسات مكتملة",
        "total_sessions" to "إجمالي الجلسات",
        "streak_days" to "سلسلة الأيام",
        "weekly_consistency" to "الانتظام",
        "adherence_rate" to "الالتزام",
        "unread_count" to "تنبيهات",
    )
    return keys.mapNotNull { (key, label) ->
        val primitive = get(key)?.jsonPrimitive ?: return@mapNotNull null
        val value = primitive.contentOrNull ?: primitive.intOrNull?.toString() ?: primitive.floatOrNull?.toString()
        value?.let { ParentMetric(label = label, value = it) }
    }.distinctBy { it.label }
}

private fun JsonObject.percentMetric(label: String, key: String): ParentMetric? =
    intAny(key)?.let { ParentMetric(label, "$it%") }

private fun JsonObject.numberMetric(label: String, key: String): ParentMetric? =
    stringAny(key)?.let { ParentMetric(label, it) }

private fun JsonObject.booleanPreferenceItems(): List<ParentActionItem> {
    val labels = listOf(
        "login_alerts" to "تنبيهات الدخول",
        "logout_alerts" to "تنبيهات الخروج",
        "lesson_alerts" to "تنبيهات الدروس",
        "quiz_alerts" to "تنبيهات الاختبارات",
        "low_score_alerts" to "تنبيهات الدرجات المنخفضة",
        "inactivity_alerts" to "تنبيهات الخمول",
        "planner_alerts" to "تنبيهات المخطط",
    )
    return labels.mapNotNull { (key, title) ->
        val enabled = booleanAny(key) ?: return@mapNotNull null
        ParentActionItem(
            id = key,
            title = title,
            status = if (enabled) "مفعل" else "متوقف",
        )
    }
}

private fun JsonObject.stringAny(vararg keys: String): String? =
    keys.firstNotNullOfOrNull { key ->
        get(key)?.jsonPrimitive?.contentOrNull
            ?: get(key)?.jsonPrimitive?.intOrNull?.toString()
            ?: get(key)?.jsonPrimitive?.floatOrNull?.toString()
    }

private fun JsonObject.intAny(vararg keys: String): Int? =
    keys.firstNotNullOfOrNull { key ->
        get(key)?.jsonPrimitive?.intOrNull ?: get(key)?.jsonPrimitive?.floatOrNull?.toInt()
    }

private fun JsonObject.booleanAny(vararg keys: String): Boolean? =
    keys.firstNotNullOfOrNull { key -> get(key)?.jsonPrimitive?.booleanOrNull }
