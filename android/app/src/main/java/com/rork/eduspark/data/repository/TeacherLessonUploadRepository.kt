package com.rork.eduspark.data.repository

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.TeacherLessonUploadDraft

data class TeacherLessonSelectedFile(
    val uriString: String,
    val filename: String,
    val mimeType: String,
    val sizeBytes: Long,
    val bytes: ByteArray,
)

enum class TeacherLessonUploadKind { Video, Pdf, Homework, Audio }

interface TeacherLessonUploadRepository {
    suspend fun uploadLessonFile(
        courseId: String,
        title: String,
        order: Int,
        file: TeacherLessonSelectedFile,
        kind: TeacherLessonUploadKind,
        generateQuiz: Boolean,
        generateNarration: Boolean,
        indexForTutor: Boolean,
    ): AppResult<TeacherLessonUploadDraft>
}
