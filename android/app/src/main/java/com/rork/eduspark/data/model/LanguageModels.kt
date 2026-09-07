package com.rork.eduspark.data.model

/**
 * Language module models.
 *
 * Mirrors Test-2SY's current product shape: one paid English module, one module-level
 * placement gate, then eight peer learning areas behind that gate.
 */
enum class CefrLevel(val code: String) {
    A1("A1"),
    A2("A2"),
    B1("B1"),
    B2("B2"),
    C1("C1"),
    C2("C2"),
}

enum class LanguageAccessStatus {
    Pending,
    Active,
    ExpiringSoon,
    Expired,
}

enum class LanguageArea(val routeSegment: String) {
    Home("hub"),
    Reading("reading"),
    Listening("listening"),
    Writing("writing"),
    Speaking("speaking"),
    Vocabulary("vocabulary"),
    Journey("journey"),
    Grammar("grammar"),
}

enum class LanguageSkill {
    Reading,
    Listening,
    Writing,
    Speaking,
    Vocabulary,
    Journey,
    Grammar,
}

data class LanguageProduct(
    val id: String,
    val name: String,
    val description: String,
    val priceLabel: String,
    val termDays: Int,
)

data class LanguagePlacementRecommendation(
    val focusSkill: LanguageSkill,
    val strengthSkill: LanguageSkill,
    val startingTopic: String,
    val corrections: List<LanguageCorrection>,
)

data class LanguageCorrection(
    val original: String,
    val corrected: String,
    val explanation: String,
)

data class LanguageAccess(
    val subscribed: Boolean,
    val status: LanguageAccessStatus,
    val product: LanguageProduct,
    val placementCompleted: Boolean,
    val expiresAtLabel: String?,
    val overallLevel: CefrLevel?,
    val targetLevel: CefrLevel?,
    val targetProgressPercent: Int,
    val estimatedTimeToNextLevel: String?,
    val nextAllowedRetakeDateLabel: String?,
    val placementRecommendation: LanguagePlacementRecommendation?,
)

data class LanguageSkillLevel(
    val skill: LanguageSkill,
    val level: CefrLevel?,
    val growthPercent: Int,
    val isStrength: Boolean = false,
    val isFocus: Boolean = false,
)

data class LanguageLearningPathSummary(
    val itemsCompleted: Int,
    val itemsTotal: Int,
    val nextArea: LanguageArea,
    val nextTitle: String,
)

data class LanguageHubSnapshot(
    val access: LanguageAccess,
    val skillLevels: List<LanguageSkillLevel>,
    val learningPath: LanguageLearningPathSummary,
)

enum class LanguagePlacementSection {
    Speaking,
    Listening,
    Reading,
    Writing,
    GrammarVocab,
}

enum class LanguagePlacementQuestionType {
    Speaking,
    ListeningMcq,
    ReadingMcq,
    Writing,
}

data class LanguagePlacementQuestion(
    val id: String,
    val section: LanguagePlacementSection,
    val type: LanguagePlacementQuestionType,
    val title: String,
    val prompt: String,
    val instructions: String,
    val options: List<String> = emptyList(),
    val passage: String? = null,
    val audioSituation: String? = null,
    val minWords: Int? = null,
    val maxWords: Int? = null,
    val sampleAnswer: String? = null,
)

data class LanguagePlacementAttempt(
    val sessionId: String,
    val questions: List<LanguagePlacementQuestion>,
    val currentIndex: Int,
    val answers: Map<String, String>,
    val totalMinutes: Int = 60,
) {
    val currentQuestion: LanguagePlacementQuestion get() = questions[currentIndex]
    val answeredCount: Int get() = answers.size
    val isLastQuestion: Boolean get() = currentIndex >= questions.lastIndex
    val progress: Float get() = if (questions.isEmpty()) 0f else answeredCount.toFloat() / questions.size.toFloat()
}

