package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.TeacherLessonUploadDraft
import com.rork.eduspark.data.repository.TeacherLessonSelectedFile
import com.rork.eduspark.data.repository.TeacherLessonUploadKind
import com.rork.eduspark.data.repository.TeacherLessonUploadRepository
import com.rork.eduspark.data.repository.TeacherRepository

class MockTeacherLessonUploadRepository(
    private val teacherRepository: TeacherRepository,
) : TeacherLessonUploadRepository {
    override suspend fun uploadLessonFile(
        courseId: String,
        title: String,
        order: Int,
        file: TeacherLessonSelectedFile,
        kind: TeacherLessonUploadKind,
        generateQuiz: Boolean,
        generateNarration: Boolean,
        indexForTutor: Boolean,
    ): AppResult<TeacherLessonUploadDraft> = teacherRepository.startLessonUpload(
        courseId = courseId,
        contentType = if (kind == TeacherLessonUploadKind.Video) LessonContentType.Video else LessonContentType.Pdf,
        mockFileName = file.filename,
        mockTotalBytes = file.sizeBytes,
        title = title,
        order = order,
        generateQuiz = generateQuiz,
        generateNarration = generateNarration,
        indexForTutor = indexForTutor,
    )
}
