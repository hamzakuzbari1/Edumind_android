package com.rork.eduspark.data.repository.remote

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.model.ExplanationLength
import com.rork.eduspark.data.model.Grade
import com.rork.eduspark.data.model.LearningGoal
import com.rork.eduspark.data.model.LearningInterest
import com.rork.eduspark.data.model.LearningPreferences
import com.rork.eduspark.data.model.LinkedParent
import com.rork.eduspark.data.model.StudentProfile
import com.rork.eduspark.data.remote.auth.ApiCallResult
import com.rork.eduspark.data.remote.profile.LinkedParentDto
import com.rork.eduspark.data.remote.profile.StudentProfileApi
import com.rork.eduspark.data.remote.profile.StudentProfileDto
import com.rork.eduspark.data.remote.profile.StudentProfileUpdateDto
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.ProfileRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

internal class RemoteProfileRepository(
    private val api: StudentProfileApi,
    private val tokenStore: SecureTokenStore,
    private val refreshCoordinator: AuthRefreshCoordinator,
    private val authRepository: AuthRepository,
) : ProfileRepository {

    private val _profile = MutableStateFlow(emptyProfile())
    override val profile: Flow<StudentProfile> = _profile.asStateFlow()

    private val _linkedParents = MutableStateFlow<List<LinkedParent>>(emptyList())
    override val linkedParents: Flow<List<LinkedParent>> = _linkedParents.asStateFlow()

    private val _learningPreferences = MutableStateFlow(LearningPreferences())
    override val learningPreferences: Flow<LearningPreferences> = _learningPreferences.asStateFlow()

    override suspend fun getProfile(): AppResult<StudentProfile> {
        val profileResponse = authorizedRequest(api::profile)
        if (profileResponse !is ApiCallResult.Success) {
            return AppResult.Failure(handleFailure(profileResponse))
        }
        val codeResponse = authorizedRequest(api::parentLinkCode)
        if (codeResponse !is ApiCallResult.Success) {
            return AppResult.Failure(handleFailure(codeResponse))
        }
        val current = _profile.value
        val updated = current.copy(parentLinkCode = codeResponse.value.linkCode)
        _profile.value = updated
        _learningPreferences.value = profileResponse.value.toPreferences()
        return AppResult.Success(updated)
    }

    override suspend fun updateProfile(
        displayName: String,
        grade: Grade,
        school: String,
    ): AppResult<StudentProfile> {
        val current = _profile.value
        val updated = current.copy(
            displayName = displayName,
            grade = grade,
            school = school,
            avatarInitial = displayName.take(1),
        )
        _profile.value = updated
        return AppResult.Success(updated)
    }

    override suspend fun getLinkedParents(): AppResult<List<LinkedParent>> =
        when (val response = authorizedRequest(api::linkedParents)) {
            is ApiCallResult.Success -> {
                val parents = response.value.parents
                    .filter(LinkedParentDto::isActive)
                    .map(LinkedParentDto::toDomain)
                _linkedParents.value = parents
                AppResult.Success(parents)
            }
            else -> AppResult.Failure(handleFailure(response))
        }

    override suspend fun revokeLinkedParent(parentId: String): AppResult<Unit> {
        _linkedParents.value = _linkedParents.value.filterNot { it.id == parentId }
        return AppResult.Success(Unit)
    }

    override suspend fun getLearningPreferences(): AppResult<LearningPreferences> =
        when (val response = authorizedRequest(api::profile)) {
            is ApiCallResult.Success -> {
                val preferences = response.value.toPreferences()
                _learningPreferences.value = preferences
                AppResult.Success(preferences)
            }
            else -> AppResult.Failure(handleFailure(response))
        }

    override suspend fun updateLearningPreferences(
        preferences: LearningPreferences,
    ): AppResult<LearningPreferences> {
        val response = authorizedRequest {
            api.updateProfile(it, preferences.toUpdateDto())
        }
        return when (response) {
            is ApiCallResult.Success -> {
                val saved = response.value.toPreferences()
                _learningPreferences.value = saved
                AppResult.Success(saved)
            }
            else -> AppResult.Failure(handleFailure(response))
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
                422 -> AppError.Validation(response.fieldErrors)
                in 500..599 -> AppError.Server
                else -> AppError.Domain(response.detail ?: "profile_request_rejected")
            }
        }
        if (error == AppError.SessionExpired) authRepository.signOut()
        return error
    }
}

private fun emptyProfile() = StudentProfile(
    displayName = "",
    grade = Grade.Baccalaureate,
    school = "",
    avatarInitial = "",
    parentLinkCode = "",
)

private fun StudentProfileDto.toPreferences() = LearningPreferences(
    goal = futureGoal.toLearningGoal(),
    explanationLength = preferredExplanationStyle.toExplanationLength(),
    interests = hobbies.mapNotNull(String::toLearningInterest).toSet(),
)

private fun LearningPreferences.toUpdateDto() = StudentProfileUpdateDto(
    hobbies = interests.map(LearningInterest::toBackendValue).sorted(),
    difficulty = "medium",
    learningStyle = "theoretical",
    futureGoal = goal.toBackendValue(),
    preferredExplanationStyle = explanationLength.toBackendValue(),
    personalityMode = "friendly_teacher",
)

private fun LinkedParentDto.toDomain() = LinkedParent(
    id = parentId.toString(),
    name = displayName,
    relationship = relationshipLabel,
    email = "",
)

private fun String.toLearningGoal(): LearningGoal = when (lowercase()) {
    "baccalaureate", "prepare_for_baccalaureate", "exam", "exams" -> LearningGoal.PrepareForBaccalaureate
    "deep_understanding", "deeper_understanding", "understanding" -> LearningGoal.DeeperUnderstanding
    else -> LearningGoal.ImproveGrades
}

private fun LearningGoal.toBackendValue(): String = when (this) {
    LearningGoal.ImproveGrades -> "improve_grades"
    LearningGoal.PrepareForBaccalaureate -> "prepare_for_baccalaureate"
    LearningGoal.DeeperUnderstanding -> "deeper_understanding"
}

private fun String.toExplanationLength(): ExplanationLength = when (lowercase()) {
    "brief", "short" -> ExplanationLength.Brief
    "detailed", "long" -> ExplanationLength.Detailed
    else -> ExplanationLength.Balanced
}

private fun ExplanationLength.toBackendValue(): String = when (this) {
    ExplanationLength.Brief -> "brief"
    ExplanationLength.Balanced -> "normal"
    ExplanationLength.Detailed -> "detailed"
}

private fun String.toLearningInterest(): LearningInterest? = when (lowercase()) {
    "football" -> LearningInterest.Football
    "gaming" -> LearningInterest.Gaming
    "music" -> LearningInterest.Music
    "drawing" -> LearningInterest.Drawing
    else -> null
}

private fun LearningInterest.toBackendValue(): String = when (this) {
    LearningInterest.Football -> "football"
    LearningInterest.Gaming -> "gaming"
    LearningInterest.Music -> "music"
    LearningInterest.Drawing -> "drawing"
}