data class LanguagePlacementSkillResult(
    val skill: LanguageSkill,
    val level: CefrLevel,
    val scorePercent: Int,
    val evidence: String,
)

data class LanguagePlacementReport(
    val recordId: String,
    val completedAtLabel: String,
    val source: String,
    val overallLevel: CefrLevel,
    val confidencePercent: Int,
    val summary: String,
    val skillResults: List<LanguagePlacementSkillResult>,
    val strongestSkill: LanguageSkill,
    val weakestSkill: LanguageSkill,
    val weeksToNextLevel: Int,
    val strengths: List<String>,
    val weaknesses: List<String>,
    val corrections: List<LanguageCorrection>,
    val recommendations: List<String>,
    val recommendedStartingTopic: String,
)

data class LanguagePlacementHistory(
    val recordId: String,
    val completedAtLabel: String,
    val source: String,
    val overallLevel: CefrLevel,
    val skillResults: List<LanguagePlacementSkillResult>,
)

enum class LanguageReadingMode {
    Practice,
    Readiness,
}

enum class LanguageReadingQuestionType {
    Mcq,
    TrueFalse,
    GapFill,
    ShortAnswer,
}

data class LanguageReadingStageNode(
    val level: CefrLevel,
    val stage: String,
    val status: String,
)

data class LanguageReadingHistoryItem(
    val title: String,
    val mode: LanguageReadingMode,
    val scorePercent: Int?,
    val completedAtLabel: String,
)

data class LanguageReadingOverview(
    val currentLevel: CefrLevel,
    val currentStage: String,
    val status: String,
    val masteryPercent: Int,
    val evidenceMet: Int,
    val evidenceTotal: Int,
    val readinessLabel: String,
    val readinessAvailable: Boolean,
    val readinessTarget: String,
    val readinessDetail: String,
    val focusSubskills: List<String>,
    val needMoreSubskills: List<String>,
    val blockers: List<String>,
    val stages: List<LanguageReadingStageNode>,
    val history: List<LanguageReadingHistoryItem>,
)

data class LanguageReadingQuestion(
    val id: String,
    val type: LanguageReadingQuestionType,
    val stem: String,
    val subskill: String,
    val choices: List<String> = emptyList(),
    val correctAnswer: String,
    val explanation: String,
    val sentenceWithBlank: String? = null,
)

data class LanguageReadingAttempt(
    val attemptId: String,
    val mode: LanguageReadingMode,
    val level: CefrLevel,
    val stage: String,
    val topic: String,
    val grammarFocus: String?,
    val title: String,
    val passage: String,
    val questions: List<LanguageReadingQuestion>,
    val answers: Map<String, String>,
) {
    val answeredCount: Int get() = answers.size
    val canSubmit: Boolean get() = questions.isNotEmpty() && questions.all { answers[it.id]?.isNotBlank() == true }
}

data class LanguageReadingQuestionResult(
    val question: LanguageReadingQuestion,
    val submittedAnswer: String,
    val correct: Boolean,
)

data class LanguageReadingResult(
    val scorePercent: Int,
    val passed: Boolean,
    val nextAction: String,
    val questionResults: List<LanguageReadingQuestionResult>,
)

data class LanguageChoiceQuestion(
    val id: String,
    val stem: String,
    val choices: List<String>,
    val correctIndex: Int,
    val explanation: String,
)

data class LanguageListeningSnapshot(
    val officialLevel: CefrLevel,
    val learningStage: String,
    val currentStepHint: String,
    val progressPercent: Int,
    val activeGoalId: String,
    val canStartPromotion: Boolean,
    val hasActiveSession: Boolean,
    val timelineSteps: List<String>,
    val historyEvents: List<String>,
)

