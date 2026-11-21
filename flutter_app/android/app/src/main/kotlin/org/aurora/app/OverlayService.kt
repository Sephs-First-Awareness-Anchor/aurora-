package org.aurora.app

// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// OverlayService -- her thin line of presence along the top of the screen
// (surface restructure 4b, Sir 2026-11-18).
//
// The draggable orb is gone.  In its place is one wiry line across the full
// width, directly under the status bar, in the same TYPE_APPLICATION_OVERLAY
// window and under the same overlay permission.  That permission, with the
// window actually showing, is what lets her tools open other apps while she
// is behind them, so the line stays a real, visible overlay window.
//
//   * Touch: the line lets every touch pass through (FLAG_NOT_TOUCHABLE).
//     Open and Hide are on the overlay's ongoing notification.
//   * Placement: the window reads the status bar's height from the system's
//     window insets and sits just beneath it, on every device and rotation.
//   * Motion: PresenceMotion.kt, drawn on the display's own frame clock
//     (Choreographer) at the screen's refresh rate.  Her state is read once
//     a second on a background thread, never on the drawing thread.
//   * Voice: MainActivity hands her real voice waveform (Visualizer on her
//     TTS audio session), each word's timing and her hearing level to
//     PresenceVoice below.
//   * Failures: anything that fails here is sent to the app (NativeFaults)
//     and shown on screen there, and a short note is drawn on the line
//     itself, so it can be screenshotted.

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.drawable.Icon
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import android.util.TypedValue
import android.view.Choreographer
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.view.WindowManager
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

/** Her voice and hearing, handed from MainActivity to the line. */
object PresenceVoice {
    @Volatile var waveform: FloatArray? = null
    @Volatile var waveformAtMs: Long = 0L
    @Volatile var wordAtMs: Long = 0L
    @Volatile var hearingLevel: Double = 0.0
    @Volatile var hearingAtMs: Long = 0L

    fun pushWaveform(bytes: ByteArray) {
        waveform = PresenceMotion.fromUnsigned8(bytes)
        waveformAtMs = System.currentTimeMillis()
    }

    fun word() { wordAtMs = System.currentTimeMillis() }

    fun hear(level: Double) {
        hearingLevel = level
        hearingAtMs = System.currentTimeMillis()
    }
}

/** Native failures, sent to the app's on-screen fault panel. */
object NativeFaults {
    private val lastSentMs = HashMap<String, Long>()
    private val main = Handler(Looper.getMainLooper())
    @Volatile var lastNote: String = ""

    fun report(where: String, e: Throwable) {
        val at = e.stackTrace.firstOrNull()
        val detail = "${e.javaClass.simpleName}: ${e.message ?: "(no message)"}" +
            (if (at != null) "\n  at $at" else "")
        report(where, detail)
    }

    fun report(where: String, detail: String) {
        Log.e("Aurora", "$where: $detail")
        lastNote = "$where: ${detail.lineSequence().firstOrNull() ?: ""}"
        val now = System.currentTimeMillis()
        synchronized(lastSentMs) {
            // The same fault every frame is sent once every few seconds.
            if (now - (lastSentMs[where] ?: 0L) < 5_000L) return
            lastSentMs[where] = now
        }
        val evt = JSONObject()
            .put("source", "native")
            .put("type", "error")
            .put("text", where)
            .put("detail", detail)
            .toString()
        main.post { try { AuroraService.eventSink?.success(evt) } catch (_: Throwable) {} }
    }
}

class OverlayService : Service() {

    companion object {
        const val ACTION_OVERLAY_TAPPED = "org.aurora.app.OVERLAY_TAPPED"
        const val ACTION_OPEN = "org.aurora.app.PRESENCE_OPEN"
        const val ACTION_HIDE = "org.aurora.app.PRESENCE_HIDE"
        private const val CHANNEL_ID = "aurora_overlay_channel"
        private const val NOTIF_ID   = 42
        private const val LINE_HEIGHT_DP = 14f
    }

    private lateinit var windowManager: WindowManager
    @Volatile private var line: AuroraPresenceLineView? = null
    private var params: WindowManager.LayoutParams? = null
    private var poller: ScheduledExecutorService? = null
    private var lastFrameNanos = 0L
    private var running = false

