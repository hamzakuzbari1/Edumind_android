package com.rork.eduspark.core.ui

import com.rork.eduspark.core.result.AppError

/**
 * The four states every EduSpark screen must ship, plus the offline variant.
 *
 * Design System / Rork Knowledge §7: "Every screen ships four states — loading (skeleton),
 * loaded, empty, error — plus an offline variant where the screen has cached data.
 * No screen is done with only the happy path."
 *
 * [Content.isStale] carries the offline variant: content exists, it came from the local
 * cache, and the screen must show the [com.rork.eduspark.ui.components.state.OfflineBanner]
 * above it rather than an error.
 */
sealed interface UiState<out T> {

    data object Loading : UiState<Nothing>

    data class Content<T>(
        val data: T,
        /** True when this data came from the offline cache and may be out of date. */
        val isStale: Boolean = false,
    ) : UiState<T>

    /** Loaded successfully, but there is nothing to show. Never render this as an error. */
    data class Empty(val reason: EmptyReason = EmptyReason.NoContent) : UiState<Nothing>

    data class Failure(val error: AppError) : UiState<Nothing>
}

enum class EmptyReason {
    /** Nothing has been created yet — invite the user to act. */
    NoContent,

    /** A filter or search returned nothing — invite the user to widen it. */
    NoResults,
}

val UiState<*>.isLoading: Boolean get() = this is UiState.Loading

fun <T> UiState<T>.dataOrNull(): T? = (this as? UiState.Content)?.data
