package org.aurora.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
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
    }

    override fun onCreate() {
        super.onCreate()
        scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification())

        scope!!.launch { bootPython() }
        scope!!.launch { pollPendingReport() }
    }

    private suspend fun pollPendingReport() {
        // Check every 5 seconds for a completed curiosity session report.
        // When one arrives, push it to Flutter as a proactive message so it
        // displays and is spoken without the user needing to send anything.
        while (true) {
            kotlinx.coroutines.delay(5_000L)
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
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .build()
    }
}
