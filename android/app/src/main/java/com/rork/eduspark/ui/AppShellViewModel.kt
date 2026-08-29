package com.rork.eduspark.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.core.locale.LocaleController
import com.rork.eduspark.core.preferences.AppPreferences
import com.rork.eduspark.core.preferences.NumeralSystem
import com.rork.eduspark.core.preferences.ThemeMode
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * App-wide display state: theme, numerals, motion, locale and connectivity.
 *
 * Deliberately the only global-ish ViewModel in the app. Everything else is feature-scoped —
 * "small stores, no global god-store" (Rork Knowledge §Stack). This one exists because the
 * theme and the offline banner genuinely are cross-cutting.
 */
data class AppShellState(
    val isReady: Boolean = false,
    val themeMode: ThemeMode = ThemeMode.System,
    val numeralSystem: NumeralSystem = NumeralSystem.Western,
    val reduceMotion: Boolean = false,
    val isOnline: Boolean = true,
    val locale: AppLocale = AppLocale.Default,
    /** False until the user has passed the A-01 language gate. */
    val hasChosenLocale: Boolean = false,
    val hasSeenValueCarousel: Boolean = false,
)

class AppShellViewModel(
    private val preferences: AppPreferences,
    private val connectivity: ConnectivityObserver,
    private val localeController: LocaleController,
) : ViewModel() {

    private val _state = MutableStateFlow(
        AppShellState(
            locale = localeController.current(),
            hasChosenLocale = localeController.hasExplicitChoice(),
        )
    )
    val state: StateFlow<AppShellState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                preferences.themeMode,
                preferences.numeralSystem,
                preferences.reduceMotionOverride,
                preferences.hasSeenValueCarousel,
            ) { theme, numerals, reduceMotion, seenCarousel ->
                Quad(theme, numerals, reduceMotion, seenCarousel)
            }.collect { (theme, numerals, reduceMotion, seenCarousel) ->
                _state.update {
                    it.copy(
                        isReady = true,
                        themeMode = theme,
                        numeralSystem = numerals,
                        reduceMotion = reduceMotion,
                        hasSeenValueCarousel = seenCarousel,
                    )
                }
            }
        }

        viewModelScope.launch {
            connectivity.isOnline.collect { online ->
                _state.update { it.copy(isOnline = online) }
            }
        }
    }

    fun setThemeMode(mode: ThemeMode) {
        viewModelScope.launch { preferences.setThemeMode(mode) }
    }

    fun setNumeralSystem(system: NumeralSystem) {
        viewModelScope.launch { preferences.setNumeralSystem(system) }
    }

    fun setReduceMotion(enabled: Boolean) {
        viewModelScope.launch { preferences.setReduceMotionOverride(enabled) }
    }

    /**
     * Applies a locale. When the direction flips, the system recreates the activity —
     * that recreation is the moment screen A-13 (Locale Switch Transition) covers.
     */
    fun setLocale(locale: AppLocale) {
        _state.update { it.copy(locale = locale, hasChosenLocale = true) }
        localeController.apply(locale)
    }

    fun markValueCarouselSeen() {
        viewModelScope.launch { preferences.setHasSeenValueCarousel(true) }
    }

    private data class Quad<A, B, C, D>(
        val first: A,
        val second: B,
        val third: C,
        val fourth: D,
    )
}
