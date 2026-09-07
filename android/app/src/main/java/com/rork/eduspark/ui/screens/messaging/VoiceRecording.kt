package com.rork.eduspark.ui.screens.messaging

import android.content.Context
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.os.Build
import java.io.File

/**
 * ══════════════════════════════════════════════════════════════════════════
 * X-02 · Conversation Thread — local voice-note recording/playback.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Plain Android helpers, not Composables — owned via `remember { }` in [ConversationThreadScreen]
 * and driven by [ConversationThreadViewModel]'s state. Local-only: files live under the app's
 * own `filesDir` (survives the process, unlike `cacheDir`, which the OS may evict at any time)
 * and are never uploaded — no backend/network call exists anywhere in this file.
 */
class VoiceRecorderController(private val context: Context) {
    private var recorder: MediaRecorder? = null
    private var outputFile: File? = null

    /** Starts recording to a fresh local file; returns false if the platform recorder failed to start. */
    fun start(): Boolean {
        val dir = File(context.filesDir, "voice_notes").apply { mkdirs() }
        val file = File(dir, "voice_${System.currentTimeMillis()}.m4a")
        val mediaRecorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            MediaRecorder(context)
        } else {
            @Suppress("DEPRECATION")
            MediaRecorder()
        }
        return try {
            mediaRecorder.apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setOutputFile(file.absolutePath)
                prepare()
                start()
            }
            recorder = mediaRecorder
            outputFile = file
            true
        } catch (error: Exception) {
            mediaRecorder.release()
            recorder = null
            outputFile = null
            false
        }
    }

    /** Stops and finalizes the current recording; returns the local file path, or null if nothing valid was captured. */
    fun stop(): String? {
        val finished = try {
            recorder?.apply { stop(); release() }
            outputFile?.absolutePath
        } catch (error: Exception) {
            outputFile?.delete()
            null
        } finally {
            recorder = null
        }
        outputFile = null
        return finished
    }

    /** Stops (if needed) and deletes the in-progress file — Cancel never leaves an orphaned recording behind. */
    fun cancel() {
        try {
            recorder?.apply { stop(); release() }
        } catch (error: Exception) {
            // Recorder was already invalid/never produced usable output — nothing else to release.
        }
        recorder = null
        outputFile?.delete()
        outputFile = null
    }
}

/**
 * One shared player per thread screen — only one voice note plays at a time, matching normal
 * chat behavior. [loadedId] lets a caller tell "resume the same clip" apart from "switch to a
 * different one" without holding any Android type itself.
 */
class VoicePlayerController {
    private var player: MediaPlayer? = null
    private var loadedId: String? = null

    fun isLoaded(id: String): Boolean = loadedId == id && player != null

    fun play(id: String, localPath: String, onCompletion: () -> Unit) {
        stop()
        player = try {
            MediaPlayer().apply {
                setDataSource(localPath)
                setOnCompletionListener { onCompletion() }
                prepare()
                start()
            }
        } catch (error: Exception) {
            onCompletion()
            null
        }
        loadedId = if (player != null) id else null
    }

    fun pause() {
        try {
            player?.takeIf { it.isPlaying }?.pause()
        } catch (error: IllegalStateException) {
            // Player already released/invalid — nothing to pause.
        }
    }

    fun resume() {
        try {
            player?.start()
        } catch (error: IllegalStateException) {
            // Player already released/invalid — nothing to resume.
        }
    }

    fun stop() {
        try {
            player?.release()
        } catch (error: Exception) {
            // Already released.
        }
        player = null
        loadedId = null
    }

    fun currentPositionMs(): Int = try {
        player?.currentPosition ?: 0
    } catch (error: IllegalStateException) {
        0
    }

    fun isPlaying(): Boolean = try {
        player?.isPlaying ?: false
    } catch (error: IllegalStateException) {
        false
    }
}
