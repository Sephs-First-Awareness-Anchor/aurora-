package org.aurora.app

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
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
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject
import java.io.ByteArrayOutputStream
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
                    "startTraining" -> {
                        val apiKey = call.argument<String>("apiKey") ?: ""
                        val model  = call.argument<String>("model")  ?: "gemini-2.5-flash"
                        val turns  = call.argument<Int>("turns")     ?: 200
                        AuroraService.startTraining(apiKey, model, turns) { reply ->
                            runOnUiThread { result.success(reply) }
                        }
                    }
                    "stopTraining"      -> { AuroraService.stopTraining(); result.success(null) }
                    "getTrainingStatus" -> {
                        AuroraService.getTrainingStatus { json ->
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

    private fun nativeSpeak(text: String) {
        if (!ttsReady || text.isEmpty()) return
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, UUID.randomUUID().toString())
    }

    // ── STT ───────────────────────────────────────────────────────────────────

    private fun startNativeStt() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) { requestRuntimePermissions(); return }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return
        // SpeechRecognizer becomes stale after each session on Android — calling
        // startListening() on a previously-used instance silently does nothing.
        // Destroy and recreate every time so each session starts from a clean state.
        speechRecognizer?.destroy()
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
        speechRecognizer?.setRecognitionListener(sttListener)
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.US.toString())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        speechRecognizer?.startListening(intent)
    }

    // ── Camera (Aurora visual sensory intake) ─────────────────────────────────

    private fun startCameraCapture() {
        ProcessCameraProvider.getInstance(this).also { future ->
            future.addListener({
                cameraProvider = future.get()
                bindCamera()
            }, ContextCompat.getMainExecutor(this))
        }
    }

    private fun bindCamera() {
        val provider = cameraProvider ?: return
        val analysis = ImageAnalysis.Builder()
            .setTargetResolution(Size(640, 480))
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
            .build()

        analysis.setAnalyzer(cameraExecutor) { proxy ->
            val now = System.currentTimeMillis()
            if (now - lastFrameMs >= FRAME_INTERVAL_MS) {
                lastFrameMs = now
                val jpeg = proxy.toJpeg()
                if (jpeg != null) AuroraService.provideCameraFrame(jpeg)
            }
            proxy.close()
        }

        try {
            provider.unbindAll()
            provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, analysis)
        } catch (e: Exception) {
            Log.w(TAG, "camera bind failed: ${e.message}")
        }
    }

    private fun ImageProxy.toJpeg(): ByteArray? {
        return try {
            val plane      = planes[0]
            val rowStride  = plane.rowStride
            val pixStride  = plane.pixelStride  // 4 for RGBA_8888
            val w          = width
            val h          = height
            val buf        = plane.buffer

            // Copy into a tightly-packed RGBA byte array, stripping row padding
            val rgba = ByteArray(w * h * 4)
            if (rowStride == w * pixStride) {
                buf.get(rgba)
            } else {
                for (row in 0 until h) {
                    buf.position(row * rowStride)
                    buf.get(rgba, row * w * 4, w * 4)
                }
            }

            val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
            bmp.copyPixelsFromBuffer(ByteBuffer.wrap(rgba))
            val out = ByteArrayOutputStream()
            bmp.compress(Bitmap.CompressFormat.JPEG, 70, out)
            bmp.recycle()
            out.toByteArray()
        } catch (e: Exception) {
            Log.w(TAG, "toJpeg: ${e.message}")
            null
        }
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
        speechRecognizer?.destroy()
        speechRecognizer = null
        tts?.shutdown()
        tts = null
        try { unregisterReceiver(overlayReceiver) } catch (_: Exception) {}
    }
}