    private val frameCallback = object : Choreographer.FrameCallback {
        override fun doFrame(frameTimeNanos: Long) {
            if (!running) return
            val dt = if (lastFrameNanos == 0L) 0.0 else (frameTimeNanos - lastFrameNanos) / 1e9
            lastFrameNanos = frameTimeNanos
            try {
                line?.frame(dt)
            } catch (e: Throwable) {
                NativeFaults.report("presence line (motion)", e)
            }
            Choreographer.getInstance().postFrameCallback(this)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification())
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        addLine()
        running = true
        Choreographer.getInstance().postFrameCallback(frameCallback)
        poller = Executors.newSingleThreadScheduledExecutor().also {
            it.scheduleWithFixedDelay({ refreshState() }, 1_500L, 1_000L, TimeUnit.MILLISECONDS)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_OPEN -> {
                bringAppToForeground()
                sendBroadcast(Intent(ACTION_OVERLAY_TAPPED).setPackage(packageName))
            }
            ACTION_HIDE -> stopSelf()
        }
        return START_STICKY
    }

    /** Her state, read off the drawing thread once a second. */
    private fun refreshState() {
        try {
            if (!com.chaquo.python.Python.isStarted()) return
            val raw = com.chaquo.python.Python.getInstance()
                .getModule("aurora_bridge")
                .callAttr("get_axis_state")?.toString() ?: return
            val j = JSONObject(raw)
            val axes = doubleArrayOf(
                j.optDouble("X", 0.5), j.optDouble("T", 0.5), j.optDouble("N", 0.5),
                j.optDouble("B", 0.5), j.optDouble("A", 0.5),
            )
            val p = j.optJSONObject("pressure")
            val pressure = if (p == null) DoubleArray(0) else doubleArrayOf(
                p.optDouble("X", 0.0), p.optDouble("T", 0.0), p.optDouble("N", 0.0),
                p.optDouble("B", 0.0), p.optDouble("A", 0.0),
            )
            val view = line ?: return
            view.post { view.setState(axes, pressure) }
        } catch (e: Throwable) {
            NativeFaults.report("presence line (reading her state)", e)
        }
    }

    private fun statusBarHeight(): Int {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val insets = windowManager.currentWindowMetrics.windowInsets
                    .getInsetsIgnoringVisibility(WindowInsets.Type.statusBars())
                return insets.top
            }
        } catch (e: Throwable) {
            NativeFaults.report("presence line (status bar height)", e)
        }
        val id = resources.getIdentifier("status_bar_height", "dimen", "android")
        return if (id > 0) resources.getDimensionPixelSize(id) else (24 * resources.displayMetrics.density).toInt()
    }

    private fun addLine() {
        val view = AuroraPresenceLineView(this)
        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

        val dp = resources.displayMetrics.density
        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            (LINE_HEIGHT_DP * dp).toInt(),
            layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )
        lp.gravity = Gravity.TOP or Gravity.START
        lp.x = 0
        lp.y = statusBarHeight()
        try {
            windowManager.addView(view, lp)
            line = view
            params = lp
        } catch (e: Throwable) {
            NativeFaults.report("presence line (showing the window)", e)
        }
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        // Rotation or a display change: sit under the status bar again.
        val lp = params ?: return
        val view = line ?: return
        try {
            lp.y = statusBarHeight()
            windowManager.updateViewLayout(view, lp)
        } catch (e: Throwable) {
            NativeFaults.report("presence line (placing it)", e)
        }
    }

    private fun bringAppToForeground() {
        try {
            val launch = packageManager.getLaunchIntentForPackage(packageName) ?: return
            launch.flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP or
                    Intent.FLAG_ACTIVITY_REORDER_TO_FRONT
            startActivity(launch)
        } catch (e: Throwable) {
            NativeFaults.report("presence line (opening the app)", e)
        }
    }

    override fun onDestroy() {
        running = false
        Choreographer.getInstance().removeFrameCallback(frameCallback)
        poller?.shutdownNow()
        poller = null
        val view = line
        line = null
        if (view != null) {
            try { windowManager.removeView(view) } catch (_: Exception) {}
        }
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(
                CHANNEL_ID, "Aurora Overlay",
                NotificationManager.IMPORTANCE_MIN
            ).apply { setShowBadge(false) }
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(ch)
        }
    }

    private fun actionIntent(action: String, code: Int): PendingIntent =
        PendingIntent.getService(
            this, code,
            Intent(this, OverlayService::class.java).setAction(action),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

    private fun buildNotification(): Notification {
        val b = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                    Notification.Builder(this, CHANNEL_ID)
                else @Suppress("DEPRECATION") Notification.Builder(this)
        val open = actionIntent(ACTION_OPEN, 1)
        val hide = actionIntent(ACTION_HIDE, 2)
        val icon = Icon.createWithResource(this, R.drawable.ic_aurora_notify)
        return b.setContentTitle("Aurora")
            .setContentText("Here with you")
            .setSmallIcon(R.drawable.ic_aurora_notify)
            .setOngoing(true)
            .setContentIntent(open)
            .addAction(Notification.Action.Builder(icon, "Open", open).build())
            .addAction(Notification.Action.Builder(icon, "Hide", hide).build())
            .build()
    }
}


