package com.rork.eduspark.core.preferences

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-26 · Settings — Notifications.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Preferences only — nothing here schedules an Android notification, registers with FCM, or
 * requests push permission. This is the same local/device preference layer [ThemeMode]/
 * [NumeralSystem] already live in, extended with the categories and quiet-hours window this
 * slice needs, not a second preferences store (see [AppPreferences]).
 *
 * Categories are drawn only from features that already exist in this app: Planner (ST-10),
 * course/lesson updates (ST-01…ST-03), quizzes/exams (ST-06…ST-09, ST-14), teacher messaging
 * is out of scope for Student Core so it is intentionally omitted, subscriptions/payments
 * (ST-16…ST-20), and achievements (ST-15).
 */
enum class NotificationCategory {
    StudyReminders,
    LessonUpdates,
    QuizReminders,
    PaymentStatus,
    Achievements,
}

data class QuietHours(
    val enabled: Boolean = false,
    val startHour: Int = 22,
    val startMinute: Int = 0,
    val endHour: Int = 7,
    val endMinute: Int = 0,
)

data class NotificationPreferences(
    val categoryEnabled: Map<NotificationCategory, Boolean>,
    val quietHours: QuietHours,
) {
    fun isEnabled(category: NotificationCategory): Boolean = categoryEnabled[category] ?: true

    val allDisabled: Boolean get() = NotificationCategory.entries.none { isEnabled(it) }
}