data class LanguageListeningLesson(
    val lessonId: String,
    val lessonTitle: String,
    val coachSummary: String,
    val focusItems: List<String>,
    val whyThisLesson: String,
    val rewardText: String,
    val levelLabel: String,
    val goalLabel: String,
    val situation: String,
    val audioInstructions: String,
    val audioSituation: String,
    val questions: List<LanguageChoiceQuestion>,
    val answers: Map<String, Int>,
    val result: LanguageListeningResult? = null,
) {
    val answeredCount: Int get() = answers.size
    val canSubmit: Boolean get() = questions.isNotEmpty() && questions.all { answers[it.id] != null }
}

data class LanguageListeningResult(
    val scorePercent: Int,
    val passed: Boolean,
    val headline: String,
    val summary: String,
    val improved: List<String>,
    val needsPractice: List<String>,
    val nextLessonTeaser: String,
)

data class LanguageWritingSnapshot(
    val officialLevel: CefrLevel,
    val learningStage: String,
    val readinessScore: Int,
    val readinessBand: String,
    val estimatedLessonsRemaining: Int,
    val activeGoalId: String,
    val blockers: List<String>,
    val progressSummary: String,
    val nextMilestone: String,
)

data class LanguageWritingLesson(
    val contentItemId: String,
    val title: String,
    val missionTitle: String,
    val prompt: String,
    val writingContext: String,
    val expectedOutput: String,
    val learningOutcomes: List<String>,
    val instructions: List<String>,
    val checklist: List<String>,
    val officialLevel: CefrLevel,
    val goal: String,
    val minWords: Int,
    val maxWords: Int,
    val draftText: String,
    val revisionNumber: Int,
    val evaluation: LanguageWritingEvaluation? = null,
    val completed: Boolean = false,
) {
    val wordCount: Int get() = draftText.trim().split(Regex("\\s+")).filter { it.isNotBlank() }.size
    val canSubmit: Boolean get() = draftText.isNotBlank()
}

data class LanguageWritingEvaluation(
    val dimensions: List<LanguageWritingDimension>,
    val strengths: List<String>,
    val improvements: List<String>,
    val encouragement: String,
    val mainIssue: String,
    val whyItMatters: String,
    val beforeExample: String,
    val afterExample: String,
    val readyToComplete: Boolean,
    val nextLesson: String,
)

data class LanguageWritingDimension(
    val label: String,
    val scorePercent: Int,
    val note: String,
)

data class LanguageSpeakingSnapshot(
    val officialLevel: CefrLevel,
    val internalStage: String,
    val focusLabel: String,
    val focusReason: String,
    val planSummary: String,
    val lessonTitle: String,
    val alexSecondsRemaining: Int,
    val promotionReadinessPercent: Int,
    val objectives: List<String>,
    val todaySteps: List<String>,
    val weakSkills: List<String>,
    val improvingSkills: List<String>,
    val currentActivityTitle: String,
    val currentActivityInstructions: String,
    val activitiesCompleted: Int,
    val activitiesTotal: Int,
)

data class LanguageSpeakingLesson(
    val packageId: String,
    val title: String,
    val currentSection: String,
    val sectionIndex: Int,
    val sectionTotal: Int,
    val vocabulary: List<String>,
    val teachingBlocks: List<String>,
    val miniPrepPrompt: String,
    val readyForDiscussion: Boolean,
)

data class LanguageSpeakingTurn(
    val role: String,
    val content: String,
    val correction: LanguageCorrection? = null,
    val fluencyScore: Int? = null,
    val grammarScore: Int? = null,
    val vocabularyScore: Int? = null,
    val confidenceScore: Int? = null,
    val pronunciationScore: Int? = null,
)

data class LanguageSpeakingSession(
    val caseTitle: String,
    val setting: String,
    val characterHooks: List<String>,
    val voiceMode: String,
    val recording: Boolean,
    val transcriptDraft: String,
    val turns: List<LanguageSpeakingTurn>,
    val completed: Boolean,
)

