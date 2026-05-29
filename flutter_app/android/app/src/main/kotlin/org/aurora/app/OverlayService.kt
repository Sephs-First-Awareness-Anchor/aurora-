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
import kotlin.math.sin  as ksin
import kotlin.math.PI   as kPI
import kotlin.math.min  as kMin
import kotlin.math.hypot

class OverlayService : Service() {

    companion object {
        const val ACTION_OVERLAY_TAPPED = "org.aurora.app.OVERLAY_TAPPED"
        private const val CHANNEL_ID = "aurora_overlay_channel"
        private const val NOTIF_ID   = 42
    }

    private lateinit var windowManager: WindowManager
    private lateinit var aurora: AuroraOrbView

    private val animHandler  = Handler(Looper.getMainLooper())
    private val animRunnable = object : Runnable {
        override fun run() { aurora.tick(); animHandler.postDelayed(this, 50L) }
    }

    private val stateHandler  = Handler(Looper.getMainLooper())
    private val stateRunnable = object : Runnable {
        override fun run() { refreshAxisState(); stateHandler.postDelayed(this, 2000L) }
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
        aurora = AuroraOrbView(this)

        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

        val dp     = resources.displayMetrics.density
        // 100dp square — sphere fills ~64% of the view, outer glow uses the rest
        val orbPx  = (100 * dp).toInt()

        val params = WindowManager.LayoutParams(
            orbPx, orbPx, layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                    or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            // Bottom-right corner; BOTTOM|END gravity so x/y are margins from the edge
            gravity = Gravity.BOTTOM or Gravity.END
            x = (16 * dp).toInt()
            y = (80 * dp).toInt()
        }

        var ix = 0; var iy = 0; var tx = 0f; var ty = 0f; var t0 = 0L
        val slop = 8f * dp

        aurora.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> {
                    ix = params.x; iy = params.y
                    tx = e.rawX; ty = e.rawY
                    t0 = System.currentTimeMillis()
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    // With BOTTOM|END gravity: x increases leftward, y increases upward
                    params.x = ix + (tx - e.rawX).toInt()
                    params.y = iy + (ty - e.rawY).toInt()
                    try { windowManager.updateViewLayout(aurora, params) } catch (_: Exception) {}
                    true
                }
                MotionEvent.ACTION_UP -> {
                    val moved = hypot((e.rawX - tx).toDouble(), (e.rawY - ty).toDouble()) > slop
                    if (!moved && System.currentTimeMillis() - t0 <= 300L) {
                        bringAppToForeground()
                        sendBroadcast(Intent(ACTION_OVERLAY_TAPPED))
                    }
                    true
                }
                else -> false
            }
        }

        try {
            windowManager.addView(aurora, params)
        } catch (e: Exception) {
            Log.e("Aurora", "orb add failed: ${e.message}")
        }
    }

    private fun bringAppToForeground() {
        packageManager.getLaunchIntentForPackage(packageName)?.apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP or
                    Intent.FLAG_ACTIVITY_REORDER_TO_FRONT
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
            val ch = NotificationChannel(
                CHANNEL_ID, "Aurora Overlay",
                NotificationManager.IMPORTANCE_MIN
            ).apply { setShowBadge(false) }
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(ch)
        }
    }

    private fun buildNotification(): Notification {
        val b = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                    Notification.Builder(this, CHANNEL_ID)
                else @Suppress("DEPRECATION") Notification.Builder(this)
        return b.setContentTitle("Aurora")
            .setContentText("Active")
            .setSmallIcon(R.drawable.ic_aurora_notify)
            .setOngoing(true)
            .build()
    }
}


// =============================================================================
// AuroraOrbView — compact floating sphere (100 dp × 100 dp)
//
// The same aurora-borealis curtain rendered inside a circular clip.
// A radial vignette gives sphere depth; a specular highlight adds the 3-D look.
// An outer purple glow ring bleeds beyond the clip and pulses with axis energy
// and speaking state — same behaviour as the full-size in-app orb.
// =============================================================================

class AuroraOrbView(context: Context) : View(context) {

    private companion object {
        private val COLORS = intArrayOf(
            0xFF00FF7F.toInt(),   // spring green
            0xFF00FFCC.toInt(),   // green-teal
            0xFF00EEFF.toInt(),   // cyan
            0xFF44AAFF.toInt(),   // sky blue
            0xFF8855FF.toInt(),   // blue-violet
            0xFFCC55FF.toInt(),   // violet
            0xFF00FF7F.toInt(),   // wrap back to green
        )
        private const val N_COLS = 60
    }

    private var phase    = 0f
    private val axes     = floatArrayOf(0.5f, 0.5f, 0.5f, 0.5f, 0.5f)
    private var speaking = false
    private val paint    = Paint(Paint.ANTI_ALIAS_FLAG)
    private val clipPath = Path()
    private var cx = 0f
    private var cy = 0f
    private var radius = 0f   // sphere clip radius

    init { setLayerType(LAYER_TYPE_HARDWARE, null) }

