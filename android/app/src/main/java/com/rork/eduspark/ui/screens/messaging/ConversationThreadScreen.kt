package com.rork.eduspark.ui.screens.messaging

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Done
import androidx.compose.material.icons.filled.DoneAll
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.InsertDriveFile
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.ui.UiState
import com.rork.eduspark.data.model.MessagingChatMessage
import com.rork.eduspark.data.model.MessageAttachment
import com.rork.eduspark.data.model.MessageAttachmentType
import com.rork.eduspark.data.model.MessageParticipant
import com.rork.eduspark.data.model.MessageParticipantRole
import com.rork.eduspark.data.model.MessageThread
import com.rork.eduspark.ui.components.action.EduIconButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduTextField
import com.rork.eduspark.ui.components.input.FieldLabelPlacement
import com.rork.eduspark.ui.components.input.SearchField
import com.rork.eduspark.ui.components.nav.SheetHandle
import com.rork.eduspark.ui.components.progress.EduLinearProgress
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.EduDivider
import com.rork.eduspark.ui.components.surface.EduGroupedSurface
import com.rork.eduspark.ui.components.surface.ListRow
import com.rork.eduspark.ui.components.surface.SkeletonDetail
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import kotlinx.coroutines.delay
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * X-02 · Conversation Thread.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Outgoing/incoming reuse the app's own two surfaces directionally — [EduCard] for outgoing
 * (solid `primary`, per approved design's `.bubble-me`; a voice bubble stays on the softer
 * `primaryContainer` tint in both directions, since [VoiceMessageContent]'s play button and
 * progress bar need a neutral surface, not solid primary, to stay legible), [EduGroupedSurface]
 * (`neutralAlpha100`) for incoming — never a new bubble language, voice notes included: a voice
 * message is the SAME bubble, just with its inner content swapped for a Play/Pause row instead
 * of text. The participant sheet reuses
 * [ModalBottomSheet] + [SheetHandle], the "bottom-sheet first" primitive the Design System's
 * own TopBar.kt already names.
 *
 * [ConversationHeader] is the runtime-review avatar fix — a visible avatar in the main screen
 * (not only inside the tap-to-open participant sheet), bound directly to
 * [MessageParticipant.avatarInitial], the single canonical field every avatar in this app
 * already reads from (X-01's thread rows, X-03's contact rows, the participant sheet below).
 * Nothing here computes an initial from role/id/a hardcoded letter.
 *
 * Recording/playback mechanics ([VoiceRecorderController]/[VoicePlayerController]) are plain
 * Android helpers owned by this Composable via `remember` — [ConversationThreadViewModel] only
 * tracks the resulting UI state, the same platform-agnostic ViewModel boundary every other
 * screen in this app keeps. Everything is local: no upload, no backend call, no WebSocket.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConversationThreadScreen(
    threadId: String,
    onBack: () -> Unit,
    onOpenParticipantProfile: (studentId: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ConversationThreadViewModel = koinViewModel(parameters = { parametersOf(threadId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val recorder = remember { VoiceRecorderController(context) }
    val voicePlayer = remember { VoicePlayerController() }
    val nowMillis = rememberMessageRelativeNowMillis(enabled = state.viewerRole == MessageParticipantRole.Parent)

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is ConversationThreadEvent.OpenParticipantProfile -> onOpenParticipantProfile(event.studentId)
            }
        }
    }

    // Drives the shared local player from state — [PENDING_VOICE_PREVIEW_ID] resolves to the
    // not-yet-sent recording's own local path; any other id resolves through the loaded thread's
    // own messages, never a second copy of the attachment path.
    LaunchedEffect(state.activeVoiceMessageId, state.isVoicePlaying) {
        val activeId = state.activeVoiceMessageId
        if (activeId == null) {
            voicePlayer.stop()
            return@LaunchedEffect
        }
        val localPath = if (activeId == PENDING_VOICE_PREVIEW_ID) {
            state.pendingVoiceNote?.localPath
        } else {
            (state.result as? UiState.Content)?.data?.messages?.firstOrNull { it.id == activeId }?.attachment?.label
        }
        if (localPath == null) {
            viewModel.stopVoiceMessage()
            return@LaunchedEffect
        }
        if (state.isVoicePlaying) {
            if (voicePlayer.isLoaded(activeId)) {
                if (!voicePlayer.isPlaying()) voicePlayer.resume()
            } else {
                voicePlayer.play(activeId, localPath) { viewModel.stopVoiceMessage() }
            }
            while (state.isVoicePlaying) {
                delay(PlaybackPollMs)
                viewModel.updatePlaybackPosition(voicePlayer.currentPositionMs())
            }
        } else {
            voicePlayer.pause()
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted && recorder.start()) viewModel.setRecording(true)
    }
    val onMicTap: () -> Unit = {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED
        if (granted) {
            if (recorder.start()) viewModel.setRecording(true)
        } else {
            permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    LaunchedEffect(state.isRecording) {
        if (state.isRecording) {
            while (true) {
                delay(RecordingTickMs)
                viewModel.tickRecordingDuration()
            }
        }
    }

    val thread = (state.result as? UiState.Content)?.data
    val other = thread?.otherParticipant(state.viewerId)
    val isTeacherViewer = state.viewerIsTeacher
    val teacherSubtitle = if (isTeacherViewer && other != null) {
        teacherConversationSubtitle(other)
    } else {
        null
    }

    EduScaffold(
        title = other?.displayName ?: stringResource(R.string.x02_title_fallback),
        subtitle = teacherSubtitle?.takeIf { it.isNotBlank() },
        onBack = onBack,
        actions = {
            if (!isTeacherViewer) {
                EduIconButton(
                    icon = Icons.Filled.Search,
                    contentDescription = stringResource(R.string.x02_search),
                    onClick = viewModel::toggleSearch,
                )
                EduIconButton(
                    icon = Icons.Filled.Info,
                    contentDescription = stringResource(R.string.x02_participant_info),
                    onClick = { viewModel.setParticipantSheetVisible(true) },
                )
            }
        },
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { SkeletonDetail(modifier = Modifier.fillMaxSize().padding(Spacing.gutter)) },
            modifier = Modifier.fillMaxSize(),
        ) { loadedThread ->
            ConversationThreadContent(
                thread = loadedThread,
                viewerId = state.viewerId,
                viewerRole = state.viewerRole,
                isTeacherViewer = isTeacherViewer,
                isSearchActive = state.isSearchActive,
                searchQuery = state.searchQuery,
                composerText = state.composerText,
                isRecording = state.isRecording,
                recordingDurationSeconds = state.recordingDurationSeconds,
                pendingAttachment = state.pendingAttachment,
                pendingVoiceNote = state.pendingVoiceNote,
                activeVoiceMessageId = state.activeVoiceMessageId,
                isVoicePlaying = state.isVoicePlaying,
                playbackPositionMs = state.playbackPositionMs,
                nowMillis = nowMillis,
                onSearchQueryChange = viewModel::updateSearchQuery,
                onComposerTextChange = viewModel::updateComposerText,
                onSend = viewModel::sendMessage,
                onAttachmentTap = { viewModel.setAttachmentPickerVisible(true) },
                onMicTap = onMicTap,
                onCancelRecording = {
                    recorder.cancel()
                    viewModel.cancelRecording()
                },
                onDiscardPendingAttachment = viewModel::discardPendingAttachment,
                onFinishRecording = {
                    val duration = state.recordingDurationSeconds
                    val path = recorder.stop()
                    if (path != null) viewModel.finishRecording(path, duration) else viewModel.cancelRecording()
                },
                onDiscardPendingVoiceNote = viewModel::discardPendingVoiceNote,
                onSendVoiceNote = viewModel::sendVoiceNote,
                onTogglePlayback = { id ->
                    if (state.activeVoiceMessageId == id) {
                        if (state.isVoicePlaying) viewModel.pauseVoiceMessage() else viewModel.resumeVoiceMessage()
                    } else {
                        viewModel.playVoiceMessage(id)
                    }
                },
            )
        }
    }

    if (state.isAttachmentPickerVisible) {
        AttachmentPickerDialog(
            onPick = viewModel::sendAttachment,
            onDismiss = { viewModel.setAttachmentPickerVisible(false) },
        )
    }

    if (state.isParticipantSheetVisible && other != null) {
        ParticipantSheet(
            participant = other,
            onViewProfile = { viewModel.onViewProfileTapped(other.id) },
            onDismiss = { viewModel.setParticipantSheetVisible(false) },
        )
    }
}

@Composable
private fun ConversationThreadContent(
    thread: MessageThread,
    viewerId: String,
    viewerRole: MessageParticipantRole?,
    isTeacherViewer: Boolean,
    isSearchActive: Boolean,
    searchQuery: String,
    composerText: String,
    isRecording: Boolean,
    recordingDurationSeconds: Int,
    pendingAttachment: MessageAttachment?,
    pendingVoiceNote: PendingVoiceNote?,
    activeVoiceMessageId: String?,
    isVoicePlaying: Boolean,
    playbackPositionMs: Int,
    nowMillis: Long,
    onSearchQueryChange: (String) -> Unit,
    onComposerTextChange: (String) -> Unit,
    onSend: () -> Unit,
    onAttachmentTap: () -> Unit,
    onMicTap: () -> Unit,
    onCancelRecording: () -> Unit,
    onDiscardPendingAttachment: () -> Unit,
    onFinishRecording: () -> Unit,
    onDiscardPendingVoiceNote: () -> Unit,
    onSendVoiceNote: () -> Unit,
    onTogglePlayback: (String) -> Unit,
) {
    val other = thread.otherParticipant(viewerId)
    val messages = thread.messages
        .filter { searchQuery.isBlank() || it.body.contains(searchQuery, ignoreCase = true) }
        .sortedByDescending { it.sentAtMillis }

    // reverseLayout + Arrangement.Bottom together are what keep a short conversation pinned
    // near the composer instead of floating at the top with dead space below it — reverseLayout
    // alone only fixes scroll direction/newest-first, not resting position for a few items.
    val listState = rememberLazyListState()
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(0)
    }

    Column(modifier = Modifier.fillMaxSize().imePadding()) {
        if (!isTeacherViewer) {
            ConversationHeader(participant = other)
        }

        if (isSearchActive) {
            SearchField(
                value = searchQuery,
                onValueChange = onSearchQueryChange,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = Spacing.gutter, vertical = Spacing.xs),
            )
        }

        LazyColumn(
            state = listState,
            reverseLayout = true,
            verticalArrangement = Arrangement.Bottom,
            contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.sm),
            modifier = Modifier.weight(1f),
        ) {
            items(messages, key = { it.id }) { message ->
                MessageBubble(
                    message = message,
                    isOutgoing = message.senderId == viewerId,
                    compact = isTeacherViewer,
                    viewerRole = viewerRole,
                    nowMillis = nowMillis,
                    isPlaying = activeVoiceMessageId == message.id && isVoicePlaying,
                    playbackPositionMs = if (activeVoiceMessageId == message.id) playbackPositionMs else 0,
                    onTogglePlayback = { onTogglePlayback(message.id) },
                    modifier = Modifier.padding(vertical = Spacing.xxs),
                )
            }
        }

        EduDivider()
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .then(if (isTeacherViewer) Modifier.background(EduTheme.colors.surface) else Modifier),
        ) {
            ComposerArea(
                text = composerText,
                isRecording = isRecording,
                recordingDurationSeconds = recordingDurationSeconds,
                pendingAttachment = pendingAttachment,
                pendingVoiceNote = pendingVoiceNote,
                isPendingPreviewPlaying = activeVoiceMessageId == PENDING_VOICE_PREVIEW_ID && isVoicePlaying,
                pendingPreviewPositionMs = if (activeVoiceMessageId == PENDING_VOICE_PREVIEW_ID) playbackPositionMs else 0,
                compact = isTeacherViewer,
                onTextChange = onComposerTextChange,
                onAttachmentTap = onAttachmentTap,
                onSend = onSend,
                onMicTap = onMicTap,
                onCancelRecording = onCancelRecording,
                onDiscardPendingAttachment = onDiscardPendingAttachment,
                onFinishRecording = onFinishRecording,
                onDiscardPendingVoiceNote = onDiscardPendingVoiceNote,
                onSendVoiceNote = onSendVoiceNote,
                onTogglePendingPreview = { onTogglePlayback(PENDING_VOICE_PREVIEW_ID) },
            )
        }
    }
}

