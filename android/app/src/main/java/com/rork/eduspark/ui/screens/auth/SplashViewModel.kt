package com.rork.eduspark.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.locale.AppLocale
import com.rork.eduspark.core.locale.LocaleController
import com.rork.eduspark.core.preferences.AppPreferences
import com.rork.eduspark.data.model.SessionUser
import com.rork.eduspark.data.repository.AuthRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * A-01 · Splash & Language Gate.
 *
 * ── The one thing to understand about this screen ─────────────────────────
 * The Screen Inventory describes the returning-launch path as "logo + silent token
 * refresh". The repository now resolves encrypted tokens through /me and performs one
 * rotation when the access token has expired. Pending remains visible until that completes.
 */
sealed interface SplashDecision {
    /** Still resolving — the branded launch frame stays up. */
    data object Pending : SplashDecision

    /** First launch ever: no language has been chosen, so the gate is shown. */
    data object LanguageGate : SplashDecision

    /** Legacy intro carousel route; retained for direct navigation/back-stack compatibility. */
    data object Carousel : SplashDecision

    /** No stored session — public entry / role landing. */
    data object Login : SplashDecision

    /**
     * A stored session was found. Carries the whole [SessionUser], not just the role —
     * a student whose session says `hasCompletedOnboarding = false` (an onboarding flow
     * killed mid-way and relaunched) must resume SO-01…SO-05, not land on Student Core.
     */
    data class Home(val user: SessionUser) : SplashDecision
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
        return when (val restored = authRepository.restoreSession()) {
            is com.rork.eduspark.core.result.AppResult.Success ->
                restored.data?.let { SplashDecision.Home(it) } ?: SplashDecision.Login
            is com.rork.eduspark.core.result.AppResult.Failure -> SplashDecision.Login
        }
    }

    private companion object {
        /** "~600ms max" from the Screen Inventory, used as the brand beat, not a fake delay. */
        const val MIN_BRAND_BEAT_MS = 600L
    }
}
