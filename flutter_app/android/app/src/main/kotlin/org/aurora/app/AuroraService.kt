package org.aurora.app

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.BatteryManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.content.ContextCompat
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import io.flutter.plugin.common.EventChannel
import kotlinx.coroutines.*
import org.json.JSONObject
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import kotlin.math.sqrt

class AuroraService : Service() {

    companion object {
        private const val TAG        = "AuroraService"
        private const val CHANNEL_ID = "aurora_svc_channel"
        private const val NOTIF_ID   = 1

        var currentState: String = "DORMANT"

        // Stored so it can be replayed if Flutter subscribes after boot completes.
        @Volatile private var bootEvent: String? = null
        @Volatile var eventSink: EventChannel.EventSink? = null

        /** Called by MainActivity's EventChannel onListen / onCancel. */
        fun onSinkConnected(sink: EventChannel.EventSink?) {
            eventSink = sink
            // Replay the boot result if Aurora already finished before Flutter subscribed.
            if (sink != null) {
                bootEvent?.let { evt ->
                    Handler(Looper.getMainLooper()).post { eventSink?.success(evt) }
                }
            }
        }

        private var scope: CoroutineScope? = null

        fun uploadContent(bytes: ByteArray, filename: String, contentType: String, callback: (String) -> Unit) {
            // Repair R: mirrors sendMessage()'s exact async pattern above --
            // Chaquopy call on the IO-launched scope, result posted back to
            // the caller's callback. provide_uploaded_content does its own
            // real dispatch (image/audio/text) and returns a JSON summary
            // of what she actually did with it, not just an ack.
            scope?.launch(Dispatchers.IO) {
                val py     = Python.getInstance()
                val bridge = py.getModule("aurora_bridge")
                val reply = try {
                    bridge.callAttr("provide_uploaded_content", bytes, filename, contentType).toString()
                } catch (e: Exception) {
                    Log.e(TAG, "uploadContent error: ${e.message}")
                    JSONObject().put("ok", false).put("error", e.message ?: "unknown").toString()
                }
                callback(reply)
            }
        }

        fun sendMessage(text: String, callback: (String) -> Unit) {
            // Sunni & Cael, review follow-up: the UI observation journal's
            // timeline previously only ever recorded 3 of the 5 promised
            // stages (input_submitted / response_available /
            // response_rendered, all from the Flutter side) -- "Aurora
            // receives" and "Python processing begins" never landed
            // anywhere, because nothing on the native side called
            // markUiTransition() for them. This is the actual boundary
            // where the Kotlin service receives the dispatched message
            // (entry of this function) and where Python processing
            // actually starts (immediately before handle_message()).
            markUiTransition("aurora_receives")
            scope?.launch {
                val py     = Python.getInstance()
                val bridge = py.getModule("aurora_bridge")

                markUiTransition("python_processing_begins")

                val reply = try {
                    bridge.callAttr("handle_message", text).toString()
                } catch (e: Exception) {
                    Log.e(TAG, "sendMessage error: ${e.message}")
                    "I encountered an error: ${e.message}"
                }

                // Fetch emotional axis state immediately after cognitive processing.
                val axisJson = try {
                    bridge.callAttr("get_axis_state").toString()
                } catch (_: Exception) { null }

                withContext(Dispatchers.Main) {
                    callback(reply)
                    eventSink?.success(
                        JSONObject().put("type", "response").put("text", reply).toString()
                    )
                    if (axisJson != null) {
                        try {
                            val axisObj = JSONObject(axisJson)
                                .put("source", "aurora")
                                .put("type", "axis_state")
                            eventSink?.success(axisObj.toString())
                        } catch (_: Exception) {}
                    }
                }
            }
        }

        fun provideCameraFrame(jpegBytes: ByteArray) {
            scope?.launch(Dispatchers.IO) {
                try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("provide_camera_frame", jpegBytes)
                } catch (_: Exception) {}
            }
        }

