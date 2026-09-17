package com.rork.eduspark

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.getValue
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.ui.AppShellViewModel
import com.rork.eduspark.ui.navigation.AppNavigation
import com.rork.eduspark.ui.theme.EduSparkTheme
import org.koin.androidx.compose.koinViewModel

/**
 * Single activity host.
 *
 * Extends [AppCompatActivity] rather than ComponentActivity because EduSpark uses
 * AppCompat's per-app locale API: it is the supported way to flip ar (RTL) ⇄ en (LTR)
 * at runtime, persist the choice, and have the framework recreate the activity so
 * layout direction, the predictive-back edge and the keyboard all follow.
 */
class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        // Held only until the shell has read its stored display preferences, so the first
        // frame is never drawn in the wrong theme (Design System: the launch frame must
        // not flash a colour outside the system).
        val splash = installSplashScreen()
        splash.setKeepOnScreenCondition { false }

        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            val shellViewModel = koinViewModel<AppShellViewModel>()
            val state by shellViewModel.state.collectAsStateWithLifecycle()

            EduSparkTheme(
                themeMode = state.themeMode,
                numeralSystem = state.numeralSystem,
                reduceMotionOverride = state.reduceMotion,
                textSizePreference = state.textSizePreference,
            ) {
                AppNavigation(
                    themeMode = state.themeMode,
                    onThemeModeChange = shellViewModel::setThemeMode,
                    numeralSystem = state.numeralSystem,
                    onNumeralSystemChange = shellViewModel::setNumeralSystem,
                    useHijriDates = state.useHijriDates,
                    onUseHijriDatesChange = shellViewModel::setUseHijriDates,
                    textSizePreference = state.textSizePreference,
                    onTextSizePreferenceChange = shellViewModel::setTextSizePreference,
                    locale = state.locale,
                    onSelectLocale = shellViewModel::setLocale,
                    isOffline = !state.isOnline,
                )
            }
        }
    }
}