    override fun onSizeChanged(w: Int, h: Int, oldW: Int, oldH: Int) {
        cx = w / 2f
        cy = h / 2f
        // Sphere uses 64% of the view — leaves 36% for outer glow ring
        radius = kMin(w, h) / 2f * 0.64f
        clipPath.reset()
        clipPath.addCircle(cx, cy, radius, Path.Direction.CW)
    }

    fun tick() {
        val energy = axes.average().toFloat().coerceIn(0f, 1f)
        phase = (phase + 0.006f + energy * 0.014f +
                if (speaking) 0.010f else 0f) % (2f * kPI.toFloat())
        invalidate()
    }

    fun updateAxisState(x: Float, t: Float, n: Float, b: Float, a: Float, speaking: Boolean) {
        axes[0] = x; axes[1] = t; axes[2] = n; axes[3] = b; axes[4] = a
        this.speaking = speaking
    }

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)

        val energy     = axes.average().toFloat().coerceIn(0f, 1f)
        val speakBoost = if (speaking) 0.22f else 0f
        val vw = width.toFloat()
        val vh = height.toFloat()

        // ── Outer glow ring — drawn BEFORE clip so it bleeds beyond sphere edge ─
        val glowA = (0.22f + energy * 0.30f + speakBoost * 0.18f).coerceIn(0f, 1f)
        paint.style = Paint.Style.FILL
        paint.shader = RadialGradient(
            cx, cy, cx,
            intArrayOf(
                Color.argb((glowA * 170).toInt().coerceIn(0, 255), 160, 80, 255),
                Color.argb((glowA *  55).toInt().coerceIn(0, 255), 100, 40, 200),
                Color.TRANSPARENT,
            ),
            floatArrayOf(radius / cx, 0.84f, 1.0f),
            Shader.TileMode.CLAMP
        )
        canvas.drawCircle(cx, cy, cx, paint)
        paint.shader = null

        // ── Aurora curtain clipped to sphere ─────────────────────────────────
        canvas.save()
        canvas.clipPath(clipPath)

        // Deep-space backdrop inside the sphere
        paint.color = Color.argb(238, 4, 4, 16)
        canvas.drawPaint(paint)

        val colW = vw / N_COLS + 1f
        for (col in 0 until N_COLS) {
            val t       = col.toFloat() / N_COLS
            val waveAmp = vh * (0.09f + energy * 0.17f + speakBoost * 0.07f)
            val waveY   = vh * 0.50f +
                waveAmp *        ksin(t *  3.8f + phase                ).toFloat() +
                waveAmp * 0.45f * ksin(t *  7.5f + phase * 1.4f + 1.2f).toFloat() +
                waveAmp * 0.20f * ksin(t * 14.0f + phase * 2.1f        ).toFloat()

            val palT   = ((t + phase * 0.04f) % 1f) * (COLORS.size - 1)
            val palIdx = palT.toInt().coerceIn(0, COLORS.size - 2)
            val color  = lerpColor(COLORS[palIdx], COLORS[palIdx + 1], palT - palIdx)
            val bright = (0.55f + 0.25f * energy +
                    0.15f * ksin(t * 23f + phase * 3f).toFloat() +
                    speakBoost * 0.5f).coerceIn(0.2f, 1f)
            val bandH  = vh * (0.55f + energy * 0.22f)
            val top    = waveY - bandH * 0.30f
            val bot    = waveY + bandH * 0.70f

            paint.shader = LinearGradient(
                0f, top, 0f, bot,
                intArrayOf(
                    Color.TRANSPARENT,
                    withAlpha(color, bright * 0.80f),
                    withAlpha(color, bright),
                    withAlpha(color, bright * 0.50f),
                    Color.TRANSPARENT,
                ),
                floatArrayOf(0f, 0.20f, 0.50f, 0.78f, 1f),
                Shader.TileMode.CLAMP
            )
            canvas.drawRect(t * vw, top.coerceAtLeast(0f), t * vw + colW, bot.coerceAtMost(vh), paint)
        }
        paint.shader = null

        // Depth vignette — darker limb makes the sphere feel 3-D
        paint.shader = RadialGradient(
            cx, cy, radius,
            intArrayOf(Color.TRANSPARENT, Color.argb(175, 0, 0, 14)),
            floatArrayOf(0.58f, 1.0f),
            Shader.TileMode.CLAMP
        )
        canvas.drawCircle(cx, cy, radius, paint)
        paint.shader = null
        canvas.restore()

        // Specular highlight — top-left bright oval for the 3-D sphere feel
        val specA = ((0.38f + energy * 0.22f + speakBoost * 0.15f) * 255).toInt().coerceIn(0, 255)
        val hx    = cx - radius * 0.28f
        val hy    = cy - radius * 0.30f
        val hr    = radius * 0.27f
        paint.shader = RadialGradient(
            hx, hy, hr,
            intArrayOf(Color.argb(specA, 240, 220, 255), Color.TRANSPARENT),
            floatArrayOf(0f, 1f),
            Shader.TileMode.CLAMP
        )
        canvas.drawCircle(hx, hy, hr, paint)
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
