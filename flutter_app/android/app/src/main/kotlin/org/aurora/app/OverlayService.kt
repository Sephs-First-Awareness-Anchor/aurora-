package org.aurora.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.*
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import android.view.*
import kotlin.math.sin as ksin
import kotlin.math.PI as kPI

class OverlayService : Service() {

    companion object {
        const val ACTION_OVERLAY_TAPPED = "org.aurora.app.OVERLAY_TAPPED"
        private const val CHANNEL_ID = "aurora_overlay_channel"
        private const val NOTIF_ID   = 42
    }

    private lateinit var windowManager: WindowManager
    private lateinit var aurora: AuroraCurtain

    private val animHandler = Handler(Looper.getMainLooper())
    private val animRunnable = object : Runnable {
        override fun run() {
            aurora.tick()
            animHandler.postDelayed(this, 50L)
        }
    }

    private val stateHandler = Handler(Looper.getMainLooper())
    private val stateRunnable = object : Runnable {
        override fun run() {
            refreshAxisState()
            stateHandler.postDelayed(this, 2000L)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification())
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        addAurora()
        animHandler.post(animRunnable)
        stateHandler.postDelayed(stateRunnable, 4000L)
    }

    private fun refreshAxisState() {
        try {
            val py  = com.chaquo.python.Python.getInstance()
            val mod = py.getModule("aurora_bridge")
            val raw = mod.callAttr("get_axis_state")?.toString() ?: return
            val j   = org.json.JSONObject(raw)
            aurora.updateAxisState(
                x        = j.optDouble("X", 0.5).toFloat(),
                t        = j.optDouble("T", 0.5).toFloat(),
                n        = j.optDouble("N", 0.5).toFloat(),
                b        = j.optDouble("B", 0.5).toFloat(),
                a        = j.optDouble("A", 0.5).toFloat(),
                speaking = j.optBoolean("speaking", false),
            )
        } catch (_: Exception) {}
    }

    private fun addAurora() {
        aurora = AuroraCurtain(this)

        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

        val dp = resources.displayMetrics.density
        // Wide ribbon, short — spans most of the screen width like a real aurora band
        val w  = (WindowManager.LayoutParams.MATCH_PARENT)
        val h  = (88 * dp).toInt()

        val params = WindowManager.LayoutParams(
            w, h, layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                    or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply { gravity = Gravity.TOP or Gravity.START; x = 0; y = 180 }

        var iy = 0; var ty = 0f; var t0 = 0L
        val slop = 8f * dp

        aurora.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> { iy = params.y; ty = e.rawY; t0 = System.currentTimeMillis(); true }
                MotionEvent.ACTION_MOVE -> { params.y = iy + (e.rawY - ty).toInt(); try { windowManager.updateViewLayout(aurora, params) } catch (_: Exception) {}; true }
                MotionEvent.ACTION_UP   -> {
                    val moved = Math.abs(e.rawY - ty) > slop
                    if (!moved && System.currentTimeMillis() - t0 <= 300L) {
                        bringAppToForeground(); sendBroadcast(Intent(ACTION_OVERLAY_TAPPED))
                    }; true
                }
                else -> false
            }
        }

        try { windowManager.addView(aurora, params) } catch (e: Exception) { Log.e("Aurora", "curtain add failed: ${e.message}") }
    }

    private fun bringAppToForeground() {
        packageManager.getLaunchIntentForPackage(packageName)?.apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT
            startActivity(this)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        animHandler.removeCallbacks(animRunnable)
        stateHandler.removeCallbacks(stateRunnable)
        try { windowManager.removeView(aurora) } catch (_: Exception) {}
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, "Aurora Overlay", NotificationManager.IMPORTANCE_MIN).apply { setShowBadge(false) }
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(ch)
        }
    }

    private fun buildNotification(): Notification {
        val b = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) Notification.Builder(this, CHANNEL_ID)
                else @Suppress("DEPRECATION") Notification.Builder(this)
        return b.setContentTitle("Aurora").setContentText("Active")
            .setSmallIcon(android.R.drawable.ic_dialog_info).setOngoing(true).build()
    }
}


// =============================================================================
// AuroraCurtain
//
// Full-width aurora borealis ribbon drawn entirely in code.  64 vertical
// gradient columns each ride a three-harmonic wave; color drifts continuously
// through green→teal→cyan→blue→violet.  Energy (avg axis value) drives wave
// amplitude, brightness, and speed.  Speaking mode adds an extra phase pulse.
// Left/right edges fade to transparent so it blends seamlessly into any screen.
// =============================================================================

