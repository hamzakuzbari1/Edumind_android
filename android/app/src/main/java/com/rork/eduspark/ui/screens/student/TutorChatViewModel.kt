package com.rork.eduspark.ui.screens.student

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.data.model.ChatMessage
import com.rork.eduspark.data.model.ChatSender
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.TutorRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * ST-04 · AI Tutor Chat / ST-05 · AI Tutor Voice Mode — one shared ViewModel.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Graph-scoped in AppNavigation exactly like [com.rork.eduspark.ui.screens.onboarding.OnboardingViewModel]
 * is across SO-01…SO-05: ST-04 and ST-05 resolve the *same instance*, so a voice exchange
 * in ST-05 is still there in the transcript when the student backs out to ST-04. Only the
 * two screens' own recording/typing UI differs — the conversation and the tutor call are
 * one thing, not two.
 */
data class TutorChatUiState(
    val lessonId: String,
    val lessonTitle: String = "",
    val messages: List<ChatMessage> = emptyList(),
    val isSending: Boolean = false,
    val error: AppError? = null,
    val isOnline: Boolean = true,
)

class TutorChatViewModel(
    private val lessonId: String,
    /** Carried from ST-03's concept-action sheet or ST-07's mistake review — sent as this
     *  conversation's opening turn exactly once, since [init] never runs twice for one instance. */
    initialPrompt: String?,
    private val tutorRepository: TutorRepository,
    private val learningRepository: LearningRepository,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(TutorChatUiState(lessonId = lessonId))
    val state: StateFlow<TutorChatUiState> = _state.asStateFlow()

    private var messageCounter = 0
    private var lastQuestion: String? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        viewModelScope.launch {
            // Decorative lesson-context pill only — a failed fetch here does not block chat.
            val result = learningRepository.getLesson(lessonId)
            if (result is AppResult.Success) {
                _state.update { it.copy(lessonTitle = result.data.title) }
            }
        }
        if (!initialPrompt.isNullOrBlank()) {
            sendMessage(initialPrompt)
        }
    }

    /** ST-04's typed input and ST-05's transcribed voice turn both call this. */
    fun sendMessage(text: String, isVoice: Boolean = false) {
        val trimmed = text.trim()
        if (trimmed.isEmpty() || _state.value.isSending) return
        lastQuestion = trimmed
        appendMessage(ChatSender.Student, trimmed, isVoice)
        requestReply(trimmed)
    }

    /** Regenerates the most recent reply — always re-asks the last real question. */
    fun regenerateLast() {
        val question = lastQuestion ?: return
        requestReply("$question (تجديد)")
    }

    /** Message-action follow-ups: each reads as its own turn in the transcript. */
    fun explainSimpler() = sendFollowUp(FOLLOW_UP_SIMPLER)

    fun giveExample() = sendFollowUp(FOLLOW_UP_EXAMPLE)

    /** Retries the last question after a failure — same call [requestReply] would have made. */
    fun retry() {
        val question = lastQuestion ?: return
        requestReply(question)
    }

    private fun sendFollowUp(prompt: String) {
        if (_state.value.isSending) return
        lastQuestion = prompt
        appendMessage(ChatSender.Student, prompt, isVoice = false)
        requestReply(prompt)
    }

    private fun requestReply(message: String) {
        _state.update { it.copy(isSending = true, error = null) }
        viewModelScope.launch {
            when (val result = tutorRepository.sendMessage(lessonId, message)) {
                is AppResult.Success -> {
                    appendMessage(ChatSender.Tutor, result.data.text, isVoice = false)
                    _state.update { it.copy(isSending = false) }
                }
                is AppResult.Failure -> _state.update { it.copy(isSending = false, error = result.error) }
            }
        }
    }

    private fun appendMessage(sender: ChatSender, text: String, isVoice: Boolean) {
        messageCounter += 1
        val message = ChatMessage(id = "msg-$messageCounter", sender = sender, text = text, isVoice = isVoice)
        _state.update { it.copy(messages = it.messages + message) }
    }

    private companion object {
        const val FOLLOW_UP_SIMPLER = "اشرح بشكل أبسط"
        const val FOLLOW_UP_EXAMPLE = "أعطني مثالاً"
    }
}
