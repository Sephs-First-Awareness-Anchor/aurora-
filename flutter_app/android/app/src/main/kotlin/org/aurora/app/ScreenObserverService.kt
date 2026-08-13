package org.aurora.app

import android.accessibilityservice.AccessibilityService
import android.graphics.Bitmap
import android.os.Build
import android.util.Log
import android.view.Display
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.io.ByteArrayOutputStream
import org.json.JSONArray
import org.json.JSONObject

class ScreenObserverService : AccessibilityService() {

    companion object {
        private const val TAG = "ScreenObserverService"

        // Sunni & Cael, "Autonomous Development Integrity" pass: this
        // service already has the harder piece of screen sensing in place
        // (accessibility access + window-content retrieval). API 30's
        // AccessibilityService.takeScreenshot() extends that same access to
        // real pixels, without whole-device MediaProjection's per-session
        // consent requirement -- appropriate for a bounded, per-turn
        // diagnostic journal rather than continuous screen recording.
        @Volatile private var instance: ScreenObserverService? = null

        /** Best-effort real screenshot capture for the UI observation
         * session journal (see AuroraService.markUiTransition). A no-op
         * (not an error) when this accessibility service isn't currently
         * running (permission not granted) or the device is below API 30 --
         * the timeline event itself still lands either way.
         *
         * Sunni & Cael, review follow-up: takeScreenshot() is inherently
         * asynchronous (its own callback API), and the original version
         * gave the caller no way to know when the capture -- and the
         * Python-side record_ui_screenshot() write it triggers -- actually
         * finished. markUiTransition() below needs that signal to avoid
         * calling stop_ui_observation_session() while a screenshot is
         * still mid-flight. onDone() fires exactly once on every exit path:
         * the two early no-op returns, both takeScreenshot() callback
         * branches, and the synchronous-throw catch block. */
        fun captureScreenshot(transition: String, onDone: () -> Unit = {}) {
            val svc = instance
            if (svc == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
                onDone()
                return
            }
            try {
                svc.takeScreenshot(
                    Display.DEFAULT_DISPLAY,
                    svc.mainExecutor,
                    object : AccessibilityService.TakeScreenshotCallback {
                        override fun onSuccess(result: AccessibilityService.ScreenshotResult) {
                            try {
                                val hwBitmap = Bitmap.wrapHardwareBuffer(
                                    result.hardwareBuffer, result.colorSpace
                                )
                                // Hardware bitmaps can't be compressed directly on
                                // every OEM/driver combination -- copy to a normal
                                // software bitmap first, same pattern used for
                                // camera frames elsewhere in this app.
                                val softBitmap = hwBitmap?.copy(Bitmap.Config.ARGB_8888, false)
                                result.hardwareBuffer.close()
                                if (softBitmap != null) {
                                    val stream = ByteArrayOutputStream()
                                    softBitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
                                    AuroraService.provideUiScreenshot(stream.toByteArray(), transition, onDone)
                                    softBitmap.recycle()
                                } else {
                                    onDone()
                                }
                            } catch (e: Exception) {
                                Log.w(TAG, "screenshot processing error: ${e.message}")
                                onDone()
                            }
                        }
                        override fun onFailure(errorCode: Int) {
                            Log.w(TAG, "takeScreenshot failed: errorCode=$errorCode")
                            onDone()
                        }
                    }
                )
            } catch (e: Exception) {
                Log.w(TAG, "takeScreenshot error: ${e.message}")
                onDone()
            }
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onDestroy() {
        super.onDestroy()
        if (instance == this) instance = null
    }

    private var lastEventMs = 0L

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return
        val now = System.currentTimeMillis()
        if (now - lastEventMs < 650L) return
        lastEventMs = now

        val visibleText = LinkedHashSet<String>()
        event.text?.forEach { addText(visibleText, it?.toString()) }
        event.contentDescription?.toString()?.let { addText(visibleText, it) }
        collectNodeText(rootInActiveWindow, visibleText, 18)

        val payload = JSONObject()
            .put("source", "android_accessibility")
            .put("observed_at", now / 1000.0)
            .put("package", event.packageName?.toString() ?: "")
            .put("class", event.className?.toString() ?: "")
            .put("event_type", eventTypeName(event.eventType))
            .put("visible_text", JSONArray(visibleText.take(16)))
            .put("action_surface", "phone_screen")

        AuroraService.provideScreenObservation(payload.toString())
        AuroraService.eventSink?.success(
            JSONObject()
                .put("source", "screen")
                .put("type", "observed")
                .put("text", summarize(payload))
                .toString()
        )
    }

    override fun onInterrupt() = Unit

    private fun collectNodeText(
        node: AccessibilityNodeInfo?,
        out: LinkedHashSet<String>,
        limit: Int
    ) {
        if (node == null || out.size >= limit) return
        addText(out, node.text?.toString())
        addText(out, node.contentDescription?.toString())
        for (i in 0 until node.childCount) {
            collectNodeText(node.getChild(i), out, limit)
            if (out.size >= limit) break
        }
    }

    private fun addText(out: LinkedHashSet<String>, raw: String?) {
        val text = raw?.trim()?.replace(Regex("\\s+"), " ") ?: return
        if (text.length < 2) return
        out.add(if (text.length > 120) text.take(117) + "..." else text)
    }

    private fun eventTypeName(type: Int): String = when (type) {
        AccessibilityEvent.TYPE_VIEW_CLICKED -> "view_clicked"
        AccessibilityEvent.TYPE_VIEW_FOCUSED -> "view_focused"
        AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED -> "text_changed"
        AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> "window_state_changed"
        AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> "window_content_changed"
        AccessibilityEvent.TYPE_VIEW_SCROLLED -> "view_scrolled"
        else -> "event_$type"
    }

    private fun summarize(payload: JSONObject): String {
        val app = payload.optString("package", "phone")
        val kind = payload.optString("event_type", "screen_event")
        val visible = payload.optJSONArray("visible_text")
        val first = if (visible != null && visible.length() > 0) visible.optString(0) else ""
        return listOf(app, kind, first).filter { it.isNotBlank() }.joinToString(" | ")
    }
}
