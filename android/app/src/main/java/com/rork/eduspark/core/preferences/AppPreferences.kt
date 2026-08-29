package com.rork.eduspark.core.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
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

        // A-07 · teaching intent, kept so the teacher does not retype it at setup (TC-01).
        val TeacherSubjects = stringSetPreferencesKey("teacher_intent_subjects")
        val TeacherGrades = stringSetPreferencesKey("teacher_intent_grades")
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
}
