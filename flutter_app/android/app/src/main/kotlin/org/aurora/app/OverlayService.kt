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
    private lateinit var orbView: AuroraOrbView

    private val animHandler = Handler(Looper.getMainLooper())
    private val animRunnable = object : Runnable {
        override fun run() {
            orbView.tickAnimation()
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
        addOrb()
        animHandler.post(animRunnable)
        stateHandler.postDelayed(stateRunnable, 4000L)
    }

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
        } catch (_: Exception) {}
    }

    private fun addOrb() {
        orbView = AuroraOrbView(this)

        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

        val dp = resources.displayMetrics.density
        val w  = (220 * dp).toInt()
        val h  = (120 * dp).toInt()

        val params = WindowManager.LayoutParams(
            w, h, layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                    or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply { gravity = Gravity.TOP or Gravity.START; x = 60; y = 200 }

        var ix = 0; var iy = 0; var tx = 0f; var ty = 0f; var t0 = 0L
        val slop = 8f * dp

        orbView.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> { ix = params.x; iy = params.y; tx = e.rawX; ty = e.rawY; t0 = System.currentTimeMillis(); true }
                MotionEvent.ACTION_MOVE -> { params.x = ix + (e.rawX - tx).toInt(); params.y = iy + (e.rawY - ty).toInt(); try { windowManager.updateViewLayout(orbView, params) } catch (_: Exception) {}; true }
                MotionEvent.ACTION_UP   -> {
                    val moved = Math.abs(e.rawX - tx) > slop || Math.abs(e.rawY - ty) > slop
                    if (!moved && System.currentTimeMillis() - t0 <= 300L) {
                        bringAppToForeground(); sendBroadcast(Intent(ACTION_OVERLAY_TAPPED))
                    }; true
                }
                else -> false
            }
        }

        try { windowManager.addView(orbView, params) } catch (e: Exception) { Log.e("Aurora", "orb add failed: ${e.message}") }
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
        try { windowManager.removeView(orbView) } catch (_: Exception) {}
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
// AuroraOrbView
//
// Five horizontal sine-wave bands flow left-to-right across the view.
// The orb sphere is painted on top, sitting inside the band stack.
// Idle: bands hold a faint shimmer.  Speaking: the high-pressure axis bands
// rise in amplitude; others stay subtle.  All axis colors are always present.
// =============================================================================

class AuroraOrbView(context: Context) : View(context) {

    private val axes     = floatArrayOf(0.5f, 0.5f, 0.5f, 0.5f, 0.5f)
    private var speaking = false

    //   X cyan  T hot-magenta  N plasma-orange  B violet  A spring-green
    private val axisColors = intArrayOf(
        0xFF00DDFF.toInt(), 0xFFFF1199.toInt(), 0xFFFF6600.toInt(),
        0xFFBB22FF.toInt(), 0xFF00FF88.toInt(),
    )

    private val phaseOffset = floatArrayOf(0f, 1.26f, 2.51f, 3.77f, 5.03f)
    private var animPhase   = 0f
    private var breathPhase = 0f

    private val paint    = Paint(Paint.ANTI_ALIAS_FLAG)
    private val wavePath = Path()

    fun tickAnimation() {
        val speed = if (speaking) 0.10f else 0.030f
        animPhase   = (animPhase   + speed)  % (kPI.toFloat() * 2f)
        breathPhase = (breathPhase + 0.016f) % (kPI.toFloat() * 2f)
        invalidate()
    }

    fun updateAxisState(x: Float, t: Float, n: Float, b: Float, a: Float, speaking: Boolean) {
        axes[0] = x; axes[1] = t; axes[2] = n; axes[3] = b; axes[4] = a
        this.speaking = speaking
    }

