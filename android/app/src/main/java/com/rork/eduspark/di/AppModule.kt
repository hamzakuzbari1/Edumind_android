package com.rork.eduspark.di

import com.rork.eduspark.BuildConfig
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.locale.LocaleController
import com.rork.eduspark.core.preferences.AppPreferences
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.mock.MockAuthRepository
import com.rork.eduspark.data.repository.mock.MockLearningRepository
import com.rork.eduspark.ui.AppShellViewModel
import com.rork.eduspark.ui.screens.auth.LoginViewModel
import com.rork.eduspark.ui.screens.auth.RegisterViewModel
import com.rork.eduspark.ui.screens.auth.SplashViewModel
import com.rork.eduspark.ui.screens.auth.ValueCarouselViewModel
import org.koin.android.ext.koin.androidApplication
import org.koin.core.module.dsl.viewModel
import org.koin.dsl.module

/**
 * Dependency graph.
 *
 * The single decision point for mock-vs-real data is [dataSourceMode], read from
 * `BuildConfig.DATA_SOURCE_MODE`. Screens and ViewModels depend only on the repository
 * interfaces, so switching the whole app to the real backend is one constant plus the
 * remote implementations — not a refactor.
 */
enum class DataSourceMode { MOCK, REMOTE }

val dataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.DATA_SOURCE_MODE) }
        .getOrDefault(DataSourceMode.MOCK)

val appModule = module {

    single { AppPreferences(androidApplication()) }
    single { ConnectivityObserver(androidApplication()) }
    single { LocaleController(androidApplication()) }

    // Replaced by a Keystore-backed store when the real API layer lands.
    single<SecureTokenStore> { InMemoryTokenStore() }

    single<AuthRepository> {
        when (dataSourceMode) {
            DataSourceMode.MOCK -> MockAuthRepository(tokenStore = get())
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — the FastAPI client has " +
                    "not been generated. Keep DATA_SOURCE_MODE=MOCK until it exists."
            )
        }
    }

    single<LearningRepository> {
        when (dataSourceMode) {
            DataSourceMode.MOCK -> MockLearningRepository()
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — see data/repository/remote."
            )
        }
    }

    viewModel { AppShellViewModel(preferences = get(), connectivity = get(), localeController = get()) }

    // ── Phase 0 · A-01 → A-04, the entry funnel ──────────────────────────
    viewModel {
        SplashViewModel(
            preferences = get(),
            localeController = get(),
            authRepository = get(),
        )
    }
    viewModel { ValueCarouselViewModel(preferences = get()) }
    viewModel { LoginViewModel(authRepository = get(), connectivity = get()) }

    // A-05 / A-06 / A-07 share one ViewModel; the role comes from the destination, so each
    // register route gets its own instance rather than three duplicated definitions.
    viewModel { (role: UserRole) ->
        RegisterViewModel(
            role = role,
            authRepository = get(),
            preferences = get(),
            connectivity = get(),
        )
    }
}
