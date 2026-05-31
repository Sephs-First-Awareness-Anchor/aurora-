package org.aurora.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
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
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import io.flutter.plugin.common.EventChannel
import kotlinx.coroutines.*
import org.json.JSONObject
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

        fun sendMessage(text: String, callback: (String) -> Unit) {
            scope?.launch {
                val py     = Python.getInstance()
                val bridge = py.getModule("aurora_bridge")

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

        fun startTraining(apiKey: String, model: String, durationMinutes: Double, callback: (String) -> Unit) {
            scope?.launch {
                val result = try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("start_training", apiKey, model, durationMinutes)
                        .toString()
                } catch (e: Exception) { "error: ${e.message}" }
                withContext(Dispatchers.Main) { callback(result) }
            }
        }

        fun stopTraining() {
            scope?.launch(Dispatchers.IO) {
                try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("stop_training")
                } catch (_: Exception) {}
            }
        }

        fun getTrainingStatus(callback: (String) -> Unit) {
            scope?.launch {
                val json = try {
                    Python.getInstance()
                        .getModule("aurora_bridge")
                        .callAttr("get_training_status")
                        .toString()
                } catch (_: Exception) { "{\"active\":false,\"turn\":0,\"total\":0}" }
                withContext(Dispatchers.Main) { callback(json) }
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

    override fun onCreate() {
        super.onCreate()
        scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification())

        initHardwareSensors()

        scope!!.launch { bootPython() }
        scope!!.launch { pollPendingReport() }
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

                // Training events — emit each turn individually
                val trainingBatch = bridge.callAttr("get_training_events").toString()
                if (trainingBatch.isNotBlank() && trainingBatch != "[]") {
                    try {
                        val arr = org.json.JSONArray(trainingBatch)
                        for (i in 0 until arr.length()) {
                            val evt = arr.getJSONObject(i).toString()
                            withContext(Dispatchers.Main) { eventSink?.success(evt) }
                        }
                    } catch (_: Exception) {}
                }
            } catch (_: Exception) { /* Python not ready yet — skip this tick */ }
        }
    }

    private suspend fun bootPython() {
        try {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(applicationContext))
            }
            val py     = Python.getInstance()
            val bridge = py.getModule("aurora_bridge")

            val stateDir = filesDir.absolutePath + "/aurora_state"
            val status   = bridge.callAttr("initialize", stateDir).toString()
            Log.i(TAG, "Aurora bridge init: $status")

            // Python returns "error: <msg>" on boot failure; treat anything else as ready.
            val isError = status.startsWith("error")
            val json = JSONObject()
                .put("type", if (isError) "error" else "ready")
                .put("text", status)
                .toString()
            bootEvent = json
            withContext(Dispatchers.Main) { eventSink?.success(json) }

        } catch (e: Exception) {
            Log.e(TAG, "Python init failed: ${e.message}")
            val json = JSONObject()
                .put("type", "error")
                .put("text", e.message ?: "init failed")
                .toString()
            bootEvent = json
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
