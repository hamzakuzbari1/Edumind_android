package com.rork.eduspark.ui.screens.teacher

import kotlin.test.Test
import kotlin.test.assertContains
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TeacherLessonUploadPickerMimeTest {

    @Test
    fun pdfPickerAcceptsPdfAndOctetStream() {
        val mimes = lessonUploadAcceptedMimeTypes(TeacherLessonSourceKind.Pdf)
        assertContains(mimes, "application/pdf")
        assertContains(mimes, "application/octet-stream")
    }

    @Test
    fun homeworkPickerAcceptsOfficeTextAndOctetStream() {
        val mimes = lessonUploadAcceptedMimeTypes(TeacherLessonSourceKind.Homework)
        assertContains(mimes, "application/pdf")
        assertContains(mimes, "application/msword")
        assertContains(mimes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assertContains(mimes, "application/vnd.ms-powerpoint")
        assertContains(mimes, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        assertContains(mimes, "text/*")
        assertContains(mimes, "application/octet-stream")
        assertTrue(mimes.none { it == "image/*" })
    }

    @Test
    fun videoAndAudioKeepWildcardFilters() {
        assertEquals(listOf("video/*"), lessonUploadAcceptedMimeTypes(TeacherLessonSourceKind.Video).toList())
        assertEquals(listOf("audio/*"), lessonUploadAcceptedMimeTypes(TeacherLessonSourceKind.Audio).toList())
    }

    @Test
    fun resolvesOctetStreamPdfUsingSourceKindNotExtensionAlone() {
        assertEquals(
            "application/pdf",
            resolveLessonUploadMimeType(
                kind = TeacherLessonSourceKind.Pdf,
                declaredMime = "application/octet-stream",
                filename = "lesson-notes",
            ),
        )
        assertEquals(
            "application/pdf",
            resolveLessonUploadMimeType(
                kind = TeacherLessonSourceKind.Homework,
                declaredMime = "application/octet-stream",
                filename = "homework.pdf",
            ),
        )
        assertEquals(
            "video/mp4",
            resolveLessonUploadMimeType(
                kind = TeacherLessonSourceKind.Video,
                declaredMime = null,
                filename = "clip.mp4",
            ),
        )
        assertEquals(
            "audio/mpeg",
            resolveLessonUploadMimeType(
                kind = TeacherLessonSourceKind.Audio,
                declaredMime = "audio/mpeg",
                filename = "voice.mp3",
            ),
        )
    }
}
