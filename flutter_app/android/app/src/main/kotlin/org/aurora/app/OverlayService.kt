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

class OverlayService : Service() {

    companion object {
        const val ACTION_OVERLAY_TAPPED = "org.aurora.app.OVERLAY_TAPPED"
        private const val CHANNEL_ID = "aurora_overlay_channel"
        private const val NOTIF_ID   = 42
    }

    private lateinit var windowManager: WindowManager
    private lateinit var orbView: AuroraOrbView

    // Animation loop: 20 fps
    private val animHandler = Handler(Looper.getMainLooper())
    private val animRunnable = object : Runnable {
        override fun run() {
            orbView.tickAnimation()
            animHandler.postDelayed(this, 50L)
        }
    }

    // Axis state poll: every 2 s once the Python stack is up
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
        Log.i("Aurora", "OverlayService: onCreate")
        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification())
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        addOrb()
        animHandler.post(animRunnable)
        stateHandler.postDelayed(stateRunnable, 4000L) // let Python boot first
    }

    // ---------- axis state ---------------------------------------------------

    private fun refreshAxisState() {
        try {
            val py  = com.chaquo.python.Python.getInstance()
            val mod = py.getModule("aurora_bridge")
            val raw = mod.callAttr("get_axis_state")?.toString() ?: return
            val j   = org.json.JSONObject(raw)
            orbView.updateAxisState(
                x        = j.optDouble("X", 0.5).toFloat(),
                t        = j.optDouble("T", 0.5).toFloat(),
                n        = j.optDouble("N", 0.5).toFloat(),
                b        = j.optDouble("B", 0.5).toFloat(),
                a        = j.optDouble("A", 0.5).toFloat(),
                speaking = j.optBoolean("speaking", false),
            )
        } catch (_: Exception) { /* Python not ready yet — silent */ }
    }

    // ---------- orb layout ---------------------------------------------------

    private fun addOrb() {
        Log.i("Aurora", "OverlayService: adding aurora orb")
        orbView = AuroraOrbView(this)

        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

        val dp  = resources.displayMetrics.density
        val w   = (200 * dp).toInt()   // wide enough for aurora rings
        val h   = (130 * dp).toInt()

        val params = WindowManager.LayoutParams(
            w, h, layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                    or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 60; y = 200
        }

        var ix = 0; var iy = 0; var tx = 0f; var ty = 0f; var t0 = 0L
        val slop = 8f * dp

        orbView.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> {
                    ix = params.x; iy = params.y
                    tx = e.rawX;   ty = e.rawY
                    t0 = System.currentTimeMillis(); true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = ix + (e.rawX - tx).toInt()
                    params.y = iy + (e.rawY - ty).toInt()
                    try { windowManager.updateViewLayout(orbView, params) } catch (_: Exception) {}
                    true
                }
                MotionEvent.ACTION_UP -> {
                    val moved = Math.abs(e.rawX - tx) > slop || Math.abs(e.rawY - ty) > slop
                    val slow  = System.currentTimeMillis() - t0 > 300L
                    if (!moved && !slow) {
                        Log.i("Aurora", "OverlayService: orb tapped")
                        bringAppToForeground()
                        sendBroadcast(Intent(ACTION_OVERLAY_TAPPED))
                    }; true
                }
                else -> false
            }
        }

        try {
            windowManager.addView(orbView, params)
            Log.i("Aurora", "OverlayService: aurora orb added")
        } catch (e: Exception) {
            Log.e("Aurora", "OverlayService: failed to add orb: ${e.message}")
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
        try { windowManager.removeView(orbView) } catch (_: Exception) {}
    }

    // ---------- notification -------------------------------------------------

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, "Aurora Overlay", NotificationManager.IMPORTANCE_MIN)
                .apply { setShowBadge(false) }
            getSystemService(NotificationManager::class.java)?.createNotificationChannel(ch)
        }
    }

    private fun buildNotification(): Notification {
        val b = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            Notification.Builder(this, CHANNEL_ID)
        else @Suppress("DEPRECATION") Notification.Builder(this)
        return b.setContentTitle("Aurora").setContentText("Overlay active")
            .setSmallIcon(android.R.drawable.ic_dialog_info).setOngoing(true).build()
    }
}


// =============================================================================
// AuroraOrbView — multicolored aurora wave rings + central orb
// =============================================================================

class AuroraOrbView(context: Context) : View(context) {

    // Axis pressures [X, T, N, B, A] — updated from Python every 2 s
    private val axes     = floatArrayOf(0.5f, 0.5f, 0.5f, 0.5f, 0.5f)
    private var speaking = false