/** The runtime-review avatar fix — see this file's own top doc comment. */
@Composable
private fun ConversationHeader(participant: MessageParticipant) {
    val colors = EduTheme.colors
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.xs),
    ) {
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(Sizing.avatar)
                .background(colors.primaryContainer, CircleShape),
        ) {
            Text(participant.avatarInitial, style = EduTheme.typography.title, color = colors.primary)
        }
        Column {
            Text(
                text = messageParticipantRoleLabel(participant.role),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
            if (participant.contextLabel.isNotBlank()) {
                Text(participant.contextLabel, style = EduTheme.typography.caption, color = colors.primary)
            }
        }
    }
}

@Composable
private fun MessageBubble(
    message: MessagingChatMessage,
    isOutgoing: Boolean,
    compact: Boolean,
    viewerRole: MessageParticipantRole?,
    nowMillis: Long,
    isPlaying: Boolean,
    playbackPositionMs: Int,
    onTogglePlayback: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors
    val bubblePadding = if (compact) {
        PaddingValues(horizontal = Spacing.sm, vertical = Spacing.xs)
    } else {
        PaddingValues(Spacing.card)
    }
    val timeLabel = if (viewerRole == MessageParticipantRole.Parent) {
        parentRelativeMessageTimeLabel(message, nowMillis)
    } else {
        message.sentAtLabel
    }

    Row(
        horizontalArrangement = if (isOutgoing) Arrangement.End else Arrangement.Start,
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(
            horizontalAlignment = if (isOutgoing) Alignment.End else Alignment.Start,
            modifier = Modifier.fillMaxWidth(if (compact) TeacherBubbleWidthFraction else BubbleWidthFraction),
        ) {
            // Approved design's `.bubble-me` is solid primary, not a soft tint — but a voice
            // bubble keeps the neutral tinted treatment in both directions: the mockup only
            // ever shows a voice message on the incoming side, and VoiceMessageContent's own
            // play button + EduLinearProgress read fine on a tint, not on solid primary.
            val isVoice = message.attachment?.type == MessageAttachmentType.Voice
            if (isOutgoing) {
                val bubbleColor = if (isVoice) colors.primaryContainer else colors.primary
                EduCard(
                    containerColor = bubbleColor,
                    borderColor = bubbleColor,
                    contentPadding = bubblePadding,
                ) {
                    MessageBubbleBody(message, isOutgoing = true, isPlaying, playbackPositionMs, onTogglePlayback)
                }
            } else {
                EduGroupedSurface(contentPadding = bubblePadding) {
                    MessageBubbleBody(message, isOutgoing = false, isPlaying, playbackPositionMs, onTogglePlayback)
                }
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.xxs),
                modifier = Modifier.padding(top = Spacing.xxs),
            ) {
                Text(timeLabel, style = EduTheme.typography.caption, color = colors.textSecondary)
                if (isOutgoing && !compact) {
                    val receiptTint = if (message.isRead) colors.primary else colors.textSecondary
                    Icon(
                        imageVector = if (message.isRead) Icons.Filled.DoneAll else Icons.Filled.Done,
                        contentDescription = null,
                        tint = receiptTint,
                        modifier = Modifier.size(Sizing.iconSm),
                    )
                    Text(
                        text = stringResource(if (message.isRead) R.string.x02_receipt_read else R.string.x02_receipt_sent),
                        style = EduTheme.typography.caption,
                        color = receiptTint,
                    )
                }
            }
        }
    }
}

