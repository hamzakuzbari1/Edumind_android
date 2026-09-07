package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.CefrLevel
import com.rork.eduspark.data.model.LanguageAccess
import com.rork.eduspark.data.model.LanguageArea
import com.rork.eduspark.data.model.LanguageGrammarLessonPhase
import com.rork.eduspark.data.model.LanguageHubSnapshot
import com.rork.eduspark.data.model.LanguageReadingMode
import com.rork.eduspark.data.model.LanguagePlacementAttempt
import com.rork.eduspark.data.model.LanguagePlacementHistory
import com.rork.eduspark.data.model.LanguagePlacementQuestionType
import com.rork.eduspark.data.model.LanguagePlacementReport
import com.rork.eduspark.data.model.LanguageSkillWorkspace
import com.rork.eduspark.data.repository.LanguageRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class LanguagePlacementStage {
    Intro,
    Exam,
    Evaluating,
    Report,
    History,
}

enum class LanguageReadingStage {
    Overview,
    Practice,
    Results,
}

enum class LanguageListeningTab {
    Journey,
    Practice,
    Promotion,
}

enum class LanguageWritingTab {
    Journey,
    Practice,
    Promotion,
}

enum class LanguageSpeakingTab {
    Journey,
    Lesson,
    Discussion,
    Alex,
    Assessment,
}

enum class LanguageVocabularyTab {
    Daily,
    Bank,
}

enum class LanguageVocabularyFilter {
    All,
    Due,
    Difficult,
}

enum class LanguageJourneyMode {
    Home,
    Session,
    Complete,
}

enum class LanguageGrammarMode {
    Roadmap,
    Lesson,
    Complete,
}

data class LanguageModuleUiState(
    val accessResult: UiState<LanguageAccess> = UiState.Loading,
    val hubResult: UiState<LanguageHubSnapshot> = UiState.Loading,
    val skillWorkspace: LanguageSkillWorkspace? = null,
    val isOnline: Boolean = true,
    val selectedArea: LanguageArea = LanguageArea.Home,
    val readingStage: LanguageReadingStage = LanguageReadingStage.Overview,
    val listeningTab: LanguageListeningTab = LanguageListeningTab.Journey,
    val writingTab: LanguageWritingTab = LanguageWritingTab.Journey,
    val speakingTab: LanguageSpeakingTab = LanguageSpeakingTab.Journey,
    val vocabularyTab: LanguageVocabularyTab = LanguageVocabularyTab.Daily,
    val vocabularyFilter: LanguageVocabularyFilter = LanguageVocabularyFilter.All,
    val journeyMode: LanguageJourneyMode = LanguageJourneyMode.Home,
    val grammarMode: LanguageGrammarMode = LanguageGrammarMode.Roadmap,
    val skillError: String? = null,
    val placementMode: Boolean = false,
    val placementStage: LanguagePlacementStage = LanguagePlacementStage.Intro,
    val placementAttempt: LanguagePlacementAttempt? = null,
    val placementReport: LanguagePlacementReport? = null,
    val placementHistory: UiState<List<LanguagePlacementHistory>> = UiState.Loading,
    val skipLevel: CefrLevel = CefrLevel.B1,
    val answerDraft: String = "",
    val playedAudioQuestionIds: Set<String> = emptySet(),
    val isBusy: Boolean = false,
)

