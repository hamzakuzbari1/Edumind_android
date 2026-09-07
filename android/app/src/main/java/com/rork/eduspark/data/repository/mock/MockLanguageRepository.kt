package com.rork.eduspark.data.repository.mock

import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.CefrLevel
import com.rork.eduspark.data.model.LanguageChoiceQuestion
import com.rork.eduspark.data.model.LanguageAccess
import com.rork.eduspark.data.model.LanguageAccessStatus
import com.rork.eduspark.data.model.LanguageArea
import com.rork.eduspark.data.model.LanguageCorrection
import com.rork.eduspark.data.model.LanguageDailyVocabQuiz
import com.rork.eduspark.data.model.LanguageDailyVocabQuizItem
import com.rork.eduspark.data.model.LanguageDailyVocabQuizResult
import com.rork.eduspark.data.model.LanguageDailyVocabQuizSummary
import com.rork.eduspark.data.model.LanguageGrammarLesson
import com.rork.eduspark.data.model.LanguageGrammarLessonPhase
import com.rork.eduspark.data.model.LanguageGrammarLevel
import com.rork.eduspark.data.model.LanguageGrammarPracticeItem
import com.rork.eduspark.data.model.LanguageGrammarPracticeType
import com.rork.eduspark.data.model.LanguageGrammarSnapshot
import com.rork.eduspark.data.model.LanguageGrammarStage
import com.rork.eduspark.data.model.LanguageGrammarTutorMessage
import com.rork.eduspark.data.model.LanguageHubSnapshot
import com.rork.eduspark.data.model.LanguageJourneyLevel
import com.rork.eduspark.data.model.LanguageJourneyMission
import com.rork.eduspark.data.model.LanguageJourneySection
import com.rork.eduspark.data.model.LanguageJourneySession
import com.rork.eduspark.data.model.LanguageJourneySnapshot
import com.rork.eduspark.data.model.LanguageJourneyStage
import com.rork.eduspark.data.model.LanguageLearningPathSummary
import com.rork.eduspark.data.model.LanguageListeningLesson
import com.rork.eduspark.data.model.LanguageListeningResult
import com.rork.eduspark.data.model.LanguageListeningSnapshot
import com.rork.eduspark.data.model.LanguagePlacementAttempt
import com.rork.eduspark.data.model.LanguagePlacementHistory
import com.rork.eduspark.data.model.LanguagePlacementQuestion
import com.rork.eduspark.data.model.LanguagePlacementQuestionType
import com.rork.eduspark.data.model.LanguagePlacementRecommendation
import com.rork.eduspark.data.model.LanguagePlacementReport
import com.rork.eduspark.data.model.LanguagePlacementSection
import com.rork.eduspark.data.model.LanguagePlacementSkillResult
import com.rork.eduspark.data.model.LanguageProduct
import com.rork.eduspark.data.model.LanguageReadingAttempt
import com.rork.eduspark.data.model.LanguageReadingHistoryItem
import com.rork.eduspark.data.model.LanguageReadingMode
import com.rork.eduspark.data.model.LanguageReadingOverview
import com.rork.eduspark.data.model.LanguageReadingQuestion
import com.rork.eduspark.data.model.LanguageReadingQuestionResult
import com.rork.eduspark.data.model.LanguageReadingQuestionType
import com.rork.eduspark.data.model.LanguageReadingResult
import com.rork.eduspark.data.model.LanguageReadingStageNode
import com.rork.eduspark.data.model.LanguageSkill
import com.rork.eduspark.data.model.LanguageSkillLevel
import com.rork.eduspark.data.model.LanguageSkillWorkspace
import com.rork.eduspark.data.model.LanguageSpeakingLesson
import com.rork.eduspark.data.model.LanguageSpeakingSession
import com.rork.eduspark.data.model.LanguageSpeakingSnapshot
import com.rork.eduspark.data.model.LanguageSpeakingTurn
import com.rork.eduspark.data.model.LanguageTrackStatus
import com.rork.eduspark.data.model.LanguageVocabularyCard
import com.rork.eduspark.data.model.LanguageVocabularyChallenge
import com.rork.eduspark.data.model.LanguageVocabularyLookup
import com.rork.eduspark.data.model.LanguageVocabularyMetrics
import com.rork.eduspark.data.model.LanguageVocabularySnapshot
import com.rork.eduspark.data.model.LanguageWritingDimension
import com.rork.eduspark.data.model.LanguageWritingEvaluation
import com.rork.eduspark.data.model.LanguageWritingLesson
import com.rork.eduspark.data.model.LanguageWritingSnapshot
import com.rork.eduspark.data.repository.LanguageRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class MockLanguageRepository : LanguageRepository {

    private val product = LanguageProduct(
        id = "english-annual",
        name = "Learn English",
        description = "An annual subscription that includes a placement test and a personalized path across reading, listening, writing, and speaking.",
        priceLabel = "75,000 SYP",
        termDays = 365,
    )

    private var subscribed = false
    private var latestReport: LanguagePlacementReport? = null
    private var attempt: LanguagePlacementAttempt? = null
    private val history = mutableListOf<LanguagePlacementHistory>()
    private var practiceCompletions = mapOf(
        LanguageSkill.Reading to 0,
        LanguageSkill.Listening to 0,
        LanguageSkill.Writing to 0,
        LanguageSkill.Speaking to 0,
        LanguageSkill.Vocabulary to 0,
        LanguageSkill.Journey to 0,
        LanguageSkill.Grammar to 0,
    )

    private val _access = MutableStateFlow(buildAccess())
    override val access: StateFlow<LanguageAccess> = _access.asStateFlow()
    private val _skillWorkspace = MutableStateFlow(buildSkillWorkspace())
    override val skillWorkspace: StateFlow<LanguageSkillWorkspace> = _skillWorkspace.asStateFlow()

    override suspend fun getAccess(): AppResult<LanguageAccess> = AppResult.Success(_access.value)

    override suspend fun subscribeLanguage(): AppResult<LanguageAccess> {
        subscribed = true
        publishAccess()
        return AppResult.Success(_access.value)
    }

    override suspend fun getHub(): AppResult<LanguageHubSnapshot> {
        val access = _access.value
        if (!access.subscribed) return AppResult.Failure(AppError.Forbidden)
        if (!access.placementCompleted) return AppResult.Failure(AppError.Domain("language_placement_required"))
        return AppResult.Success(
            LanguageHubSnapshot(
                access = access,
                skillLevels = skillLevelsFor(latestReport),
                learningPath = LanguageLearningPathSummary(
                    itemsCompleted = 7 + practiceCompletions.values.sum(),
                    itemsTotal = 18,
                    nextArea = LanguageArea.Journey,
                    nextTitle = latestReport?.recommendedStartingTopic
                        ?: "Short listening dialogues for school and daily routines",
                ),
            )
        )
    }

    override suspend fun getPlacementHistory(): AppResult<List<LanguagePlacementHistory>> =
        AppResult.Success(history.toList())

    override fun startPlacementExam(): LanguagePlacementAttempt {
        val next = LanguagePlacementAttempt(
            sessionId = "mock-language-placement",
            questions = placementQuestions,
            currentIndex = 0,
            answers = emptyMap(),
        )
        attempt = next
        return next
    }

    override fun savePlacementAnswer(questionId: String, answer: String): LanguagePlacementAttempt {
        val current = attempt ?: startPlacementExam()
        val next = current.copy(answers = current.answers + (questionId to answer))
        attempt = next
        return next
    }

    override fun goToPlacementQuestion(index: Int): LanguagePlacementAttempt {
        val current = attempt ?: startPlacementExam()
        val next = current.copy(currentIndex = index.coerceIn(0, current.questions.lastIndex))
        attempt = next
        return next
    }

    override suspend fun completePlacementExam(): AppResult<LanguagePlacementReport> {
        val current = attempt ?: return AppResult.Failure(AppError.Domain("language_exam_not_started"))
        if (current.answers.size < current.questions.size) {
            return AppResult.Failure(AppError.Validation(mapOf("placement" to "Answer every section before finishing.")))
        }
        val report = buildReport(source = "AI exam", baseline = null)
        saveReport(report)
        attempt = null
        return AppResult.Success(report)
    }

    override suspend fun skipPlacement(level: CefrLevel): AppResult<LanguagePlacementReport> {
        val report = buildReport(source = "Baseline selection", baseline = level)
        saveReport(report)
        attempt = null
        return AppResult.Success(report)
    }

    override fun startReadingAttempt(mode: LanguageReadingMode): LanguageReadingAttempt {
        val next = readingAttemptTemplate.copy(
            attemptId = "reading-${mode.name.lowercase()}-${practiceCompletions[LanguageSkill.Reading] ?: 0}",
            mode = mode,
            answers = emptyMap(),
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(readingAttempt = next, readingResult = null)
        return next
    }

    override fun saveReadingAnswer(questionId: String, answer: String): LanguageReadingAttempt {
        val current = _skillWorkspace.value.readingAttempt ?: startReadingAttempt(LanguageReadingMode.Practice)
        val next = current.copy(answers = current.answers + (questionId to answer))
        _skillWorkspace.value = _skillWorkspace.value.copy(readingAttempt = next)
        return next
    }

    override suspend fun submitReadingAttempt(): AppResult<LanguageReadingResult> {
        val current = _skillWorkspace.value.readingAttempt
            ?: return AppResult.Failure(AppError.Domain("reading_attempt_not_started"))
        if (!current.canSubmit) return AppResult.Failure(AppError.Validation(mapOf("reading" to "Answer every question.")))
        val rows = current.questions.map { question ->
            val answer = current.answers[question.id].orEmpty()
            LanguageReadingQuestionResult(
                question = question,
                submittedAnswer = answer,
                correct = answer.trim().equals(question.correctAnswer.trim(), ignoreCase = true),
            )
        }
        val score = (rows.count { it.correct } * 100) / rows.size.coerceAtLeast(1)
        val result = LanguageReadingResult(
            scorePercent = score,
            passed = score >= 70,
            nextAction = if (score >= 80) "Readiness evidence added" else "Retry this stage",
            questionResults = rows,
        )
        completePractice(LanguageSkill.Reading)
        val historyItem = LanguageReadingHistoryItem(
            title = current.title,
            mode = current.mode,
            scorePercent = score,
            completedAtLabel = "Today",
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(
            readingOverview = _skillWorkspace.value.readingOverview.copy(
                masteryPercent = (_skillWorkspace.value.readingOverview.masteryPercent + 6).coerceAtMost(100),
                evidenceMet = (_skillWorkspace.value.readingOverview.evidenceMet + 1).coerceAtMost(_skillWorkspace.value.readingOverview.evidenceTotal),
                history = listOf(historyItem) + _skillWorkspace.value.readingOverview.history.take(2),
                blockers = if (score >= 80) emptyList() else _skillWorkspace.value.readingOverview.blockers,
            ),
            readingResult = result,
        )
        publishAccess()
        return AppResult.Success(result)
    }

    override fun resetReadingResult() {
        _skillWorkspace.value = _skillWorkspace.value.copy(readingAttempt = null, readingResult = null)
    }

    override fun selectListeningGoal(goalId: String): LanguageSkillWorkspace {
        _skillWorkspace.value = _skillWorkspace.value.copy(
            listening = _skillWorkspace.value.listening.copy(activeGoalId = goalId)
        )
        return _skillWorkspace.value
    }

    override fun startListeningLesson(): LanguageListeningLesson {
        val lesson = listeningLessonTemplate.copy(answers = emptyMap(), result = null)
        _skillWorkspace.value = _skillWorkspace.value.copy(
            listening = _skillWorkspace.value.listening.copy(hasActiveSession = true),
            listeningLesson = lesson,
        )
        return lesson
    }

    override fun saveListeningAnswer(questionId: String, answerIndex: Int): LanguageListeningLesson {
        val current = _skillWorkspace.value.listeningLesson ?: startListeningLesson()
        val next = current.copy(answers = current.answers + (questionId to answerIndex))
        _skillWorkspace.value = _skillWorkspace.value.copy(listeningLesson = next)
        return next
    }

    override suspend fun submitListeningLesson(): AppResult<LanguageListeningLesson> {
        val current = _skillWorkspace.value.listeningLesson
            ?: return AppResult.Failure(AppError.Domain("listening_lesson_not_started"))
        if (!current.canSubmit) return AppResult.Failure(AppError.Validation(mapOf("listening" to "Answer every question.")))
        val score = (current.questions.count { current.answers[it.id] == it.correctIndex } * 100) / current.questions.size.coerceAtLeast(1)
        val result = LanguageListeningResult(
            scorePercent = score,
            passed = score >= 70,
            headline = if (score >= 70) "Great listening work" else "Replay and retry",
            summary = "You identified the main purpose, but fast contractions still need practice.",
            improved = listOf("Main idea from context", "Speaker intention"),
            needsPractice = listOf("Numbers in fast speech", "Reduced forms like gonna and wanna"),
            nextLessonTeaser = "Next clip: asking for directions at a bus stop.",
        )
        completePractice(LanguageSkill.Listening)
        val next = current.copy(result = result)
        _skillWorkspace.value = _skillWorkspace.value.copy(
            listening = _skillWorkspace.value.listening.copy(
                progressPercent = (_skillWorkspace.value.listening.progressPercent + 7).coerceAtMost(100),
                hasActiveSession = false,
                historyEvents = listOf("${score}% listening practice") + _skillWorkspace.value.listening.historyEvents.take(2),
            ),
            listeningLesson = next,
        )
        publishAccess()
        return AppResult.Success(next)
    }

    override fun retryListeningLesson(): LanguageListeningLesson? {
        val current = _skillWorkspace.value.listeningLesson ?: return null
        val next = current.copy(answers = emptyMap(), result = null)
        _skillWorkspace.value = _skillWorkspace.value.copy(listeningLesson = next)
        return next
    }

    override fun nextListeningLesson(): LanguageListeningLesson = startListeningLesson()

    override fun selectWritingGoal(goalId: String): LanguageSkillWorkspace {
        _skillWorkspace.value = _skillWorkspace.value.copy(
            writing = _skillWorkspace.value.writing.copy(activeGoalId = goalId)
        )
        return _skillWorkspace.value
    }

    override fun startWritingLesson(): LanguageWritingLesson {
        val lesson = writingLessonTemplate.copy(draftText = "", revisionNumber = 0, evaluation = null, completed = false)
        _skillWorkspace.value = _skillWorkspace.value.copy(writingLesson = lesson)
        return lesson
    }

    override fun updateWritingDraft(text: String): LanguageWritingLesson? {
        val current = _skillWorkspace.value.writingLesson ?: return null
        val next = current.copy(draftText = text)
        _skillWorkspace.value = _skillWorkspace.value.copy(writingLesson = next)
        return next
    }

    override suspend fun submitWritingDraft(complete: Boolean): AppResult<LanguageWritingLesson> {
        val current = _skillWorkspace.value.writingLesson
            ?: return AppResult.Failure(AppError.Domain("writing_lesson_not_started"))
        if (!current.canSubmit) return AppResult.Failure(AppError.Validation(mapOf("writing" to "Write a draft first.")))
        val ready = current.wordCount >= current.minWords
        val evaluation = LanguageWritingEvaluation(
            dimensions = listOf(
                LanguageWritingDimension("Task response", if (ready) 84 else 62, "You answered the prompt with a clear purpose."),
                LanguageWritingDimension("Grammar", 76, "Watch subject-verb agreement in present simple."),
                LanguageWritingDimension("Vocabulary", 80, "Good everyday vocabulary with room for stronger connectors."),
            ),
            strengths = listOf("Clear opening sentence", "Relevant example from school life"),
            improvements = listOf("Add one reason sentence", "Use because/so to connect ideas"),
            encouragement = "Your message is understandable and friendly.",
            mainIssue = "Some sentences are too short to show B1 control.",
            whyItMatters = "Longer connected sentences help the reader follow your explanation.",
            beforeExample = "I study. I read notes. I sleep.",
            afterExample = "I study my notes first, because it helps me remember the important ideas before I sleep.",
            readyToComplete = ready,
            nextLesson = "Write a short opinion with two supporting reasons.",
        )
        val next = current.copy(
            revisionNumber = current.revisionNumber + 1,
            evaluation = evaluation,
            completed = complete && ready,
        )
        if (next.completed) {
            completePractice(LanguageSkill.Writing)
            _skillWorkspace.value = _skillWorkspace.value.copy(
                writing = _skillWorkspace.value.writing.copy(
                    readinessScore = (_skillWorkspace.value.writing.readinessScore + 5).coerceAtMost(100),
                    estimatedLessonsRemaining = (_skillWorkspace.value.writing.estimatedLessonsRemaining - 1).coerceAtLeast(0),
                ),
                writingLesson = next,
            )
            publishAccess()
        } else {
            _skillWorkspace.value = _skillWorkspace.value.copy(writingLesson = next)
        }
        return AppResult.Success(next)
    }

    override fun startSpeakingLearning(): LanguageSpeakingLesson {
        val next = speakingLessonTemplate.copy(sectionIndex = 1, readyForDiscussion = false)
        _skillWorkspace.value = _skillWorkspace.value.copy(speakingLesson = next)
        return next
    }

    override fun advanceSpeakingLesson(): LanguageSpeakingLesson {
        val current = _skillWorkspace.value.speakingLesson ?: startSpeakingLearning()
        val nextIndex = (current.sectionIndex + 1).coerceAtMost(current.sectionTotal)
        val next = current.copy(
            sectionIndex = nextIndex,
            currentSection = if (nextIndex >= current.sectionTotal) "Guided discussion ready" else "Practice block $nextIndex",
            readyForDiscussion = nextIndex >= current.sectionTotal,
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(
            speaking = _skillWorkspace.value.speaking.copy(activitiesCompleted = nextIndex - 1),
            speakingLesson = next,
        )
        return next
    }

    override fun openSpeakingDiscussion(): LanguageSpeakingSession {
        val session = _skillWorkspace.value.speakingSession ?: speakingSessionTemplate
        _skillWorkspace.value = _skillWorkspace.value.copy(speakingSession = session)
        return session
    }

    override fun toggleSpeakingRecording(): LanguageSpeakingSession {
        val current = _skillWorkspace.value.speakingSession ?: openSpeakingDiscussion()
        val next = current.copy(recording = !current.recording)
        _skillWorkspace.value = _skillWorkspace.value.copy(speakingSession = next)
        return next
    }

    override fun updateSpeakingTranscript(text: String): LanguageSpeakingSession? {
        val current = _skillWorkspace.value.speakingSession ?: return null
        val next = current.copy(transcriptDraft = text)
        _skillWorkspace.value = _skillWorkspace.value.copy(speakingSession = next)
        return next
    }

    override fun submitSpeakingTurn(): LanguageSpeakingSession? {
        val current = _skillWorkspace.value.speakingSession ?: return null
        val text = current.transcriptDraft.ifBlank {
            "I think the science club should meet after school because students have more time."
        }
        val student = LanguageSpeakingTurn(
            role = "user",
            content = text,
            fluencyScore = 78,
            grammarScore = 72,
            vocabularyScore = 80,
            confidenceScore = 74,
            pronunciationScore = 76,
        )
        val assistant = LanguageSpeakingTurn(
            role = "assistant",
            content = "Good. Try adding one more detail about the benefit for your classmates.",
            correction = LanguageCorrection(
                original = "students has more time",
                corrected = "students have more time",
                explanation = "Use have with plural subject students.",
            ),
        )
        val next = current.copy(
            recording = false,
            transcriptDraft = "",
            turns = current.turns + student + assistant,
            completed = current.turns.size >= 2,
        )
        if (next.completed) {
            completePractice(LanguageSkill.Speaking)
            _skillWorkspace.value = _skillWorkspace.value.copy(
                speaking = _skillWorkspace.value.speaking.copy(
                    activitiesCompleted = _skillWorkspace.value.speaking.activitiesCompleted.coerceAtLeast(2),
                    promotionReadinessPercent = (_skillWorkspace.value.speaking.promotionReadinessPercent + 4).coerceAtMost(100),
                ),
                speakingSession = next,
            )
            publishAccess()
        } else {
            _skillWorkspace.value = _skillWorkspace.value.copy(speakingSession = next)
        }
        return next
    }

    override fun resetSpeakingConversation(): LanguageSpeakingSession {
        val next = speakingSessionTemplate
        _skillWorkspace.value = _skillWorkspace.value.copy(speakingSession = next)
        return next
    }

    override fun generateVocabularyBatch(): LanguageVocabularySnapshot {
        val current = _skillWorkspace.value.vocabulary
        val next = current.copy(dailyGenerated = true, currentDailyIndex = 0)
        _skillWorkspace.value = _skillWorkspace.value.copy(vocabulary = next)
        return next
    }

    override fun toggleVocabularyArabic(cardId: String): LanguageVocabularySnapshot {
        val current = _skillWorkspace.value.vocabulary
        fun toggle(card: LanguageVocabularyCard) =
            if (card.id == cardId) card.copy(arabicRevealed = !card.arabicRevealed) else card
        val next = current.copy(
            dailyWords = current.dailyWords.map(::toggle),
            bankCards = current.bankCards.map(::toggle),
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(vocabulary = next)
        return next
    }

    override fun gradeVocabularyCard(cardId: String, quality: Int): LanguageVocabularySnapshot {
        val current = _skillWorkspace.value.vocabulary
        fun grade(card: LanguageVocabularyCard) =
            if (card.id == cardId) {
                card.copy(
                    status = if (quality >= 4) "known" else if (quality == 3) "learning" else "difficult",
                    due = quality < 4,
                    difficult = quality <= 3,
                )
            } else {
                card
            }
        val nextDailyIndex = if (current.dailyWords.any { it.id == cardId }) {
            (current.currentDailyIndex + 1).coerceAtMost(current.dailyWords.lastIndex.coerceAtLeast(0))
        } else {
            current.currentDailyIndex
        }
        val next = current.copy(
            metrics = current.metrics.copy(
                knownWords = current.metrics.knownWords + if (quality >= 4) 1 else 0,
                dueToday = (current.metrics.dueToday - 1).coerceAtLeast(0),
                reviewedToday = (current.metrics.reviewedToday + 1).coerceAtMost(current.metrics.dailyReviewGoal),
                remainingAiWordsToday = (current.metrics.remainingAiWordsToday - 1).coerceAtLeast(0),
            ),
            dailyWords = current.dailyWords.map(::grade),
            bankCards = current.bankCards.map(::grade),
            currentDailyIndex = nextDailyIndex,
        )
        completePractice(LanguageSkill.Vocabulary)
        _skillWorkspace.value = _skillWorkspace.value.copy(vocabulary = next)
        publishAccess()
        return next
    }

    override fun lookupVocabularyWord(word: String): LanguageVocabularyLookup {
        val lookup = LanguageVocabularyLookup(
            word = word.trim().ifBlank { "practice" },
            partOfSpeech = "verb / noun",
            cefrLevel = CefrLevel.A2,
            definition = "To do something again and again so you improve.",
            exampleSentence = "I practice English for twenty minutes every day.",
            pronunciationTip = "Stress the first syllable: PRAK-tis.",
            synonyms = listOf("train", "rehearse", "review"),
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(lookup = lookup)
        )
        return lookup
    }

    override fun loadVocabularyChallenge(): LanguageVocabularyChallenge {
        val challenge = LanguageVocabularyChallenge(
            contextHint = "Use your due school words in one paragraph.",
            paragraphSegments = listOf("Maya made a ", " plan, then she checked her ", " before the exam."),
            blanks = listOf("blank1", "blank2"),
            optionsPool = listOf("careful", "schedule", "confident", "library"),
            answers = mapOf("blank1" to "", "blank2" to ""),
            checked = false,
            score = 0,
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(challenge = challenge)
        )
        return challenge
    }

    override fun setVocabularyChallengeAnswer(blank: String, answer: String): LanguageVocabularyChallenge? {
        val current = _skillWorkspace.value.vocabulary.challenge ?: return null
        val next = current.copy(answers = current.answers + (blank to answer), checked = false)
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(challenge = next)
        )
        return next
    }

    override fun checkVocabularyChallenge(): LanguageVocabularyChallenge? {
        val current = _skillWorkspace.value.vocabulary.challenge ?: return null
        val key = mapOf("blank1" to "careful", "blank2" to "schedule")
        val score = key.count { (blank, answer) -> current.answers[blank] == answer }
        val next = current.copy(checked = true, score = score)
        completePractice(LanguageSkill.Vocabulary)
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(challenge = next)
        )
        publishAccess()
        return next
    }

    override fun startDailyVocabularyQuiz(): LanguageDailyVocabQuiz {
        val next = _skillWorkspace.value.vocabulary.dailyQuiz.copy(
            started = true,
            currentIndex = 0,
            phase = "spelling",
            guess = "",
            revealedWord = "",
            results = emptyList(),
            summary = null,
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(dailyQuiz = next)
        )
        return next
    }

    override fun updateDailyVocabularyGuess(value: String): LanguageDailyVocabQuiz {
        val next = _skillWorkspace.value.vocabulary.dailyQuiz.copy(guess = value)
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(dailyQuiz = next)
        )
        return next
    }

    override fun submitDailyVocabularySpelling(): LanguageDailyVocabQuiz {
        val current = _skillWorkspace.value.vocabulary.dailyQuiz
        val item = current.items.getOrNull(current.currentIndex) ?: return current
        val correct = current.guess.trim().equals(item.word, ignoreCase = true)
        val near = !correct && current.guess.trim().lowercase().take(4) == item.word.lowercase().take(4)
        val next = current.copy(
            phase = "pronunciation",
            revealedWord = item.word,
            results = current.results + LanguageDailyVocabQuizResult(item.itemId, correct, near, pronunciationScore = null),
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(dailyQuiz = next)
        )
        return next
    }

    override fun scoreDailyVocabularyPronunciation(score: Int): LanguageDailyVocabQuiz {
        val current = _skillWorkspace.value.vocabulary.dailyQuiz
        val results = current.results.toMutableList()
        val last = results.lastOrNull() ?: return current
        results[results.lastIndex] = last.copy(pronunciationScore = score)
        val next = current.copy(results = results)
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(dailyQuiz = next)
        )
        return next
    }

    override fun nextDailyVocabularyQuizWord(): LanguageDailyVocabQuiz {
        val current = _skillWorkspace.value.vocabulary.dailyQuiz
        val isLast = current.currentIndex >= current.items.lastIndex
        val next = if (isLast) {
            val scores = current.results.mapNotNull { it.pronunciationScore }
            current.copy(
                summary = LanguageDailyVocabQuizSummary(
                    spellingCorrect = current.results.count { it.spellingCorrect },
                    spellingTotal = current.results.size,
                    pronunciationAverage = if (scores.isEmpty()) 0 else scores.sum() / scores.size,
                ),
                alreadyCompletedToday = true,
            )
        } else {
            current.copy(
                currentIndex = current.currentIndex + 1,
                phase = "spelling",
                guess = "",
                revealedWord = "",
            )
        }
        if (isLast) completePractice(LanguageSkill.Vocabulary)
        _skillWorkspace.value = _skillWorkspace.value.copy(
            vocabulary = _skillWorkspace.value.vocabulary.copy(dailyQuiz = next)
        )
        publishAccess()
        return next
    }

    override fun openJourneyStage(grammarId: String): LanguageSkillWorkspace {
        val currentStage = _skillWorkspace.value.journey.levels
            .flatMap { it.stages }
            .firstOrNull { it.grammarId == grammarId && it.status != LanguageTrackStatus.Locked }
            ?: return _skillWorkspace.value
        _skillWorkspace.value = _skillWorkspace.value.copy(
            journey = _skillWorkspace.value.journey.copy(
                currentStageTitle = currentStage.title,
                currentGoal = currentStage.mission.goal,
                todayMission = currentStage.mission,
            )
        )
        return _skillWorkspace.value
    }

    override fun startJourneySession(): LanguageJourneySession {
        val snapshot = _skillWorkspace.value.journey
        val session = LanguageJourneySession(
            sessionId = "journey-${practiceCompletions[LanguageSkill.Journey] ?: 0}",
            currentGrammarName = snapshot.todayMission.focusGrammar,
            mission = snapshot.todayMission,
            sections = snapshot.previewSections.map { it.copy(completed = false) },
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(journeySession = session)
        return session
    }

    override fun completeJourneySession(): LanguageSkillWorkspace {
        val session = _skillWorkspace.value.journeySession ?: startJourneySession()
        completePractice(LanguageSkill.Journey)
        val nextJourney = _skillWorkspace.value.journey.copy(
            streakDays = _skillWorkspace.value.journey.streakDays + 1,
            todayMinutes = _skillWorkspace.value.journey.todayMinutes + session.mission.estimatedMinutes,
            completedStages = (_skillWorkspace.value.journey.completedStages + 1).coerceAtMost(_skillWorkspace.value.journey.totalStages),
            stageIndex = (_skillWorkspace.value.journey.stageIndex + 1).coerceAtMost(_skillWorkspace.value.journey.stageTotal),
            nextMilestone = "Tomorrow: use present simple in a short speaking mission",
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(
            journey = nextJourney,
            journeySession = session.copy(
                completed = true,
                sections = session.sections.map { it.copy(completed = true) },
            ),
        )
        publishAccess()
        return _skillWorkspace.value
    }

    override fun startGrammarLesson(grammarId: String?): LanguageGrammarLesson {
        val selected = _skillWorkspace.value.grammar.levels
            .flatMap { it.stages }
            .firstOrNull { it.grammarId == (grammarId ?: _skillWorkspace.value.grammar.currentGrammarId) && it.status != LanguageTrackStatus.Locked }
        val lesson = grammarLessonTemplate.copy(
            lessonId = "grammar-${selected?.grammarId ?: _skillWorkspace.value.grammar.currentGrammarId}",
            grammarId = selected?.grammarId ?: _skillWorkspace.value.grammar.currentGrammarId,
            displayName = selected?.title ?: _skillWorkspace.value.grammar.currentName,
            cefrLevel = selected?.cefrLevel ?: _skillWorkspace.value.grammar.currentCefr,
            phase = LanguageGrammarLessonPhase.Welcome,
            practiceItems = grammarLessonTemplate.practiceItems.map { it.copy(answer = "", checked = false, correct = false, feedback = "") },
            tutorMessages = grammarLessonTemplate.tutorMessages,
            tutorDraft = "",
            completed = false,
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(grammarLesson = lesson)
        return lesson
    }

    override fun goToGrammarPhase(phase: LanguageGrammarLessonPhase): LanguageGrammarLesson {
        val current = _skillWorkspace.value.grammarLesson ?: startGrammarLesson()
        val next = current.copy(phase = phase)
        _skillWorkspace.value = _skillWorkspace.value.copy(grammarLesson = next)
        return next
    }

    override fun answerGrammarPractice(itemId: String, answer: String): LanguageGrammarLesson? {
        val current = _skillWorkspace.value.grammarLesson ?: return null
        val next = current.copy(
            practiceItems = current.practiceItems.map {
                if (it.id == itemId) it.copy(answer = answer, checked = false, feedback = "") else it
            }
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(grammarLesson = next)
        return next
    }

    override fun checkGrammarPractice(itemId: String): LanguageGrammarLesson? {
        val current = _skillWorkspace.value.grammarLesson ?: return null
        val next = current.copy(
            practiceItems = current.practiceItems.map { item ->
                if (item.id != itemId) {
                    item
                } else {
                    val cleaned = item.answer.trim().replace(Regex("\\s+"), " ")
                    val correct = cleaned.equals(item.correctAnswer, ignoreCase = true)
                    item.copy(
                        checked = true,
                        correct = correct,
                        feedback = if (correct) "Correct. You used the target form in the right place." else "Review the subject first, then choose am, is, or are.",
                    )
                }
            }
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(grammarLesson = next)
        return next
    }

    override fun updateGrammarTutorDraft(text: String): LanguageGrammarLesson? {
        val current = _skillWorkspace.value.grammarLesson ?: return null
        val next = current.copy(tutorDraft = text)
        _skillWorkspace.value = _skillWorkspace.value.copy(grammarLesson = next)
        return next
    }

    override fun askGrammarTutor(prompt: String): LanguageGrammarLesson? {
        val current = _skillWorkspace.value.grammarLesson ?: return null
        val question = prompt.trim().ifBlank { "Can you explain this with one more example?" }
        val next = current.copy(
            tutorDraft = "",
            tutorMessages = current.tutorMessages +
                LanguageGrammarTutorMessage("user", question) +
                LanguageGrammarTutorMessage("assistant", "Think about the subject first. I am, he/she/it is, and you/we/they are. Try one sentence from your school day."),
        )
        _skillWorkspace.value = _skillWorkspace.value.copy(grammarLesson = next)
        return next
    }

    override fun completeGrammarLesson(): LanguageSkillWorkspace {
        val current = _skillWorkspace.value.grammarLesson ?: startGrammarLesson()
        completePractice(LanguageSkill.Grammar)
        val grammar = _skillWorkspace.value.grammar
        _skillWorkspace.value = _skillWorkspace.value.copy(
            grammar = grammar.copy(
                completedStages = (grammar.completedStages + 1).coerceAtMost(grammar.totalStages),
                masteryPercent = (grammar.masteryPercent + 6).coerceAtMost(100),
                confidencePercent = (grammar.confidencePercent + 5).coerceAtMost(100),
                recommendation = "Next lesson: present simple routines after this grammar block.",
            ),
            grammarLesson = current.copy(phase = LanguageGrammarLessonPhase.Complete, completed = true),
        )
        publishAccess()
        return _skillWorkspace.value
    }

    private fun saveReport(report: LanguagePlacementReport) {
        subscribed = true
        latestReport = report
        history.removeAll { it.recordId == report.recordId }
        history.add(
            0,
            LanguagePlacementHistory(
                recordId = report.recordId,
                completedAtLabel = report.completedAtLabel,
                source = report.source,
                overallLevel = report.overallLevel,
                skillResults = report.skillResults,
            )
        )
        publishAccess()
    }

    private fun publishAccess() {
        _access.value = buildAccess()
    }

    private fun completePractice(skill: LanguageSkill) {
        practiceCompletions = practiceCompletions + (skill to ((practiceCompletions[skill] ?: 0) + 1))
    }

    private fun buildSkillWorkspace(): LanguageSkillWorkspace = LanguageSkillWorkspace(
        readingOverview = LanguageReadingOverview(
            currentLevel = CefrLevel.B1,
            currentStage = "Core",
            status = "active",
            masteryPercent = 64,
            evidenceMet = 3,
            evidenceTotal = 5,
            readinessLabel = "Building",
            readinessAvailable = true,
            readinessTarget = "B1 Advanced",
            readinessDetail = "Complete one more mixed question set before readiness.",
            focusSubskills = listOf("inference 62%", "reference words 68%"),
            needMoreSubskills = listOf("gap fill 1/3", "short answer 1/3"),
            blockers = listOf("Answer more question types.", "Keep your recent score over 70%."),
            stages = CefrLevel.entries.flatMap { level ->
                listOf("Beginner", "Core", "Advanced").map { stage ->
                    val status = when {
                        level.ordinal < CefrLevel.B1.ordinal -> "completed"
                        level == CefrLevel.B1 && stage == "Core" -> "current"
                        level == CefrLevel.B1 && stage == "Advanced" -> "open"
                        else -> "locked"
                    }
                    LanguageReadingStageNode(level, stage, status)
                }
            },
            history = listOf(
                LanguageReadingHistoryItem("Maya's study routine", LanguageReadingMode.Practice, 82, "Today"),
                LanguageReadingHistoryItem("Library notice", LanguageReadingMode.Practice, 74, "Yesterday"),
            ),
        ),
        listening = LanguageListeningSnapshot(
            officialLevel = CefrLevel.A2,
            learningStage = "Core",
            currentStepHint = "Practice short school dialogues, then unlock promotion.",
            progressPercent = 46,
            activeGoalId = "school",
            canStartPromotion = false,
            hasActiveSession = false,
            timelineSteps = listOf("Goal selected", "Daily listening clip", "Promotion test", "Level update"),
            historyEvents = listOf("A2 Core clip 78%", "Direction dialogue 67%"),
        ),
        writing = LanguageWritingSnapshot(
            officialLevel = CefrLevel.B1,
            learningStage = "Core",
            readinessScore = 58,
            readinessBand = "Developing",
            estimatedLessonsRemaining = 4,
            activeGoalId = "school",
            blockers = listOf("Complete two more revised drafts.", "Use connectors in every paragraph."),
            progressSummary = "3 writing missions completed this month",
            nextMilestone = "Write a clear opinion paragraph",
        ),
        speaking = LanguageSpeakingSnapshot(
            officialLevel = CefrLevel.A2,
            internalStage = "Core",
            focusLabel = "Complete answers",
            focusReason = "Placement found short spoken answers with missing details.",
            planSummary = "Learn the language block, discuss a case, then talk live with Alex.",
            lessonTitle = "Explaining a club decision",
            alexSecondsRemaining = 420,
            promotionReadinessPercent = 52,
            objectives = listOf("Give a reason", "Use have/has correctly", "Add one example"),
            todaySteps = listOf("Lesson package", "Guided discussion", "Live Alex practice"),
            weakSkills = listOf("sentence length", "present simple agreement"),
            improvingSkills = listOf("confidence", "vocabulary range"),
            currentActivityTitle = "Science club meeting",
            currentActivityInstructions = "Explain when the club should meet and why.",
            activitiesCompleted = 0,
            activitiesTotal = 3,
        ),
        vocabulary = buildVocabularySnapshot(),
        journey = buildJourneySnapshot(),
        grammar = buildGrammarSnapshot(),
    )

    private val readingAttemptTemplate = LanguageReadingAttempt(
        attemptId = "reading-practice",
        mode = LanguageReadingMode.Practice,
        level = CefrLevel.B1,
        stage = "Core",
        topic = "School routines",
        grammarFocus = "present simple",
        title = "Maya's New Study Routine",
        passage = "Maya used to study late at night, but she often felt tired the next morning. After her teacher suggested a shorter daily plan, Maya began reviewing vocabulary for twenty minutes after school and reading one page before dinner. Her test scores improved because she practiced more often, not because she studied longer.",
        questions = listOf(
            LanguageReadingQuestion(
                id = "r1",
                type = LanguageReadingQuestionType.Mcq,
                stem = "What is the main reason Maya changed her study routine?",
                subskill = "main idea",
                choices = listOf("She wanted more time for sports", "Shorter daily practice worked better", "She stopped reading", "She had fewer words"),
                correctAnswer = "1",
                explanation = "The passage says her scores improved because she practiced more often.",
            ),
            LanguageReadingQuestion(
                id = "r2",
                type = LanguageReadingQuestionType.TrueFalse,
                stem = "Maya began studying for a longer time every night.",
                subskill = "detail",
                choices = listOf("True", "False"),
                correctAnswer = "false",
                explanation = "She changed to a shorter daily plan.",
            ),
            LanguageReadingQuestion(
                id = "r3",
                type = LanguageReadingQuestionType.GapFill,
                stem = "Complete the sentence.",
                subskill = "grammar in context",
                correctAnswer = "often",
                explanation = "Often matches the idea of repeated daily practice.",
                sentenceWithBlank = "Her test scores improved because she practiced more ____.",
            ),
        ),
        answers = emptyMap(),
    )

    private val listeningLessonTemplate = LanguageListeningLesson(
        lessonId = "listen-a2-core-1",
        lessonTitle = "A quiet place to study",
        coachSummary = "Listen for why the speaker chooses the library.",
        focusItems = listOf("main reason", "speaker intention", "homework vocabulary"),
        whyThisLesson = "Your placement showed that fast school dialogues need more evidence.",
        rewardText = "Unlock the next short dialogue after submitting all answers.",
        levelLabel = "A2 Core",
        goalLabel = "School",
        situation = "Two classmates talk after class.",
        audioInstructions = "Play the clip, then answer all questions. Replay is allowed.",
        audioSituation = "Audio mock: Lina asks Omar why he is going to the library. He says the classroom is noisy and he needs to finish the science project before tomorrow.",
        questions = listOf(
            LanguageChoiceQuestion("l1", "Why is Omar going to the library?", listOf("To borrow a novel", "To finish a science project", "To meet his parent"), 1, "He says he needs to finish the science project."),
            LanguageChoiceQuestion("l2", "What problem does he mention?", listOf("The classroom is noisy", "The library is closed", "He lost his notebook"), 0, "The noisy classroom is the reason he chooses the library."),
            LanguageChoiceQuestion("l3", "When is the project due?", listOf("Today", "Tomorrow", "Next week"), 1, "He says before tomorrow."),
        ),
        answers = emptyMap(),
    )

    private val writingLessonTemplate = LanguageWritingLesson(
        contentItemId = "writing-b1-core-1",
        title = "Message before an exam",
        missionTitle = "Write a useful message to a friend",
        prompt = "Write a short message to a friend explaining how you prepare for an important exam.",
        writingContext = "Your friend feels worried and wants a practical plan.",
        expectedOutput = "60-90 words with a reason, example, and friendly closing.",
        learningOutcomes = listOf("Explain a plan", "Use sequence words", "Give one helpful reason"),
        instructions = listOf("Write in English.", "Use first, then, and because.", "Keep the tone friendly."),
        checklist = listOf("A clear opening", "At least one reason", "One example from your routine"),
        officialLevel = CefrLevel.B1,
        goal = "school",
        minWords = 50,
        maxWords = 90,
        draftText = "",
        revisionNumber = 0,
    )

    private val speakingLessonTemplate = LanguageSpeakingLesson(
        packageId = "speak-a2-core-1",
        title = "Explaining a club decision",
        currentSection = "Mission language",
        sectionIndex = 1,
        sectionTotal = 3,
        vocabulary = listOf("meeting", "after school", "because", "I agree", "I suggest"),
        teachingBlocks = listOf("Use because to add a reason.", "Use have with plural nouns: students have time."),
        miniPrepPrompt = "Say one complete sentence about when the club should meet.",
        readyForDiscussion = false,
    )

    private val speakingSessionTemplate = LanguageSpeakingSession(
        caseTitle = "Science club meeting",
        setting = "Your class is choosing a meeting time for the science club.",
        characterHooks = listOf("Lina wants lunch time", "Omar wants after school"),
        voiceMode = "tap-to-record",
        recording = false,
        transcriptDraft = "",
        turns = emptyList(),
        completed = false,
    )

    private fun buildVocabularySnapshot(): LanguageVocabularySnapshot {
        val cards = listOf(
            LanguageVocabularyCard("v1", "schedule", "جدول", "I checked my schedule before the exam.", "راجعت جدولي قبل الامتحان.", "noun", CefrLevel.A2, "learning", due = true, difficult = false, imageHint = "calendar"),
            LanguageVocabularyCard("v2", "careful", "حذر / دقيق", "Be careful when you read the instructions.", "كن دقيقاً عندما تقرأ التعليمات.", "adjective", CefrLevel.A2, "new", due = true, difficult = false, imageHint = "checklist"),
            LanguageVocabularyCard("v3", "confident", "واثق", "She felt confident after practicing.", "شعرت بالثقة بعد التدريب.", "adjective", CefrLevel.B1, "known", due = false, difficult = false, imageHint = "student speaking"),
        )
        return LanguageVocabularySnapshot(
            studentLevel = CefrLevel.A2,
            lessonLevel = CefrLevel.A2,
            metrics = LanguageVocabularyMetrics(
                totalWords = 24,
                knownWords = 9,
                dueToday = 6,
                newWords = 5,
                reviewedToday = 2,
                dailyReviewGoal = 10,
                remainingAiWordsToday = 8,
            ),
            dailyWords = cards,
            bankCards = cards,
            currentDailyIndex = 0,
            dailyGenerated = false,
            dailyQuiz = LanguageDailyVocabQuiz(
                items = listOf(
                    LanguageDailyVocabQuizItem("qv1", "schedule", "A plan that shows times for activities.", "I checked my s_______ before class."),
                    LanguageDailyVocabQuizItem("qv2", "careful", "Trying not to make mistakes.", "Be c_______ with the answer sheet."),
                ),
                started = false,
                currentIndex = 0,
                phase = "spelling",
                guess = "",
                revealedWord = "",
                results = emptyList(),
                summary = null,
                alreadyCompletedToday = false,
            ),
            challenge = null,
            lookup = null,
        )
    }

    private fun buildJourneySnapshot(): LanguageJourneySnapshot {
        val mission = LanguageJourneyMission(
            title = "Help a classmate describe today",
            scenario = "Your AI teacher asks you to explain where people are and how they feel before class.",
            goal = "Use am, is, and are in short school sentences.",
            estimatedMinutes = 18,
            focusGrammar = "Present be",
        )
        val sections = listOf(
            LanguageJourneySection("mission", "Mission brief", "AI teacher", "Understand the daily situation and success goal.", 3),
            LanguageJourneySection("learn", "Tiny lesson", "Explanation", "Review am, is, are with examples.", 5),
            LanguageJourneySection("practice", "Guided practice", "Interactive", "Complete sentences and fix one mistake.", 7),
            LanguageJourneySection("wrap", "Progress update", "Reflection", "Mark the mission complete and preview tomorrow.", 3),
        )
        val levels = listOf(
            journeyLevel(CefrLevel.A1, LanguageTrackStatus.Completed, 3, 3),
            journeyLevel(CefrLevel.A2, LanguageTrackStatus.Current, 1, 3),
            journeyLevel(CefrLevel.B1, LanguageTrackStatus.Locked, 0, 3),
        )
        return LanguageJourneySnapshot(
            greeting = "Good to see you. Today we stay close to one useful mission.",
            currentStageTitle = "A2 Daily Mission 2",
            currentGoal = mission.goal,
            currentLevel = CefrLevel.A2,
            streakDays = 4,
            todayMinutes = 12,
            completedStages = 4,
            totalStages = 9,
            stageIndex = 2,
            stageTotal = 3,
            nextMilestone = "Finish one daily mission to unlock the next A2 speaking scene.",
            energyLabel = "steady",
            confidencePercent = 66,
            levels = levels,
            todayMission = mission,
            previewSections = sections,
        )
    }

    private fun journeyLevel(
        cefr: CefrLevel,
        status: LanguageTrackStatus,
        completed: Int,
        total: Int,
    ): LanguageJourneyLevel {
        val titles = when (cefr) {
            CefrLevel.A1 -> listOf("Meet the teacher", "Classroom basics", "First routine")
            CefrLevel.A2 -> listOf("Ask for help", "Describe today", "Plan after school")
            else -> listOf("Explain opinions", "Tell a short story", "Solve a daily problem")
        }
        val stages = titles.mapIndexed { index, title ->
            val stageStatus = when {
                status == LanguageTrackStatus.Completed -> LanguageTrackStatus.Completed
                status == LanguageTrackStatus.Locked -> LanguageTrackStatus.Locked
                index < completed -> LanguageTrackStatus.Completed
                index == completed -> LanguageTrackStatus.Current
                else -> LanguageTrackStatus.Locked
            }
            LanguageJourneyStage(
                grammarId = "journey-${cefr.code.lowercase()}-${index + 1}",
                title = title,
                cefrLevel = cefr,
                order = index + 1,
                status = stageStatus,
                mission = LanguageJourneyMission(
                    title = title,
                    scenario = "Practice this in a school-life conversation with your AI teacher.",
                    goal = "Complete one useful English mission.",
                    estimatedMinutes = 15 + index,
                    focusGrammar = if (cefr == CefrLevel.A2 && index == 1) "Present be" else "Daily English",
                ),
            )
        }
        return LanguageJourneyLevel(cefr, status, completed, total, stages)
    }

    private fun buildGrammarSnapshot(): LanguageGrammarSnapshot {
        val levels = listOf(
            grammarLevel(CefrLevel.A1, LanguageTrackStatus.Completed, 3, 3),
            grammarLevel(CefrLevel.A2, LanguageTrackStatus.Current, 1, 3),
            grammarLevel(CefrLevel.B1, LanguageTrackStatus.Locked, 0, 3),
        )
        return LanguageGrammarSnapshot(
            currentGrammarId = "gram_be_present",
            currentName = "Present be",
            currentCefr = CefrLevel.A2,
            currentStageIndex = 2,
            currentStageTotal = 3,
            completedStages = 4,
            totalStages = 9,
            masteryPercent = 58,
            confidencePercent = 62,
            estimatedMinutes = 16,
            recommendation = "Start the current grammar lesson, then review mistakes with the tutor.",
            nextGrammarName = "Present simple routines",
            levels = levels,
        )
    }

    private fun grammarLevel(
        cefr: CefrLevel,
        status: LanguageTrackStatus,
        completed: Int,
        total: Int,
    ): LanguageGrammarLevel {
        val titles = when (cefr) {
            CefrLevel.A1 -> listOf("I am / you are", "There is / there are", "Simple questions")
            CefrLevel.A2 -> listOf("Can and cannot", "Present be", "Present simple routines")
            else -> listOf("Past simple stories", "Future plans", "Because and so")
        }
        val stages = titles.mapIndexed { index, title ->
            val stageStatus = when {
                status == LanguageTrackStatus.Completed -> LanguageTrackStatus.Completed
                status == LanguageTrackStatus.Locked -> LanguageTrackStatus.Locked
                index < completed -> LanguageTrackStatus.Completed
                index == completed -> LanguageTrackStatus.Current
                else -> LanguageTrackStatus.Locked
            }
            LanguageGrammarStage(
                grammarId = if (title == "Present be") "gram_be_present" else "gram-${cefr.code.lowercase()}-${index + 1}",
                title = title,
                cefrLevel = cefr,
                order = index + 1,
                status = stageStatus,
                masteryPercent = when (stageStatus) {
                    LanguageTrackStatus.Completed -> 100
                    LanguageTrackStatus.Current -> 58
                    LanguageTrackStatus.Open -> 20
                    LanguageTrackStatus.Locked -> 0
                },
                estimatedMinutes = 12 + index * 2,
            )
        }
        return LanguageGrammarLevel(cefr, status, completed, total, stages)
    }

    private val grammarLessonTemplate = LanguageGrammarLesson(
        lessonId = "grammar-gram_be_present",
        grammarId = "gram_be_present",
        displayName = "Present be",
        cefrLevel = CefrLevel.A2,
        phase = LanguageGrammarLessonPhase.Welcome,
        lessonGoal = "Use am, is, and are to describe people and places.",
        missionLine = "Today your AI teacher helps you describe a classroom scene clearly.",
        whereUsed = "You use this when you introduce yourself, describe friends, and answer simple school questions.",
        whyUseful = "It is the base for many English sentences, so fixing it improves speaking and writing quickly.",
        explanationBlocks = listOf(
            "Use am with I: I am ready.",
            "Use is with he, she, it, and one person or thing.",
            "Use are with you, we, they, and plural nouns.",
        ),
        examples = listOf(
            LanguageCorrection("She are ready.", "She is ready.", "She is one person, so use is."),
            LanguageCorrection("We is in class.", "We are in class.", "We is plural, so use are."),
            LanguageCorrection("I are nervous.", "I am nervous.", "I always uses am."),
        ),
        practiceItems = listOf(
            LanguageGrammarPracticeItem(
                id = "gp1",
                type = LanguageGrammarPracticeType.Choice,
                prompt = "Lina ____ ready for the quiz.",
                choices = listOf("am", "is", "are"),
                correctAnswer = "is",
                hint = "Lina is she.",
            ),
            LanguageGrammarPracticeItem(
                id = "gp2",
                type = LanguageGrammarPracticeType.FillBlank,
                prompt = "Complete: I ____ in the English room.",
                correctAnswer = "am",
                hint = "Use the special form with I.",
            ),
            LanguageGrammarPracticeItem(
                id = "gp3",
                type = LanguageGrammarPracticeType.WordBank,
                prompt = "Build the sentence: They / not / late",
                wordBank = listOf("They", "are", "not", "late"),
                correctAnswer = "They are not late",
                hint = "Plural subject needs are.",
            ),
        ),
        speakingPrompt = "Say one sentence about your classroom using am, is, or are.",
        writingPrompt = "Write two short sentences about your school day.",
        reflectionPrompt = "Which subject word helps you choose the verb?",
        summary = "You practiced choosing am, is, and are from the subject.",
        tutorMessages = listOf(
            LanguageGrammarTutorMessage("assistant", "I am here if this lesson feels confusing. Ask about any example or practice sentence."),
        ),
    )

    private fun buildAccess(): LanguageAccess {
        val report = latestReport
        val overall = report?.overallLevel
        return LanguageAccess(
            subscribed = subscribed,
            status = if (subscribed) LanguageAccessStatus.Active else LanguageAccessStatus.Pending,
            product = product,
            placementCompleted = report != null,
            expiresAtLabel = if (subscribed) "Sep 3, 2027" else null,
            overallLevel = overall,
            targetLevel = nextLevelAfter(overall ?: CefrLevel.B1),
            targetProgressPercent = if (report == null) 0 else 58,
            estimatedTimeToNextLevel = if (report == null) null else "${report.weeksToNextLevel} weeks",
            nextAllowedRetakeDateLabel = if (report == null) null else "Oct 3, 2026",
            placementRecommendation = report?.let {
                LanguagePlacementRecommendation(
                    focusSkill = it.weakestSkill,
                    strengthSkill = it.strongestSkill,
                    startingTopic = it.recommendedStartingTopic,
                    corrections = it.corrections,
                )
            },
        )
    }

    private fun skillLevelsFor(report: LanguagePlacementReport?): List<LanguageSkillLevel> {
        val rows = report?.skillResults.orEmpty()
        val bySkill = rows.associateBy { it.skill }
        return listOf(
            LanguageSkillLevel(
                skill = LanguageSkill.Reading,
                level = bySkill[LanguageSkill.Reading]?.level,
                growthPercent = 12 + (practiceCompletions[LanguageSkill.Reading] ?: 0) * 2,
                isStrength = report?.strongestSkill == LanguageSkill.Reading,
                isFocus = report?.weakestSkill == LanguageSkill.Reading,
            ),
            LanguageSkillLevel(
                skill = LanguageSkill.Listening,
                level = bySkill[LanguageSkill.Listening]?.level,
                growthPercent = 8 + (practiceCompletions[LanguageSkill.Listening] ?: 0) * 2,
                isStrength = report?.strongestSkill == LanguageSkill.Listening,
                isFocus = report?.weakestSkill == LanguageSkill.Listening,
            ),
            LanguageSkillLevel(
                skill = LanguageSkill.Writing,
                level = bySkill[LanguageSkill.Writing]?.level,
                growthPercent = 10 + (practiceCompletions[LanguageSkill.Writing] ?: 0) * 2,
                isStrength = report?.strongestSkill == LanguageSkill.Writing,
                isFocus = report?.weakestSkill == LanguageSkill.Writing,
            ),
            LanguageSkillLevel(
                skill = LanguageSkill.Speaking,
                level = bySkill[LanguageSkill.Speaking]?.level,
                growthPercent = 6 + (practiceCompletions[LanguageSkill.Speaking] ?: 0) * 2,
                isStrength = report?.strongestSkill == LanguageSkill.Speaking,
                isFocus = report?.weakestSkill == LanguageSkill.Speaking,
            ),
            LanguageSkillLevel(
                skill = LanguageSkill.Vocabulary,
                level = report?.overallLevel,
                growthPercent = 7 + (practiceCompletions[LanguageSkill.Vocabulary] ?: 0) * 2,
            ),
            LanguageSkillLevel(
                skill = LanguageSkill.Journey,
                level = report?.overallLevel ?: CefrLevel.A2,
                growthPercent = 44 + (practiceCompletions[LanguageSkill.Journey] ?: 0) * 3,
            ),
            LanguageSkillLevel(
                skill = LanguageSkill.Grammar,
                level = report?.overallLevel ?: CefrLevel.A2,
                growthPercent = 58 + (practiceCompletions[LanguageSkill.Grammar] ?: 0) * 3,
            ),
        )
    }

    private fun buildReport(source: String, baseline: CefrLevel?): LanguagePlacementReport {
        val overall = baseline ?: CefrLevel.B1
        val skillResults = if (baseline != null) {
            listOf(
                LanguagePlacementSkillResult(LanguageSkill.Speaking, baseline, 64, "baseline"),
                LanguagePlacementSkillResult(LanguageSkill.Listening, baseline, 64, "baseline"),
                LanguagePlacementSkillResult(LanguageSkill.Reading, baseline, 64, "baseline"),
                LanguagePlacementSkillResult(LanguageSkill.Writing, baseline, 64, "baseline"),
            )
        } else {
            listOf(
                LanguagePlacementSkillResult(LanguageSkill.Speaking, CefrLevel.A2, 68, "rubric score"),
                LanguagePlacementSkillResult(LanguageSkill.Listening, CefrLevel.A2, 62, "2/3 correct"),
                LanguagePlacementSkillResult(LanguageSkill.Reading, CefrLevel.B1, 82, "3/3 correct"),
                LanguagePlacementSkillResult(LanguageSkill.Writing, CefrLevel.B1, 78, "rubric score"),
            )
        }

        return LanguagePlacementReport(
            recordId = if (baseline == null) "placement-ai-001" else "placement-skip-${baseline.code}",
            completedAtLabel = "Sep 3, 2026",
            source = source,
            overallLevel = overall,
            confidencePercent = if (baseline == null) 86 else 64,
            summary = if (baseline == null) {
                "Your reading and writing are B1-ready. Listening and speaking need focused daily practice before the next level jump."
            } else {
                "You chose ${baseline.code} as your starting level. EduMind will adapt your path from this baseline."
            },
            skillResults = skillResults,
            strongestSkill = if (baseline == null) LanguageSkill.Reading else LanguageSkill.Writing,
            weakestSkill = if (baseline == null) LanguageSkill.Listening else LanguageSkill.Speaking,
            weeksToNextLevel = if (baseline == null) 8 else 10,
            strengths = listOf(
                "You understand the main idea in short school texts.",
                "Your written answers can explain a simple opinion clearly.",
            ),
            weaknesses = listOf(
                "Spoken answers need longer complete sentences.",
                "Listening accuracy drops when the speaker uses everyday contractions.",
            ),
            corrections = listOf(
                LanguageCorrection(
                    original = "I very like study English.",
                    corrected = "I really like studying English.",
                    explanation = "Use an adverb before like, and gerund after like for activities.",
                ),
                LanguageCorrection(
                    original = "She go to school every day.",
                    corrected = "She goes to school every day.",
                    explanation = "Add -s to the verb with he, she, or it in the present simple.",
                ),
            ),
            recommendations = listOf(
                "Start with short listening dialogues before grammar-heavy lessons.",
                "Speak in full answer frames: reason, example, closing sentence.",
                "Review present simple agreement while reading short passages.",
            ),
            recommendedStartingTopic = "Short listening dialogues for school and daily routines",
        )
    }

    private fun nextLevelAfter(level: CefrLevel): CefrLevel? = when (level) {
        CefrLevel.A1 -> CefrLevel.A2
        CefrLevel.A2 -> CefrLevel.B1
        CefrLevel.B1 -> CefrLevel.B2
        CefrLevel.B2 -> CefrLevel.C1
        CefrLevel.C1 -> CefrLevel.C2
        CefrLevel.C2 -> null
    }

    private val placementQuestions = listOf(
        LanguagePlacementQuestion(
            id = "speaking-1",
            section = LanguagePlacementSection.Speaking,
            type = LanguagePlacementQuestionType.Speaking,
            title = "Speaking",
            prompt = "Tell the examiner about your normal school day. Include one thing you enjoy and one thing you want to improve.",
            instructions = "Record or upload your spoken answer, then submit it manually.",
            sampleAnswer = "I go to school in the morning, and I enjoy English because I can use it online. I want to improve my speaking confidence.",
        ),
        LanguagePlacementQuestion(
            id = "listening-1",
            section = LanguagePlacementSection.Listening,
            type = LanguagePlacementQuestionType.ListeningMcq,
            title = "Listening",
            prompt = "Why is the student going to the library after class?",
            instructions = "Play the audio first, then answer the question.",
            audioSituation = "Two classmates talk about homework, a science project, and a quiet place to study.",
            options = listOf(
                "To meet a teacher",
                "To finish a science project",
                "To borrow a novel",
                "To wait for a parent",
            ),
        ),
        LanguagePlacementQuestion(
            id = "reading-1",
            section = LanguagePlacementSection.Reading,
            type = LanguagePlacementQuestionType.ReadingMcq,
            title = "Reading",
            prompt = "What is the main reason Maya changed her study routine?",
            instructions = "Read the passage, then choose the best answer.",
            passage = "Maya used to study late at night, but she often felt tired the next morning. After her teacher suggested a shorter daily plan, Maya began reviewing vocabulary for twenty minutes after school and reading one page before dinner. Her test scores improved because she practiced more often, not because she studied longer.",
            options = listOf(
                "She wanted more time for sports",
                "She learned that shorter daily practice worked better",
                "She stopped reading before dinner",
                "She had fewer vocabulary words",
            ),
        ),
        LanguagePlacementQuestion(
            id = "writing-1",
            section = LanguagePlacementSection.Writing,
            type = LanguagePlacementQuestionType.Writing,
            title = "Writing",
            prompt = "Write a short message to a friend explaining how you prepare for an important exam.",
            instructions = "Write a complete answer with examples.",
            minWords = 40,
            maxWords = 80,
        ),
    )
}