@Composable
private fun MessageBubbleBody(
    message: MessagingChatMessage,
    isOutgoing: Boolean,
    isPlaying: Boolean,
    playbackPositionMs: Int,
    onTogglePlayback: () -> Unit,
) {
    val attachment = message.attachment
    if (attachment != null && attachment.type == MessageAttachmentType.Voice) {
        VoiceMessageContent(
            attachment = attachment,
            isPlaying = isPlaying,
            playbackPositionMs = playbackPositionMs,
            onTogglePlayback = onTogglePlayback,
        )
        return
    }

    val colors = EduTheme.colors
    // Outgoing text bubbles are solid `primary` now (approved design's `.bubble-me`) — content
    // has to flip to the on-primary pair or it disappears into its own background.
    val contentColor = if (isOutgoing) colors.onPrimary else colors.textPrimary
    val iconTint = if (isOutgoing) colors.onPrimary else colors.primary

    Column {
        if (message.body.isNotBlank()) {
            Text(message.body, style = EduTheme.typography.body, color = contentColor)
        }
        attachment?.let {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                modifier = Modifier.padding(top = if (message.body.isNotBlank()) Spacing.xs else 0.dp),
            ) {
                Icon(
                    imageVector = attachmentIcon(it.type),
                    contentDescription = null,
                    tint = iconTint,
                    modifier = Modifier.size(Sizing.icon),
                )
                Text(
                    text = it.label,
                    style = EduTheme.typography.caption,
                    color = contentColor,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

/**
 * A voice message is still the SAME bubble ([EduCard]/[EduGroupedSurface], reused by
 * [MessageBubble]) — only the inner content changes to a Play/Pause row. Progress reuses
 * [EduLinearProgress], the app's own existing progress primitive, rather than a waveform.
 */
@Composable
private fun VoiceMessageContent(
    attachment: MessageAttachment,
    isPlaying: Boolean,
    playbackPositionMs: Int,
    onTogglePlayback: () -> Unit,
) {
    val colors = EduTheme.colors
    val durationSeconds = attachment.durationSeconds ?: 0
    val progress = if (durationSeconds > 0) (playbackPositionMs / 1000f / durationSeconds).coerceIn(0f, 1f) else 0f

    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(Spacing.xs)) {
        EduIconButton(
            icon = if (isPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow,
            contentDescription = stringResource(if (isPlaying) R.string.x02_pause else R.string.x02_play),
            tint = colors.primary,
            onClick = onTogglePlayback,
        )
        Column(modifier = Modifier.weight(1f)) {
            EduLinearProgress(progress = progress)
            Text(
                text = formatDurationLabel(durationSeconds),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
                modifier = Modifier.padding(top = Spacing.xxs),
            )
        }
    }
}

private fun attachmentIcon(type: MessageAttachmentType) = when (type) {
    MessageAttachmentType.Image -> Icons.Filled.Image
    MessageAttachmentType.File -> Icons.Filled.InsertDriveFile
    MessageAttachmentType.Link -> Icons.Filled.Link
    // Never reached — Voice attachments are rendered by [VoiceMessageContent] instead.
    MessageAttachmentType.Voice -> Icons.Filled.Mic
}

private fun formatDurationLabel(totalSeconds: Int): String {
    val minutes = totalSeconds / 60
    val seconds = totalSeconds % 60
    return "%02d:%02d".format(minutes, seconds)
}

/**
 * The composer area — three mutually exclusive states sharing the SAME row position/height as
 * the idle composer, never a floating overlay. Idle keeps the existing Attach/field/Send
 * treatment and simply adds one more [EduIconButton] for the mic, the same component every
 * other composer action already uses.
 */
@Composable
private fun ComposerArea(
    text: String,
    isRecording: Boolean,
    recordingDurationSeconds: Int,
    pendingAttachment: MessageAttachment?,
    pendingVoiceNote: PendingVoiceNote?,
    isPendingPreviewPlaying: Boolean,
    pendingPreviewPositionMs: Int,
    compact: Boolean = false,
    onTextChange: (String) -> Unit,
    onAttachmentTap: () -> Unit,
    onSend: () -> Unit,
    onMicTap: () -> Unit,
    onCancelRecording: () -> Unit,
    onDiscardPendingAttachment: () -> Unit,
    onFinishRecording: () -> Unit,
    onDiscardPendingVoiceNote: () -> Unit,
    onSendVoiceNote: () -> Unit,
    onTogglePendingPreview: () -> Unit,
) {
    val colors = EduTheme.colors
    val canSend = text.isNotBlank() || pendingAttachment != null

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = Spacing.gutter, vertical = if (compact) Spacing.xs else Spacing.sm),
    ) {
        if (pendingAttachment != null && !isRecording && pendingVoiceNote == null) {
            PendingAttachmentPreview(
                attachment = pendingAttachment,
                onDiscard = onDiscardPendingAttachment,
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
        }

        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
            modifier = Modifier.fillMaxWidth(),
        ) {
            when {
                isRecording -> {
                    Box(
                        modifier = Modifier
                            .size(Sizing.iconSm)
                            .background(colors.danger, CircleShape),
                    )
                    Text(
                        text = formatDurationLabel(recordingDurationSeconds),
                        style = EduTheme.typography.body,
                        color = colors.textPrimary,
                        modifier = Modifier
                            .weight(1f)
                            .padding(start = Spacing.xs),
                    )
                    EduIconButton(
                        icon = Icons.Filled.Close,
                        contentDescription = stringResource(R.string.x02_recording_cancel),
                        onClick = onCancelRecording,
                    )
                    EduIconButton(
                        icon = Icons.Filled.Check,
                        contentDescription = stringResource(R.string.x02_recording_finish),
                        tint = colors.primary,
                        onClick = onFinishRecording,
                    )
                }

                pendingVoiceNote != null -> {
                    EduIconButton(
                        icon = if (isPendingPreviewPlaying) Icons.Filled.Pause else Icons.Filled.PlayArrow,
                        contentDescription = stringResource(if (isPendingPreviewPlaying) R.string.x02_pause else R.string.x02_play),
                        tint = colors.primary,
                        onClick = onTogglePendingPreview,
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        val progress = if (pendingVoiceNote.durationSeconds > 0) {
                            (pendingPreviewPositionMs / 1000f / pendingVoiceNote.durationSeconds).coerceIn(0f, 1f)
                        } else {
                            0f
                        }
                        EduLinearProgress(progress = progress)
                        Text(
                            text = formatDurationLabel(pendingVoiceNote.durationSeconds),
                            style = EduTheme.typography.caption,
                            color = colors.textSecondary,
                            modifier = Modifier.padding(top = Spacing.xxs),
                        )
                    }
                    EduIconButton(
                        icon = Icons.Filled.Delete,
                        contentDescription = stringResource(R.string.x02_voice_preview_delete),
                        onClick = onDiscardPendingVoiceNote,
                    )
                    EduIconButton(
                        icon = Icons.AutoMirrored.Filled.Send,
                        contentDescription = stringResource(R.string.x02_send),
                        tint = colors.primary,
                        onClick = onSendVoiceNote,
                    )
                }

                else -> {
                    EduIconButton(
                        icon = Icons.Filled.AttachFile,
                        contentDescription = stringResource(R.string.x02_attach),
                        onClick = onAttachmentTap,
                    )
                    EduTextField(
                        value = text,
                        onValueChange = onTextChange,
                        label = if (compact) "" else stringResource(R.string.x02_composer_label),
                        placeholder = stringResource(R.string.x02_composer_placeholder),
                        labelPlacement = if (compact) FieldLabelPlacement.Above else FieldLabelPlacement.Floating,
                        modifier = Modifier.weight(1f),
                    )
                    EduIconButton(
                        icon = Icons.Filled.Mic,
                        contentDescription = stringResource(R.string.x02_mic),
                        onClick = onMicTap,
                    )
                    EduIconButton(
                        icon = Icons.AutoMirrored.Filled.Send,
                        contentDescription = stringResource(R.string.x02_send),
                        enabled = canSend,
                        tint = if (canSend) colors.primary else colors.textSecondary,
                        onClick = onSend,
                    )
                }
            }
        }
    }
}

@Composable
private fun PendingAttachmentPreview(
    attachment: MessageAttachment,
    onDiscard: () -> Unit,
    modifier: Modifier = Modifier,
) {
    EduGroupedSurface(modifier = modifier) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            Icon(
                imageVector = attachmentIcon(attachment.type),
                contentDescription = null,
                tint = EduTheme.colors.primary,
                modifier = Modifier.size(Sizing.iconLg),
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.x02_pending_attachment),
                    style = EduTheme.typography.caption,
                    color = EduTheme.colors.textSecondary,
                )
                Text(
                    text = attachment.label,
                    style = EduTheme.typography.body,
                    color = EduTheme.colors.textPrimary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            EduIconButton(
                icon = Icons.Filled.Close,
                contentDescription = stringResource(R.string.x02_remove_attachment),
                onClick = onDiscard,
            )
        }
    }
}

