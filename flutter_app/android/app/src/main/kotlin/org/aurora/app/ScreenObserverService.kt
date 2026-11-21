// Authors: Sunni (Sir) Morningstar & Cael Devo
package org.aurora.app

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Bitmap
import android.graphics.Path
import android.graphics.Rect
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.Display
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.io.ByteArrayOutputStream
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
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

        // ── Her hands on the screen ──────────────────────────────────────
        // The same accessibility access that lets her see the screen lets
        // her act on it: press, hold, scroll, type, and the phone's own
        // back / home / recents.  Python (aurora_screen_apprenticeship.py)
        // reads a frame, chooses a node by its own grounding, and acts on
        // that node by its place in that frame.  A frame is only good until
        // the next read: acting on an older one is refused as "stale", so
        // she never presses something that has moved.  Nothing here chooses
        // what to press.

        private const val MAX_NODES = 240
        private val frameLock = Any()
        @Volatile private var frameId = 0L
        private var frameNodes: List<AccessibilityNodeInfo> = emptyList()
        // Her own presses, so the click events they cause are known as hers
        // and not taken for Sir showing her.
        @Volatile private var lastSelfActMs = 0L

        @JvmStatic
        fun isRunning(): Boolean = instance != null

        private fun fail(error: String): String =
            JSONObject().put("ok", false).put("error", error).toString()

        /** The screen as she can act on it: every node with something to
         * read or something to do, in tree order, with its place. */
        @JvmStatic
        fun readScreen(): String {
            val svc = instance ?: return fail("screen_hands_not_enabled")
            if (!AuroraService.screenSensingOn) return fail("screen_sensing_off")
            val root = svc.rootInActiveWindow ?: return fail("no_active_window")
            val kept = ArrayList<AccessibilityNodeInfo>()
            val arr = JSONArray()
            walk(root, 0, kept, arr)
            val bounds = Rect()
            root.getBoundsInScreen(bounds)
            val id = synchronized(frameLock) {
                frameId += 1
                frameNodes = kept
                frameId
            }
            return JSONObject()
                .put("ok", true)
                .put("frame", id)
                .put("package", root.packageName?.toString() ?: "")
                .put("screen", JSONArray().put(bounds.width()).put(bounds.height()))
                .put("nodes", arr)
                .put("at", System.currentTimeMillis() / 1000.0)
                .toString()
        }

        private fun walk(node: AccessibilityNodeInfo?, depth: Int,
                         kept: ArrayList<AccessibilityNodeInfo>, arr: JSONArray) {
            if (node == null || node.isPassword || kept.size >= MAX_NODES) return
            val text = node.text?.toString()?.trim() ?: ""
            val desc = node.contentDescription?.toString()?.trim() ?: ""
            val viewId = node.viewIdResourceName ?: ""
            val actionable = node.isClickable || node.isLongClickable ||
                node.isScrollable || node.isEditable || node.isCheckable
            if (node.isVisibleToUser && (actionable || text.isNotEmpty() || desc.isNotEmpty())) {
                val r = Rect()
                node.getBoundsInScreen(r)
                val password = node.isPassword
                arr.put(JSONObject()
                    .put("i", kept.size)
                    .put("text", if (password) "" else text.take(160))
                    .put("desc", desc.take(160))
                    .put("view_id", viewId)
                    .put("cls", node.className?.toString() ?: "")
                    .put("clickable", node.isClickable)
                    .put("long_clickable", node.isLongClickable)
                    .put("scrollable", node.isScrollable)
                    .put("editable", node.isEditable)
                    .put("checkable", node.isCheckable)
                    .put("checked", node.isChecked)
                    .put("password", password)
                    .put("actionable_ancestor", clickableAncestor(node) != null)
                    .put("depth", depth)
                    .put("bounds", JSONArray().put(r.left).put(r.top).put(r.right).put(r.bottom)))
                kept.add(node)
            }
            for (i in 0 until node.childCount) {
                walk(node.getChild(i), depth + 1, kept, arr)
                if (kept.size >= MAX_NODES) break
            }
        }

        private fun clickableAncestor(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
            var p: AccessibilityNodeInfo? = node.parent
            var hops = 0
            while (p != null && hops < 6) {
                if (p.isClickable) return p
                p = p.parent
                hops += 1
            }
            return null
        }

        private fun scrollableAncestor(node: AccessibilityNodeInfo): AccessibilityNodeInfo? {
            var p: AccessibilityNodeInfo? = node
            var hops = 0
            while (p != null && hops < 10) {
                if (p.isScrollable) return p
                p = p.parent
                hops += 1
            }
            return null
        }

        /** Act on node [index] of frame [frame].  action: tap, long_press,
         * scroll_forward, scroll_backward, type, focus. */
        @JvmStatic
        fun act(frame: Long, index: Int, action: String, text: String): String {
            val svc = instance ?: return fail("screen_hands_not_enabled")
            if (!AuroraService.screenSensingOn) return fail("screen_sensing_off")
            val node = synchronized(frameLock) {
                if (frame != frameId) return fail("stale")
                frameNodes.getOrNull(index)
            } ?: return fail("no_such_node")
            if (!node.refresh() || !node.isVisibleToUser || node.isPassword ||
                svc.rootInActiveWindow?.windowId != node.windowId) return fail("stale")
            lastSelfActMs = System.currentTimeMillis()
            val done = when (action) {
                "tap" -> {
                    val target = if (node.isClickable) node else clickableAncestor(node)
                    if (target != null) target.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    else svc.gestureAt(node, 60L)
                }
                "long_press" -> {
                    if (node.isLongClickable) node.performAction(AccessibilityNodeInfo.ACTION_LONG_CLICK)
                    else svc.gestureAt(node, 700L)
                }
                "scroll_forward" -> scrollableAncestor(node)
                    ?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD) ?: false
                "scroll_backward" -> scrollableAncestor(node)
                    ?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD) ?: false
                "type" -> {
                    // Never into a password box: what goes there is Sir's alone.
                    if (node.isPassword || !node.isEditable) false
                    else {
                        val args = Bundle()
                        args.putCharSequence(
                            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
                        node.performAction(AccessibilityNodeInfo.ACTION_FOCUS)
                        node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
                    }
                }
                "focus" -> node.performAction(AccessibilityNodeInfo.ACTION_FOCUS)
                else -> return fail("unknown_action:$action")
            }
            lastSelfActMs = System.currentTimeMillis()
            return JSONObject().put("ok", done).put("action", action).put("index", index)
                .apply { if (!done) put("error", "not_accepted") }
                .toString()
        }

        /** The phone's own keys: back, home, recents, notifications. */
        @JvmStatic
        fun globalAction(name: String): String {
            val svc = instance ?: return fail("screen_hands_not_enabled")
            if (!AuroraService.screenSensingOn) return fail("screen_sensing_off")
            val code = when (name) {
                "back" -> AccessibilityService.GLOBAL_ACTION_BACK
                "home" -> AccessibilityService.GLOBAL_ACTION_HOME
                "recents" -> AccessibilityService.GLOBAL_ACTION_RECENTS
                "notifications" -> AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS
                else -> return fail("unknown_global:$name")
            }
            lastSelfActMs = System.currentTimeMillis()
            val done = svc.performGlobalAction(code)
            return JSONObject().put("ok", done).put("action", name).toString()
        }

        /** A swipe across the screen, for a page that has no scroll action. */
        @JvmStatic
        fun swipe(x1: Int, y1: Int, x2: Int, y2: Int, durationMs: Long): String {
            val svc = instance ?: return fail("screen_hands_not_enabled")
            if (!AuroraService.screenSensingOn) return fail("screen_sensing_off")
            val path = Path()
            path.moveTo(x1.toFloat(), y1.toFloat())
            path.lineTo(x2.toFloat(), y2.toFloat())
            lastSelfActMs = System.currentTimeMillis()
            val done = svc.dispatchAndWait(path, durationMs.coerceIn(50L, 2_000L))
            return JSONObject().put("ok", done).put("action", "swipe").toString()
        }

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
            if (svc == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.R ||
                !AuroraService.screenSensingOn || svc.passwordFocused()) {
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
                                if (!AuroraService.screenSensingOn || svc.passwordFocused()) {
                                    result.hardwareBuffer.close()
                                    onDone()
                                    return
                                }
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

    private fun gestureAt(node: AccessibilityNodeInfo, durationMs: Long): Boolean {
        val r = Rect()
        node.getBoundsInScreen(r)
        if (r.isEmpty) return false
        val path = Path()
        path.moveTo(r.exactCenterX(), r.exactCenterY())
        return dispatchAndWait(path, durationMs)
    }

    private fun dispatchAndWait(path: Path, durationMs: Long): Boolean {
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0L, durationMs))
            .build()
        val latch = CountDownLatch(1)
        val done = AtomicBoolean(false)
        val sent = dispatchGesture(gesture, object : AccessibilityService.GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                done.set(true); latch.countDown()
            }
            override fun onCancelled(gestureDescription: GestureDescription?) {
                latch.countDown()
            }
        }, null)
        if (!sent) return false
        latch.await(durationMs + 1_500L, TimeUnit.MILLISECONDS)
        return done.get()
    }

    /** What a press or a typed change touched, so a step Sir shows her with
     * his own hands can be paired with what he said. */
    private fun sourceNode(event: AccessibilityEvent): JSONObject? {
        val n = event.source ?: return null
        val r = Rect()
        n.getBoundsInScreen(r)
        val password = n.isPassword || event.isPassword
        return JSONObject()
            .put("text", if (password) "" else (n.text?.toString()?.trim() ?: "").take(160))
            .put("desc", (n.contentDescription?.toString()?.trim() ?: "").take(160))
            .put("view_id", n.viewIdResourceName ?: "")
            .put("cls", n.className?.toString() ?: "")
            .put("editable", n.isEditable)
            .put("password", password)
            .put("bounds", JSONArray().put(r.left).put(r.top).put(r.right).put(r.bottom))
    }

    override fun onDestroy() {
        super.onDestroy()
        if (instance == this) instance = null
    }

    private var lastEventMs = 0L

    private fun passwordFocused(): Boolean {
        val root = rootInActiveWindow ?: return true
        return root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)?.isPassword == true
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        event ?: return
        synchronized(frameLock) {
            frameId += 1
            frameNodes = emptyList()
        }
        if (!AuroraService.screenSensingOn || event.isPassword ||
            event.source?.isPassword == true || passwordFocused()) return
        val now = System.currentTimeMillis()
        // A press or a typed change is a moment, not ambience: it is never
        // throttled away, because it may be Sir showing her a step.
        val moment = event.eventType == AccessibilityEvent.TYPE_VIEW_CLICKED ||
            event.eventType == AccessibilityEvent.TYPE_VIEW_LONG_CLICKED ||
            event.eventType == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED
        if (!moment && now - lastEventMs < 650L) return
        if (!moment) lastEventMs = now

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
        if (moment) {
            sourceNode(event)?.let { payload.put("source_node", it) }
            // Within a moment of her own press, the event is hers.
            payload.put("agent", if (now - lastSelfActMs < 900L) "self" else "user")
            if (event.eventType == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED && !event.isPassword) {
                payload.put("typed", (event.text?.joinToString(" ") ?: "").take(200))
            }
        }

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
        if (node == null || node.isPassword || out.size >= limit) return
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
        AccessibilityEvent.TYPE_VIEW_LONG_CLICKED -> "view_long_clicked"
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