// =============================================================================
// AuroraPresenceLineView -- one thin line, the full width of the screen.
//
// Drawn from PresenceMotion every display frame.  At rest its colour,
// thickness, drift and tension are her state; while she listens her hearing
// moves it; while she speaks it traces her voice.  Touches pass through the
// window, so the view never handles one.
// =============================================================================

class AuroraPresenceLineView(context: Context) : View(context) {

    private val motion = PresenceMotion()
    private val dp = resources.displayMetrics.density
    private val path = Path()
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }
    private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }
    private val notePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 120, 120)
        textSize = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 9f, resources.displayMetrics)
    }
    private var shape = FloatArray(0)
    private val hsv = FloatArray(3)

    fun setState(axes: DoubleArray, pressure: DoubleArray) {
        motion.setState(axes, pressure)
    }

    fun frame(dt: Double) {
        val now = System.currentTimeMillis()
        val v = PresenceVoice
        // Her voice: the waveform while it is fresh, plus a soft nudge on
        // each word that fades over a quarter second.
        val wave = if (now - v.waveformAtMs < 250L) v.waveform else null
        val wordNudge = if (v.wordAtMs > 0L) kotlin.math.exp(-(now - v.wordAtMs) / 250.0) else 0.0
        motion.setVoice(maxOf(PresenceMotion.levelOf(wave), 0.6 * wordNudge))
        // Her hearing, while it is fresh.
        motion.setHearing(if (now - v.hearingAtMs < 1_000L) v.hearingLevel else 0.0)
        motion.step(dt)
        shape = motion.shape(dt, wave)
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()
        if (w <= 0f || h <= 0f) return
        try {
            val pts = shape
            if (pts.size < 2) return
            val thick = (motion.thickness.value * dp).toFloat()
            val mid = h / 2f
            val amp = (h / 2f - thick).coerceAtLeast(1f)
            path.reset()
            for (i in pts.indices) {
                val x = w * i / (pts.size - 1)
                val y = mid + pts[i] * amp
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            var hue = (motion.hue.value % 360.0).toFloat()
            if (hue < 0f) hue += 360f
            hsv[0] = hue
            hsv[1] = motion.saturation.value.toFloat().coerceIn(0f, 1f)
            hsv[2] = motion.brightness.value.toFloat().coerceIn(0f, 1f)
            val colour = Color.HSVToColor(hsv)
            glowPaint.color = Color.argb(70, Color.red(colour), Color.green(colour), Color.blue(colour))
            glowPaint.strokeWidth = thick * 3f
            canvas.drawPath(path, glowPaint)
            linePaint.color = colour
            linePaint.strokeWidth = thick
            canvas.drawPath(path, linePaint)
            val note = NativeFaults.lastNote
            if (note.isNotEmpty()) canvas.drawText(note.take(90), 4f * dp, h - 2f, notePaint)
        } catch (e: Throwable) {
            NativeFaults.report("presence line (drawing)", e)
        }
    }
}
