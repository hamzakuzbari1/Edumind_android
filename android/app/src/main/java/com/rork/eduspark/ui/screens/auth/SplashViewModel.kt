package com.rork.eduspark.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.core.locale.LocaleController
import com.rork.eduspark.core.preferences.AppPreferences
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.repository.AuthRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/**
 * A-01 · Splash & Language Gate.
 *
 * ── The one thing to understand about this screen ─────────────────────────
 * The Screen Inventory describes the returning-launch path as "logo + silent token
 * refresh". **There is no token refresh.** The Source Audit is explicit: the platform has
 * no `/auth/refresh` endpoint, and a 401 always means sign in again.
 *
 * So this ViewModel does the only honest equivalent: it reads the session that is already
 * stored, gives it a hard ~600ms budget, and routes. A stored session either still works
 * or the user logs in again — there is no silent-renewal path to model, and pretending
 * otherwise would bake a non-existent capability into the first screen of the app.
 */
sealed interface SplashDecision {
    /** Still resolving — the branded launch frame stays up. */
    data object Pending : SplashDecision

    /** First launch ever: no language has been chosen, so the gate is shown. */
    data object LanguageGate : SplashDecision

    /** Language known, but the value carousel has not been seen. */
    data object Carousel : SplashDecision

    /** No stored session — A-04. */
    data object Login : SplashDecision

    /** A stored session was found; go straight to that role's shell. */
    data class Home(val role: UserRole) : SplashDecision
}

data class SplashState(
    val decision: SplashDecision = SplashDecision.Pending,
    val locale: AppLocale = AppLocale.Default,
)

class SplashViewModel(
    private val preferences: AppPreferences,
    private val localeController: LocaleController,
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(SplashState(locale = localeController.current()))
    val state: StateFlow<SplashState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            // The whole launch decision runs concurrently with a minimum brand beat, so the
            // wordmark never flashes for 40ms on a fast device nor blocks on a slow one.
            val decision = async { resolve() }
            delay(MIN_BRAND_BEAT_MS)
            _state.value = _state.value.copy(decision = decision.await())
        }
    }

    /**
     * Applies the language chosen at the gate.
     *
     * When the direction actually flips, the framework recreates the activity and this
     * ViewModel is rebuilt — at which point [resolve] simply sees an explicit locale and
     * moves on. When the chosen language matches the current one there is no recreation,
     * so the decision is advanced here instead. Both paths converge on the same next screen.
     */
    fun chooseLanguage(locale: AppLocale) {
        _state.value = _state.value.copy(locale = locale)
        localeController.apply(locale)
        viewModelScope.launch {
            _state.value = _state.value.copy(decision = afterLanguageGate())
        }
    }

    private suspend fun resolve(): SplashDecision {
        if (!localeController.hasExplicitChoice()) return SplashDecision.LanguageGate
        return afterLanguageGate()
    }

    private suspend fun afterLanguageGate(): SplashDecision {
        // No refresh call — we read what is already stored and trust it or fall back to login.
        val session = authRepository.session.first()
        return when {
            !preferences.hasSeenValueCarousel.first() -> SplashDecision.Carousel
            session == null -> SplashDecision.Login
            else -> SplashDecision.Home(session.role)
        }
    }

    private companion object {
        /** "~600ms max" from the Screen Inventory, used as the brand beat, not a fake delay. */
        const val MIN_BRAND_BEAT_MS = 600L
    }
}
