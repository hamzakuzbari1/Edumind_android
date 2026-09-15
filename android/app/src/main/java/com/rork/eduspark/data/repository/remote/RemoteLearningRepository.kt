package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.ContinueLearningItem
import com.rork.eduspark.data.model.GamificationSnapshot
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LearningPath
import com.rork.eduspark.data.model.LearningStep
import com.rork.eduspark.data.model.LearningUnit
import com.rork.eduspark.data.model.LessonDetail
import com.rork.eduspark.data.model.LessonMediaType
import com.rork.eduspark.data.model.LessonStatus
import com.rork.eduspark.data.model.PlannerItem
import com.rork.eduspark.data.model.StudentCourseSummary
import com.rork.eduspark.data.model.StudentHomeSnapshot
import com.rork.eduspark.data.model.SubjectProgress
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.gamification.StudentGamificationApi
import com.rork.eduspark.data.remote.gamification.toSnapshot
import com.rork.eduspark.data.remote.learning.CourseLessonDto
import com.rork.eduspark.data.remote.learning.GamificationProfileDto
import com.rork.eduspark.data.remote.learning.LessonProgressDto
import com.rork.eduspark.data.remote.learning.LessonProgressUpdateDto
import com.rork.eduspark.data.remote.learning.StudentCourseCardDto
import com.rork.eduspark.data.remote.learning.StudentCourseDetailDto
import com.rork.eduspark.data.remote.learning.StudentCourseResumeLessonDto
import com.rork.eduspark.data.remote.learning.StudentCourseUnitDto
import com.rork.eduspark.data.remote.learning.StudentDashboardDto
import com.rork.eduspark.data.remote.learning.StudentLearningApi
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.LearningRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