@Composable
private fun AttachmentPickerDialog(onPick: (MessageAttachment) -> Unit, onDismiss: () -> Unit) {
    Dialog(onDismissRequest = onDismiss) {
        EduCard {
            Text(
                text = stringResource(R.string.x02_attach_title),
                style = EduTheme.typography.title,
                color = EduTheme.colors.textPrimary,
                modifier = Modifier.padding(bottom = Spacing.xs),
            )
            ListRow(
                title = stringResource(R.string.x02_attach_image),
                supporting = SAMPLE_IMAGE,
                leading = Icons.Filled.Image,
                onClick = { onPick(MessageAttachment(MessageAttachmentType.Image, SAMPLE_IMAGE)) },
            )
            ListRow(
                title = stringResource(R.string.x02_attach_file),
                supporting = SAMPLE_FILE,
                leading = Icons.Filled.InsertDriveFile,
                onClick = { onPick(MessageAttachment(MessageAttachmentType.File, SAMPLE_FILE)) },
            )
            ListRow(
                title = stringResource(R.string.x02_attach_link),
                supporting = SAMPLE_LINK,
                leading = Icons.Filled.Link,
                onClick = { onPick(MessageAttachment(MessageAttachmentType.Link, SAMPLE_LINK)) },
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ParticipantSheet(
    participant: MessageParticipant,
    onViewProfile: () -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = EduTheme.colors
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        containerColor = colors.surface,
        sheetState = rememberModalBottomSheetState(),
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
        ) {
            SheetHandle(modifier = Modifier.padding(bottom = Spacing.md))
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(Sizing.avatarLg)
                    .background(colors.primaryContainer, CircleShape),
            ) {
                Text(participant.avatarInitial, style = EduTheme.typography.display, color = colors.primary)
            }
            Text(
                text = participant.displayName,
                style = EduTheme.typography.titleLg,
                color = colors.textPrimary,
                modifier = Modifier.padding(top = Spacing.sm),
            )
            Text(
                text = messageParticipantRoleLabel(participant.role),
                style = EduTheme.typography.caption,
                color = colors.textSecondary,
            )
            if (participant.contextLabel.isNotBlank()) {
                Text(
                    text = participant.contextLabel,
                    style = EduTheme.typography.body,
                    color = colors.textSecondary,
                    modifier = Modifier.padding(top = Spacing.xxs),
                )
            }
            // A "view profile" link is only ever offered when a real, already-built screen
            // exists for this relationship — TC-13 Student Profile, Teacher-side only. There
            // is no Student-facing Teacher profile screen anywhere in the app yet, so a
            // Student's participant sheet never offers this action (see this screen's doc
            // comment; no fake profile route is invented here).
            if (participant.role == MessageParticipantRole.Student) {
                SecondaryButton(
                    text = stringResource(R.string.x02_view_profile),
                    onClick = onViewProfile,
                    modifier = Modifier.padding(top = Spacing.md),
                )
            }
            Box(modifier = Modifier.height(Spacing.sm))
        }
    }
}

private const val BubbleWidthFraction = 0.82f
private const val TeacherBubbleWidthFraction = 0.78f
private const val SAMPLE_IMAGE = "project_photo.jpg"
private const val SAMPLE_FILE = "lesson_notes.pdf"
private const val SAMPLE_LINK = "https://example.edu/resource"
private const val PlaybackPollMs = 200L
private const val RecordingTickMs = 1000L
