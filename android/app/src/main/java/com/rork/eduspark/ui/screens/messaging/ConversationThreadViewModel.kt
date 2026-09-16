package com.rork.eduspark.ui.screens.messaging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.core.result.AppResult
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.MessageAttachment
import com.rork.eduspark.data.model.MessageAttachmentType
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.MessageThread
import com.rork.eduspark.data.remote.media.MediaUrlResolver
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.MessagingRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * ══════════════════════════════════════════════════════════════════════════
 * X-02 · Conversation Thread.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * [threadId] is parameterised in, same shape every other id-scoped ViewModel in this app
 * uses. Opening the thread marks every message the viewer did not send as read
 * ([MessagingRepository.markThreadRead]) — reflected immediately back on X-01 because both
 * screens read the same canonical [MessagingRepository.threads] hot flow, never a
 * screen-local copy.
 */
data class ConversationThreadUiState(
    val result: UiState<MessageThread> = UiState.Loading,
    val isOnline: Boolean = true,
    val viewerId: String = "",
    val viewerIsTeacher: Boolean = false,
    val searchQuery: String = "",
    val isSearchActive: Boolean = false,
    val composerText: String = "",
    val isAttachmentPickerVisible: Boolean = false,
    val isParticipantSheetVisible: Boolean = false,
    val isRecording: Boolean = false,
    val recordingDurationSeconds: Int = 0,
    val pendingVoiceNote: PendingVoiceNote? = null,
    /** The message id currently loaded in the player — or [PENDING_VOICE_PREVIEW_ID] while previewing [pendingVoiceNote] before it's sent. */
    val activeVoiceMessageId: String? = null,
    val isVoicePlaying: Boolean = false,
    val playbackPositionMs: Int = 0,
    val resolvedVoiceRefs: Map<String, String> = emptyMap(),
)

/** A stopped-but-not-yet-sent local recording — never written to the canonical repository until [ConversationThreadViewModel.sendVoiceNote]. */
data class PendingVoiceNote(val localPath: String, val durationSeconds: Int)

/** Sentinel [ConversationThreadUiState.activeVoiceMessageId] for playing back [ConversationThreadUiState.pendingVoiceNote] — never collides with a real [com.rork.eduspark.data.model.MessagingChatMessage.id]. */
const val PENDING_VOICE_PREVIEW_ID = "pending-voice-preview"

sealed interface ConversationThreadEvent {
    data class OpenParticipantProfile(val studentId: String) : ConversationThreadEvent
    data class OpenAttachment(val url: String) : ConversationThreadEvent
}

