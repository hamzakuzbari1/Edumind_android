package com.rork.eduspark.data.repository

import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.CefrLevel
import com.rork.eduspark.data.model.LanguageAccess
import com.rork.eduspark.data.model.LanguageDailyVocabQuiz
import com.rork.eduspark.data.model.LanguageGrammarLesson
import com.rork.eduspark.data.model.LanguageGrammarLessonPhase
import com.rork.eduspark.data.model.LanguageJourneySession
import com.rork.eduspark.data.model.LanguageListeningLesson
import com.rork.eduspark.data.model.LanguageHubSnapshot
import com.rork.eduspark.data.model.LanguagePlacementAttempt
import com.rork.eduspark.data.model.LanguagePlacementHistory
import com.rork.eduspark.data.model.LanguagePlacementReport
import com.rork.eduspark.data.model.LanguageReadingAttempt
import com.rork.eduspark.data.model.LanguageReadingMode
import com.rork.eduspark.data.model.LanguageReadingResult
import com.rork.eduspark.data.model.LanguageSkillWorkspace
import com.rork.eduspark.data.model.LanguageSpeakingLesson
import com.rork.eduspark.data.model.LanguageSpeakingSession
import com.rork.eduspark.data.model.LanguageVocabularyChallenge
import com.rork.eduspark.data.model.LanguageVocabularyLookup
import com.rork.eduspark.data.model.LanguageVocabularySnapshot
import com.rork.eduspark.data.model.LanguageWritingLesson
import kotlinx.coroutines.flow.StateFlow

/**
 * LN-01/LN-04 foundation — one product-level English module contract.
 *
 * Test-2SY treats Language access as a module-level entitlement, then gates every
 * learning area behind the AI placement result. The Android foundation mirrors that
 * boundary directly instead of forcing it through school-course entitlement models.
 */
interface LanguageRepository {
    val access: StateFlow<LanguageAccess>
    val skillWorkspace: StateFlow<LanguageSkillWorkspace>

    suspend fun getAccess(): AppResult<LanguageAccess>

    suspend fun subscribeLanguage(): AppResult<LanguageAccess>

    suspend fun getHub(): AppResult<LanguageHubSnapshot>

    suspend fun getPlacementHistory(): AppResult<List<LanguagePlacementHistory>>

    fun startPlacementExam(): LanguagePlacementAttempt

    fun savePlacementAnswer(questionId: String, answer: String): LanguagePlacementAttempt

    fun goToPlacementQuestion(index: Int): LanguagePlacementAttempt

    suspend fun completePlacementExam(): AppResult<LanguagePlacementReport>

    suspend fun skipPlacement(level: CefrLevel): AppResult<LanguagePlacementReport>

    fun startReadingAttempt(mode: LanguageReadingMode): LanguageReadingAttempt

    fun saveReadingAnswer(questionId: String, answer: String): LanguageReadingAttempt

    suspend fun submitReadingAttempt(): AppResult<LanguageReadingResult>

    fun resetReadingResult()

    fun selectListeningGoal(goalId: String): LanguageSkillWorkspace

    fun startListeningLesson(): LanguageListeningLesson

    fun saveListeningAnswer(questionId: String, answerIndex: Int): LanguageListeningLesson

    suspend fun submitListeningLesson(): AppResult<LanguageListeningLesson>

    fun retryListeningLesson(): LanguageListeningLesson?

    fun nextListeningLesson(): LanguageListeningLesson

    fun selectWritingGoal(goalId: String): LanguageSkillWorkspace

    fun startWritingLesson(): LanguageWritingLesson

    fun updateWritingDraft(text: String): LanguageWritingLesson?

    suspend fun submitWritingDraft(complete: Boolean): AppResult<LanguageWritingLesson>

    fun startSpeakingLearning(): LanguageSpeakingLesson

    fun advanceSpeakingLesson(): LanguageSpeakingLesson

    fun openSpeakingDiscussion(): LanguageSpeakingSession

    fun toggleSpeakingRecording(): LanguageSpeakingSession

    fun updateSpeakingTranscript(text: String): LanguageSpeakingSession?

    fun submitSpeakingTurn(): LanguageSpeakingSession?

    fun resetSpeakingConversation(): LanguageSpeakingSession

    fun generateVocabularyBatch(): LanguageVocabularySnapshot

    fun toggleVocabularyArabic(cardId: String): LanguageVocabularySnapshot

    fun gradeVocabularyCard(cardId: String, quality: Int): LanguageVocabularySnapshot

    fun lookupVocabularyWord(word: String): LanguageVocabularyLookup

    fun loadVocabularyChallenge(): LanguageVocabularyChallenge

    fun setVocabularyChallengeAnswer(blank: String, answer: String): LanguageVocabularyChallenge?

    fun checkVocabularyChallenge(): LanguageVocabularyChallenge?

    fun startDailyVocabularyQuiz(): LanguageDailyVocabQuiz

    fun updateDailyVocabularyGuess(value: String): LanguageDailyVocabQuiz

    fun submitDailyVocabularySpelling(): LanguageDailyVocabQuiz

    fun scoreDailyVocabularyPronunciation(score: Int): LanguageDailyVocabQuiz

    fun nextDailyVocabularyQuizWord(): LanguageDailyVocabQuiz

    fun openJourneyStage(grammarId: String): LanguageSkillWorkspace

    fun startJourneySession(): LanguageJourneySession

    fun completeJourneySession(): LanguageSkillWorkspace

    fun startGrammarLesson(grammarId: String? = null): LanguageGrammarLesson

    fun goToGrammarPhase(phase: LanguageGrammarLessonPhase): LanguageGrammarLesson

    fun answerGrammarPractice(itemId: String, answer: String): LanguageGrammarLesson?

    fun checkGrammarPractice(itemId: String): LanguageGrammarLesson?

    fun askGrammarTutor(prompt: String): LanguageGrammarLesson?

    fun updateGrammarTutorDraft(text: String): LanguageGrammarLesson?

    fun completeGrammarLesson(): LanguageSkillWorkspace
}
