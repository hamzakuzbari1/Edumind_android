package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LessonContentType
import com.rork.eduspark.data.model.TeacherCourseCreateRequest
import com.rork.eduspark.data.model.TeacherCourseFormSubject
import com.rork.eduspark.data.model.TeacherCourseStatus
import com.rork.eduspark.data.model.TeacherCourseSummary
import com.rork.eduspark.data.model.TeacherLesson
import com.rork.eduspark.data.model.TeacherLessonStatus
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.teacher.TeacherCourseCreateRequestDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseLessonDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseSubjectOptionDto
import com.rork.eduspark.data.remote.teacher.TeacherCourseUpdateRequestDto
import com.rork.eduspark.data.remote.teacher.TeacherCoursesApi
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherRepository

/**
 * Replaces mock `c1`/`c2` course ids with the existing teacher Course APIs so
 * create, list, detail, lessons, and upload share one real catalog.
 */
internal class TeacherRepositoryWithRemoteCourses(
    private val delegate: TeacherRepository,
    private val api: TeacherCoursesApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : TeacherRepository by delegate {

    override suspend fun getCourses(teacherId: String): AppResult<List<TeacherCourseSummary>> =
        when (val response = authorizedRequest { api.listCourses(it) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.map(TeacherCourseDto::toSummary))
            else -> AppResult.Failure(handleFailure(response))
        }

    override suspend fun getCourseFormSubjects(grade: Grade): AppResult<List<TeacherCourseFormSubject>> =
        when (val response = authorizedRequest { api.getFormContext(it, grade.toTeacherCourseGradeInt()) }) {
            is ApiCallResult.Success -> AppResult.Success(
                response.value.subjects.map(TeacherCourseSubjectOptionDto::toFormSubject),
            )
            else -> AppResult.Failure(handleFailure(response))
        }

    override suspend fun createCourse(request: TeacherCourseCreateRequest): AppResult<TeacherCourseSummary> {
        val subjectId = request.subjectId.toIntOrNull()?.takeIf { it > 0 }
            ?: return AppResult.Failure(AppError.Domain("invalid_subject_id"))
        val body = TeacherCourseCreateRequestDto(
            title = request.title.trim(),
            description = request.description?.trim()?.takeIf { it.isNotEmpty() },
            subjectId = subjectId,
            grade = request.grade.toTeacherCourseGradeInt(),
            price = 0f,
            currency = "SYP",
            isPublished = request.published,
        )
        return when (val response = authorizedRequest { api.createCourse(it, body) }) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toSummary())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun setCoursePublished(
        courseId: String,
        published: Boolean,
    ): AppResult<TeacherCourseSummary> {
        val numericId = courseId.toIntOrNull()?.takeIf { it > 0 }
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        return when (
            val response = authorizedRequest {
                api.updateCourse(it, numericId, TeacherCourseUpdateRequestDto(isPublished = published))
            }
        ) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toSummary())
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getCourse(courseId: String): AppResult<TeacherCourseSummary> {
        val numericId = courseId.toIntOrNull()?.takeIf { it > 0 }
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        return when (val listed = getCourses(teacherId = "")) {
            is AppResult.Success -> listed.data.firstOrNull { it.id == numericId.toString() }
                ?.let { AppResult.Success(it) }
                ?: AppResult.Failure(AppError.NotFound)
            is AppResult.Failure -> listed
        }
    }

    override suspend fun getLessons(courseId: String): AppResult<List<TeacherLesson>> {
        val numericId = courseId.toIntOrNull()?.takeIf { it > 0 }
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        return when (val response = authorizedRequest { api.listLessons(it, numericId) }) {
            is ApiCallResult.Success -> AppResult.Success(
                response.value.map { it.toLesson(courseId) }.sortedBy { it.order },
            )
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun getLesson(courseId: String, lessonId: String): AppResult<TeacherLesson> {
        return when (val listed = getLessons(courseId)) {
            is AppResult.Success -> listed.data.firstOrNull { it.id == lessonId }
                ?.let { AppResult.Success(it) }
                ?: AppResult.Failure(AppError.NotFound)
            is AppResult.Failure -> listed
        }
    }

    override suspend fun setLessonVisible(
        courseId: String,
        lessonId: String,
        visible: Boolean,
    ): AppResult<TeacherLesson> {
        val numericCourseId = courseId.toIntOrNull()?.takeIf { it > 0 }
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        val numericLessonId = lessonId.toIntOrNull()?.takeIf { it > 0 }
            ?: return AppResult.Failure(AppError.Domain("invalid_lesson_id"))
        return when (
            val response = authorizedRequest {
                api.updateLessonVisibility(it, numericCourseId, numericLessonId, visible)
            }
        ) {
            is ApiCallResult.Success -> AppResult.Success(response.value.toLesson(courseId))
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    override suspend fun reorderLessons(
        courseId: String,
        orderedLessonIds: List<String>,
    ): AppResult<List<TeacherLesson>> {
        if (courseId.toIntOrNull()?.takeIf { it > 0 } == null) {
            return AppResult.Failure(AppError.Domain("invalid_course_id"))
        }
        return when (val listed = getLessons(courseId)) {
            is AppResult.Success -> AppResult.Success(
                orderedLessonIds.mapIndexedNotNull { index, id ->
                    listed.data.firstOrNull { it.id == id }?.copy(order = index + 1)
                },
            )
            is AppResult.Failure -> listed
        }
    }

    private suspend fun <T> authorizedRequest(
        call: suspend (String) -> ApiCallResult<T>,
    ): ApiCallResult<T> {
        val stored = tokenStore.read() ?: return ApiCallResult.HttpFailure(401)
        val first = call(stored.accessToken)
        if (first !is ApiCallResult.HttpFailure || first.statusCode != 401) return first
        return when (val refreshed = refreshCoordinator.refreshAfterUnauthorized(stored.accessToken)) {
            is AppResult.Success -> call(refreshed.data.accessToken)
            is AppResult.Failure -> ApiCallResult.HttpFailure(401)
        }
    }

    private suspend fun handleFailure(response: ApiCallResult<*>): AppError {
        val error = when (response) {
            ApiCallResult.NetworkFailure -> AppError.Network
            ApiCallResult.InvalidResponse -> AppError.Unknown
            is ApiCallResult.Success -> AppError.Unknown
            is ApiCallResult.HttpFailure -> when (response.statusCode) {
                401 -> AppError.SessionExpired
                403 -> AppError.Forbidden
                404, 410 -> AppError.NotFound
                422 -> if (response.fieldErrors.isNotEmpty()) {
                    AppError.Validation(response.fieldErrors)
                } else {
                    AppError.Domain(response.detail ?: "teacher_courses_validation_failed")
                }
                in 500..599 -> AppError.Server
                else -> AppError.Domain(response.detail ?: "teacher_courses_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

internal fun TeacherCourseDto.toSummary() = TeacherCourseSummary(
    id = id.toString(),
    title = title,
    subjectId = subjectId.toString(),
    subjectTitle = subjectName,
    grade = grade.toTeacherCourseGrade(),
    studentCount = 0,
    lessonCount = lessonCount,
    status = if (isPublished) TeacherCourseStatus.Published else TeacherCourseStatus.Draft,
)

internal fun TeacherCourseSubjectOptionDto.toFormSubject() = TeacherCourseFormSubject(
    id = id.toString(),
    name = nameAr,
    grade = grade.toTeacherCourseGrade(),
)

internal fun TeacherCourseLessonDto.toLesson(courseId: String) = TeacherLesson(
    id = id.toString(),
    courseId = courseId,
    title = title,
    order = sortOrder,
    contentType = if (hasVideo || !videoUrl.isNullOrBlank()) LessonContentType.Video else LessonContentType.Pdf,
    status = toTeacherLessonStatus(),
)

internal fun TeacherCourseLessonDto.toTeacherLessonStatus(): TeacherLessonStatus = when {
    status.equals("processing", ignoreCase = true) -> TeacherLessonStatus.Processing
    !isVisible || status.equals("error", ignoreCase = true) -> TeacherLessonStatus.Draft
    else -> TeacherLessonStatus.Published
}

internal fun Int.toTeacherCourseGrade(): Grade = when (this) {
    10 -> Grade.Grade10
    11 -> Grade.Grade11
    else -> Grade.Baccalaureate
}

internal fun Grade.toTeacherCourseGradeInt(): Int = when (this) {
    Grade.Grade10 -> 10
    Grade.Grade11 -> 11
    Grade.Baccalaureate -> 12
}
