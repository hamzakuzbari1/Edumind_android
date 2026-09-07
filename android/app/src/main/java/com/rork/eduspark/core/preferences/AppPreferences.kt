package com.rork.eduspark.core.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.io.IOException

/** Theme selection. Dark is a designed first-class theme, never derived (Design System §3). */
enum class ThemeMode { System, Light, Dark }

/**
 * Design System §6.3 — Western digits are the default in *both* locales because Syrian
 * students read them fluently and they keep scores, timers and grades consistent.
 * Arabic-Indic digits are a user setting, never a default.
 */
enum class NumeralSystem { Western, ArabicIndic }

/**
 * ST-25. A small, deliberately non-arbitrary step on top of the type ramp's `.sp` sizes —
 * `.sp` already scales with the OS accessibility font setting at measure time, so this
 * multiplier and the system's own scale compose rather than compete (see [com.rork.eduspark.ui.theme.eduTypographyFor]).
 */
enum class TextSizePreference { Default, Large }

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "eduspark_settings")

/**
 * Small, typed preference store for display settings only.
 *
 * Auth tokens never live here — they go through
 * [com.rork.eduspark.core.session.SecureTokenStore].
 */
class AppPreferences(context: Context) {

    private val store = context.applicationContext.dataStore

    private object Keys {
        val ThemeMode = stringPreferencesKey("theme_mode")
        val Numerals = stringPreferencesKey("numeral_system")
        val HijriDates = booleanPreferencesKey("hijri_dates")
        val ReduceMotionOverride = booleanPreferencesKey("reduce_motion_override")
        val HasSeenCarousel = booleanPreferencesKey("has_seen_value_carousel")
        val TextSize = stringPreferencesKey("text_size_preference")

        // A-07 · teaching intent, kept so the teacher does not retype it at setup (TC-01).
        val TeacherSubjects = stringSetPreferencesKey("teacher_intent_subjects")
        val TeacherGrades = stringSetPreferencesKey("teacher_intent_grades")

        // ST-26 · one boolean per NotificationCategory, plus the quiet-hours window.
        val NotifStudyReminders = booleanPreferencesKey("notif_study_reminders")
        val NotifLessonUpdates = booleanPreferencesKey("notif_lesson_updates")
        val NotifQuizReminders = booleanPreferencesKey("notif_quiz_reminders")
        val NotifPaymentStatus = booleanPreferencesKey("notif_payment_status")
        val NotifAchievements = booleanPreferencesKey("notif_achievements")
        val QuietHoursEnabled = booleanPreferencesKey("quiet_hours_enabled")
        val QuietHoursStartHour = intPreferencesKey("quiet_hours_start_hour")
        val QuietHoursStartMinute = intPreferencesKey("quiet_hours_start_minute")
        val QuietHoursEndHour = intPreferencesKey("quiet_hours_end_hour")
        val QuietHoursEndMinute = intPreferencesKey("quiet_hours_end_minute")

        fun forCategory(category: NotificationCategory): Preferences.Key<Boolean> = when (category) {
            NotificationCategory.StudyReminders -> NotifStudyReminders
            NotificationCategory.LessonUpdates -> NotifLessonUpdates
            NotificationCategory.QuizReminders -> NotifQuizReminders
            NotificationCategory.PaymentStatus -> NotifPaymentStatus
            NotificationCategory.Achievements -> NotifAchievements
        }
    }

    private val preferences: Flow<Preferences> = store.data.catch { throwable ->
        // A corrupt or unreadable store must never crash launch — fall back to defaults.
        if (throwable is IOException) emit(emptyPreferences()) else throw throwable
    }

    val themeMode: Flow<ThemeMode> = preferences.map { prefs ->
        prefs[Keys.ThemeMode]?.let { stored -> ThemeMode.entries.firstOrNull { it.name == stored } }
            ?: ThemeMode.System
    }

    val numeralSystem: Flow<NumeralSystem> = preferences.map { prefs ->
        prefs[Keys.Numerals]?.let { stored -> NumeralSystem.entries.firstOrNull { it.name == stored } }
            ?: NumeralSystem.Western
    }