class RemoteLearningRepository internal constructor(
    private val api: StudentLearningApi,
    private val gamificationApi: StudentGamificationApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : LearningRepository {

    private val completedLessonIdsFlow = MutableStateFlow<Set<String>>(emptySet())
    override val completedLessonIds: Flow<Set<String>> = completedLessonIdsFlow.asStateFlow()

    private val lessonContext = mutableMapOf<String, LessonContext>()
    private val lessonMediaTypes = mutableMapOf<String, Set<LessonMediaType>>()
    private var latestDashboard: StudentDashboardDto? = null

    override suspend fun getStudentHome(): AppResult<StudentHomeSnapshot> {
        val dashboard = when (val response = authorizedRequest(api::dashboard)) {
            is ApiCallResult.Success -> response.value
            else -> return AppResult.Failure(handleFailure(response))
        }
        latestDashboard = dashboard
        val cards = dashboard.courses.map(StudentCourseCardDto::toSummary)
        val continueItem = dashboard.courses.firstOrNull { it.unlocked }?.let { course ->
            when (val detailResult = fetchCourseDetail(course.id)) {
                is AppResult.Success -> detailResult.data.toContinueItem()
                is AppResult.Failure -> null
            }
        }
        return AppResult.Success(
            StudentHomeSnapshot(
                studentName = "EduMind",
                grade = dashboard.grade.toGrade(),
                streakDays = dashboard.gamification?.currentStreak ?: 0,
                gamification = dashboard.gamification.toDomain(),
                continueItem = continueItem,
                todayPlan = emptyList<PlannerItem>(),
                subjects = cards.map {
                    SubjectProgress(
                        courseId = it.courseId,
                        title = it.title,
                        progress = it.progress,
                        currentLabel = it.currentLabel,
                        teacherName = it.teacherName,
                    )
                },
                hasActiveProject = false,
                englishAvailable = false,
                completedLessonsTotal = cards.sumOf { it.completedLessonCount },
                lastQuizScorePercent = null,
            )
        )
    }

    override suspend fun getPath(pathId: String): AppResult<LearningPath> {
        val courseId = pathId.toPositiveIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_course_id"))
        return fetchCourseDetail(courseId)
    }

    override suspend fun getStudentCourses(): AppResult<List<StudentCourseSummary>> =
        requestAndMap(api::dashboard) { dashboard ->
            latestDashboard = dashboard
            dashboard.courses.map(StudentCourseCardDto::toSummary)
        }

    override suspend fun getGamification(): AppResult<GamificationSnapshot> =
        requestAndMap(gamificationApi::profile) { profile -> profile.toSnapshot() }

    override suspend fun getLesson(lessonId: String): AppResult<LessonDetail> {
        val numericLessonId = lessonId.toPositiveIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_lesson_id"))
        if (tokenStore.read() == null) return AppResult.Failure(AppError.SessionExpired)
        val lessonResponse = authorizedRequest { api.lesson(it, numericLessonId) }
        if (lessonResponse !is ApiCallResult.Success) {
            return AppResult.Failure(handleFailure(lessonResponse))
        }
        val progress = when (val progressResponse = authorizedRequest { api.lessonProgress(it, numericLessonId) }) {
            is ApiCallResult.Success -> progressResponse.value
            else -> null
        }
        val lesson = lessonResponse.value.toLessonDetail(lessonContext[lessonId], progress).let {
            if (lessonId in completedLessonIdsFlow.value) it.copy(isCompleted = true) else it
        }
        lessonMediaTypes[lessonId] = lesson.mediaTypes
        return AppResult.Success(lesson)
    }

    override suspend fun recordLessonStarted(lessonId: String, mediaTypes: Set<LessonMediaType>) {
        val body = LessonProgressUpdateDto(
            videoPercent = if (LessonMediaType.Video in mediaTypes) 1f else null,
            pdfOpened = if (LessonMediaType.Pdf in mediaTypes) true else null,
        )
        updateRemoteProgress(lessonId, body)
    }

    override suspend fun updateLessonProgress(
        lessonId: String,
        videoProgress: Float?,
        pdfProgress: Float?,
        pdfOpened: Boolean?,
    ) {
        updateRemoteProgress(
            lessonId,
            LessonProgressUpdateDto(
                videoPercent = videoProgress?.toPercent(),
                pdfPercent = pdfProgress?.toPercent(),
                pdfOpened = pdfOpened,
            )
        )
    }

    private suspend fun updateRemoteProgress(
        lessonId: String,
        body: LessonProgressUpdateDto,
    ): LessonProgressDto? {
        val numericLessonId = lessonId.toPositiveIntOrNull() ?: return null
        return when (
            val response = authorizedRequest { api.updateLessonProgress(it, numericLessonId, body) }
        ) {
            is ApiCallResult.Success -> {
                if (response.value.isCompleted) {
                    completedLessonIdsFlow.update { it + lessonId }
                }
                response.value
            }
            else -> null
        }
    }

    override suspend fun markLessonCompleted(lessonId: String) {
        val numericLessonId = lessonId.toPositiveIntOrNull() ?: return
        val mediaTypes = lessonMediaTypes[lessonId].orEmpty()
        updateRemoteProgress(
            lessonId,
            LessonProgressUpdateDto(
                videoPercent = if (LessonMediaType.Video in mediaTypes) 100f else null,
                pdfPercent = if (LessonMediaType.Pdf in mediaTypes) 100f else null,
                pdfOpened = if (LessonMediaType.Pdf in mediaTypes) true else null,
            )
        )
        when (val response = authorizedRequest { api.verifyCompletion(it, numericLessonId) }) {
            is ApiCallResult.Success -> {
                if (response.value.success || response.value.progress?.isCompleted == true) {
                    completedLessonIdsFlow.update { it + lessonId }
                }
            }
            else -> Unit
        }
    }

    private suspend fun fetchCourseDetail(courseId: Int): AppResult<LearningPath> =
        requestAndMap(call = { token -> api.course(token, courseId) }) { detail ->
            detail.toLearningPath().also { path ->
                path.units.flatMap { unit -> unit.steps }.forEachIndexed { index, step ->
                    lessonMediaTypes[step.id] = step.mediaTypes
                    lessonContext[step.id] = LessonContext(
                        courseId = path.id,
                        courseTitle = path.title,
                        teacherName = path.teacherName,
                        lessonIndex = index + 1,
                        lessonTotal = path.totalLessonCount.coerceAtLeast(path.steps.size),
                    )
                }
            }
        }

    private suspend fun <Dto, Domain> requestAndMap(
        call: suspend (String) -> ApiCallResult<Dto>,
        mapper: (Dto) -> Domain,
    ): AppResult<Domain> = when (val response = authorizedRequest(call)) {
        is ApiCallResult.Success -> AppResult.Success(mapper(response.value))
        else -> AppResult.Failure(handleFailure(response))
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
                422 -> AppError.Validation(response.fieldErrors)
                in 500..599 -> AppError.Server
                else -> AppError.Domain(response.detail ?: "learning_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

private data class LessonContext(
    val courseId: String,
    val courseTitle: String,
    val teacherName: String,
    val lessonIndex: Int,
    val lessonTotal: Int,
)

private fun StudentCourseCardDto.toSummary() = StudentCourseSummary(
    courseId = id.toString(),
    title = title,
    teacherName = teacherName,
    progress = progressPercent.toProgress(),
    currentLabel = subjectName,
    isEntitled = unlocked,
    isPublished = true,
    completedLessonCount = if (unlocked) completedLessonCount else 0,
    totalLessonCount = lessonCount,
)

private fun StudentCourseDetailDto.toLearningPath(): LearningPath {
    val resumeId = resumeLesson?.lessonId?.toString()
    val mappedUnits = units.map { unit ->
        unit.toDomain(
            courseUnlocked = unlocked,
            resumeLessonId = resumeId,
        )
    }
    val flatSteps = mappedUnits.flatMap { it.steps }
    return LearningPath(
        id = id.toString(),
        title = title,
        subtitle = description ?: subjectName,
        progress = progressPercent.toProgress(),
        steps = flatSteps,
        teacherName = teacherName,
        quizCount = 0,
        isPublished = true,
        isEntitled = unlocked,
        lastUpdatedLabel = "",
        completedLessonCount = if (unlocked) completedLessonCount else 0,
        totalLessonCount = lessonCount.coerceAtLeast(flatSteps.size),
        units = mappedUnits,
    )
}

private fun StudentCourseUnitDto.toDomain(
    courseUnlocked: Boolean,
    resumeLessonId: String?,
) = LearningUnit(
    id = id?.toString(),
    title = title,
    subtitle = description,
    progress = progressPercent.toProgress(),
    completedLessonCount = if (courseUnlocked) completedLessonCount else 0,
    totalLessonCount = lessonCount.coerceAtLeast(lessons.size),
    steps = lessons.sortedWith(compareBy<CourseLessonDto> { it.sortOrder }.thenBy { it.id })
        .map { lesson ->
            lesson.toStep(
                courseUnlocked = courseUnlocked,
                isCurrent = courseUnlocked && lesson.id.toString() == resumeLessonId,
            )
        },
)

private fun CourseLessonDto.toStep(
    courseUnlocked: Boolean,
    isCurrent: Boolean,
) = LearningStep(
    id = id.toString(),
    title = title,
    subtitle = unitTitle ?: description,
    status = toLessonStatus(courseUnlocked),
    isCurrent = isCurrent,
    isCompleted = completed || completionPercent >= 100,
    durationMinutes = defaultDurationMinutes(),
    mediaTypes = mediaTypes(),
    minutesLeft = if (isCurrent) defaultDurationMinutes() else null,
)

private fun CourseLessonDto.toLessonDetail(
    context: LessonContext?,
    progress: LessonProgressDto? = null,
) = LessonDetail(
    id = id.toString(),
    courseId = context?.courseId ?: "",
    courseTitle = context?.courseTitle ?: unitTitle ?: "المادة",
    teacherName = context?.teacherName ?: "",
    title = title,
    status = toLessonStatus(courseUnlocked = true),
    mediaTypes = mediaTypes(),
    durationMinutes = defaultDurationMinutes(),
    pageCount = if (LessonMediaType.Pdf in mediaTypes()) 6 else 0,
    lessonIndex = context?.lessonIndex ?: sortOrder.coerceAtLeast(1),
    lessonTotal = context?.lessonTotal ?: 1,
    isCompleted = completed || completionPercent >= 100 || progress?.isCompleted == true,
    videoProgress = (progress?.videoProgressPercent ?: videoProgressPercent).toProgress(),
    pdfProgress = (progress?.pdfProgressPercent ?: pdfProgressPercent).toProgress(),
    pdfOpened = progress?.pdfOpened ?: false,
    quizId = null,
    keyIdeas = description
        ?.lines()
        ?.map(String::trim)
        ?.filter(String::isNotBlank)
        ?.take(3)
        .orEmpty(),
)

private fun LearningPath.toContinueItem(): ContinueLearningItem? {
    val lessons = units.flatMap { it.steps }
    val lesson = lessons.firstOrNull { it.isCurrent }
        ?: lessons.firstOrNull { !it.isCompleted && it.status == LessonStatus.Processed }
        ?: lessons.firstOrNull()
        ?: return null
    val index = lessons.indexOfFirst { it.id == lesson.id }.takeIf { it >= 0 }?.plus(1) ?: 1
    return ContinueLearningItem(
        lessonId = lesson.id,
        courseId = id,
        lessonTitle = lesson.title,
        subjectTitle = title,
        subjectSubtitle = units.firstOrNull { unit -> unit.steps.any { it.id == lesson.id } }?.title ?: subtitle,
        minutesLeft = lesson.minutesLeft ?: lesson.durationMinutes,
        lessonIndex = index,
        lessonTotal = totalLessonCount.coerceAtLeast(lessons.size),
        mediaTypes = lesson.mediaTypes,
        teacherName = teacherName,
    )
}

private fun CourseLessonDto.toLessonStatus(courseUnlocked: Boolean): LessonStatus {
    if (!courseUnlocked) return LessonStatus.LockedByEntitlement
    return when (status?.lowercase()) {
        "draft" -> LessonStatus.Draft
        "processing" -> LessonStatus.Processing
        "error", "failed" -> LessonStatus.Error
        else -> LessonStatus.Processed
    }
}

private fun CourseLessonDto.mediaTypes(): Set<LessonMediaType> = buildSet {
    val type = lessonType.lowercase()
    if (hasVideo || videoUrl != null || "video" in type) add(LessonMediaType.Video)
    if (hasPdf || pdfUrl != null || homeworkUrl != null || "pdf" in type || "homework" in type) {
        add(LessonMediaType.Pdf)
    }
    if (isEmpty()) add(LessonMediaType.Video)
}

private fun CourseLessonDto.defaultDurationMinutes(): Int = when {
    LessonMediaType.Video in mediaTypes() -> 12
    LessonMediaType.Pdf in mediaTypes() -> 10
    else -> 8
}

private fun GamificationProfileDto?.toDomain() = GamificationSnapshot(
    level = this?.level ?: 1,
    xp = this?.totalXp ?: 0,
    progressToNextLevel = (this?.progressPercent ?: 0).toProgress(),
    streakDays = this?.currentStreak ?: 0,
    xpForNextLevel = this?.xpForLevel ?: this?.xpToNextLevel ?: 0,
)

private fun Int?.toGrade(): Grade = when (this) {
    10 -> Grade.Grade10
    11 -> Grade.Grade11
    else -> Grade.Baccalaureate
}

private fun Int.toProgress(): Float = (this / 100f).coerceIn(0f, 1f)

private fun Float.toProgress(): Float = (this / 100f).coerceIn(0f, 1f)

private fun Float.toPercent(): Float = (this.coerceIn(0f, 1f) * 100f).coerceIn(0f, 100f)

private fun String.toPositiveIntOrNull(): Int? = toIntOrNull()?.takeIf { it > 0 }