    // Each axis has a dominant hue.  Rings overlap so the aurora blends.
    //   X  Existence  → deep cyan     #00CFFF
    //   T  Temporal   → spring green  #00FF88
    //   N  Energy     → amber-orange  #FF8800
    //   B  Boundary   → violet        #CC44FF
    //   A  Agency     → warm gold     #FFD700
    private val axisColors = intArrayOf(
        0xFF00CFFF.toInt(),
        0xFF00FF88.toInt(),
        0xFFFF8800.toInt(),
        0xFFCC44FF.toInt(),
        0xFFFFD700.toInt(),
    )

    // Per-ring independent phase offsets so they undulate out of sync
    private val phaseOffset = floatArrayOf(0f, 1.26f, 2.51f, 3.77f, 5.03f)
    private var animPhase   = 0f    // master animation phase
    private var breathPhase = 0f    // slow global breathe

    private val paint    = Paint(Paint.ANTI_ALIAS_FLAG)
    private val ringRect = RectF()

    // ---- called every frame -------------------------------------------------

    fun tickAnimation() {
        val speed = if (speaking) 0.14f else 0.045f
        animPhase   = (animPhase   + speed) % (Math.PI.toFloat() * 2f)
        breathPhase = (breathPhase + 0.022f) % (Math.PI.toFloat() * 2f)
        invalidate()
    }

    // ---- called from OverlayService -----------------------------------------

    fun updateAxisState(x: Float, t: Float, n: Float, b: Float, a: Float, speaking: Boolean) {
        axes[0] = x; axes[1] = t; axes[2] = n; axes[3] = b; axes[4] = a
        this.speaking = speaking
        // invalidate() is handled by the animation tick — no need here
    }

    // ---- drawing ------------------------------------------------------------

    override fun onDraw(canvas: Canvas) {
        val cx    = width  / 2f
        val cy    = height / 2f
        val orbR  = minOf(width, height) * 0.21f
        val breathe = 1f + Math.sin(breathPhase.toDouble()).toFloat() * 0.05f

        // Draw rings from outermost inward so inner rings paint over outer
        for (i in 4 downTo 0) {
            val pressure = axes[i].coerceIn(0.05f, 1f)
            val phi      = animPhase + phaseOffset[i]

            // Ring geometry: ellipses wider than tall — the aurora band shape
            // Outer rings are larger; inner rings sit closer to the orb
            val ringSpread   = (i + 1) * 0.55f + pressure * 0.20f
            val ringW        = orbR * (2.2f + ringSpread)
            val ringH        = orbR * (0.55f + ringSpread * 0.28f)
            val pulseFactor  = 1f + Math.sin(phi.toDouble()).toFloat() *
                               (if (speaking) 0.20f else 0.08f) * pressure

            val rw = ringW * pulseFactor * breathe
            val rh = ringH * pulseFactor * breathe
            ringRect.set(cx - rw, cy - rh, cx + rw, cy + rh)

            // Filled aurora band — low alpha, soft glow
            val fillAlpha = ((25 + pressure * 55) * pulseFactor).toInt().coerceIn(0, 90)
            paint.style = Paint.Style.FILL
            paint.color = axisColors[i]
            paint.alpha = fillAlpha
            canvas.drawOval(ringRect, paint)

            // Glowing edge stroke
            val strokeAlpha = ((70 + pressure * 140) * pulseFactor).toInt().coerceIn(0, 220)
            paint.style      = Paint.Style.STROKE
            paint.strokeWidth = 2.5f + pressure * 4.5f
            paint.alpha      = strokeAlpha
            canvas.drawOval(ringRect, paint)
        }

        // ── Central orb ──────────────────────────────────────────────────────
        val r = orbR * breathe
        paint.style = Paint.Style.FILL
        paint.alpha = 255

        // Glow halo behind the orb — blends dominant axis color
        val dominantIdx = axes.indices.maxByOrNull { axes[it] } ?: 4
        val haloShader = RadialGradient(
            cx, cy, r * 2.4f,
            intArrayOf(
                (axisColors[dominantIdx] and 0x00FFFFFF) or 0x55000000,
                0x00000000,
            ),
            floatArrayOf(0.25f, 1f),
            Shader.TileMode.CLAMP,
        )
        paint.shader = haloShader
        canvas.drawCircle(cx, cy, r * 2.4f, paint)
        paint.shader = null

        // Core orb: radial gradient white-core → violet-white → deep purple
        val orbShader = RadialGradient(
            cx, cy, r,
            intArrayOf(
                0xFFFFFFFF.toInt(),
                0xFFECD5FF.toInt(),
                0xFFB060FF.toInt(),
                0xFF5010A0.toInt(),
            ),
            floatArrayOf(0f, 0.22f, 0.62f, 1f),
            Shader.TileMode.CLAMP,
        )
        paint.shader = orbShader
        canvas.drawCircle(cx, cy, r, paint)
        paint.shader = null
    }
}