class AuroraCurtain(context: Context) : View(context) {

    private companion object {
        private val COLORS = intArrayOf(
            0xFF00FF7F.toInt(),  // spring green
            0xFF00FFCC.toInt(),  // green-teal
            0xFF00EEFF.toInt(),  // cyan
            0xFF44AAFF.toInt(),  // sky blue
            0xFF8855FF.toInt(),  // blue-violet
            0xFFCC55FF.toInt(),  // violet
            0xFF00FF7F.toInt(),  // loop back to green
        )
        private const val N_COLS = 80
    }

    private var phase    = 0f
    private val axes     = floatArrayOf(0.5f, 0.5f, 0.5f, 0.5f, 0.5f)
    private var speaking = false
    private val paint    = Paint(Paint.ANTI_ALIAS_FLAG)

    init { setLayerType(LAYER_TYPE_HARDWARE, null) }

    fun tick() {
        val energy = axes.average().toFloat().coerceIn(0f, 1f)
        phase = (phase + 0.006f + energy * 0.014f + if (speaking) 0.010f else 0f) % (2f * kPI.toFloat())
        invalidate()
    }

    fun updateAxisState(x: Float, t: Float, n: Float, b: Float, a: Float, speaking: Boolean) {
        axes[0] = x; axes[1] = t; axes[2] = n; axes[3] = b; axes[4] = a
        this.speaking = speaking
    }

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)
        val vw     = width.toFloat()
        val vh     = height.toFloat()
        val energy = axes.average().toFloat().coerceIn(0f, 1f)
        val colW   = vw / N_COLS + 1f

        for (col in 0 until N_COLS) {
            val t = col.toFloat() / N_COLS

            // Three harmonics → organic curtain flutter
            val waveAmp = vh * (0.10f + energy * 0.18f)
            val waveY   = vh * 0.50f +
                waveAmp *        ksin(t *  3.8f + phase                ).toFloat() +
                waveAmp * 0.45f * ksin(t *  7.5f + phase * 1.4f + 1.2f).toFloat() +
                waveAmp * 0.20f * ksin(t * 14.0f + phase * 2.1f        ).toFloat()

            // Color drifts rightward across the palette over time
            val palT   = ((t + phase * 0.04f) % 1f) * (COLORS.size - 1)
            val palIdx = palT.toInt().coerceIn(0, COLORS.size - 2)
            val color  = lerpColor(COLORS[palIdx], COLORS[palIdx + 1], palT - palIdx)

            // Per-column brightness shimmer
            val bright = (0.55f + 0.25f * energy +
                0.15f * ksin(t * 23f + phase * 3f).toFloat()).coerceIn(0.2f, 1f)

            // Left/right edge fade so the ribbon dissolves into the screen
            val edgeFade = ksin(t * kPI.toFloat()).toFloat().coerceIn(0f, 1f)

            val bandH = vh * (0.60f + energy * 0.20f)
            val top   = waveY - bandH * 0.30f
            val bot   = waveY + bandH * 0.70f

            // Vertical gradient: transparent top/bottom, bright center
            paint.shader = LinearGradient(
                0f, top, 0f, bot,
                intArrayOf(
                    Color.TRANSPARENT,
                    withAlpha(color, bright * edgeFade * 0.80f),
                    withAlpha(color, bright * edgeFade),
                    withAlpha(color, bright * edgeFade * 0.50f),
                    Color.TRANSPARENT
                ),
                floatArrayOf(0f, 0.20f, 0.50f, 0.78f, 1f),
                Shader.TileMode.CLAMP
            )
            canvas.drawRect(t * vw, top.coerceAtLeast(0f), t * vw + colW, bot.coerceAtMost(vh), paint)
        }
        paint.shader = null
    }

    private fun lerpColor(a: Int, b: Int, f: Float): Int {
        val inv = 1f - f
        return Color.rgb(
            (Color.red(a)   * inv + Color.red(b)   * f).toInt(),
            (Color.green(a) * inv + Color.green(b) * f).toInt(),
            (Color.blue(a)  * inv + Color.blue(b)  * f).toInt(),
        )
    }

    private fun withAlpha(color: Int, alpha: Float) = Color.argb(
        (alpha * 255f).toInt().coerceIn(0, 255),
        Color.red(color), Color.green(color), Color.blue(color)
    )
}
