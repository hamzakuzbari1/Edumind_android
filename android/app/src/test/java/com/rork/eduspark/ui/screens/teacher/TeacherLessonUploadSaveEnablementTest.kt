package com.rork.eduspark.ui.screens.teacher

import com.rork.eduspark.data.repository.TeacherLessonSelectedFile
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class TeacherLessonUploadSaveEnablementTest {

    @Test
    fun saveEnabledWhenTitleAndRealPdfBytesPresent() {
        val form = TeacherLessonUploadFormState(
            sourceKind = TeacherLessonSourceKind.Pdf,
            title = "النهايات",
            selectedFile = sampleFile(filename = "limits.pdf", mimeType = "application/pdf"),
        )
        assertTrue(hasTeacherSource(form))
        assertTrue(canSaveLesson(form))
        assertTrue(
            TeacherLessonUploadUiState(form = form, step = 3).primaryActionEnabled,
        )
    }

    @Test
    fun saveDisabledWithoutRealSelectedFileEvenWithTitle() {
        val form = TeacherLessonUploadFormState(
            sourceKind = TeacherLessonSourceKind.Pdf,
            title = "النهايات",
            selectedFile = null,
        )
        assertFalse(hasTeacherSource(form))
        assertFalse(canSaveLesson(form))
        assertFalse(
            TeacherLessonUploadUiState(form = form, step = 3).primaryActionEnabled,
        )
    }

    @Test
    fun saveDisabledForEmptyBytePayload() {
        val form = TeacherLessonUploadFormState(
            sourceKind = TeacherLessonSourceKind.Pdf,
            title = "النهايات",
            selectedFile = sampleFile(bytes = ByteArray(0)),
        )
        assertFalse(hasTeacherSource(form))
        assertFalse(canSaveLesson(form))
    }

    @Test
    fun videoAudioHomeworkAlsoRequireRealSelectedFile() {
        listOf(
            TeacherLessonSourceKind.Video,
            TeacherLessonSourceKind.Audio,
            TeacherLessonSourceKind.Homework,
        ).forEach { kind ->
            assertFalse(
                canSaveLesson(
                    TeacherLessonUploadFormState(sourceKind = kind, title = "درس", selectedFile = null),
                ),
            )
            assertTrue(
                canSaveLesson(
                    TeacherLessonUploadFormState(
                        sourceKind = kind,
                        title = "درس",
                        selectedFile = sampleFile(),
                    ),
                ),
            )
        }
    }

    @Test
    fun videoLinkRequiresUrlNotMockFileFields() {
        assertFalse(
            canSaveLesson(
                TeacherLessonUploadFormState(
                    sourceKind = TeacherLessonSourceKind.VideoLink,
                    title = "درس",
                    videoLink = "",
                ),
            ),
        )
        assertTrue(
            canSaveLesson(
                TeacherLessonUploadFormState(
                    sourceKind = TeacherLessonSourceKind.VideoLink,
                    title = "درس",
                    videoLink = "https://example.com/v.mp4",
                ),
            ),
        )
    }

    private fun sampleFile(
        filename: String = "lesson.pdf",
        mimeType: String = "application/pdf",
        bytes: ByteArray = byteArrayOf(1, 2, 3),
    ) = TeacherLessonSelectedFile(
        uriString = "content://documents/1",
        filename = filename,
        mimeType = mimeType,
        sizeBytes = bytes.size.toLong(),
        bytes = bytes,
    )
}
