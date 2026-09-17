package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.OnboardingTeacher
import com.rork.eduspark.data.model.StudentOnboardingStatus
import com.rork.eduspark.data.model.StudentOnboardingStep
import com.rork.eduspark.data.model.SubjectGroup
import com.rork.eduspark.data.model.SubjectOption
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.onboarding.GradeUpdateDto
import com.rork.eduspark.data.remote.onboarding.OnboardingStatusDto
import com.rork.eduspark.data.remote.onboarding.StudentOnboardingApi
import com.rork.eduspark.data.remote.onboarding.SubjectDto
import com.rork.eduspark.data.remote.onboarding.SubjectsUpdateDto
import com.rork.eduspark.data.remote.onboarding.TeacherChoiceDto
import com.rork.eduspark.data.remote.onboarding.TeacherDto
import com.rork.eduspark.data.remote.onboarding.TeachersUpdateDto
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.OnboardingRepository

internal class RemoteStudentOnboardingRepository(
    private val api: StudentOnboardingApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : OnboardingRepository {

    override suspend fun getStatus(): AppResult<StudentOnboardingStatus> =
        requestAndMap(api::status, OnboardingStatusDto::toDomain)

    override suspend fun getSubjects(grade: Grade): AppResult<List<SubjectOption>> =
        requestAndMap(
            call = { api.subjects(it, grade.toBackendGrade()) },
            mapper = { rows -> rows.map(SubjectDto::toDomain) },
        )

    override suspend fun saveGrade(grade: Grade): AppResult<StudentOnboardingStatus> =
        requestAndMap(
            call = { api.saveGrade(it, GradeUpdateDto(grade.toBackendGrade())) },
            mapper = OnboardingStatusDto::toDomain,
        )

    override suspend fun saveSubjects(subjectIds: Set<String>): AppResult<StudentOnboardingStatus> {
        val ids = subjectIds.mapNumericIds()
            ?: return AppResult.Failure(AppError.Domain("invalid_subject_id"))
        return requestAndMap(
            call = { api.saveSubjects(it, SubjectsUpdateDto(ids)) },
            mapper = OnboardingStatusDto::toDomain,
        )
    }

    override suspend fun getTeachers(
        subjectId: String,
        grade: Grade,
    ): AppResult<List<OnboardingTeacher>> {
        val numericSubjectId = subjectId.toPositiveIntOrNull()
            ?: return AppResult.Failure(AppError.Domain("invalid_subject_id"))
        return requestAndMap(
            call = { api.teachers(it, numericSubjectId, grade.toBackendGrade()) },
            mapper = { rows -> rows.map(TeacherDto::toDomain) },
        )
    }

    override suspend fun saveTeachers(
        teacherIdBySubject: Map<String, String>,
    ): AppResult<StudentOnboardingStatus> {
        val choices = teacherIdBySubject.map { (subjectId, teacherId) ->
            val numericSubjectId = subjectId.toPositiveIntOrNull()
                ?: return AppResult.Failure(AppError.Domain("invalid_subject_id"))
            val numericTeacherId = teacherId.toPositiveIntOrNull()
                ?: return AppResult.Failure(AppError.Domain("invalid_teacher_id"))
            TeacherChoiceDto(numericSubjectId, numericTeacherId)
        }
        return requestAndMap(
            call = { api.saveTeachers(it, TeachersUpdateDto(choices)) },
            mapper = OnboardingStatusDto::toDomain,
        )
    }

    override suspend fun complete(): AppResult<StudentOnboardingStatus> {
        return when (val response = authorizedRequest(api::complete)) {
            is ApiCallResult.Success -> getStatus()
            else -> AppResult.Failure(handleFailure(response))
        }
    }

    private suspend fun <Dto, Domain> requestAndMap(
        call: suspend (String) -> ApiCallResult<Dto>,
        mapper: (Dto) -> Domain?,
    ): AppResult<Domain> = when (val response = authorizedRequest(call)) {
        is ApiCallResult.Success -> mapper(response.value)
            ?.let { AppResult.Success(it) }
            ?: AppResult.Failure(AppError.Unknown)
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
                else -> AppError.Domain(response.detail ?: "onboarding_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

private fun Grade.toBackendGrade(): Int = when (this) {
    Grade.Grade10 -> 10
    Grade.Grade11 -> 11
    Grade.Baccalaureate -> 12
}

private fun Int.toDomainGrade(): Grade? = when (this) {
    10 -> Grade.Grade10
    11 -> Grade.Grade11
    12 -> Grade.Baccalaureate
    else -> null
}

private fun OnboardingStatusDto.toDomain(): StudentOnboardingStatus? {
    val mappedStep = when (step.lowercase()) {
        "grade" -> StudentOnboardingStep.Grade
        "subjects" -> StudentOnboardingStep.Subjects
        "teachers" -> StudentOnboardingStep.Teachers
        "complete" -> StudentOnboardingStep.Complete
        else -> return null
    }
    val mappedGrade = grade?.toDomainGrade()
    if (grade != null && mappedGrade == null) return null
    return StudentOnboardingStatus(
        step = mappedStep,
        grade = mappedGrade,
        onboardingComplete = onboardingComplete,
        selectedSubjectIds = selectedSubjectIds.map(Int::toString).toSet(),
        selectedTeacherIdBySubject = teacherChoices.associate {
            it.subjectId.toString() to it.teacherProfileId.toString()
        },
    )
}

private fun SubjectDto.toDomain() = SubjectOption(
    id = id.toString(),
    name = nameAr,
    slug = slug,
    group = if (slug in setOf("math", "physics", "chemistry", "biology")) {
        SubjectGroup.Core
    } else {
        SubjectGroup.LanguagesAndGeneral
    },
)

private fun TeacherDto.toDomain() = OnboardingTeacher(
    id = id.toString(),
    subjectId = subjectId.toString(),
    name = fullName,
    yearsTeaching = null,
    rating = rating,
    studentCount = studentCount,
    priceLabel = null,
    introClipSeconds = null,
)

private fun String.toPositiveIntOrNull(): Int? = toIntOrNull()?.takeIf { it > 0 }

private fun Set<String>.mapNumericIds(): List<Int>? {
    val mapped = map { it.toPositiveIntOrNull() ?: return null }
    return mapped.sorted()
}
