package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.TeacherExperienceInfo
import com.rork.eduspark.data.model.TeacherIdentityInfo
import com.rork.eduspark.data.model.TeacherPricingInfo
import com.rork.eduspark.data.model.TeacherProfessionalDocument
import com.rork.eduspark.data.model.TeacherQualification
import com.rork.eduspark.data.model.TeacherSetupDocument
import com.rork.eduspark.data.model.TeacherSetupState
import com.rork.eduspark.data.model.TeacherSetupStepId
import com.rork.eduspark.data.model.TeacherSubjectsGrades
import com.rork.eduspark.data.model.TeacherVoiceSample
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.media.absoluteMediaUrl
import com.rork.eduspark.data.remote.teacher.TeacherPortfolioDto
import com.rork.eduspark.data.remote.teacher.TeacherProfileCvDto
import com.rork.eduspark.data.remote.teacher.TeacherProfileUpdateDto
import com.rork.eduspark.data.remote.teacher.TeacherQualificationWriteDto
import com.rork.eduspark.data.remote.teacher.TeacherSetupApi
import com.rork.eduspark.data.remote.teacher.TeacherSetupStatusDto
import com.rork.eduspark.data.remote.teacher.TeacherSubjectDto
import com.rork.eduspark.data.remote.teacher.TeacherTeachingExperienceWriteDto
import com.rork.eduspark.data.remote.teacher.TeacherTeachingUpdateDto
import com.rork.eduspark.data.remote.teacher.TeacherWhyStudyPointWriteDto
import com.rork.eduspark.data.remote.teacher.TeachingImpactUpdateDto
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.TeacherSetupRepository

