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
        val sz = (200 * dp).toInt()   // square — gives planetary waveform rings room

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
// AuroraOrbView — planetary waveform rings + central orb
//
// Five colored sound-wave rings wrap around the central sphere.
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

    // Stacked horizontal bands. The orb sits inside this field like a planet
    // inside electrified rings.
    private val bandOffset = floatArrayOf(-0.66f, -0.34f, 0f, 0.34f, 0.66f)

    // Per-ring independent phase offsets so they ripple out of sync.
    private val phaseOffset = floatArrayOf(0f, 1.26f, 2.51f, 3.77f, 5.03f)

    private var animPhase   = 0f
    private var breathPhase = 0f

    private val paint    = Paint(Paint.ANTI_ALIAS_FLAG)
    private val wavePath = Path()

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

        // Back half of the electric sound bands.
        drawElectricBands(canvas, cx, cy, orbR, breathe, dominantIdx, false)

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

        val orbShader = RadialGradient(
            cx, cy, r,
            intArrayOf(
                0xFFDCC8FF.toInt(),
                0xFF7B38D8.toInt(),
                0xFF37115F.toInt(),
                0xFF08000F.toInt(),
            ),
            floatArrayOf(0f, 0.20f, 0.62f, 1f),
            Shader.TileMode.CLAMP,
        )
        paint.shader = orbShader
        canvas.drawCircle(cx, cy, r, paint)
        paint.shader = null

        // Front half of the bands, thinner and partially transparent.
        drawElectricBands(canvas, cx, cy, orbR, breathe, dominantIdx, true)
    }

    private fun drawElectricBands(
        canvas: Canvas,
        cx: Float,
        cy: Float,
        orbR: Float,
        breathe: Float,
        dominantIdx: Int,
        frontPass: Boolean
    ) {
        for (i in 0..4) {
            val pressure = axes[i].coerceIn(0.05f, 1f)
            val phi      = animPhase + phaseOffset[i]
            val sinPhi   = Math.sin(phi.toDouble()).toFloat()

            // Active = dominant axis while speaking.
            // High   = elevated pressure (>0.58) but not dominant.
            // Idle   = low ripple, charged but subdued.
            val isActive = speaking && i == dominantIdx
            val isHigh   = speaking && pressure > 0.58f && !isActive

            val chargeFactor = 1f + sinPhi * if (isActive) 0.24f else if (isHigh) 0.14f else 0.06f
            val ampScale = if (isActive) 0.24f else if (isHigh) 0.15f else if (speaking) 0.065f else 0.025f
            val amplitude = orbR * ampScale * (0.82f + pressure * 0.36f) * breathe

            wavePath.reset()
            val steps = 132
            val major = orbR * 1.82f * breathe
            val yBase = cy + orbR * bandOffset[i]
            val start = if (frontPass) -0.58f else -1.0f
            val end = if (frontPass) 0.58f else 1.0f
            for (s in 0..steps) {
                val u = start + (end - start) * s / steps.toFloat()
                val x = cx + u * major
                val ringCurve = Math.sin((u * Math.PI).toDouble()).toFloat() * orbR * 0.12f
                val envelope = 0.34f + 0.66f * Math.sqrt((1f - u * u).coerceIn(0f, 1f).toDouble()).toFloat()
                val carrier = Math.sin(((u + 1f) * Math.PI * 7.0 + phi).toDouble()).toFloat()
                val jitter = Math.sin(((u + 1f) * Math.PI * 19.0 + phi * 1.7f).toDouble()).toFloat() * amplitude * 0.22f
                val y = yBase + ringCurve + carrier * amplitude * envelope + jitter
                if (s == 0) wavePath.moveTo(x, y) else wavePath.lineTo(x, y)
            }

            val baseAlpha = when {
                isActive -> (205 + pressure * 70).toInt()
                isHigh   -> (130 + pressure * 70).toInt()
                else     -> (44  + pressure * 54).toInt()
            }
            val strokeAlpha = (baseAlpha * chargeFactor).toInt().coerceIn(0, 255)
            val strokeW     = (when {
                isActive -> 3.8f + pressure * 2.8f
                isHigh   -> 2.0f + pressure * 1.4f
                else     -> 0.9f + pressure * 0.8f
            }) * chargeFactor * (if (frontPass) 0.76f else 1.0f)

            paint.style       = Paint.Style.STROKE
            paint.color       = Color.BLACK
            paint.alpha       = if (frontPass) 148 else 210
            paint.strokeWidth = strokeW + (if (isActive) 4.4f else 3.2f)
            paint.strokeCap   = Paint.Cap.ROUND
            paint.strokeJoin  = Paint.Join.ROUND
            canvas.drawPath(wavePath, paint)

            // Glow pass — broader stroke at low alpha for the charged halo effect
            paint.style       = Paint.Style.STROKE
            paint.color       = axisColors[i]
            paint.alpha       = (strokeAlpha * 0.42f).toInt().coerceIn(0, 120)
            paint.strokeWidth = strokeW * (if (frontPass) 3.0f else 5.4f)
            paint.strokeCap   = Paint.Cap.ROUND
            paint.strokeJoin  = Paint.Join.ROUND
            canvas.drawPath(wavePath, paint)

            // Main waveform stroke
            paint.alpha       = strokeAlpha
            paint.strokeWidth = strokeW
            canvas.drawPath(wavePath, paint)
        }
    }
}