data class LanguageVocabularySnapshot(
    val studentLevel: CefrLevel,
    val lessonLevel: CefrLevel,
    val metrics: LanguageVocabularyMetrics,
    val dailyWords: List<LanguageVocabularyCard>,
    val bankCards: List<LanguageVocabularyCard>,
    val currentDailyIndex: Int,
    val dailyGenerated: Boolean,
    val dailyQuiz: LanguageDailyVocabQuiz,
    val challenge: LanguageVocabularyChallenge?,
    val lookup: LanguageVocabularyLookup?,
)

data class LanguageVocabularyMetrics(
    val totalWords: Int,
    val knownWords: Int,
    val dueToday: Int,
    val newWords: Int,
    val reviewedToday: Int,
    val dailyReviewGoal: Int,
    val remainingAiWordsToday: Int,
)

data class LanguageVocabularyCard(
    val id: String,
    val word: String,
    val translationAr: String,
    val example: String,
    val exampleAr: String,
    val partOfSpeech: String,
    val cefrLevel: CefrLevel,
    val status: String,
    val due: Boolean,
    val difficult: Boolean,
    val arabicRevealed: Boolean = false,
    val imageHint: String,
)

data class LanguageVocabularyLookup(
    val word: String,
    val partOfSpeech: String,
    val cefrLevel: CefrLevel,
    val definition: String,
    val exampleSentence: String,
    val pronunciationTip: String,
    val synonyms: List<String>,
)

data class LanguageVocabularyChallenge(
    val contextHint: String,
    val paragraphSegments: List<String>,
    val blanks: List<String>,
    val optionsPool: List<String>,
    val answers: Map<String, String>,
    val checked: Boolean,
    val score: Int,
)

data class LanguageDailyVocabQuiz(
    val items: List<LanguageDailyVocabQuizItem>,
    val started: Boolean,
    val currentIndex: Int,
    val phase: String,
    val guess: String,
    val revealedWord: String,
    val results: List<LanguageDailyVocabQuizResult>,
    val summary: LanguageDailyVocabQuizSummary?,
    val alreadyCompletedToday: Boolean,
)

data class LanguageDailyVocabQuizItem(
    val itemId: String,
    val word: String,
    val definition: String,
    val exampleMasked: String,
)

data class LanguageDailyVocabQuizResult(
    val itemId: String,
    val spellingCorrect: Boolean,
    val spellingNearMiss: Boolean,
    val pronunciationScore: Int?,
)

data class LanguageDailyVocabQuizSummary(
    val spellingCorrect: Int,
    val spellingTotal: Int,
    val pronunciationAverage: Int,
)

enum class LanguageTrackStatus {
    Completed,
    Current,
    Open,
    Locked,
}

data class LanguageJourneyMission(
    val title: String,
    val scenario: String,
    val goal: String,
    val estimatedMinutes: Int,
    val focusGrammar: String,
)

data class LanguageJourneySection(
    val id: String,
    val title: String,
    val kind: String,
    val purpose: String,
    val estimatedMinutes: Int,
    val completed: Boolean = false,
)

data class LanguageJourneyStage(
    val grammarId: String,
    val title: String,
    val cefrLevel: CefrLevel,
    val order: Int,
    val status: LanguageTrackStatus,
    val mission: LanguageJourneyMission,
)

data class LanguageJourneyLevel(
    val cefrLevel: CefrLevel,
    val status: LanguageTrackStatus,
    val completedStages: Int,
    val totalStages: Int,
    val stages: List<LanguageJourneyStage>,
)

data class LanguageJourneySnapshot(
    val greeting: String,
    val currentStageTitle: String,
    val currentGoal: String,
    val currentLevel: CefrLevel,
    val streakDays: Int,
    val todayMinutes: Int,
    val completedStages: Int,
    val totalStages: Int,
    val stageIndex: Int,
    val stageTotal: Int,
    val nextMilestone: String,
    val energyLabel: String,
    val confidencePercent: Int,
    val levels: List<LanguageJourneyLevel>,
    val todayMission: LanguageJourneyMission,
    val previewSections: List<LanguageJourneySection>,
)