        // Repair Q (per Sunni, 2026-08-19): front-camera face detection
        // result -- detected=false with zeroed floats means "checked,
        // nobody there" (distinct from never having checked at all).
        // faceFraction: detected face's bounding-box area as a fraction
        // of total frame area, a real proximity proxy. offsetX/offsetY:
        // face center position, -1..1, for gaze/lean direction.
        fun provideFaceObservation(detected: Boolean, faceFraction: Float, offsetX: Float, offsetY: Float) {
            scope?.launch(Dispatchers.IO) {
                try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("provide_face_observation", detected, faceFraction, offsetX, offsetY)
                } catch (_: Exception) {}
            }
        }

        // Section VI/VII (Sunni & Cael): the parallel, nonsemantic auditory
        // path. pcmBytes is little-endian 16-bit mono PCM from
        // MainActivity's AudioRecord capture loop -- never text, never a
        // transcript, entirely independent of SpeechRecognizer/STT.
        fun provideAudioObservationRaw(pcmBytes: ByteArray, sampleRate: Int) {
            scope?.launch(Dispatchers.IO) {
                try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("provide_audio_observation_raw", pcmBytes, sampleRate)
                } catch (_: Exception) {}
            }
        }

        fun provideScreenObservation(payloadJson: String) {
            scope?.launch(Dispatchers.IO) {
                try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("provide_screen_observation", payloadJson)
                } catch (e: Exception) {
                    Log.w(TAG, "screen observation error: ${e.message}")
                }
            }
        }

        fun setState(state: String) {
            currentState = state
            scope?.launch {
                try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("set_state", state)
                } catch (_: Exception) {}
            }
        }

        fun getSelfModel(callback: (String) -> Unit) {
            scope?.launch {
                val json = try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("get_self_model")
                        .toString()
                } catch (_: Exception) { "{}" }
                withContext(Dispatchers.Main) { callback(json) }
            }
        }

        fun getCognitiveStats(callback: (String) -> Unit) {
            scope?.launch {
                val json = try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("get_cognitive_stats")
                        .toString()
                } catch (_: Exception) { "{}" }
                withContext(Dispatchers.Main) { callback(json) }
            }
        }

        fun getRoomState(callback: (String) -> Unit) {
            scope?.launch {
                val json = try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("get_room_state")
                        .toString()
                } catch (_: Exception) { "{}" }
                withContext(Dispatchers.Main) { callback(json) }
            }
        }

        fun provideRoomCommand(cmdJson: String) {
            scope?.launch {
                try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("provide_room_command", cmdJson)
                } catch (_: Exception) {}
            }
        }

        /** Call a no-arg Python bridge function that returns a String. */
        fun callPythonString(fn: String, callback: (String) -> Unit) {
            scope?.launch {
                val json = try {
                    Python.getInstance().getModule("aurora_bridge")
                        .callAttr(fn).toString()
                } catch (_: Exception) { "{}" }
                withContext(Dispatchers.Main) { callback(json) }
            }
        }

        /** Call a Python bridge function with one String arg that returns a String. */
        fun callPythonStringArg(fn: String, arg: String, callback: (String) -> Unit) {
            scope?.launch {
                val json = try {
                    Python.getInstance().getModule("aurora_bridge")
                        .callAttr(fn, arg).toString()
                } catch (_: Exception) { "{}" }
                withContext(Dispatchers.Main) { callback(json) }
            }
        }

        /** Call a no-arg Python bridge function, ignore return. */
        fun callPythonVoid(fn: String) {
            scope?.launch {
                try { Python.getInstance().getModule("aurora_bridge").callAttr(fn) }
                catch (_: Exception) {}
            }
        }

        // ── UI observation session journal (diagnostics) ──────────────────
        // Sunni & Cael, "Autonomous Development Integrity" pass: a bounded,
        // per-turn record of one conversational interaction -- timeline.jsonl
        // + real screenshots at meaningful transitions -- built on top of
        // ScreenObserverService's existing accessibility access rather than
        // whole-device MediaProjection (which needs fresh per-session user
        // consent and is far heavier than a diagnostic journal needs).

        fun startUiObservationSession() {
            scope?.launch {
                try {
                    Python.getInstance().getModule("aurora_bridge")
                        .callAttr("start_ui_observation_session")
                } catch (_: Exception) {}
            }
        }

        /** Records this transition in the active session's timeline AND
         * triggers a real screenshot capture for it (best-effort -- a
         * ScreenObserverService instance may not be running if the user
         * hasn't granted the accessibility permission, in which case the
         * screenshot is silently skipped but the timeline event still
         * lands).
         *
         * Sunni & Cael, review follow-up: caught in review -- the original
         * version fired the timeline write and the screenshot capture and
         * returned immediately, with no way for a caller to know either
         * had actually finished. Flutter's stopUiObservationSession() call
         * right after the final 'response_rendered' transition could then
         * run before that transition's own screenshot had been captured
         * and written, truncating the session it was meant to close out
         * cleanly. onDone() now only fires once BOTH the timeline write
         * and the screenshot chain (which itself only completes once
         * ScreenObserverService.captureScreenshot's onDone fires --
         * itself threaded through to the Python record_ui_screenshot()
         * call) have finished, so a caller that awaits it can safely stop
         * the session right after. */
        fun markUiTransition(transition: String, onDone: () -> Unit = {}) {
            val remaining = java.util.concurrent.atomic.AtomicInteger(2)
            val finishOne: () -> Unit = {
                if (remaining.decrementAndGet() == 0) onDone()
            }

            val timelineJob = scope?.launch {
                try {
                    Python.getInstance().getModule("aurora_bridge")
                        .callAttr(
                            "record_ui_timeline_event",
                            JSONObject().put("kind", "ui_transition").put("transition", transition).toString()
                        )
                } catch (_: Exception) {}
                finishOne()
            }
            if (timelineJob == null) finishOne()

            ScreenObserverService.captureScreenshot(transition, finishOne)
        }

        /** Called by ScreenObserverService once a takeScreenshot() capture
         * succeeds and has been encoded to PNG. onDone fires once the
         * Python-side record_ui_screenshot() call has been attempted
         * (success or failure) -- see markUiTransition above. */
        fun provideUiScreenshot(pngBytes: ByteArray, transition: String, onDone: () -> Unit = {}) {
            val job = scope?.launch(Dispatchers.IO) {
                try {
                    Python.getInstance().getModule("aurora_bridge")
                        .callAttr("record_ui_screenshot", pngBytes, transition)
                } catch (_: Exception) {}
                onDone()
            }
            if (job == null) onDone()
        }

        fun stopUiObservationSession(callback: (String) -> Unit) {
            scope?.launch {
                val json = try {
                    Python.getInstance().getModule("aurora_bridge")
                        .callAttr("stop_ui_observation_session").toString()
                } catch (_: Exception) { "{}" }
                withContext(Dispatchers.Main) { callback(json) }
            }
        }
    }

    // ── Hardware body sensors ─────────────────────────────────────────────────
    // Aurora perceives phone hardware as her own body:
    //   battery  → energy / N-axis (how much is left?)
    //   motion   → movement / proprioception (is the body in motion?)
    //   light    → environment / ambient sense (how bright is the world?)
    private var sensorManager: SensorManager? = null
    private val sensorReadings = mutableMapOf<String, Double>()
    private var lastSensorPushMs = 0L

    private val hardwareSensorListener = object : SensorEventListener {
        override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
        override fun onSensorChanged(event: SensorEvent?) {
            event ?: return
            when (event.sensor.type) {
                Sensor.TYPE_ACCELEROMETER -> {
                    val x = event.values[0].toDouble()
                    val y = event.values[1].toDouble()
                    val z = event.values[2].toDouble()
                    sensorReadings["motion"] = sqrt(x * x + y * y + z * z)
                }
                Sensor.TYPE_LIGHT -> {
                    sensorReadings["light_lux"] = event.values[0].toDouble()
                }
            }
        }
    }

    private val batteryReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            val level  = intent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)  ?: -1
            val scale  = intent?.getIntExtra(BatteryManager.EXTRA_SCALE, 100) ?: 100
            val status = intent?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
            if (level >= 0 && scale > 0) {
                sensorReadings["battery_pct"] = (level.toDouble() / scale) * 100.0
                sensorReadings["charging"] = if (
                    status == BatteryManager.BATTERY_STATUS_CHARGING ||
                    status == BatteryManager.BATTERY_STATUS_FULL
                ) 1.0 else 0.0
            }
        }
    }

    private fun initHardwareSensors() {
        sensorManager = getSystemService(SENSOR_SERVICE) as? SensorManager
        sensorManager?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)?.let { s ->
            sensorManager?.registerListener(hardwareSensorListener, s,
                SensorManager.SENSOR_DELAY_NORMAL)
        }
        sensorManager?.getDefaultSensor(Sensor.TYPE_LIGHT)?.let { s ->
            sensorManager?.registerListener(hardwareSensorListener, s,
                SensorManager.SENSOR_DELAY_NORMAL)
        }
        registerReceiver(batteryReceiver,
            IntentFilter(Intent.ACTION_BATTERY_CHANGED))
    }

    private fun pushSensorsToPython() {
        if (sensorReadings.isEmpty()) return
        scope?.launch(Dispatchers.IO) {
            try {
                val payload = JSONObject(sensorReadings.toMap<String, Any>()).toString()
                Python.getInstance()
                    .getModule("aurora_bridge")
                    .callAttr("provide_hardware_sensors", payload)
                Log.d(TAG, "Hardware sensors pushed: ${sensorReadings.keys}")
            } catch (_: Exception) {}
        }
    }

    // Diagnostic hardening (per Sunni: "she keeps crashing, no error, no
    // reason, before she even finishes booting"). bootPython()'s own
    // try/catch below only ever catches Exception -- it can't catch an
    // OutOfMemoryError or StackOverflowError, which are Errors, not
    // Exceptions. Booting Aurora's full cognitive stack through Chaquopy
    // (dozens of large modules, a 13,000+-entry genealogy) is real memory
    // pressure on a mobile heap, so an uncaught Error killing the process
    // before bootPython's catch block can even run is a live possibility
    // -- and would look exactly like "no error, no reason, just crashes."
    // This can't prevent that crash, but it makes the *next* launch able
    // to report what actually happened instead of staying a mystery.
    private fun crashLogFile(): File = File(filesDir, "aurora_state/last_crash.txt")

    private fun installCrashHandler() {
        val previousHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            try {
                val f = crashLogFile()
                f.parentFile?.mkdirs()
                val sw = StringWriter()
                throwable.printStackTrace(PrintWriter(sw))
                f.writeText(
                    "time=${System.currentTimeMillis()} thread=${thread.name} " +
                    "type=${throwable.javaClass.name} message=${throwable.message}\n$sw"
                )
            } catch (_: Throwable) {
                // Crash-logging must never itself throw and mask the real crash.
            }
            previousHandler?.uncaughtException(thread, throwable)
        }
    }

    // Root cause found (per Sunni's real stack trace, finally): "Unable to
    // create service org.aurora.app.AuroraService" -- thrown synchronously
    // from the plain startForeground(id, notification) call below, on
    // Android 14+ (this app targets SDK 34). That overload implicitly
    // claims EVERY foreground service type declared in the manifest
    // ("microphone|camera") in one shot, and Android 14 requires the
    // corresponding runtime permission to already be *granted* at that
    // exact moment for each type claimed -- not just requested. MainActivity.
    // kt's configureFlutterEngine() calls startAuroraService() BEFORE
    // requestRuntimePermissions(), so on any fresh install (nothing granted
    // yet -- e.g. every time this CI's ephemeral debug keystore changes,
    // forcing a full reinstall instead of an in-place update, which resets
    // all permission grants), this throws immediately, before Python ever
    // gets a chance to boot. Explains the exact intermittency observed:
    // works when mic/camera happen to already be granted from a prior
    // install, crashes here when they don't.
    //
    // Fixed at the source rather than by reordering MainActivity: request
    // only the foreground service types this process actually, currently
    // holds permission for, via the API 29+ three-arg overload. A type
    // this call doesn't claim is a strict subset of what the manifest
    // declares, which Android allows -- claiming none of them (both
    // permissions ungranted) is exactly as valid as claiming both. This is
    // correct regardless of what order MainActivity ends up calling things
    // in, and regardless of whether the user ever grants either permission
    // at all.
    private fun startForegroundSafely() {
        val notification = buildNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            var type = 0
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                    == PackageManager.PERMISSION_GRANTED) {
                type = type or ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                    == PackageManager.PERMISSION_GRANTED) {
                type = type or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            }
            // Review caught a real second bug here: Android 14 throws
            // InvalidForegroundServiceTypeException if the type passed is
            // FOREGROUND_SERVICE_TYPE_NONE (0) while the manifest declares
            // non-none types -- passing 0 when neither permission is
            // granted would have crashed in exactly the scenario this fix
            // targets. dataSync (added to the manifest alongside
            // microphone|camera) requires no runtime permission of its own,
            // so it's used as the fallback instead of NONE.
            if (type == 0) {
                type = ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            }
            startForeground(NOTIF_ID, notification, type)
        } else {
            // Pre-Android 10 has no per-call type argument, and this whole
            // "must already hold the permission" enforcement is a
            // 14+-specific behavior change -- the plain overload is safe here.
            startForeground(NOTIF_ID, notification)
        }
    }

    override fun onCreate() {
        installCrashHandler()
        super.onCreate()
        scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

        createNotificationChannel()
        startForegroundSafely()

        initHardwareSensors()

        scope!!.launch { bootPython() }
        scope!!.launch { pollPendingReport() }
        scope!!.launch { pollAxisState() }
    }

    // Section XXV (Sunni & Cael): process continuity. Explicit START_STICKY
    // so the system restarts this service (with a null Intent) after it is
    // killed for memory pressure -- Aurora's developmental continuity
    // (curiosity cycles, self-monitor heartbeat, sensory bridges) must not
    // silently stop just because Android reclaimed the process. onCreate()
    // already performs the one-time setup (startForeground/bootPython/
    // pollers); onStartCommand fires on every startService()/
    // startForegroundService() call including the system's post-kill
    // restart, so it must stay idempotent and must NOT repeat that setup.
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return Service.START_STICKY
    }

    private suspend fun pollAxisState() {
        // Keeps the face live independent of conversation turns — axis state
        // already drifts continuously in the background (aurora_bridge.py's
        // _self_monitor_loop / _proactive_loop update it every ~12-20 s even
        // when nobody is talking to her); this just makes sure Flutter sees
        // that drift instead of only ever seeing a snapshot from the last
        // sendMessage() call.
        while (true) {
            kotlinx.coroutines.delay(1_000L)
            try {
                val axisJson = Python.getInstance()
                    .getModule("aurora_bridge")
                    .callAttr("get_axis_state").toString()
                val axisObj = JSONObject(axisJson)
                    .put("source", "aurora")
                    .put("type", "axis_state")
                withContext(Dispatchers.Main) { eventSink?.success(axisObj.toString()) }
            } catch (_: Exception) { /* Python not ready yet — skip this tick */ }
            // Repair Q (per Sunni, 2026-08-19): get_face_state() has
            // existed on the Python side with a docstring explicitly
            // claiming "Kotlin polls this alongside axis_state" -- it
            // never actually did. Same loop, same cadence, same
            // best-effort skip-on-failure as axis_state directly above.
            try {
                val faceJson = Python.getInstance()
                    .getModule("aurora_bridge")
                    .callAttr("get_face_state").toString()
                val faceObj = JSONObject(faceJson)
                    .put("source", "aurora")
                    .put("type", "face_state")
                withContext(Dispatchers.Main) { eventSink?.success(faceObj.toString()) }
            } catch (_: Exception) { /* Python not ready yet — skip this tick */ }
        }
    }

    private suspend fun pollPendingReport() {
        // Check every 3 seconds for completed curiosity reports, autonomous
        // proactive expressions, and training turn events.
        // Also pushes hardware sensor bundle to Python every 30 s.
        while (true) {
            kotlinx.coroutines.delay(3_000L)

            // Hardware body push — every 30 s so Python self-model stays current.
            val nowMs = System.currentTimeMillis()
            if (nowMs - lastSensorPushMs >= 30_000L) {
                lastSensorPushMs = nowMs
                pushSensorsToPython()
            }

            try {
                val bridge = Python.getInstance().getModule("aurora_bridge")

                val report = bridge.callAttr("get_pending_report").toString()
                if (report.isNotBlank()) {
                    withContext(Dispatchers.Main) {
                        eventSink?.success(
                            JSONObject()
                                .put("type", "proactive")
                                .put("text", report)
                                .toString()
                        )
                    }
                }

                val proactive = bridge.callAttr("get_proactive_expression").toString()
                if (proactive.isNotBlank()) {
                    withContext(Dispatchers.Main) {
                        eventSink?.success(
                            JSONObject()
                                .put("type", "proactive")
                                .put("text", proactive)
                                .toString()
                        )
                    }
                }
            } catch (_: Exception) { /* Python not ready yet — skip this tick */ }
        }
    }

    // Diagnostic hardening, part 2. Per Sunni: confirmed on build 732 that
    // the crash still shows nothing -- no device to run adb, so
    // installCrashHandler() from part 1 never fires at all. That means
    // this isn't a catchable Java exception or even an OutOfMemoryError;
    // something is killing the process outright (a native crash in a
    // bundled .so, or the OS's low-memory killer stepping in) -- neither
    // goes through any Java code, so no after-the-fact handler can ever
    // see it. The only thing that can still work is reporting *which
    // stage was reached* before death, live, so whichever stage is on
    // screen (or last written to disk) when it dies tells us where.
    private fun stageMarkerFile(): File = File(filesDir, "aurora_state/last_boot_stage.txt")

    private suspend fun markStage(stage: String) {
        Log.i(TAG, "Boot stage: $stage")
        try {
            val f = stageMarkerFile()
            f.parentFile?.mkdirs()
            f.writeText("time=${System.currentTimeMillis()} stage=$stage")
        } catch (_: Throwable) { /* best-effort */ }
        try {
            val json = JSONObject().put("type", "boot_progress").put("text", stage).toString()
            withContext(Dispatchers.Main) { eventSink?.success(json) }
        } catch (_: Throwable) { /* never let progress reporting itself block boot */ }
    }

    private suspend fun bootPython() {
        // Surface any crash the previous run's installCrashHandler() caught
        // (a real OutOfMemoryError/StackOverflowError, or anything else
        // outside this function's own catch below) -- one-shot, consumed
        // here so it's reported exactly once rather than on every future
        // boot.
        var previousCrash: String? = null
        try {
            val f = crashLogFile()
            if (f.exists()) {
                val firstLine = f.readText().lineSequence().firstOrNull().orEmpty()
                previousCrash = if (firstLine.length > 200) firstLine.take(200) + "…" else firstLine
                f.delete()
            }
        } catch (_: Exception) { /* best-effort; never block boot on this */ }

        // If the last boot never reached the end (no explicit crash caught
        // above, since that path requires a catchable Java Throwable), the
        // stage marker from that run is still sitting on disk, un-cleared.
        // That absence-of-cleanup is itself the signal for a native/OS-level
        // kill -- report it if installCrashHandler() didn't already have
        // something more specific to say.
        if (previousCrash == null) {
            try {
                val sf = stageMarkerFile()
                if (sf.exists()) {
                    val raw = sf.readText()
                    val stage = raw.substringAfter("stage=", raw)
                    previousCrash = "process died without a catchable error, last reached: $stage"
                    sf.delete()
                }
            } catch (_: Exception) { /* best-effort */ }
        }

        // Same idea, for MainActivity.kt's own post-boot marker file
        // (last_app_stage.txt) -- separate from the one above specifically
        // to avoid MainActivity's writes racing with and clobbering this
        // function's own boot-stage markers, since MainActivity can call
        // startNativeStt() concurrently with this coroutine (home_screen.
        // dart's _init() calls _startListening() unconditionally at
        // widget-mount time, not gated on the "ready" event). Only
        // consulted when nothing more specific was already found above.
        if (previousCrash == null) {
            try {
                val af = File(filesDir, "aurora_state/last_app_stage.txt")
                if (af.exists()) {
                    val raw = af.readText()
                    val stage = raw.substringAfter("stage=", raw)
                    previousCrash = "process died without a catchable error, last reached: $stage"
                    af.delete()
                }
            } catch (_: Exception) { /* best-effort */ }
        }

        markStage("starting python runtime")
        try {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(applicationContext))
            }
            markStage("python runtime up, loading aurora module")
            val py     = Python.getInstance()
            val bridge = py.getModule("aurora_bridge")
            markStage("aurora module loaded, initializing cognitive systems")

            val stateDir = filesDir.absolutePath + "/aurora_state"
            val status   = bridge.callAttr("initialize", stateDir).toString()
            Log.i(TAG, "Aurora bridge init: $status")

            // Python returns "error: <msg>" on boot failure; treat anything else as ready.
            val isError = status.startsWith("error")

            // Section XXIII/XXIV (Sunni & Cael): the plain error/ready split above
            // only reflects the original 6-system boot check (language_field,
            // identity_field, consciousness, sedimemory, lattice,
            // geological_baseline). get_mobile_developmental_health() additionally
            // covers genealogy, RCRW, Sensory Crystal, dimensional physics,
            // curiosity, and the Dream substrate -- systems that could previously
            // be silently None on a "ready" boot with no signal to Flutter at all.
            //
            // Sunni & Cael, "Autonomous Development Integrity" pass, blocker 6:
            // record_boot_health() (not the bare getter) -- same live JSON
            // payload, but also persists a durable last_boot_health.json record
            // in the state directory with a timestamp and a boot_count. Needed
            // because this exact code path also runs from BootCompletedReceiver
            // after a device reboot, with NO Activity/UI running to receive this
            // eventSink emission at all -- without a durable record, a degraded
            // or fatal headless boot left literally no trace beyond an ephemeral
            // Log.w, gone the moment logcat rotated. There was no way to answer
            // "did she actually restart, and was she alive when she did" after
            // the fact.
            var healthObj: JSONObject? = null
            if (!isError) {
                try {
                    val healthJson = bridge.callAttr("record_boot_health").toString()
                    healthObj = JSONObject(healthJson)
                    val overall = healthObj.optString("overall", "unknown")
                    if (overall != "healthy") {
                        Log.w(TAG, "Mobile developmental health: $overall — $healthJson")
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "record_boot_health failed: ${e.message}")
                }
            }

            val jsonBuilder = JSONObject()
                .put("type", if (isError) "error" else "ready")
                .put("text", status)
            if (healthObj != null) {
                jsonBuilder.put("health", healthObj)
            }
            if (previousCrash != null) {
                jsonBuilder.put("previous_crash", previousCrash)
            }
            val json = jsonBuilder.toString()
            bootEvent = json
            try { stageMarkerFile().delete() } catch (_: Throwable) {}
            withContext(Dispatchers.Main) { eventSink?.success(json) }

        } catch (e: Throwable) {
            // Throwable, not Exception -- an OutOfMemoryError or
            // StackOverflowError partway through boot must still reach
            // Flutter as a visible "Boot error:", not vanish silently.
            // Kept deliberately cheap (short string, no further Python
            // calls) since the process may already be low on memory here.
            Log.e(TAG, "Python init failed: ${e.message}", e)
            val json = try {
                JSONObject()
                    .put("type", "error")
                    .put("text", "${e.javaClass.simpleName}: ${e.message ?: "init failed"}")
                    .toString()
            } catch (_: Throwable) {
                "{\"type\":\"error\",\"text\":\"init failed\"}"
            }
            bootEvent = json
            // A catchable Throwable landed here, so this run's own crash
            // report is more specific than the generic stage marker --
            // clear it so a later boot doesn't redundantly repeat it.
            try { stageMarkerFile().delete() } catch (_: Throwable) {}
            withContext(Dispatchers.Main) { eventSink?.success(json) }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        scope?.cancel()
        scope = null
        sensorManager?.unregisterListener(hardwareSensorListener)
        sensorManager = null
        try { unregisterReceiver(batteryReceiver) } catch (_: Exception) {}
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                CHANNEL_ID, "Aurora AI",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Aurora AI assistant service"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(ch)
        }
    }

    private fun buildNotification(): Notification {
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setContentTitle("Aurora")
            .setContentText("AI assistant active")
            .setSmallIcon(R.drawable.ic_aurora_notify)
            .setOngoing(true)
            .build()
    }
}