    override fun onDraw(canvas: Canvas) {
        val w  = width.toFloat()
        val cx = w / 2f
        val cy = height / 2f
        // Orb radius scales to view height so the sphere fills the vertical space cleanly.
        val orbR   = height * 0.35f
        val breathe = 1f + ksin(breathPhase) * 0.025f

        // ── Plasma bands: converge into orb center, fan out at edges ─────────
        // At x=cx every band's y-offset → 0; at the edges they fan to ±spread.
        val spread  = if (speaking) orbR * 1.6f else orbR * 0.7f
        val steps   = 100
        for (i in 0..4) {
            val pressure = axes[i].coerceIn(0.05f, 1f)
            val phi      = animPhase + phaseOffset[i]
            val sinPhi   = ksin(phi)
            val bandFrac = (i / 4f) * 2f - 1f   // −1 to +1

            val baseAmp = if (speaking)
                orbR * (0.12f + pressure * 0.14f)
            else
                orbR * (0.015f + pressure * 0.015f)

            val baseAlpha = if (speaking)
                (150 + pressure * 95).toInt().coerceIn(0, 245)
            else
                (20 + pressure * 30).toInt().coerceIn(0, 70)
            val alpha   = (baseAlpha * (0.80f + 0.20f * (sinPhi + 1f) / 2f)).toInt().coerceIn(0, 255)
            val strokeW = if (speaking) 1.8f + pressure * 1.2f else 1.0f

            wavePath.reset()
            for (s in 0..steps) {
                val t  = s.toFloat() / steps
                val x  = t * w
                // Convergence: 0 at center, 1 at edges (quadratic)
                val d        = (t - 0.5f) * 2f               // −1..+1
                val envelope = d * d                          // 0 at center, 1 at edge
                val bandY    = cy + bandFrac * spread * envelope
                val amp      = baseAmp * (0.25f + 0.75f * kotlin.math.abs(d)) *
                               (0.80f + 0.20f * (sinPhi + 1f) / 2f) * breathe
                val y        = bandY + amp * ksin(t * kPI.toFloat() * 3.5f + phi)
                if (s == 0) wavePath.moveTo(x, y) else wavePath.lineTo(x, y)
            }

            // Outer glow
            paint.style       = Paint.Style.STROKE
            paint.color       = axisColors[i]
            paint.alpha       = (alpha * 0.14f).toInt().coerceIn(0, 60)
            paint.strokeWidth = strokeW * 7f
            canvas.drawPath(wavePath, paint)
            // Mid glow
            paint.alpha       = (alpha * 0.32f).toInt().coerceIn(0, 120)
            paint.strokeWidth = strokeW * 2.8f
            canvas.drawPath(wavePath, paint)
            // Core line
            paint.alpha       = alpha
            paint.strokeWidth = strokeW
            canvas.drawPath(wavePath, paint)
        }

        // ── Orb sphere (on top) ───────────────────────────────────────────────
        val r = orbR * breathe
        paint.style = Paint.Style.FILL
        paint.alpha = 255

        // Corona bloom
        val domIdx      = axes.indices.maxByOrNull { axes[it] } ?: 2
        val bloomShader = RadialGradient(
            cx, cy, r * 2.2f,
            intArrayOf((axisColors[domIdx] and 0x00FFFFFF) or 0x55000000, 0x00000000),
            floatArrayOf(0.25f, 1f), Shader.TileMode.CLAMP,
        )
        paint.shader = bloomShader
        canvas.drawCircle(cx, cy, r * 2.2f, paint)
        paint.shader = null

        // Explosive core gradient: white → orange → deep-purple
        val orbShader = RadialGradient(
            cx, cy, r,
            intArrayOf(0xFFFFFFFF.toInt(), 0xFFFF8800.toInt(), 0xFF5500CC.toInt(), 0xFF110022.toInt()),
            floatArrayOf(0f, 0.30f, 0.68f, 1f), Shader.TileMode.CLAMP,
        )
        paint.shader = orbShader
        canvas.drawCircle(cx, cy, r, paint)
        paint.shader = null

        // Center flash point
        val flashR = r * (0.20f + 0.10f * (ksin(breathPhase) + 1f) / 2f)
        paint.color = 0xFFFFFFFF.toInt()
        paint.alpha = if (speaking) 220 else 100
        canvas.drawCircle(cx, cy, flashR, paint)
    }
}