class LanguageModuleViewModel(
    private val languageRepository: LanguageRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(LanguageModuleUiState())
    val state: StateFlow<LanguageModuleUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            languageRepository.access.collect { access ->
                _state.update { it.copy(accessResult = UiState.Content(access)) }
                if (access.subscribed && access.placementCompleted) refreshHub()
            }
        }
        viewModelScope.launch {
            languageRepository.skillWorkspace.collect { workspace ->
                _state.update { it.copy(skillWorkspace = workspace) }
            }
        }
        load()
    }

    fun retry() = load()

    fun selectArea(area: LanguageArea) {
        val access = (_state.value.accessResult as? UiState.Content)?.data ?: return
        if (!access.subscribed || !access.placementCompleted) return
        _state.update { it.copy(selectedArea = area, placementMode = false, skillError = null) }
    }

    fun startReadingPractice(mode: LanguageReadingMode) {
        languageRepository.startReadingAttempt(mode)
        _state.update { it.copy(readingStage = LanguageReadingStage.Practice, skillError = null) }
    }

    fun updateReadingAnswer(questionId: String, answer: String) {
        languageRepository.saveReadingAnswer(questionId, answer)
    }

    fun submitReading() {
        viewModelScope.launch {
            when (val result = languageRepository.submitReadingAttempt()) {
                is AppResult.Success -> {
                    refreshHub()
                    _state.update { it.copy(readingStage = LanguageReadingStage.Results, skillError = null) }
                }

                is AppResult.Failure -> _state.update { it.copy(skillError = result.error.toString()) }
            }
        }
    }

    fun resetReading() {
        languageRepository.resetReadingResult()
        _state.update { it.copy(readingStage = LanguageReadingStage.Overview, skillError = null) }
    }

    fun selectListeningTab(tab: LanguageListeningTab) {
        _state.update { it.copy(listeningTab = tab, skillError = null) }
    }

    fun selectListeningGoal(goalId: String) {
        languageRepository.selectListeningGoal(goalId)
    }

    fun startListeningPractice() {
        languageRepository.startListeningLesson()
        _state.update { it.copy(listeningTab = LanguageListeningTab.Practice, skillError = null) }
    }

    fun updateListeningAnswer(questionId: String, answerIndex: Int) {
        languageRepository.saveListeningAnswer(questionId, answerIndex)
    }

    fun submitListening() {
        viewModelScope.launch {
            when (val result = languageRepository.submitListeningLesson()) {
                is AppResult.Success -> {
                    refreshHub()
                    _state.update { it.copy(skillError = null) }
                }

                is AppResult.Failure -> _state.update { it.copy(skillError = result.error.toString()) }
            }
        }
    }

    fun retryListening() {
        languageRepository.retryListeningLesson()
    }

    fun nextListeningLesson() {
        languageRepository.nextListeningLesson()
    }

    fun selectWritingTab(tab: LanguageWritingTab) {
        _state.update { it.copy(writingTab = tab, skillError = null) }
    }

    fun selectWritingGoal(goalId: String) {
        languageRepository.selectWritingGoal(goalId)
    }

    fun startWritingPractice() {
        languageRepository.startWritingLesson()
        _state.update { it.copy(writingTab = LanguageWritingTab.Practice, skillError = null) }
    }

    fun updateWritingDraft(text: String) {
        languageRepository.updateWritingDraft(text)
    }

    fun submitWritingDraft(complete: Boolean) {
        viewModelScope.launch {
            when (val result = languageRepository.submitWritingDraft(complete)) {
                is AppResult.Success -> {
                    if (result.data.completed) refreshHub()
                    _state.update { it.copy(skillError = null) }
                }

                is AppResult.Failure -> _state.update { it.copy(skillError = result.error.toString()) }
            }
        }
    }

    fun selectSpeakingTab(tab: LanguageSpeakingTab) {
        if (tab == LanguageSpeakingTab.Lesson && _state.value.skillWorkspace?.speakingLesson == null) {
            languageRepository.startSpeakingLearning()
        }
        if (tab == LanguageSpeakingTab.Discussion && _state.value.skillWorkspace?.speakingSession == null) {
            languageRepository.openSpeakingDiscussion()
        }
        _state.update { it.copy(speakingTab = tab, skillError = null) }
    }

    fun startSpeakingLearning() {
        languageRepository.startSpeakingLearning()
        _state.update { it.copy(speakingTab = LanguageSpeakingTab.Lesson, skillError = null) }
    }

    fun advanceSpeakingLesson() {
        val lesson = languageRepository.advanceSpeakingLesson()
        if (lesson.readyForDiscussion) {
            languageRepository.openSpeakingDiscussion()
            _state.update { it.copy(speakingTab = LanguageSpeakingTab.Discussion) }
        }
    }

    fun toggleSpeakingRecording() {
        languageRepository.toggleSpeakingRecording()
    }

    fun updateSpeakingTranscript(text: String) {
        languageRepository.updateSpeakingTranscript(text)
    }

    fun submitSpeakingTurn() {
        languageRepository.submitSpeakingTurn()
        refreshHub()
    }

    fun resetSpeakingConversation() {
        languageRepository.resetSpeakingConversation()
    }

    fun selectVocabularyTab(tab: LanguageVocabularyTab) {
        _state.update { it.copy(vocabularyTab = tab, skillError = null) }
    }

    fun selectVocabularyFilter(filter: LanguageVocabularyFilter) {
        _state.update { it.copy(vocabularyFilter = filter) }
    }

    fun generateVocabularyBatch() {
        languageRepository.generateVocabularyBatch()
    }

    fun toggleVocabularyArabic(cardId: String) {
        languageRepository.toggleVocabularyArabic(cardId)
    }

    fun gradeVocabularyCard(cardId: String, quality: Int) {
        languageRepository.gradeVocabularyCard(cardId, quality)
        refreshHub()
    }

    fun lookupVocabularyWord(word: String) {
        languageRepository.lookupVocabularyWord(word)
    }

    fun loadVocabularyChallenge() {
        languageRepository.loadVocabularyChallenge()
    }

    fun setVocabularyChallengeAnswer(blank: String, answer: String) {
        languageRepository.setVocabularyChallengeAnswer(blank, answer)
    }

    fun checkVocabularyChallenge() {
        languageRepository.checkVocabularyChallenge()
        refreshHub()
    }

    fun startDailyVocabularyQuiz() {
        languageRepository.startDailyVocabularyQuiz()
    }

    fun updateDailyVocabularyGuess(value: String) {
        languageRepository.updateDailyVocabularyGuess(value)
    }

    fun submitDailyVocabularySpelling() {
        languageRepository.submitDailyVocabularySpelling()
    }

    fun scoreDailyVocabularyPronunciation(score: Int) {
        languageRepository.scoreDailyVocabularyPronunciation(score)
    }

    fun nextDailyVocabularyQuizWord() {
        languageRepository.nextDailyVocabularyQuizWord()
        refreshHub()
    }

    fun openJourneyStage(grammarId: String) {
        languageRepository.openJourneyStage(grammarId)
        _state.update { it.copy(journeyMode = LanguageJourneyMode.Home, skillError = null) }
    }

    fun startJourneySession() {
        languageRepository.startJourneySession()
        _state.update { it.copy(journeyMode = LanguageJourneyMode.Session, skillError = null) }
    }

    fun completeJourneySession() {
        languageRepository.completeJourneySession()
        refreshHub()
        _state.update { it.copy(journeyMode = LanguageJourneyMode.Complete, skillError = null) }
    }

    fun returnToJourneyHome() {
        _state.update { it.copy(journeyMode = LanguageJourneyMode.Home, skillError = null) }
    }

    fun startGrammarLesson(grammarId: String? = null) {
        languageRepository.startGrammarLesson(grammarId)
        _state.update { it.copy(grammarMode = LanguageGrammarMode.Lesson, skillError = null) }
    }

    fun goToGrammarPhase(phase: LanguageGrammarLessonPhase) {
        languageRepository.goToGrammarPhase(phase)
    }

    fun advanceGrammarLesson() {
        val current = _state.value.skillWorkspace?.grammarLesson ?: languageRepository.startGrammarLesson()
        val next = LanguageGrammarLessonPhase.entries
            .getOrNull((current.phase.ordinal + 1).coerceAtMost(LanguageGrammarLessonPhase.entries.lastIndex))
            ?: LanguageGrammarLessonPhase.Complete
        if (next == LanguageGrammarLessonPhase.Complete) {
            completeGrammarLesson()
        } else {
            languageRepository.goToGrammarPhase(next)
        }
    }

    fun updateGrammarPractice(itemId: String, answer: String) {
        languageRepository.answerGrammarPractice(itemId, answer)
    }

    fun checkGrammarPractice(itemId: String) {
        languageRepository.checkGrammarPractice(itemId)
    }

    fun updateGrammarTutorDraft(text: String) {
        languageRepository.updateGrammarTutorDraft(text)
    }

    fun askGrammarTutor(prompt: String) {
        languageRepository.askGrammarTutor(prompt)
    }

    fun completeGrammarLesson() {
        languageRepository.completeGrammarLesson()
        refreshHub()
        _state.update { it.copy(grammarMode = LanguageGrammarMode.Complete, skillError = null) }
    }

    fun returnToGrammarRoadmap() {
        _state.update { it.copy(grammarMode = LanguageGrammarMode.Roadmap, skillError = null) }
    }

    fun subscribe() {
        if (_state.value.isBusy) return
        _state.update { it.copy(isBusy = true) }
        viewModelScope.launch {
            languageRepository.subscribeLanguage()
            _state.update {
                it.copy(
                    isBusy = false,
                    placementMode = true,
                    placementStage = LanguagePlacementStage.Intro,
                )
            }
        }
    }

    fun openPlacementIntro() {
        _state.update {
            it.copy(
                placementMode = true,
                placementStage = LanguagePlacementStage.Intro,
                placementAttempt = null,
                placementReport = null,
                answerDraft = "",
            )
        }
    }

    fun startPlacementExam() {
        val attempt = languageRepository.startPlacementExam()
        _state.update {
            it.copy(
                placementMode = true,
                placementStage = LanguagePlacementStage.Exam,
                placementAttempt = attempt,
                placementReport = null,
                playedAudioQuestionIds = emptySet(),
                answerDraft = answerFor(attempt),
            )
        }
    }

    fun startFreshPlacementExam() = startPlacementExam()

    fun selectSkipLevel(level: CefrLevel) {
        _state.update { it.copy(skipLevel = level) }
    }

    fun skipPlacement() {
        if (_state.value.isBusy) return
        _state.update { it.copy(isBusy = true) }
        viewModelScope.launch {
            when (val result = languageRepository.skipPlacement(_state.value.skipLevel)) {
                is AppResult.Success -> {
                    refreshHub()
                    _state.update {
                        it.copy(
                            isBusy = false,
                            placementMode = false,
                            placementStage = LanguagePlacementStage.Intro,
                            placementReport = result.data,
                            selectedArea = LanguageArea.Home,
                        )
                    }
                }

                is AppResult.Failure -> {
                    _state.update { it.copy(isBusy = false, accessResult = UiState.Failure(result.error)) }
                }
            }
        }
    }

    fun goToPlacementQuestion(index: Int) {
        val attempt = languageRepository.goToPlacementQuestion(index)
        _state.update { it.copy(placementAttempt = attempt, answerDraft = answerFor(attempt)) }
    }

    fun updateAnswerDraft(value: String) {
        _state.update { it.copy(answerDraft = value) }
    }

    fun useSampleSpeakingAnswer() {
        val sample = _state.value.placementAttempt?.currentQuestion?.sampleAnswer ?: return
        updateAnswerDraft(sample)
    }

    fun markListeningPlayed() {
        val questionId = _state.value.placementAttempt?.currentQuestion?.id ?: return
        _state.update { it.copy(playedAudioQuestionIds = it.playedAudioQuestionIds + questionId) }
    }

    fun submitCurrentAnswer() {
        val current = _state.value
        val attempt = current.placementAttempt ?: return
        val question = attempt.currentQuestion
        val answer = answerPayload(question.type, current.answerDraft, question.options) ?: return
        val saved = languageRepository.savePlacementAnswer(question.id, answer)

        if (saved.isLastQuestion) {
            completePlacementExam()
        } else {
            val next = languageRepository.goToPlacementQuestion(saved.currentIndex + 1)
            _state.update { it.copy(placementAttempt = next, answerDraft = answerFor(next)) }
        }
    }

    fun openPlacementHistory() {
        _state.update {
            it.copy(
                placementMode = true,
                placementStage = LanguagePlacementStage.History,
                placementAttempt = null,
                placementReport = null,
            )
        }
        loadPlacementHistory()
    }

    fun returnToLanguageHome() {
        refreshHub()
        _state.update {
            it.copy(
                placementMode = false,
                placementStage = LanguagePlacementStage.Intro,
                placementAttempt = null,
                selectedArea = LanguageArea.Home,
            )
        }
    }

    fun openAreaFromPlacement(area: LanguageArea) {
        refreshHub()
        _state.update {
            it.copy(
                placementMode = false,
                placementStage = LanguagePlacementStage.Intro,
                placementAttempt = null,
                selectedArea = area,
            )
        }
    }

    private fun load() {
        _state.update { it.copy(accessResult = UiState.Loading) }
        viewModelScope.launch {
            when (val result = languageRepository.getAccess()) {
                is AppResult.Success -> {
                    _state.update { it.copy(accessResult = UiState.Content(result.data)) }
                    if (result.data.subscribed && result.data.placementCompleted) refreshHub()
                }

                is AppResult.Failure -> _state.update { it.copy(accessResult = UiState.Failure(result.error)) }
            }
        }
    }

    private fun refreshHub() {
        _state.update { it.copy(hubResult = UiState.Loading) }
        viewModelScope.launch {
            when (val result = languageRepository.getHub()) {
                is AppResult.Success -> _state.update { it.copy(hubResult = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(hubResult = UiState.Failure(result.error)) }
            }
        }
    }

    private fun loadPlacementHistory() {
        _state.update { it.copy(placementHistory = UiState.Loading) }
        viewModelScope.launch {
            when (val result = languageRepository.getPlacementHistory()) {
                is AppResult.Success -> _state.update { it.copy(placementHistory = UiState.Content(result.data)) }
                is AppResult.Failure -> _state.update { it.copy(placementHistory = UiState.Failure(result.error)) }
            }
        }
    }

    private fun completePlacementExam() {
        _state.update { it.copy(placementStage = LanguagePlacementStage.Evaluating, isBusy = true) }
        viewModelScope.launch {
            when (val result = languageRepository.completePlacementExam()) {
                is AppResult.Success -> {
                    refreshHub()
                    _state.update {
                        it.copy(
                            isBusy = false,
                            placementStage = LanguagePlacementStage.Report,
                            placementReport = result.data,
                        )
                    }
                }

                is AppResult.Failure -> {
                    _state.update { it.copy(isBusy = false, accessResult = UiState.Failure(result.error)) }
                }
            }
        }
    }

    private fun answerFor(attempt: LanguagePlacementAttempt): String =
        attempt.answers[attempt.currentQuestion.id].orEmpty()

    private fun answerPayload(
        type: LanguagePlacementQuestionType,
        raw: String,
        options: List<String>,
    ): String? {
        val trimmed = raw.trim()
        if (trimmed.isBlank()) return null
        return if (type == LanguagePlacementQuestionType.ListeningMcq || type == LanguagePlacementQuestionType.ReadingMcq) {
            val index = trimmed.toIntOrNull() ?: return null
            options.getOrNull(index)
        } else {
            trimmed
        }
    }
}
