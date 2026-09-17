package com.rork.eduspark.data.remote.media

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class MediaUrlsTest {
    @Test
    fun absoluteHttpUrlsPassThrough() {
        assertEquals(
            "https://cdn.supabase.co/storage/v1/object/public/edumind-public/avatars/a.png",
            absoluteMediaUrl(
                "https://cdn.supabase.co/storage/v1/object/public/edumind-public/avatars/a.png",
                "https://api.example.com",
            ),
        )
    }

    @Test
    fun relativeUploadsPrefixedWithApiHost() {
        assertEquals(
            "https://api.example.com/uploads/teachers/1/a.png",
            absoluteMediaUrl("/uploads/teachers/1/a.png", "https://api.example.com/"),
        )
    }

    @Test
    fun privateDownloadEndpointIsNotAbsoluteMediaUrl() {
        assertNull(absoluteMediaUrl("/api/media/42/download-url", "https://api.example.com"))
        assertEquals(
            MediaRefKind.PrivateDownloadEndpoint,
            classifyMediaRef("/api/media/42/download-url"),
        )
        assertEquals(42, parsePrivateMediaId("/api/media/42/download-url"))
    }

    @Test
    fun classifiesPublicLegacyAndLocal() {
        assertEquals(
            MediaRefKind.PublicAbsolute,
            classifyMediaRef("https://cdn.example.com/public/a.png"),
        )
        assertEquals(MediaRefKind.LegacyUploads, classifyMediaRef("/uploads/x.pdf"))
        assertEquals(MediaRefKind.LocalDevice, classifyMediaRef("content://media/1"))
        assertEquals(MediaRefKind.Unknown, classifyMediaRef(""))
    }

    @Test
    fun blankBecomesNull() {
        assertNull(absoluteMediaUrl("  ", "https://api.example.com"))
        assertNull(absoluteMediaUrl(null, "https://api.example.com"))
    }
}
