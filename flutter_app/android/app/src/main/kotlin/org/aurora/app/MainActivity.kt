package org.aurora.app

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject
import java.util.Locale
import java.util.UUID

class MainActivity : FlutterActivity() {

    private val BRIDGE       = "org.aurora.app/bridge"
    private val EVENTS       = "org.aurora.app/events"
    private val PERM_REQUEST = 1001

    @Volatile private var pendingSummon = false

    private val overlayReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            if (intent?.action == OverlayService.ACTION_OVERLAY_TAPPED) {
                pendingSummon = true
            }
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
                    JSONObject()
                        .put("source", "stt")
                        .put("type", "error")
                        .put("error", error)
                        .toString()
                )
            }
        }

        override fun onResults(results: Bundle?) {
            val text = results
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull() ?: ""
            runOnUiThread {
                AuroraService.eventSink?.success(
                    JSONObject()
                        .put("source", "stt")
                        .put("type", "result")
                        .put("text", text)
                        .put("final", true)
                        .toString()
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
                    JSONObject()
                        .put("source", "stt")
                        .put("type", "partial")
                        .put("text", text)
                        .toString()
                )
            }
        }

        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

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
                    "hasOverlayPermission"    -> result.success(hasOverlayPermission())
                    "requestOverlayPermission" -> {
                        requestOverlayPermission()
                        result.success(null)
                    }
                    "consumeOverlayTap" -> {
                        val had = pendingSummon
                        pendingSummon = false
                        result.success(had)
                    }
                    "startListening" -> {
                        startNativeStt()
                        result.success(null)
                    }
                    "stopListening" -> {
                        speechRecognizer?.stopListening()
                        result.success(null)
                    }
                    "speak" -> {
                        nativeSpeak(call.argument<String>("text") ?: "")
                        result.success(null)
                    }
                    "stopSpeaking" -> {
                        tts?.stop()
                        result.success(null)
                    }
                    "captureVision" -> {
                        captureVision()
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }

        EventChannel(engine.dartExecutor.binaryMessenger, EVENTS)
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(args: Any?, sink: EventChannel.EventSink?) {
                    AuroraService.eventSink = sink
                }
                override fun onCancel(args: Any?) {
                    AuroraService.eventSink = null
                }
            })

        startAuroraService()
        registerOverlayReceiver()
        requestRuntimePermissions()
    }

    private fun requestRuntimePermissions() {
        val perms = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            perms.add(Manifest.permission.RECORD_AUDIO)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            perms.add(Manifest.permission.CAMERA)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                perms.add(Manifest.permission.POST_NOTIFICATIONS)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_MEDIA_IMAGES)
                    != PackageManager.PERMISSION_GRANTED) {
                perms.add(Manifest.permission.READ_MEDIA_IMAGES)
            }
        } else {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                perms.add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                perms.add(Manifest.permission.READ_EXTERNAL_STORAGE)
            }
        }
        if (perms.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, perms.toTypedArray(), PERM_REQUEST)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERM_REQUEST) {
            val results = JSONObject()
            permissions.forEachIndexed { i, p ->
                val granted = grantResults[i] == PackageManager.PERMISSION_GRANTED
                val key = when(p) {
                    Manifest.permission.RECORD_AUDIO -> "microphone"
                    Manifest.permission.CAMERA -> "camera"
                    Manifest.permission.WRITE_EXTERNAL_STORAGE, 
                    Manifest.permission.READ_EXTERNAL_STORAGE,
                    Manifest.permission.READ_MEDIA_IMAGES -> "storage"
                    else -> p
                }
                results.put(key, granted)
            }
            
            runOnUiThread {
                AuroraService.eventSink?.success(
                    JSONObject()
                        .put("source", "permission")
                        .put("type", "update")
                        .put("granted_map", results)
                        .toString()
                )
            }
        }
    }

    // ── Camera Sensory ───────────────────────────────────────────────────────
    
    private fun captureVision() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            requestRuntimePermissions()
            return
        }

        val cameraProviderFuture = androidx.camera.lifecycle.ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            try {
                val cameraProvider = cameraProviderFuture.get()
                val imageCapture = androidx.camera.core.ImageCapture.Builder()
                    .setCaptureMode(androidx.camera.core.ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                    .build()

                val cameraSelector = androidx.camera.core.CameraSelector.DEFAULT_BACK_CAMERA

                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, imageCapture)

                val file = java.io.File(filesDir, "aurora_state/vision_seeds/screen/frame_latest.png")
                file.parentFile?.mkdirs()

                val outputOptions = androidx.camera.core.ImageCapture.OutputFileOptions.Builder(file).build()

                imageCapture.takePicture(
                    outputOptions,
                    ContextCompat.getMainExecutor(this),
                    object : androidx.camera.core.ImageCapture.OnImageSavedCallback {
                        override fun onImageSaved(output: androidx.camera.core.ImageCapture.OutputFileResults) {
                            Log.i("Aurora", "Vision capture successful: ${file.absolutePath}")
                            
                            // Haptic feedback
                            val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as android.os.Vibrator
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                                vibrator.vibrate(android.os.VibrationEffect.createOneShot(50, android.os.VibrationEffect.DEFAULT_AMPLITUDE))
                            } else {
                                @Suppress("DEPRECATION") vibrator.vibrate(50)
                            }

                            AuroraService.eventSink?.success(
                                JSONObject()
                                    .put("source", "camera")
                                    .put("type", "captured")
                                    .put("path", file.absolutePath)
                                    .toString()
                            )
                        }
                        override fun onError(exc: androidx.camera.core.ImageCaptureException) {
                            Log.e("Aurora", "Vision capture failed: ${exc.message}")
                        }
                    }
                )
            } catch (e: Exception) {
                Log.e("Aurora", "CameraProvider init failed: ${e.message}")
            }
        }, ContextCompat.getMainExecutor(this))
    }

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
                                JSONObject()
                                    .put("source", "tts")
                                    .put("type", "done")
                                    .toString()
                            )
                        }
                    }
                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) {}
                })
            }
        }
    }

    private fun nativeSpeak(text: String) {
        if (!ttsReady || text.isEmpty()) return
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, UUID.randomUUID().toString())
    }

    private fun startNativeStt() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            requestRuntimePermissions()
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return
        if (speechRecognizer == null) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
            speechRecognizer?.setRecognitionListener(sttListener)
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.US.toString())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        speechRecognizer?.startListening(intent)
    }

    private fun startAuroraService() {
        val i = Intent(this, AuroraService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i)
        else startService(i)
    }

    private fun registerOverlayReceiver() {
        val filter = IntentFilter(OverlayService.ACTION_OVERLAY_TAPPED)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(overlayReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(overlayReceiver, filter)
        }
    }

    private fun hasOverlayPermission() =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(this)

    private fun requestOverlayPermission() {
        startActivity(
            Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName"))
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        speechRecognizer?.destroy()
        speechRecognizer = null
        tts?.shutdown()
        tts = null
        try { unregisterReceiver(overlayReceiver) } catch (_: Exception) {}
    }
}
