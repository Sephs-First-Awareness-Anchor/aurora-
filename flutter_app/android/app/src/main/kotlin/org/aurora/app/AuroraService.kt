package org.aurora.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
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
        @Volatile var eventSink: EventChannel.EventSink? = null

        private var scope: CoroutineScope? = null

        fun sendMessage(text: String, callback: (String) -> Unit) {
            scope?.launch {
                val reply = try {
                    val py     = Python.getInstance()
                    val bridge = py.getModule("aurora_bridge")
                    bridge.callAttr("handle_message", text).toString()
                } catch (e: Exception) {
                    Log.e(TAG, "sendMessage error: ${e.message}")
                    "I encountered an error: ${e.message}"
                }
                withContext(Dispatchers.Main) {
                    callback(reply)
                    eventSink?.success(
                        JSONObject().put("type", "response").put("text", reply).toString()
                    )
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
    }

    private suspend fun bootPython() {
        try {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(applicationContext))
            }
            val py     = Python.getInstance()
            val bridge = py.getModule("aurora_bridge")

            // Pass the app's files directory so Aurora can persist state
            val stateDir = filesDir.absolutePath + "/aurora_state"
            val status   = bridge.callAttr("initialize", stateDir).toString()
            Log.i(TAG, "Aurora bridge init: $status")

            withContext(Dispatchers.Main) {
                eventSink?.success(
                    JSONObject().put("type", "ready").put("text", status).toString()
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Python init failed: ${e.message}")
            withContext(Dispatchers.Main) {
                eventSink?.success(
                    JSONObject().put("type", "error").put("text", e.message ?: "init failed").toString()
                )
            }
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
