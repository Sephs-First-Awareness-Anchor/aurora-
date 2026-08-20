package org.aurora.app

import android.Manifest
import android.app.AlertDialog
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Process
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.ByteBuffer
import java.util.Locale
import java.util.UUID
import java.util.concurrent.Executors

class MainActivity : FlutterActivity() {

    private companion object {
        const val TAG         = "MainActivity"
        const val BRIDGE      = "org.aurora.app/bridge"
        const val EVENTS      = "org.aurora.app/events"
        const val PERM_REQUEST = 1001
        const val FRAME_INTERVAL_MS = 1_000L  // 1 FPS is ample for Aurora's visual loop
        const val FACE_DETECT_INTERVAL_MS = 300L  // faster than FRAME_INTERVAL_MS -- proximity should feel responsive
        const val AMBIENT_AUDIO_SAMPLE_RATE = 16_000  // Hz -- ample for the DSP features computed Python-side
        const val AUDIO_PUSH_INTERVAL_MS = 1_000L      // bounded push rate (Section XXVIII battery discipline)
    }

    // Diagnostic hardening, part 6 (per Sunni: repeated tests never showed
    // any previous-crash report, no matter what got added). The chain that
    // was supposed to surface it -- Python writes a file -> AuroraService.
    // bootPython() reads it -> sends a JSON event -> Flutter's EventChannel
    // has to be listening -> gets rendered as a chat message -- has several
    // places it can silently fail, and critically, AuroraService is a
    // START_STICKY foreground service: after a crash, Android can restart
    // it in the background before the user ever reopens the app, which
    // would read-and-delete the crash file with no UI attached to show it,
    // burning the one-shot report on nobody. This reads the same three
    // diagnostic files directly, in plain Kotlin, with no dependency on
    // Python having booted, the Flutter engine being configured, or the
    // EventChannel being connected -- and shows them in a native
    // AlertDialog the instant this Activity is created. Deliberately does
    // NOT go through Flutter at all, so none of the prior failure modes
    // can apply to this path.
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        reportAndClearPreviousCrash()
    }

    // A review on this same change caught a real problem: AuroraService
    // can already be mid-boot (restarted headlessly via BootCompletedReceiver
    // or START_STICKY) by the time this Activity opens, actively writing
    // NEW markers into these same files for a boot that's still genuinely
    // in progress -- not a leftover from a dead process at all. Reading
    // and deleting on file-existence alone can't tell "abandoned by a
    // process that's gone" apart from "being actively refreshed right
    // now," and would both misreport a live boot as a past crash AND
    // delete AuroraService's own in-progress marker out from under it.
    // Every writer of these files stamps a leading "time=<epoch ms>" --
    // a marker only counts as stale (and only then gets consumed) if it's
    // older than this. Anything actively being refreshed writes far more
    // often than this threshold, so a truly live boot never qualifies.
    private val STALE_THRESHOLD_MS = 5_000L

    private fun markerTimestampMs(text: String): Long? =
        Regex("""time=(\d+)""").find(text)?.groupValues?.get(1)?.toLongOrNull()

    private fun reportAndClearPreviousCrash() {
        try {
            val stateDir = File(filesDir, "aurora_state")
            val sources = listOf(
                "fatal error (caught exception/OOM)" to File(stateDir, "last_crash.txt"),
                "boot sequence" to File(stateDir, "last_boot_stage.txt"),
                "app/native call" to File(stateDir, "last_app_stage.txt"),
            )
            val now = System.currentTimeMillis()
            val lines = mutableListOf<String>()
            for ((label, f) in sources) {
                if (!f.exists()) continue
                val text = f.readText().trim()
                if (text.isEmpty()) { f.delete(); continue }
                val ts = markerTimestampMs(text)
                // Recent + parseable => almost certainly a live, in-progress
                // write from a boot that's still actually running right now.
                // Leave it alone entirely -- don't read it as a crash, don't
                // delete it, let that boot's own lifecycle handle it.
                if (ts != null && (now - ts) < STALE_THRESHOLD_MS) continue
                lines.add("[$label]\n$text")
                f.delete()
            }
            if (lines.isEmpty()) return
            AlertDialog.Builder(this)
                .setTitle("Aurora didn't close cleanly last time")
                .setMessage(lines.joinToString("\n\n"))
                .setPositiveButton("OK", null)
                .setCancelable(true)
                .show()
        } catch (_: Throwable) {
            // Diagnostic reporting must never itself crash the app.
        }
    }

    @Volatile private var pendingSummon = false

    private val overlayReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            if (intent?.action == OverlayService.ACTION_OVERLAY_TAPPED) pendingSummon = true
        }
    }

    // ── TTS ──────────────────────────────────────────────────────────────────
    private var tts: TextToSpeech? = null
    private var ttsReady = false

    // ── STT ──────────────────────────────────────────────────────────────────
    private var speechRecognizer: SpeechRecognizer? = null

    private val sttListener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {}
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {}
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {}

        override fun onError(error: Int) {
            runOnUiThread {
                AuroraService.eventSink?.success(
                    JSONObject().put("source","stt").put("type","error").put("error",error).toString()
                )
            }
        }

        override fun onResults(results: Bundle?) {
            val text = results
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull() ?: ""
            runOnUiThread {
                AuroraService.eventSink?.success(
                    JSONObject().put("source","stt").put("type","result")
                        .put("text",text).put("final",true).toString()
                )
            }
        }

        override fun onPartialResults(partialResults: Bundle?) {
            val text = partialResults
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull() ?: ""
            if (text.isEmpty()) return
            runOnUiThread {
                AuroraService.eventSink?.success(
                    JSONObject().put("source","stt").put("type","partial").put("text",text).toString()
                )
            }
        }

        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    // ── Camera ───────────────────────────────────────────────────────────────
    private val cameraExecutor = Executors.newSingleThreadExecutor()
    private var cameraProvider: ProcessCameraProvider? = null
    private var lastFrameMs = 0L
    // Repair Q: which physical camera is currently bound -- back camera
    // is the default, passive environmental-awareness stream (unchanged
    // from before); front camera is bound specifically during active
    // conversation (see startNativeStt / TTS onDone below), since that's
    // when there's an actual face in frame to react to.
    private var isCameraFront = false
    // Low-cost mode: FAST accuracy, no landmarks/classification/tracking
    // -- this only ever needs a bounding box for proximity/position, not
    // expression or identity.
    private val faceDetector by lazy {
        FaceDetection.getClient(
            FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
                .build()
        )
    }
    private var lastFaceDetectMs = 0L

    // ── Ambient audio (Section VI/VII, Sunni & Cael: Aurora must be able to
    // hear without requiring speech recognition) ───────────────────────────
    // This is a PARALLEL, independent capture path from SpeechRecognizer
    // above -- it never transcribes, never competes for STT's result
    // callback, and keeps running (subject to the same lifecycle) whether
    // or not a speech-recognition session is simultaneously active.
    //
    // NOTE (verification required, cannot be confirmed without a physical
    // device/build): some Android OEMs restrict concurrent AudioRecord +
    // SpeechRecognizer access to the microphone, or duck one when the
    // other is active. This implementation assumes concurrent access is
    // permitted (the common case on stock AOSP-derived builds); if a
    // device rejects it, AudioRecord.getState() will report
    // STATE_UNINITIALIZED and startAmbientAudioCapture() below no-ops
    // safely rather than crashing -- but the actual behavior needs
    // confirming on real hardware, not assumed from this source alone.
    private val audioExecutor = Executors.newSingleThreadExecutor()
    private var audioRecord: AudioRecord? = null
    @Volatile private var audioCaptureRunning = false
    private var lastAudioPushMs = 0L

    // ─────────────────────────────────────────────────────────────────────────

    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)

        initTts()

        MethodChannel(engine.dartExecutor.binaryMessenger, BRIDGE)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "sendMessage" -> {
                        val text = call.argument<String>("text") ?: ""
                        AuroraService.sendMessage(text) { reply ->
                            runOnUiThread { result.success(reply) }
                        }
                    }
                    "getState"  -> result.success(AuroraService.currentState)
                    "setState"  -> {
                        AuroraService.setState(call.argument<String>("state") ?: "DORMANT")
                        result.success(null)
                    }
                    "startOverlay" -> {
                        if (hasOverlayPermission()) {
                            val i = Intent(this, OverlayService::class.java)
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                                startForegroundService(i)
                            else startService(i)
                            result.success(true)
                        } else {
                            requestOverlayPermission()
                            result.success(false)
                        }
                    }
                    "stopOverlay" -> {
                        stopService(Intent(this, OverlayService::class.java))
                        result.success(null)
                    }
                    "hasOverlayPermission"     -> result.success(hasOverlayPermission())
                    "requestOverlayPermission" -> { requestOverlayPermission(); result.success(null) }
                    "hasScreenObserverPermission" -> result.success(hasScreenObserverPermission())
                    "requestScreenObserverPermission" -> { requestScreenObserverPermission(); result.success(null) }
                    "consumeOverlayTap" -> {
                        val had = pendingSummon; pendingSummon = false; result.success(had)
                    }
                    "startListening" -> { startNativeStt(); result.success(null) }
                    "stopListening"  -> { speechRecognizer?.stopListening(); result.success(null) }
                    "speak"          -> { nativeSpeak(call.argument<String>("text") ?: ""); result.success(null) }
                    "stopSpeaking"   -> { tts?.stop(); result.success(null) }
                    "captureVision"  -> {
                        AuroraService.eventSink?.success(
                            JSONObject().put("source","camera").put("type","captured").toString()
                        )
                        result.success(null)
                    }
                    // Repair R (per Sunni, 2026-08-19): "providing me a way
                    // to upload files and audio and pictures she then
                    // receives and processes would be a huge benefit to her
                    // discovery and development." bytes/filename/contentType
                    // come from Dart's file_picker selection; contentType is
                    // Dart's own best-effort guess (extension-based) --
                    // provide_uploaded_content() on the Python side does its
                    // own real dispatch by actual content, this is only a
                    // routing hint, never trusted as ground truth.
                    "uploadContent" -> {
                        val bytes = call.argument<ByteArray>("bytes")
                        val filename = call.argument<String>("filename") ?: "upload"
                        val contentType = call.argument<String>("contentType") ?: "unknown"
                        if (bytes == null) {
                            result.success(JSONObject().put("ok", false).put("error", "no_bytes").toString())
                        } else {
                            AuroraService.uploadContent(bytes, filename, contentType) { reply ->
                                runOnUiThread { result.success(reply) }
                            }
                        }
                    }
                    "getSelfModel" -> {
                        AuroraService.getSelfModel { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "getCognitiveStats" -> {
                        AuroraService.getCognitiveStats { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "getRoomState" -> {
                        AuroraService.getRoomState { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "provideRoomCommand" -> {
                        val cmd = call.argument<String>("cmd") ?: "{}"
                        AuroraService.provideRoomCommand(cmd)
                        result.success(null)
                    }
                    "startGauntlet" -> {
                        AuroraService.callPythonString("start_gauntlet") { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "stopGauntlet" -> {
                        AuroraService.callPythonVoid("stop_gauntlet")
                        result.success(null)
                    }
                    "getGauntletStatus" -> {
                        AuroraService.callPythonString("get_gauntlet_status") { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "triggerCuriosityCycle" -> {
                        val n = call.argument<Int>("n") ?: 5
                        AuroraService.callPythonStringArg("trigger_curiosity_cycle", n.toString()) { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "triggerEvoCycle" -> {
                        val ticks = call.argument<Int>("ticks") ?: 20
                        AuroraService.callPythonStringArg("trigger_evo_cycle", ticks.toString()) { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "startUiObservationSession" -> {
                        AuroraService.startUiObservationSession()
                        result.success(null)
                    }
                    "markUiTransition" -> {
                        val transition = call.argument<String>("transition") ?: ""
                        // Sunni & Cael, review follow-up: wait for the
                        // timeline write AND screenshot capture to actually
                        // finish before resolving, so a Dart-side `await`
                        // on this call (see home_screen.dart's
                        // 'response_rendered' transition) is a real
                        // guarantee, not just a MethodChannel round trip.
                        AuroraService.markUiTransition(transition) {
                            runOnUiThread { result.success(null) }
                        }
                    }
                    "stopUiObservationSession" -> {
                        AuroraService.stopUiObservationSession { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    // ── Habitat (Aurora Build 712, App Developmental Habitat) ──
                    // Every case is a thin pass-through via the existing generic
                    // callPythonString/callPythonStringArg helpers -- no new
                    // developmental logic belongs at this layer.
                    "habitatGetAffordances" -> {
                        AuroraService.callPythonString("habitat_get_affordances") { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatGetState" -> {
                        val params = call.argument<String>("params") ?: ""
                        AuroraService.callPythonStringArg("habitat_get_state", params) { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatGetEntity" -> {
                        val params = call.argument<String>("params") ?: "{}"
                        AuroraService.callPythonStringArg("habitat_get_entity", params) { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatGetHistory" -> {
                        val params = call.argument<String>("params") ?: "{}"
                        AuroraService.callPythonStringArg("habitat_get_history", params) { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatGetLineage" -> {
                        val entityId = call.argument<String>("entityId") ?: ""
                        AuroraService.callPythonStringArg("habitat_get_lineage", entityId) { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatAct" -> {
                        val actionJson = call.argument<String>("actionJson") ?: "{}"
                        AuroraService.callPythonStringArg("habitat_act", actionJson) { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatIntegrityReport" -> {
                        AuroraService.callPythonString("habitat_integrity_report") { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatBackup" -> {
                        AuroraService.callPythonString("habitat_backup") { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatRestore" -> {
                        val backupPath = call.argument<String>("backupPath") ?: ""
                        AuroraService.callPythonStringArg("habitat_restore", backupPath) { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatIsolateCorrupt" -> {
                        AuroraService.callPythonString("habitat_isolate_corrupt") { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    "habitatReset" -> {
                        AuroraService.callPythonString("habitat_reset") { json ->
                            runOnUiThread { result.success(json) }
                        }
                    }
                    else             -> result.notImplemented()
                }
            }

        EventChannel(engine.dartExecutor.binaryMessenger, EVENTS)
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(args: Any?, sink: EventChannel.EventSink?) { AuroraService.onSinkConnected(sink) }
                override fun onCancel(args: Any?) { AuroraService.onSinkConnected(null) }
            })

        startAuroraService()
        registerOverlayReceiver()
        requestRuntimePermissions()

        // Start camera immediately if permission is already granted
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            startCameraCapture()
        }
        // Start the PARALLEL ambient-audio path immediately if permission is
        // already granted -- independent of whether/when SpeechRecognizer
        // sessions happen (Section VI/VII).
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                == PackageManager.PERMISSION_GRANTED) {
            startAmbientAudioCapture()
        }
    }

    // ── Permissions ───────────────────────────────────────────────────────────

    private fun requestRuntimePermissions() {
        val perms = mutableListOf<String>()
        fun need(p: String) = ContextCompat.checkSelfPermission(this, p) != PackageManager.PERMISSION_GRANTED
        if (need(Manifest.permission.RECORD_AUDIO)) perms.add(Manifest.permission.RECORD_AUDIO)
        if (need(Manifest.permission.CAMERA))       perms.add(Manifest.permission.CAMERA)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            need(Manifest.permission.POST_NOTIFICATIONS))
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        if (perms.isNotEmpty()) ActivityCompat.requestPermissions(this, perms.toTypedArray(), PERM_REQUEST)
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != PERM_REQUEST) return

        fun granted(p: String): Boolean {
            val i = permissions.indexOf(p)
            return i >= 0 && grantResults[i] == PackageManager.PERMISSION_GRANTED
        }

        if (granted(Manifest.permission.RECORD_AUDIO)) {
            runOnUiThread {
                AuroraService.eventSink?.success(
                    JSONObject().put("source","permission").put("type","microphone").put("granted",true).toString()
                )
            }
            startAmbientAudioCapture()
        }
        if (granted(Manifest.permission.CAMERA)) startCameraCapture()
    }

    // ── TTS ───────────────────────────────────────────────────────────────────

    private fun initTts() {
        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.US
                tts?.setSpeechRate(0.9f)
                ttsReady = true
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {}
                    override fun onDone(utteranceId: String?) {
                        // Repair Q: conversation-active window ends when
                        // she finishes speaking (if listening restarts
                        // right after, startNativeStt() below switches
                        // back to front camera again -- a little
                        // redundant rebinding in that case, correct and
                        // simple either way).
                        switchCamera(front = false)
                        runOnUiThread {
                            AuroraService.eventSink?.success(
                                JSONObject().put("source","tts").put("type","done").toString()
                            )
                        }
                    }
                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) {}
                    // Fires for each spoken word/range — minSdk 26 guarantees this is called.
                    override fun onRangeStart(utteranceId: String?, start: Int, end: Int, frame: Int) {
                        runOnUiThread {
                            AuroraService.eventSink?.success(
                                JSONObject().put("source","tts").put("type","word").toString()
                            )
                        }
                    }
                })
            }
        }
    }

    // Diagnostic hardening, part 5 (per Sunni: she now boots all the way to
    // "Listening…" -- boot itself succeeds -- but crashes again almost
    // immediately after, too fast for any polling-loop heartbeat to catch).
    // The first real native calls after a successful boot are exactly here:
    // TextToSpeech.speak() (the 'ready' case in home_screen.dart calls
    // _speak("Aurora is online.") right away) and SpeechRecognizer creation/
    // start.
    //
    // Two things a review caught before this shipped, both real:
    // 1. home_screen.dart's _init() calls _startListening() unconditionally
    //    at Flutter widget-mount time -- concurrently with, not after,
    //    AuroraService.kt's bootPython(). Writing to the same
    //    last_boot_stage.txt file both processes' markers use would let
    //    this class's writes clobber the actual Python boot trail (or vice
    //    versa) on a genuine race. Uses its own last_app_stage.txt instead
    //    -- bootPython() checks both files, preferring the boot-stage one
    //    since a real boot failure is diagnostically more specific.
    // 2. A marker left behind after a call *succeeds* looks identical to
    //    one left behind because the process died mid-call -- there's
    //    nothing else that ever clears this file. Without clearing it,
    //    every ordinary future close/force-stop/reboot would falsely
    //    report "previous crash" forever after the first real one. Cleared
    //    once startListening() actually returns without throwing, since
    //    reaching a stable, actively-listening state means nothing died.
    private fun markAppStage(stage: String) {
        try {
            val f = File(filesDir, "aurora_state/last_app_stage.txt")
            f.parentFile?.mkdirs()
            f.writeText("time=${System.currentTimeMillis()} stage=$stage")
        } catch (_: Throwable) { /* best-effort */ }
    }

    private fun clearAppStage() {
        try { File(filesDir, "aurora_state/last_app_stage.txt").delete() } catch (_: Throwable) {}
    }

    private fun nativeSpeak(text: String) {
        if (!ttsReady || text.isEmpty()) return
        markAppStage("nativeSpeak: about to call tts.speak(\"${text.take(60)}\")")
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, UUID.randomUUID().toString())
        markAppStage("nativeSpeak: tts.speak() call returned")
    }

    // ── STT ───────────────────────────────────────────────────────────────────

    private fun startNativeStt() {
        markAppStage("startNativeStt: entered")
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) { requestRuntimePermissions(); return }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return
        // Repair Q: about to actively listen to a person -- there's a
        // face to react to now. See switchCamera()'s docstring for the
        // symmetric back-camera switch on TTS completion.
        markAppStage("startNativeStt: about to switchCamera(front=true)")
        switchCamera(front = true)
        // SpeechRecognizer becomes stale after each session on Android — calling
        // startListening() on a previously-used instance silently does nothing.
        // Destroy and recreate every time so each session starts from a clean state.
        markAppStage("startNativeStt: about to create SpeechRecognizer")
        speechRecognizer?.destroy()
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
        speechRecognizer?.setRecognitionListener(sttListener)
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.US.toString())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        markAppStage("startNativeStt: about to call speechRecognizer.startListening()")
        speechRecognizer?.startListening(intent)
        // Reached a stable, actively-listening state -- clear rather than
        // leave a "returned" marker sitting around to be misread as a
        // crash symptom on some unrelated future launch.
        clearAppStage()
    }

    // ── Camera (Aurora visual sensory intake) ─────────────────────────────────

    private fun startCameraCapture() {
        ProcessCameraProvider.getInstance(this).also { future ->
            future.addListener({
                cameraProvider = future.get()
                bindCamera(front = false)
            }, ContextCompat.getMainExecutor(this))
        }
    }

    // Repair Q (per Sunni, 2026-08-19): rebinds to whichever camera is
    // requested. Called with front=true when active conversation begins
    // (there's a face to react to) and front=false once it ends (back to
    // passive environmental scanning, the original always-on behavior).
    // A no-op guard on isCameraFront avoids redundant unbind/rebind
    // churn if called twice for the same state in a row.
    private fun switchCamera(front: Boolean) {
        if (front == isCameraFront) return
        bindCamera(front)
    }

    private fun bindCamera(front: Boolean) {
        val provider = cameraProvider ?: return
        isCameraFront = front
        // Sunni, 2026-08-21: OUTPUT_IMAGE_FORMAT_RGBA_8888 used to be
        // requested here, which routes every frame through CameraX's
        // internal RenderScript-based YUV->RGBA converter -- confirmed
        // live as a real, intermittent crash ("Only JPEG and YUV_420_888
        // are supported now" IllegalArgumentException, thrown from a
        // background analyzer thread on camera switch). YUV_420_888 is
        // CameraX's own guaranteed-safe default output format, needs no
        // internal conversion, and is what ML Kit's InputImage.fromMediaImage()
        // natively expects anyway -- toJpeg() below does its own
        // stride-aware YUV_420_888 -> NV21 -> JPEG conversion instead.
        val analysis = ImageAnalysis.Builder()
            .setTargetResolution(Size(640, 480))
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
            .build()

        analysis.setAnalyzer(cameraExecutor) { proxy ->
            val now = System.currentTimeMillis()
            if (now - lastFrameMs >= FRAME_INTERVAL_MS) {
                lastFrameMs = now
                val jpeg = proxy.toJpeg()
                if (jpeg != null) AuroraService.provideCameraFrame(jpeg)
            }
            // Face detection only makes sense pointed at a person -- only
            // runs on the front stream, and closes the proxy itself
            // (ML Kit detection is async) rather than falling through to
            // the unconditional proxy.close() below.
            if (front && now - lastFaceDetectMs >= FACE_DETECT_INTERVAL_MS) {
                lastFaceDetectMs = now
                detectFace(proxy)
            } else {
                proxy.close()
            }
        }

        try {
            provider.unbindAll()
            val selector = if (front) CameraSelector.DEFAULT_FRONT_CAMERA else CameraSelector.DEFAULT_BACK_CAMERA
            provider.bindToLifecycle(this, selector, analysis)
        } catch (e: Exception) {
            Log.w(TAG, "camera bind failed: ${e.message}")
        }
    }

    // Repair Q: runs ML Kit face detection on one front-camera frame and
    // forwards a bounding-box-derived proximity/position signal to
    // Python. faceFraction is the detected face's area as a fraction of
    // total frame area -- a simple, real proxy for "how close" (a face
    // filling more of the frame is a face that's closer to the lens,
    // exactly the way it would read to a person). offsetX/offsetY are
    // the face center's position within the frame, -1..1 from
    // left/top to right/bottom, for gaze/lean-direction. Reports
    // detected=false (not just silence) when no face is found, so
    // Python can distinguish "no one's there" from "haven't checked yet."
    // MUST close the ImageProxy in every branch, including on failure --
    // an un-closed proxy stalls the whole analyzer pipeline.
    private fun detectFace(proxy: ImageProxy) {
        val mediaImage = proxy.image
        if (mediaImage == null) {
            proxy.close()
            return
        }
        val inputImage = InputImage.fromMediaImage(mediaImage, proxy.imageInfo.rotationDegrees)
        faceDetector.process(inputImage)
            .addOnSuccessListener { faces ->
                if (faces.isNotEmpty()) {
                    // Largest face if more than one is in frame -- the
                    // one most likely to be whoever's actually talking.
                    val face = faces.maxByOrNull { it.boundingBox.width().toLong() * it.boundingBox.height().toLong() }
                    if (face != null) {
                        val frameW = inputImage.width.toFloat()
                        val frameH = inputImage.height.toFloat()
                        val box = face.boundingBox
                        val faceFraction = ((box.width().toFloat() * box.height().toFloat()) / (frameW * frameH)).coerceIn(0f, 1f)
                        val cx = box.centerX().toFloat()
                        val cy = box.centerY().toFloat()
                        val offsetX = (((cx / frameW) - 0.5f) * 2f).coerceIn(-1f, 1f)
                        val offsetY = (((cy / frameH) - 0.5f) * 2f).coerceIn(-1f, 1f)
                        AuroraService.provideFaceObservation(true, faceFraction, offsetX, offsetY)
                    } else {
                        AuroraService.provideFaceObservation(false, 0f, 0f, 0f)
                    }
                } else {
                    AuroraService.provideFaceObservation(false, 0f, 0f, 0f)
                }
            }
            .addOnFailureListener {
                // Best-effort sensory signal -- a detection failure is
                // not an error worth surfacing, just "nothing this tick."
            }
            .addOnCompleteListener {
                proxy.close()
            }
    }

    private fun ImageProxy.toJpeg(): ByteArray? {
        return try {
            val nv21 = yuv420888ToNv21(this)
            val yuvImage = YuvImage(nv21, ImageFormat.NV21, width, height, null)
            val out = ByteArrayOutputStream()
            yuvImage.compressToJpeg(Rect(0, 0, width, height), 70, out)
            out.toByteArray()
        } catch (e: Exception) {
            Log.w(TAG, "toJpeg: ${e.message}")
            null
        }
    }

    // Row/pixel-stride-aware YUV_420_888 -> NV21 conversion (standard
    // Android camera pattern -- planes are not guaranteed tightly packed
    // or interleaved the same way across devices, so a naive buffer
    // concat can produce a corrupted image even when it doesn't crash).
    // Y plane copied row by row at rowStride; U/V planes interleaved as
    // NV21's V,U,V,U,... using each plane's own rowStride/pixelStride.
    private fun yuv420888ToNv21(image: ImageProxy): ByteArray {
        val w = image.width
        val h = image.height
        val yPlane = image.planes[0]
        val uPlane = image.planes[1]
        val vPlane = image.planes[2]

        val nv21 = ByteArray(w * h * 3 / 2)
        var pos = 0

        val yBuffer = yPlane.buffer
        val yRowStride = yPlane.rowStride
        for (row in 0 until h) {
            yBuffer.position(row * yRowStride)
            yBuffer.get(nv21, pos, w)
            pos += w
        }

        val uBuffer = uPlane.buffer
        val vBuffer = vPlane.buffer
        val uRowStride = uPlane.rowStride
        val uPixelStride = uPlane.pixelStride
        val vRowStride = vPlane.rowStride
        val vPixelStride = vPlane.pixelStride
        val chromaHeight = h / 2
        val chromaWidth = w / 2
        for (row in 0 until chromaHeight) {
            for (col in 0 until chromaWidth) {
                val vIndex = row * vRowStride + col * vPixelStride
                val uIndex = row * uRowStride + col * uPixelStride
                nv21[pos++] = vBuffer.get(vIndex)
                nv21[pos++] = uBuffer.get(uIndex)
            }
        }
        return nv21
    }

    // ── Ambient audio (Section VI/VII) ──────────────────────────────────────
    //
    // Bounded, low-rate raw-PCM capture -- mirrors the camera path's
    // FRAME_INTERVAL_MS throttling in spirit (Section XXVIII: no constant
    // maximum-frequency sampling). Chunks are read continuously off the
    // mic (AudioRecord itself blocks on read()), but only pushed to Python
    // at AUDIO_PUSH_INTERVAL_MS, so the DSP/Chaquopy cost stays bounded
    // even though the underlying hardware stream is continuous.
    private fun startAmbientAudioCapture() {
        if (audioCaptureRunning) return
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) return

        val sampleRate = AMBIENT_AUDIO_SAMPLE_RATE
        val minBufferBytes = AudioRecord.getMinBufferSize(
            sampleRate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
        )
        if (minBufferBytes <= 0) {
            Log.w(TAG, "ambient audio: device does not support the requested format")
            return
        }
        val bufferBytes = minBufferBytes * 2

        @Suppress("MissingPermission")  // checked above
        fun tryCreate(source: Int): AudioRecord? = try {
            val candidate = AudioRecord(
                source, sampleRate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, bufferBytes,
            )
            if (candidate.state == AudioRecord.STATE_INITIALIZED) candidate else {
                candidate.release()
                null
            }
        } catch (e: Exception) {
            Log.w(TAG, "ambient audio: AudioRecord(source=$source) failed: ${e.message}")
            null
        }

        // UNPROCESSED gives the rawest signal (no AGC/noise-suppression
        // coloring the features below) but isn't guaranteed available on
        // every device; MIC is the universal fallback.
        val record = tryCreate(MediaRecorder.AudioSource.UNPROCESSED)
            ?: tryCreate(MediaRecorder.AudioSource.MIC)

        if (record == null) {
            Log.w(TAG, "ambient audio: AudioRecord failed to initialize on this device -- capture unavailable")
            return
        }

        audioRecord = record
        audioCaptureRunning = true
        record.startRecording()

        audioExecutor.execute {
            Process.setThreadPriority(Process.THREAD_PRIORITY_AUDIO)
            val chunk = ShortArray(bufferBytes / 2)
            while (audioCaptureRunning) {
                val rec = audioRecord ?: break
                val read = try {
                    rec.read(chunk, 0, chunk.size)
                } catch (e: Exception) {
                    Log.w(TAG, "ambient audio read failed: ${e.message}")
                    break
                }
                if (read <= 0) continue

                val now = System.currentTimeMillis()
                if (now - lastAudioPushMs < AUDIO_PUSH_INTERVAL_MS) continue
                lastAudioPushMs = now

                // Pack the read samples into little-endian 16-bit PCM bytes --
                // matches provide_audio_observation_raw()'s expected format
                // exactly (numpy.frombuffer(..., dtype="<i2")).
                val bytes = ByteArray(read * 2)
                val bb = ByteBuffer.wrap(bytes).order(java.nio.ByteOrder.LITTLE_ENDIAN)
                for (i in 0 until read) bb.putShort(chunk[i])
                AuroraService.provideAudioObservationRaw(bytes, sampleRate)
            }
        }
    }

    private fun stopAmbientAudioCapture() {
        audioCaptureRunning = false
        try {
            audioRecord?.stop()
        } catch (_: Exception) {}
        audioRecord?.release()
        audioRecord = null
    }

    // ── Service / overlay helpers ─────────────────────────────────────────────

    private fun startAuroraService() {
        val i = Intent(this, AuroraService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i)
        else startService(i)
    }

    private fun registerOverlayReceiver() {
        val filter = IntentFilter(OverlayService.ACTION_OVERLAY_TAPPED)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
            registerReceiver(overlayReceiver, filter, RECEIVER_NOT_EXPORTED)
        else
            registerReceiver(overlayReceiver, filter)
    }

    private fun hasOverlayPermission() =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(this)

    private fun requestOverlayPermission() =
        startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))

    private fun hasScreenObserverPermission(): Boolean {
        val enabled = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        val serviceName = "$packageName/${ScreenObserverService::class.java.name}"
        return enabled.split(':').any { it.equals(serviceName, ignoreCase = true) }
    }

    private fun requestScreenObserverPermission() =
        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    override fun onDestroy() {
        super.onDestroy()
        cameraProvider?.unbindAll()
        cameraExecutor.shutdown()
        stopAmbientAudioCapture()
        audioExecutor.shutdown()
        speechRecognizer?.destroy()
        speechRecognizer = null
        tts?.shutdown()
        tts = null
        try { unregisterReceiver(overlayReceiver) } catch (_: Exception) {}
    }
}