data class LanguageJourneySession(
    val sessionId: String,
    val currentGrammarName: String,
    val mission: LanguageJourneyMission,
    val sections: List<LanguageJourneySection>,
    val completed: Boolean = false,
)

data class LanguageGrammarStage(
    val grammarId: String,
    val title: String,
    val cefrLevel: CefrLevel,
    val order: Int,
    val status: LanguageTrackStatus,
    val masteryPercent: Int,
    val estimatedMinutes: Int,
)

data class LanguageGrammarLevel(
    val cefrLevel: CefrLevel,
    val status: LanguageTrackStatus,
    val completedStages: Int,
    val totalStages: Int,
    val stages: List<LanguageGrammarStage>,
)

data class LanguageGrammarSnapshot(
    val currentGrammarId: String,
    val currentName: String,
    val currentCefr: CefrLevel,
    val currentStageIndex: Int,
    val currentStageTotal: Int,
    val completedStages: Int,
    val totalStages: Int,
    val masteryPercent: Int,
    val confidencePercent: Int,
    val estimatedMinutes: Int,
    val recommendation: String,
    val nextGrammarName: String,
    val levels: List<LanguageGrammarLevel>,
)

enum class LanguageGrammarLessonPhase {
    Welcome,
    Mission,
    Learn,
    Practice,
    Speaking,
    Writing,
    Reflection,
    Complete,
}

enum class LanguageGrammarPracticeType {
    Choice,
    FillBlank,
    WordBank,
}

data class LanguageGrammarPracticeItem(
    val id: String,
    val type: LanguageGrammarPracticeType,
    val prompt: String,
    val choices: List<String> = emptyList(),
    val correctAnswer: String,
    val wordBank: List<String> = emptyList(),
    val answer: String = "",
    val checked: Boolean = false,
    val correct: Boolean = false,
    val feedback: String = "",
    val hint: String = "",
)

data class LanguageGrammarTutorMessage(
    val role: String,
    val content: String,
)

data class LanguageGrammarLesson(
    val lessonId: String,
    val grammarId: String,
    val displayName: String,
    val cefrLevel: CefrLevel,
    val phase: LanguageGrammarLessonPhase,
    val lessonGoal: String,
    val missionLine: String,
    val whereUsed: String,
    val whyUseful: String,
    val explanationBlocks: List<String>,
    val examples: List<LanguageCorrection>,
    val practiceItems: List<LanguageGrammarPracticeItem>,
    val speakingPrompt: String,
    val writingPrompt: String,
    val reflectionPrompt: String,
    val summary: String,
    val tutorMessages: List<LanguageGrammarTutorMessage>,
    val tutorDraft: String = "",
    val completed: Boolean = false,
) {
    val phaseIndex: Int get() = LanguageGrammarLessonPhase.entries.indexOf(phase).coerceAtLeast(0)
    val phaseTotal: Int get() = LanguageGrammarLessonPhase.entries.size
    val correctPracticeCount: Int get() = practiceItems.count { it.checked && it.correct }
    val canContinuePractice: Boolean get() = practiceItems.all { it.checked }
}

data class LanguageSkillWorkspace(
    val readingOverview: LanguageReadingOverview,
    val readingAttempt: LanguageReadingAttempt? = null,
    val readingResult: LanguageReadingResult? = null,
    val listening: LanguageListeningSnapshot,
    val listeningLesson: LanguageListeningLesson? = null,
    val writing: LanguageWritingSnapshot,
    val writingLesson: LanguageWritingLesson? = null,
    val speaking: LanguageSpeakingSnapshot,
    val speakingLesson: LanguageSpeakingLesson? = null,
    val speakingSession: LanguageSpeakingSession? = null,
    val vocabulary: LanguageVocabularySnapshot,
    val journey: LanguageJourneySnapshot,
    val journeySession: LanguageJourneySession? = null,
    val grammar: LanguageGrammarSnapshot,
    val grammarLesson: LanguageGrammarLesson? = null,
)
