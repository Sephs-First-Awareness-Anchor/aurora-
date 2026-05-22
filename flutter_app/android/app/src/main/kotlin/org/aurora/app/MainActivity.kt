package org.aurora.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.os.Build
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject

class MainActivity : FlutterActivity() {

    private val BRIDGE = "org.aurora.app/bridge"
    private val EVENTS = "org.aurora.app/events"

    // Set to true when OverlayService broadcasts a tap while the app was
    // backgrounded. Cleared after MainActivity reads and forwards it.
    @Volatile private var pendingSummon = false

    private val overlayReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            if (intent?.action == OverlayService.ACTION_OVERLAY_TAPPED) {
                pendingSummon = true
                // onResume fires right after because bringAppToForeground()
                // was already called inside OverlayService
            }
        }
    }

    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)

        // ── MethodChannel ──────────────────────────────────────────────────
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
                    "hasOverlayPermission" -> result.success(hasOverlayPermission())
                    "requestOverlayPermission" -> {
                        requestOverlayPermission()
                        result.success(null)
                    }
                    // Dart calls this on resume to ask if the overlay was tapped
                    "consumeOverlayTap" -> {
                        val had = pendingSummon
                        pendingSummon = false
                        result.success(had)
                    }
                    else -> result.notImplemented()
                }
            }

        // ── EventChannel ───────────────────────────────────────────────────
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
            Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName"))
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        try { unregisterReceiver(overlayReceiver) } catch (_: Exception) {}
    }
}