    val useHijriDates: Flow<Boolean> = preferences.map { it[Keys.HijriDates] ?: false }

    val reduceMotionOverride: Flow<Boolean> = preferences.map { it[Keys.ReduceMotionOverride] ?: false }

    val hasSeenValueCarousel: Flow<Boolean> = preferences.map { it[Keys.HasSeenCarousel] ?: false }

    val textSizePreference: Flow<TextSizePreference> = preferences.map { prefs ->
        prefs[Keys.TextSize]?.let { stored -> TextSizePreference.entries.firstOrNull { it.name == stored } }
            ?: TextSizePreference.Default
    }

    /** ST-26. All five categories default enabled — an education app's own reminders are opt-out, not opt-in. */
    val notificationPreferences: Flow<NotificationPreferences> = preferences.map { prefs ->
        NotificationPreferences(
            categoryEnabled = NotificationCategory.entries.associateWith { category ->
                prefs[Keys.forCategory(category)] ?: true
            },
            quietHours = QuietHours(
                enabled = prefs[Keys.QuietHoursEnabled] ?: false,
                startHour = prefs[Keys.QuietHoursStartHour] ?: 22,
                startMinute = prefs[Keys.QuietHoursStartMinute] ?: 0,
                endHour = prefs[Keys.QuietHoursEndHour] ?: 7,
                endMinute = prefs[Keys.QuietHoursEndMinute] ?: 0,
            ),
        )
    }

    /**
     * The subjects and grades a teacher picked while registering.
     *
     * Held **on the device only**. Registration itself sends nothing but name, email,
     * password and role, because that is all the platform accepts — this is a local draft
     * that TC-01 Teacher Setup will read so the teacher does not answer the same question
     * twice. It is display state, never a credential.
     */
    val teacherIntentSubjects: Flow<Set<String>> =
        preferences.map { it[Keys.TeacherSubjects] ?: emptySet() }

    val teacherIntentGrades: Flow<Set<String>> =
        preferences.map { it[Keys.TeacherGrades] ?: emptySet() }

    suspend fun setThemeMode(mode: ThemeMode) {
        store.edit { it[Keys.ThemeMode] = mode.name }
    }

    suspend fun setNumeralSystem(system: NumeralSystem) {
        store.edit { it[Keys.Numerals] = system.name }
    }

    suspend fun setUseHijriDates(enabled: Boolean) {
        store.edit { it[Keys.HijriDates] = enabled }
    }

    suspend fun setReduceMotionOverride(enabled: Boolean) {
        store.edit { it[Keys.ReduceMotionOverride] = enabled }
    }

    suspend fun setHasSeenValueCarousel(seen: Boolean) {
        store.edit { it[Keys.HasSeenCarousel] = seen }
    }

    suspend fun setTeacherIntent(subjectIds: Set<String>, gradeIds: Set<String>) {
        store.edit {
            it[Keys.TeacherSubjects] = subjectIds
            it[Keys.TeacherGrades] = gradeIds
        }
    }

    suspend fun setTextSizePreference(preference: TextSizePreference) {
        store.edit { it[Keys.TextSize] = preference.name }
    }

    suspend fun setNotificationCategoryEnabled(category: NotificationCategory, enabled: Boolean) {
        store.edit { it[Keys.forCategory(category)] = enabled }
    }

    /**
     * Always writes the full window — called both when toggling [QuietHours.enabled] and when
     * changing the start/end time, so disabling never has to special-case "leave the times
     * alone": the caller already carries the last-known times forward either way.
     */
    suspend fun setQuietHours(quietHours: QuietHours) {
        store.edit {
            it[Keys.QuietHoursEnabled] = quietHours.enabled
            it[Keys.QuietHoursStartHour] = quietHours.startHour
            it[Keys.QuietHoursStartMinute] = quietHours.startMinute
            it[Keys.QuietHoursEndHour] = quietHours.endHour
            it[Keys.QuietHoursEndMinute] = quietHours.endMinute
        }
    }
}
