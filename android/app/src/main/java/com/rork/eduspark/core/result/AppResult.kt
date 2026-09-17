package com.rork.eduspark.core.result

/**
 * Transport-agnostic result returned by every repository.
 *
 * Repositories never leak HTTP, Ktor, or JSON types upward — the UI layer only ever
 * sees [AppResult]. That is the seam which lets the current mock implementations be
 * swapped for the generated FastAPI client without touching a single composable.
 */
sealed interface AppResult<out T> {
    data class Success<T>(val data: T) : AppResult<T>
    data class Failure(val error: AppError) : AppResult<Nothing>
}

inline fun <T, R> AppResult<T>.map(transform: (T) -> R): AppResult<R> = when (this) {
    is AppResult.Success -> AppResult.Success(transform(data))
    is AppResult.Failure -> this
}

inline fun <T> AppResult<T>.onSuccess(block: (T) -> Unit): AppResult<T> {
    if (this is AppResult.Success) block(data)
    return this
}

inline fun <T> AppResult<T>.onFailure(block: (AppError) -> Unit): AppResult<T> {
    if (this is AppResult.Failure) block(error)
    return this
}

fun <T> AppResult<T>.getOrNull(): T? = (this as? AppResult.Success)?.data

/**
 * The error vocabulary of the client.
 *
 * Deliberately small and backend-shape-free: these describe what the *user* has to do,
 * not what the server returned. Mapping real FastAPI error payloads onto these cases is
 * a single adapter written when the generated client lands.
 */
sealed interface AppError {
    /** No usable connection. The screen should fall back to cached content when it has any. */
    data object Offline : AppError

    /** Reached the network but the request timed out or the socket failed. */
    data object Network : AppError

    /** 5xx-class failure. */
    data object Server : AppError

    /** 401 after the single refresh-and-retry path has failed. */
    data object SessionExpired : AppError

    /** 403 — authenticated but not entitled (e.g. unpaid course). */
    data object Forbidden : AppError

    /** 404 / 410 (the backend returns 410 Gone on several deprecated routes). */
    data object NotFound : AppError

    /** Field-level validation rejected by the server, keyed by field name. */
    data class Validation(val fieldErrors: Map<String, String>) : AppError

    /** Domain rule failure carrying a message key resolved by the UI. */
    data class Domain(val code: String) : AppError

    data object Unknown : AppError
}
