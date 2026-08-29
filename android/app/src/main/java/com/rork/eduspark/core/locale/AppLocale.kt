package com.rork.eduspark.core.locale

import android.content.Context
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat

/**
 * Supported locales.
 *
 * Design System §6.9: "Adding a third language must require zero code changes — only a new
 * locale bundle and a direction flag. No language names in component logic, ever."
 *
 * Consequently nothing outside this file branches on a language: components ask for
 * [AppLocale.isRtl] or simply use start/end layout, which Compose resolves from the
 * configuration. Adding Kurdish or French means one entry here, one values-xx bundle,
 * and one line in res/xml/locales_config.xml.
 */
enum class AppLocale(
    val tag: String,
    val isRtl: Boolean,
) {
    /** Primary locale — Arabic is the design language, not a translation. */
    Arabic(tag = "ar", isRtl = true),

    English(tag = "en", isRtl = false);

    companion object {
        val Default: AppLocale = Arabic

        fun fromTag(tag: String?): AppLocale? =
            entries.firstOrNull { tag != null && tag.startsWith(it.tag, ignoreCase = true) }
    }
}

/**
 * Applies and reads the per-app locale.
 *
 * Uses AppCompat's per-app language API, which persists the choice itself
 * (see `autoStoreLocales` in the manifest) and recreates the activity so
 * `LayoutDirection` flips correctly. That recreation is the moment screen
 * **A-13 · Locale Switch Transition** is designed to cover.
 */
class LocaleController(private val appContext: Context) {

    fun current(): AppLocale {
        val applied = AppCompatDelegate.getApplicationLocales()
        val tag = if (!applied.isEmpty) applied[0]?.language else null
        return AppLocale.fromTag(tag)
            ?: AppLocale.fromTag(systemLanguageTag())
            ?: AppLocale.Default
    }

    /** True before the user has ever passed the A-01 language gate. */
    fun hasExplicitChoice(): Boolean = !AppCompatDelegate.getApplicationLocales().isEmpty

    /**
     * Persists [locale] and triggers the framework locale change.
     * The hosting activity is recreated by the system when the direction flips.
     */
    fun apply(locale: AppLocale) {
        AppCompatDelegate.setApplicationLocales(
            LocaleListCompat.forLanguageTags(locale.tag)
        )
    }

    private fun systemLanguageTag(): String? {
        val configLocales = appContext.resources.configuration.locales
        return if (configLocales.isEmpty) null else configLocales[0].language
    }
}
