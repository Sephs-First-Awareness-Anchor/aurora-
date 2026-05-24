package org.aurora.app

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray
import org.json.JSONObject

class ScreenObserverService : AccessibilityService() {

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
