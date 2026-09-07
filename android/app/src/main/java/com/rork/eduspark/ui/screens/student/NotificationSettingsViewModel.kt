package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.preferences.AppPreferences
import com.rork.eduspark.core.preferences.NotificationCategory
import com.rork.eduspark.core.preferences.NotificationPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-26 · Settings — Notifications.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Preferences only, entirely local — [AppPreferences] is the same DataStore-backed store
 * ST-25 reads, never a second one. There is deliberately no [com.rork.eduspark.core.connectivity.ConnectivityObserver]
 * dependency here: every read/write in this screen is a local preference and cannot fail on
 * offline, so there is no offline state to represent. Disabling quiet hours only ever writes
 * `enabled = false` onto the *existing* [com.rork.eduspark.core.preferences.QuietHours] copy —
 * the previously chosen start/end always survive, per [setQuietHoursEnabled].
 */
data class NotificationSettingsUiState(
    /** Null only until the first DataStore emission arrives — not a loading spinner, just "not yet". */
    val preferences: NotificationPreferences? = null,
)

class NotificationSettingsViewModel(
    private val preferences: AppPreferences,
) : ViewModel() {

    private val _state = MutableStateFlow(NotificationSettingsUiState())
    val state: StateFlow<NotificationSettingsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            preferences.notificationPreferences.collect { prefs ->
                _state.update { it.copy(preferences = prefs) }
            }
        }
    }

    fun setCategoryEnabled(category: NotificationCategory, enabled: Boolean) {
        viewModelScope.launch { preferences.setNotificationCategoryEnabled(category, enabled) }
    }

    fun setQuietHoursEnabled(enabled: Boolean) {
        val current = _state.value.preferences?.quietHours ?: return
        viewModelScope.launch { preferences.setQuietHours(current.copy(enabled = enabled)) }
    }

    fun setQuietHoursStart(hour: Int, minute: Int) {
        val current = _state.value.preferences?.quietHours ?: return
        viewModelScope.launch { preferences.setQuietHours(current.copy(startHour = hour, startMinute = minute)) }
    }

    fun setQuietHoursEnd(hour: Int, minute: Int) {
        val current = _state.value.preferences?.quietHours ?: return
        viewModelScope.launch { preferences.setQuietHours(current.copy(endHour = hour, endMinute = minute)) }
    }
}
