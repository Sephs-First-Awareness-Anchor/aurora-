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

        val dp = resources.displayMetrics.density
        val sz = (200 * dp).toInt()   // square — gives orbital rings full room

        val params = WindowManager.LayoutParams(
            sz, sz, layoutFlag,
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
// AuroraOrbView — planetary orbital rings + central orb
//
// Five thin flat ellipses, each rotated to a different orbital inclination,
// wrap around the central sphere like multi-plane planetary rings.
//
// Idle:    all rings at a low charged ripple — slight alpha pulse via sin wave.
// Speaking: only rings whose axis pressure is above the active threshold light
//           up; the rest stay at low ripple.  This means only the colors
//           matching Aurora's current cognitive state are prominent.
// =============================================================================

class AuroraOrbView(context: Context) : View(context) {

    // Axis pressures [X, T, N, B, A] — polled from Python every 2 s
    private val axes     = floatArrayOf(0.5f, 0.5f, 0.5f, 0.5f, 0.5f)
    private var speaking = false

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

    // Orbital inclination angles — each ring wraps at a different plane angle.
    // Spread to suggest distinct orbital trajectories around the sphere.
    private val orbitAngle = floatArrayOf(15f, 48f, 80f, -22f, -55f)

    // Slight radius variation so adjacent rings don't sit exactly on top of each other.
    private val orbitRadiusMul = floatArrayOf(1.30f, 1.42f, 1.36f, 1.24f, 1.48f)

    // Per-ring independent phase offsets so they ripple out of sync.
    private val phaseOffset = floatArrayOf(0f, 1.26f, 2.51f, 3.77f, 5.03f)

    private var animPhase   = 0f
    private var breathPhase = 0f

    private val paint    = Paint(Paint.ANTI_ALIAS_FLAG)
    private val ringRect = RectF()

    // ---- called every 50 ms (20 fps) ----------------------------------------

    fun tickAnimation() {
        val speed = if (speaking) 0.11f else 0.036f
        animPhase   = (animPhase   + speed)  % (Math.PI.toFloat() * 2f)
        breathPhase = (breathPhase + 0.018f) % (Math.PI.toFloat() * 2f)
        invalidate()
    }

    // ---- called from OverlayService on each axis poll -----------------------

    fun updateAxisState(x: Float, t: Float, n: Float, b: Float, a: Float, speaking: Boolean) {
        axes[0] = x; axes[1] = t; axes[2] = n; axes[3] = b; axes[4] = a
        this.speaking = speaking
    }

    // ---- drawing ------------------------------------------------------------

    override fun onDraw(canvas: Canvas) {
        val cx      = width  / 2f
        val cy      = height / 2f
        val orbR    = minOf(width, height) * 0.22f
        val breathe = 1f + Math.sin(breathPhase.toDouble()).toFloat() * 0.03f

        val dominantIdx = axes.indices.maxByOrNull { axes[it] } ?: 4

        // ── Planetary rings ───────────────────────────────────────────────────
        // Draw all rings. Each is a thin flat ellipse rotated to its orbital angle.
        // Two stroke passes per ring: sharp main edge + wide low-alpha glow.
        for (i in 0..4) {
            val pressure = axes[i].coerceIn(0.05f, 1f)
            val phi      = animPhase + phaseOffset[i]
            val sinPhi   = Math.sin(phi.toDouble()).toFloat()

            // Active = dominant axis while speaking.
            // High   = elevated pressure (>0.58) but not dominant.
            // Idle   = low ripple, charged but subdued.
            val isActive = speaking && i == dominantIdx
            val isHigh   = speaking && pressure > 0.58f && !isActive

            // Ripple amplitude scales with state — idle still feels charged.
            val rippleAmt    = if (isActive) 0.30f else if (isHigh) 0.16f else 0.09f
            val chargeFactor = 1f + sinPhi * rippleAmt

            // Ring geometry: very flat ellipse — orbR × 0.07 minor axis ratio.
            val rMajor = orbR * orbitRadiusMul[i] * breathe
            val rMinor = rMajor * 0.07f

            canvas.save()
            canvas.rotate(orbitAngle[i], cx, cy)
            ringRect.set(cx - rMajor, cy - rMinor, cx + rMajor, cy + rMinor)

            // Main ring stroke
            val baseAlpha = when {
                isActive -> (185 + pressure * 65).toInt()
                isHigh   -> (110 + pressure * 55).toInt()
                else     -> (28  + pressure * 36).toInt()
            }
            val strokeAlpha = (baseAlpha * chargeFactor).toInt().coerceIn(0, 255)
            val strokeW     = (when {
                isActive -> 3.8f + pressure * 2.8f
                isHigh   -> 2.0f + pressure * 1.4f
                else     -> 0.9f + pressure * 0.8f
            }) * chargeFactor

            paint.style       = Paint.Style.STROKE
            paint.color       = axisColors[i]
            paint.alpha       = strokeAlpha
            paint.strokeWidth = strokeW
            canvas.drawOval(ringRect, paint)

            // Glow pass — broader stroke at ~30% alpha for the charged halo effect
            paint.alpha       = (strokeAlpha * 0.30f).toInt().coerceIn(0, 95)
            paint.strokeWidth = strokeW * 3.5f
            canvas.drawOval(ringRect, paint)

            canvas.restore()
        }

        // ── Central orb ──────────────────────────────────────────────────────
        val r = orbR * breathe
        paint.style = Paint.Style.FILL
        paint.alpha = 255

        // Soft halo — dominant axis color bleeds out behind the orb
        val haloShader = RadialGradient(
            cx, cy, r * 2.2f,
            intArrayOf(
                (axisColors[dominantIdx] and 0x00FFFFFF) or 0x50000000,
                0x00000000,
            ),
            floatArrayOf(0.28f, 1f),
            Shader.TileMode.CLAMP,
        )
        paint.shader = haloShader
        canvas.drawCircle(cx, cy, r * 2.2f, paint)
        paint.shader = null

        // Core orb: white-core → lavender → violet → deep purple
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
