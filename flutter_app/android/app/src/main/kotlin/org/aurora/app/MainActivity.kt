package org.aurora.app

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    private val BRIDGE  = "org.aurora.app/bridge"
    private val EVENTS  = "org.aurora.app/events"

    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)

        // ── MethodChannel: Dart → Kotlin ───────────────────────────────────
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
                    "requestOverlayPermission" -> {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                            && !Settings.canDrawOverlays(this)
                        ) {
                            startActivity(
                                Intent(
                                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                    Uri.parse("package:$packageName")
                                )
                            )
                        }
                        result.success(Settings.canDrawOverlays(this))
                    }
                    "hasOverlayPermission" ->
                        result.success(
                            Build.VERSION.SDK_INT < Build.VERSION_CODES.M
                                    || Settings.canDrawOverlays(this)
                        )
                    else -> result.notImplemented()
                }
            }

        // ── EventChannel: Kotlin → Dart (streaming events) ────────────────
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
    }

    private fun startAuroraService() {
        val intent = Intent(this, AuroraService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }
}