class ConversationThreadViewModel(
    private val threadId: String,
    private val authRepository: AuthRepository,
    private val messagingRepository: MessagingRepository,
    private val mediaUrlResolver: MediaUrlResolver,
    connectivity: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(ConversationThreadUiState())
    val state: StateFlow<ConversationThreadUiState> = _state.asStateFlow()

    private val _events = Channel<ConversationThreadEvent>(Channel.BUFFERED)
    val events: Flow<ConversationThreadEvent> = _events.receiveAsFlow()

    private var loadJob: Job? = null

    init {
        viewModelScope.launch {
            connectivity.isOnline.collect { online -> _state.update { it.copy(isOnline = online) } }
        }
        load()
    }

    fun retry() = load()

    private fun load() {
        loadJob?.cancel()
        _state.update { it.copy(result = UiState.Loading) }
        loadJob = viewModelScope.launch {
            val session = authRepository.session.first()
            val viewerId = session?.messagingParticipantIdOrNull()
            if (viewerId == null) {
                _state.update { it.copy(result = UiState.Failure(AppError.NotFound)) }
                return@launch
            }
            _state.update {
                it.copy(
                    viewerId = viewerId,
                    viewerIsTeacher = session?.messagingRoleOrNull() == MessageParticipantRole.Teacher,
                )
            }
            messagingRepository.getThread(threadId)
            messagingRepository.markThreadRead(threadId, viewerId)
            messagingRepository.threads.collect { all ->
                val thread = all.firstOrNull { it.id == threadId }
                _state.update {
                    it.copy(result = if (thread != null) UiState.Content(thread) else UiState.Failure(AppError.NotFound))
                }
            }
        }
    }

    fun updateComposerText(text: String) = _state.update { it.copy(composerText = text) }

    fun sendMessage() {
        val body = _state.value.composerText
        val viewerId = _state.value.viewerId
        if (body.isBlank() || viewerId.isEmpty()) return
        _state.update { it.copy(composerText = "") }
        viewModelScope.launch { messagingRepository.sendMessage(threadId, viewerId, body) }
    }

    fun sendAttachment(attachment: MessageAttachment) {
        val viewerId = _state.value.viewerId
        if (viewerId.isEmpty()) return
        _state.update { it.copy(isAttachmentPickerVisible = false) }
        viewModelScope.launch { messagingRepository.sendMessage(threadId, viewerId, "", attachment) }
    }

    fun toggleSearch() = _state.update {
        it.copy(isSearchActive = !it.isSearchActive, searchQuery = if (it.isSearchActive) "" else it.searchQuery)
    }

    fun updateSearchQuery(query: String) = _state.update { it.copy(searchQuery = query) }

    fun setAttachmentPickerVisible(visible: Boolean) = _state.update { it.copy(isAttachmentPickerVisible = visible) }

    fun setParticipantSheetVisible(visible: Boolean) = _state.update { it.copy(isParticipantSheetVisible = visible) }

    fun onViewProfileTapped(studentId: String) {
        _state.update { it.copy(isParticipantSheetVisible = false) }
        viewModelScope.launch { _events.send(ConversationThreadEvent.OpenParticipantProfile(studentId)) }
    }

    // ── Voice notes — local-only; nothing here touches network or a repository call until
    // the finished recording is explicitly sent (see [sendVoiceNote]). Recording mechanics
    // themselves (MediaRecorder/permission) live in the Composable via [VoiceRecorderController]
    // — this ViewModel only tracks the resulting UI state, same platform-agnostic boundary
    // every other ViewModel in this app keeps.

    fun setRecording(recording: Boolean) = _state.update {
        it.copy(isRecording = recording, recordingDurationSeconds = 0)
    }

    fun tickRecordingDuration() = _state.update { it.copy(recordingDurationSeconds = it.recordingDurationSeconds + 1) }

    fun cancelRecording() = _state.update { it.copy(isRecording = false, recordingDurationSeconds = 0) }

    fun finishRecording(localPath: String, durationSeconds: Int) = _state.update {
        it.copy(
            isRecording = false,
            recordingDurationSeconds = 0,
            pendingVoiceNote = PendingVoiceNote(localPath, durationSeconds),
            activeVoiceMessageId = null,
            isVoicePlaying = false,
            playbackPositionMs = 0,
        )
    }

    fun discardPendingVoiceNote() = _state.update {
        it.copy(pendingVoiceNote = null, activeVoiceMessageId = null, isVoicePlaying = false, playbackPositionMs = 0)
    }

    fun sendVoiceNote() {
        val pending = _state.value.pendingVoiceNote ?: return
        val viewerId = _state.value.viewerId
        if (viewerId.isEmpty()) return
        _state.update {
            it.copy(pendingVoiceNote = null, activeVoiceMessageId = null, isVoicePlaying = false, playbackPositionMs = 0)
        }
        viewModelScope.launch {
            messagingRepository.sendMessage(
                threadId,
                viewerId,
                "",
                MessageAttachment(MessageAttachmentType.Voice, pending.localPath, pending.durationSeconds),
            )
        }
    }

    fun openAttachment(attachment: MessageAttachment) {
        val ref = attachment.mediaRef ?: attachment.label
        viewModelScope.launch {
            when (val resolved = mediaUrlResolver.resolve(ref)) {
                is AppResult.Success -> _events.send(ConversationThreadEvent.OpenAttachment(resolved.data.url))
                is AppResult.Failure -> Unit
            }
        }
    }

    /** Starts (or restarts) playback for [id] — a real message id, or [PENDING_VOICE_PREVIEW_ID]. */
    fun playVoiceMessage(id: String, mediaRef: String? = null) {
        val ref = mediaRef?.takeIf { it.isNotBlank() }
        if (ref == null || id == PENDING_VOICE_PREVIEW_ID) {
            _state.update { it.copy(activeVoiceMessageId = id, isVoicePlaying = true, playbackPositionMs = 0) }
            return
        }
        viewModelScope.launch {
            when (val resolved = mediaUrlResolver.resolve(ref)) {
                is AppResult.Success -> _state.update {
                    it.copy(
                        activeVoiceMessageId = id,
                        isVoicePlaying = true,
                        playbackPositionMs = 0,
                        resolvedVoiceRefs = it.resolvedVoiceRefs + (id to resolved.data.url),
                    )
                }
                is AppResult.Failure -> Unit
            }
        }
    }

    fun pauseVoiceMessage() = _state.update { it.copy(isVoicePlaying = false) }

    fun resumeVoiceMessage() = _state.update { it.copy(isVoicePlaying = true) }

    fun stopVoiceMessage() = _state.update {
        it.copy(activeVoiceMessageId = null, isVoicePlaying = false, playbackPositionMs = 0)
    }

    fun updatePlaybackPosition(positionMs: Int) = _state.update { it.copy(playbackPositionMs = positionMs) }
}