internal class RemoteTeacherSetupRepository(
    private val api: TeacherSetupApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
    private val apiBaseUrl: String,
) : TeacherSetupRepository {

    private val localDrafts = mutableMapOf<String, LocalOnlyTeacherSetup>()
    private val lastStates = mutableMapOf<String, TeacherSetupState>()

    override suspend fun getSetupState(teacherId: String): AppResult<TeacherSetupState> {
        val status = request(api::status).valueOrReturn { return it }
        val cv = request(api::cv).valueOrReturn { return it }
        val portfolio = request(api::portfolio).valueOrReturn { return it }
        val catalog = loadCatalog(status.grades).valueOrReturn { return it }
        val state = mapState(teacherId, status, cv, portfolio, catalog)
        lastStates[teacherId] = state
        return AppResult.Success(state)
    }

    override suspend fun saveIdentity(
        teacherId: String,
        identity: TeacherIdentityInfo,
    ): AppResult<TeacherSetupState> {
        val bio = identity.headline.ifBlank { identity.bio }.trim().ifBlank { null }
        request {
            api.updateProfile(
                it,
                TeacherProfileUpdateDto(fullName = identity.displayName.trim(), bio = bio),
            )
        }.valueOrReturn { return it }

        val whyStudy = identity.whyStudyWithMe.trim()
        if (whyStudy.isNotEmpty()) {
            val portfolio = request(api::portfolio).valueOrReturn { return it }
            val first = portfolio.whyStudyPoints.minByOrNull { it.sortOrder }
            val body = TeacherWhyStudyPointWriteDto(title = whyStudy.take(255), description = whyStudy)
            if (first == null) {
                request { api.createWhyStudyPoint(it, body) }.valueOrReturn { return it }
            } else {
                request { api.updateWhyStudyPoint(it, first.id, body) }.valueOrReturn { return it }
            }
        }

        when (val refreshed = authRepository.restoreSession()) {
            is AppResult.Failure -> return refreshed
            is AppResult.Success -> Unit
        }
        markLocalComplete(teacherId, TeacherSetupStepId.Identity)
        return getSetupState(teacherId)
    }

    override suspend fun saveSubjectsGrades(
        teacherId: String,
        subjectsGrades: TeacherSubjectsGrades,
    ): AppResult<TeacherSetupState> {
        val grades = subjectsGrades.grades.map(Grade::toBackendGrade).sorted()
        val catalog = loadCatalog(grades).valueOrReturn { return it }
        val requested = subjectsGrades.subjectIds
        val availableKeys = catalog.flatMap { listOf(it.slug, it.id.toString()) }.toSet()
        if (requested.any { it !in availableKeys }) {
            return AppResult.Failure(AppError.Domain("invalid_teacher_subject_id"))
        }
        val subjectIds = catalog
            .filter { it.slug in requested || it.id.toString() in requested }
            .map { it.id }
            .distinct()
            .sorted()
        if (grades.isEmpty() || subjectIds.isEmpty()) {
            return AppResult.Failure(AppError.Validation(emptyMap()))
        }
        request {
            api.updateTeaching(it, TeacherTeachingUpdateDto(subjectIds = subjectIds, grades = grades))
        }.valueOrReturn { return it }
        markLocalComplete(teacherId, TeacherSetupStepId.SubjectsGrades)
        return getSetupState(teacherId)
    }

    override suspend fun saveQualifications(
        teacherId: String,
        qualifications: List<TeacherQualification>,
    ): AppResult<TeacherSetupState> {
        val current = request(api::cv).valueOrReturn { return it }.qualifications
        val currentIds = current.map { it.id }.toSet()
        val retainedIds = mutableSetOf<Int>()
        qualifications.forEachIndexed { index, qualification ->
            val body = TeacherQualificationWriteDto(
                title = qualification.title.trim(),
                institution = qualification.institution.trim().ifBlank { null },
                year = qualification.year?.toIntOrNull(),
                sortOrder = index,
            )
            val numericId = qualification.id.toIntOrNull()?.takeIf { it in currentIds }
            if (numericId == null) {
                request { api.createQualification(it, body) }.valueOrReturn { return it }
            } else {
                retainedIds += numericId
                request { api.updateQualification(it, numericId, body) }.valueOrReturn { return it }
            }
        }
        currentIds.minus(retainedIds).forEach { id ->
            request { api.deleteQualification(it, id) }.valueOrReturn { return it }
        }
        markLocalComplete(teacherId, TeacherSetupStepId.Qualifications)
        return getSetupState(teacherId)
    }

    override suspend fun saveExperience(
        teacherId: String,
        experience: TeacherExperienceInfo,
    ): AppResult<TeacherSetupState> {
        val portfolio = request(api::portfolio).valueOrReturn { return it }
        val impact = portfolio.teachingImpact
        request {
            api.updateImpact(
                it,
                TeachingImpactUpdateDto(
                    totalStudentsTaught = impact.totalStudentsTaught,
                    grade12StudentsTaught = impact.grade12StudentsTaught,
                    studentsCompletedSubject = impact.studentsCompletedSubject,
                    studentsExcellentGrades = impact.studentsExcellentGrades,
                    yearsTeachingSubject = experience.yearsOfExperience,
                ),
            )
        }.valueOrReturn { return it }

        val description = experience.description.trim()
        if (description.isNotEmpty()) {
            val cv = request(api::cv).valueOrReturn { return it }
            val first = cv.teachingExperiences.minByOrNull { it.sortOrder }
            val body = TeacherTeachingExperienceWriteDto(
                title = description.take(255),
                description = description,
                sortOrder = first?.sortOrder ?: 0,
            )
            if (first == null) {
                request { api.createExperience(it, body) }.valueOrReturn { return it }
            } else {
                request { api.updateExperience(it, first.id, body) }.valueOrReturn { return it }
            }
        }

        local(teacherId).teachingModes = experience.teachingModes
        markLocalComplete(teacherId, TeacherSetupStepId.Experience)
        return getSetupState(teacherId)
    }

    override suspend fun saveDocuments(
        teacherId: String,
        documents: List<TeacherSetupDocument>,
    ): AppResult<TeacherSetupState> = updateLocal(teacherId, TeacherSetupStepId.Documents) {
        it.documents = documents
    }

    override suspend fun savePricing(
        teacherId: String,
        pricing: TeacherPricingInfo,
    ): AppResult<TeacherSetupState> = updateLocal(teacherId, TeacherSetupStepId.Pricing) {
        it.pricing = pricing
    }

    override suspend fun saveVoiceSample(
        teacherId: String,
        voiceSample: TeacherVoiceSample,
    ): AppResult<TeacherSetupState> = updateLocal(teacherId, TeacherSetupStepId.VoiceSample) {
        it.voiceSample = voiceSample
    }

    override suspend fun uploadAvatar(
        teacherId: String,
        bytes: ByteArray,
        filename: String,
        mimeType: String,
    ): AppResult<TeacherSetupState> {
        if (bytes.isEmpty()) {
            return AppResult.Failure(AppError.Domain("empty_avatar_file"))
        }
        request {
            api.uploadAvatar(
                accessToken = it,
                bytes = bytes,
                filename = filename,
                mimeType = mimeType,
            )
        }.valueOrReturn { return it }
        return getSetupState(teacherId)
    }

    override suspend fun finishSetup(teacherId: String): AppResult<TeacherSetupState> {
        request(api::complete).valueOrReturn { return it }
        when (val refreshed = authRepository.restoreSession()) {
            is AppResult.Failure -> return refreshed
            is AppResult.Success -> if (refreshed.data?.hasCompletedOnboarding != true) {
                return AppResult.Failure(AppError.Domain("teacher_setup_not_complete"))
            }
        }
        local(teacherId).completedStepIds += TeacherSetupStepId.entries
        return getSetupState(teacherId)
    }

    private suspend fun loadCatalog(grades: List<Int>): AppResult<List<TeacherSubjectDto>> {
        val rows = mutableListOf<TeacherSubjectDto>()
        grades.distinct().forEach { grade ->
            val result = request { api.subjects(it, grade) }
            when (result) {
                is AppResult.Success -> rows += result.data
                is AppResult.Failure -> return result
            }
        }
        return AppResult.Success(rows.distinctBy { it.id })
    }

    private fun mapState(
        teacherId: String,
        status: TeacherSetupStatusDto,
        cv: TeacherProfileCvDto,
        portfolio: TeacherPortfolioDto,
        catalog: List<TeacherSubjectDto>,
    ): TeacherSetupState {
        val local = local(teacherId)
        val subjectIds = status.subjectIds.map { id ->
            catalog.firstOrNull { it.id == id }?.slug ?: id.toString()
        }.toSet()
        val grades = status.grades.mapNotNull(Int::toDomainGrade).toSet()
        val completed = if (status.setupComplete) {
            TeacherSetupStepId.entries.toSet()
        } else {
            buildSet {
                addAll(local.completedStepIds)
                if (!status.bio.isNullOrBlank()) add(TeacherSetupStepId.Identity)
                if (subjectIds.isNotEmpty() && grades.isNotEmpty()) add(TeacherSetupStepId.SubjectsGrades)
                if (cv.qualifications.isNotEmpty()) add(TeacherSetupStepId.Qualifications)
                if (cv.teachingExperiences.isNotEmpty() || portfolio.teachingImpact.yearsTeachingSubject != null) {
                    add(TeacherSetupStepId.Experience)
                }
            }
        }
        val firstExperience = cv.teachingExperiences.minByOrNull { it.sortOrder }
        return TeacherSetupState(
            teacherId = teacherId,
            identity = TeacherIdentityInfo(
                displayName = status.displayName ?: status.fullName.orEmpty(),
                headline = status.bio.orEmpty(),
                bio = status.bio.orEmpty(),
                whyStudyWithMe = portfolio.whyStudyPoints
                    .sortedBy { it.sortOrder }
                    .joinToString("\n") { it.description ?: it.title },
                photoUrl = absoluteMediaUrl(
                    status.imageUrl?.takeIf { it.isNotBlank() } ?: status.avatarUrl,
                    apiBaseUrl,
                ),
            ),
            subjectsGrades = TeacherSubjectsGrades(subjectIds = subjectIds, grades = grades),
            qualifications = cv.qualifications.sortedBy { it.sortOrder }.map {
                TeacherQualification(
                    id = it.id.toString(),
                    title = it.title,
                    institution = it.institution.orEmpty(),
                    year = it.year?.toString(),
                )
            },
            experience = TeacherExperienceInfo(
                yearsOfExperience = portfolio.teachingImpact.yearsTeachingSubject,
                description = firstExperience?.description ?: firstExperience?.title.orEmpty(),
                teachingModes = local.teachingModes,
            ),
            documents = local.documents,
            professionalDocuments = portfolio.professionalDocuments
                .sortedBy { it.sortOrder }
                .map {
                    TeacherProfessionalDocument(
                        id = it.id.toString(),
                        title = it.title,
                        documentType = it.documentType,
                        fileUrl = it.fileUrl,
                        originalFilename = it.originalFilename,
                        mimeType = it.mimeType,
                        sortOrder = it.sortOrder,
                    )
                },
            pricing = local.pricing,
            voiceSample = local.voiceSample,
            completedStepIds = completed,
        )
    }

    private fun updateLocal(
        teacherId: String,
        step: TeacherSetupStepId,
        update: (LocalOnlyTeacherSetup) -> Unit,
    ): AppResult<TeacherSetupState> {
        val local = local(teacherId)
        update(local)
        local.completedStepIds += step
        val current = lastStates[teacherId] ?: TeacherSetupState(teacherId = teacherId)
        val updated = current.copy(
            documents = local.documents,
            pricing = local.pricing,
            voiceSample = local.voiceSample,
            experience = current.experience.copy(teachingModes = local.teachingModes),
            completedStepIds = current.completedStepIds + local.completedStepIds,
        )
        lastStates[teacherId] = updated
        return AppResult.Success(updated)
    }

    private fun local(teacherId: String) = localDrafts.getOrPut(teacherId) { LocalOnlyTeacherSetup() }

    private fun markLocalComplete(teacherId: String, step: TeacherSetupStepId) {
        local(teacherId).completedStepIds += step
    }

    private suspend fun <T> request(call: suspend (String) -> ApiCallResult<T>): AppResult<T> =
        when (val response = authorizedRequest(call)) {
            is ApiCallResult.Success -> AppResult.Success(response.value)
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
                else -> AppError.Domain(response.detail ?: "teacher_setup_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

private class LocalOnlyTeacherSetup(
    var teachingModes: Set<String> = emptySet(),
    var documents: List<TeacherSetupDocument> = emptyList(),
    var pricing: TeacherPricingInfo = TeacherPricingInfo(),
    var voiceSample: TeacherVoiceSample = TeacherVoiceSample(),
    var completedStepIds: Set<TeacherSetupStepId> = emptySet(),
)

private inline fun <T> AppResult<T>.valueOrReturn(onFailure: (AppResult.Failure) -> Nothing): T =
    when (this) {
        is AppResult.Success -> data
        is AppResult.Failure -> onFailure(this)
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
