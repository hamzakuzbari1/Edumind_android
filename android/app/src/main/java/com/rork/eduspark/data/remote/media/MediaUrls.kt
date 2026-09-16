package com.rork.eduspark.data.remote.media

/**
 * Classifies backend media references returned in API payloads.
 *
 * Signed download URLs are never classified as permanent public media — they must be
 * re-fetched via [MediaRefKind.PrivateDownloadEndpoint] when needed.
 */
enum class MediaRefKind {
    /** Absolute http(s) URL safe to load directly (e.g. public Supabase object). */
    PublicAbsolute,

    /** Legacy local disk path under `/uploads/...`. */
    LegacyUploads,

    /** Private MediaObject resolver path: `/api/media/{id}/download-url`. */
    PrivateDownloadEndpoint,

    /** content:// or file:// local device URI. */
    LocalDevice,

    /** Unrecognized / empty. */
    Unknown,
}

private val PRIVATE_DOWNLOAD_PATH =
    Regex("""^/api/media/(\d+)/download-url/?$""", RegexOption.IGNORE_CASE)

/**
 * Turns backend media paths into loadable URLs for Coil / ImageView when the ref is
 * already public or legacy. Private `/api/media/{id}/download-url` refs must go through
 * [MediaUrlResolver] — do not treat them as permanent media URLs.
 */
fun absoluteMediaUrl(path: String?, apiBaseUrl: String): String? {
    val kind = classifyMediaRef(path)
    return when (kind) {
        MediaRefKind.PublicAbsolute, MediaRefKind.LocalDevice -> path!!.trim()
        MediaRefKind.LegacyUploads -> {
            val raw = path!!.trim()
            val root = apiBaseUrl.trimEnd('/')
            if (raw.startsWith("/")) root + raw else "$root/$raw"
        }
        MediaRefKind.PrivateDownloadEndpoint, MediaRefKind.Unknown -> null
    }
}

fun classifyMediaRef(path: String?): MediaRefKind {
    val raw = path?.trim().orEmpty()
    if (raw.isEmpty()) return MediaRefKind.Unknown
    if (raw.startsWith("content://") || raw.startsWith("file://")) return MediaRefKind.LocalDevice
    if (raw.startsWith("http://") || raw.startsWith("https://")) return MediaRefKind.PublicAbsolute
    if (PRIVATE_DOWNLOAD_PATH.matches(raw)) return MediaRefKind.PrivateDownloadEndpoint
    if (raw.startsWith("/uploads/") || raw.startsWith("uploads/")) return MediaRefKind.LegacyUploads
    // Relative API paths that aren't the download endpoint — treat as host-relative legacy-style.
    if (raw.startsWith("/")) {
        return if (raw.contains("/download-url")) MediaRefKind.PrivateDownloadEndpoint
        else MediaRefKind.LegacyUploads
    }
    return MediaRefKind.Unknown
}

fun parsePrivateMediaId(path: String?): Int? {
    val raw = path?.trim().orEmpty()
    return PRIVATE_DOWNLOAD_PATH.matchEntire(raw)?.groupValues?.getOrNull(1)?.toIntOrNull()
}
