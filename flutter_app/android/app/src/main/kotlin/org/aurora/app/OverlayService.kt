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
// Renders the same two-layer photo-based orb as the Flutter main screen.
// aurora_bg.png is drawn statically; each strand PNG (cyan/blue/purple/pink/
// warm) is drawn with a scanline warp whose amplitude and speed come directly
// from Aurora's emotional axis values (N/T/B/A/X).  Axis=0 → strand barely
// moves; axis=1 → strand surges at full amplitude.
// =============================================================================

class AuroraOrbView(context: Context) : View(context) {

    private companion object {
        // Strand assets in same order as Flutter _strands list.
        val STRAND_ASSETS   = arrayOf("strand_cyan.png", "strand_blue.png",
                                       "strand_purple.png", "strand_pink.png",
                                       "strand_warm.png")
        // axes[] stores: 0=X  1=T  2=N  3=B  4=A
        // Each strand's axis index:  cyan→N(2)  blue→T(1)  purple→B(3)  pink→A(4)  warm→X(0)
        val STRAND_AXIS_IDX = intArrayOf(2, 1, 3, 4, 0)
        const val N_SLICES  = 80
    }

    // Axis state: indices 0=X  1=T  2=N  3=B  4=A
    private val axes     = floatArrayOf(0.5f, 0.5f, 0.5f, 0.5f, 0.5f)
    private var speaking = false

    private var bgBitmap: Bitmap? = null
    private val strandBitmaps: Array<Bitmap?> = arrayOfNulls(STRAND_ASSETS.size)

    // Per-strand travel phase 0..1
    private val travelPhase = FloatArray(STRAND_ASSETS.size) { it * 0.2f }

    private val paint    = Paint(Paint.ANTI_ALIAS_FLAG).apply { isFilterBitmap = true }
    private val colorMat = ColorMatrix()
    private val srcRect  = Rect()
    private val dstRectF = RectF()

    init {
        setLayerType(LAYER_TYPE_HARDWARE, null)
        Thread {
            bgBitmap = loadAsset("aurora_bg.png")
            for (i in STRAND_ASSETS.indices) strandBitmaps[i] = loadAsset(STRAND_ASSETS[i])
            postInvalidate()
        }.start()
    }

    private fun loadAsset(name: String): Bitmap? = try {
        val opts = BitmapFactory.Options().apply { inSampleSize = 2 }
        context.assets.open("flutter_assets/assets/$name").use {
            BitmapFactory.decodeStream(it, null, opts)
        }
    } catch (_: Exception) { null }

    fun tickAnimation() {
        for (i in travelPhase.indices) {
            val axisVal  = axes[STRAND_AXIS_IDX[i]].coerceIn(0f, 1f)
            val periodMs = (8000f - axisVal * 7300f).coerceIn(700f, 8000f)
            travelPhase[i] = (travelPhase[i] + 50f / periodMs) % 1f
        }
        invalidate()
    }

    fun updateAxisState(x: Float, t: Float, n: Float, b: Float, a: Float, speaking: Boolean) {
        axes[0] = x; axes[1] = t; axes[2] = n; axes[3] = b; axes[4] = a
        this.speaking = speaking
    }

    override fun onDraw(canvas: Canvas) {
        val vw = width.toFloat()
        val vh = height.toFloat()
        val bg = bgBitmap ?: return

        // ── Static background ─────────────────────────────────────────────────
        val bgBright = if (speaking) 0.78f else 0.20f
        drawBitmapFitH(canvas, bg, vw, vh, bgBright)

        // ── Each strand warped by its axis value ──────────────────────────────
        for (i in strandBitmaps.indices) {
            val bmp     = strandBitmaps[i] ?: continue
            val axisVal = axes[STRAND_AXIS_IDX[i]].coerceIn(0f, 1f)
            val tRad    = travelPhase[i] * kPI.toFloat() * 2f
            val amp     = axisVal * 0.85f
            val bright  = (axisVal * 0.85f + 0.10f).coerceIn(0f, 1f)
            drawStrandWarped(canvas, bmp, vw, vh, tRad, amp, bright)
        }

        // ── Center glow ───────────────────────────────────────────────────────
        val e = if (speaking) 1.00f else 0.18f
        drawCenterGlow(canvas, vw / 2f, vh / 2f, vh * 0.38f, e)
    }

    private fun drawBitmapFitH(canvas: Canvas, bmp: Bitmap,
                                vw: Float, vh: Float, bright: Float) {
        val scale = vh / bmp.height
        val bw    = bmp.width * scale
        val bx    = (vw - bw) / 2f
        setPaintBrightness(bright)
        srcRect.set(0, 0, bmp.width, bmp.height)
        dstRectF.set(bx, 0f, bx + bw, vh)
        canvas.drawBitmap(bmp, srcRect, dstRectF, paint)
    }

    private fun drawStrandWarped(canvas: Canvas, bmp: Bitmap,
                                  vw: Float, vh: Float,
                                  tRad: Float, amp: Float, bright: Float) {
        val scale = vh / bmp.height
        val bw    = bmp.width * scale
        val bx    = (vw - bw) / 2f
        setPaintBrightness(bright)

        val srcSliceW = bmp.width.toFloat() / N_SLICES
        val dstSliceW = bw / N_SLICES

        for (s in 0 until N_SLICES) {
            val t      = s.toFloat() / N_SLICES
            val d      = (t - 0.5f) * 2f
            val env    = d * d
            val inward = if (t < 0.5f) -tRad else tRad

            val dy = vh * amp * (
                env * ksin(t * kPI.toFloat() * 3.8f + tRad + inward) * 0.080f
              + env * ksin(t * kPI.toFloat() * 8.5f + tRad * 1.5f + inward * 1.1f) * 0.035f
              +       ksin(t * kPI.toFloat() * 14.0f + tRad * 2.2f) * 0.010f
            )

            srcRect.set(
                (t * bmp.width).toInt(), 0,
                ((t + 1f / N_SLICES) * bmp.width + 1).toInt().coerceAtMost(bmp.width),
                bmp.height
            )
            dstRectF.set(bx + t * bw, dy, bx + t * bw + dstSliceW, vh + dy)
            canvas.drawBitmap(bmp, srcRect, dstRectF, paint)
        }
    }

    private fun setPaintBrightness(b: Float) {
        colorMat.set(floatArrayOf(
            b, 0f, 0f, 0f, 0f,
            0f, b, 0f, 0f, 0f,
            0f, 0f, b, 0f, 0f,
            0f, 0f, 0f, 1f, 0f,
        ))
        paint.colorFilter = ColorMatrixColorFilter(colorMat)
    }

    private fun drawCenterGlow(canvas: Canvas, cx: Float, cy: Float,
                                r: Float, e: Float) {
        paint.colorFilter = null
        paint.style       = Paint.Style.FILL

        // Ambient bloom
        paint.shader = RadialGradient(
            cx, cy, r,
            intArrayOf(
                Color.argb((e * 66).toInt().coerceIn(0, 255),  255, 255, 255),
                Color.argb((e * 26).toInt().coerceIn(0, 255),  255, 136,   0),
                Color.TRANSPARENT,
            ),
            floatArrayOf(0f, 0.38f, 1f), Shader.TileMode.CLAMP
        )
        canvas.drawCircle(cx, cy, r, paint)

        // Tight hot core
        paint.shader = RadialGradient(
            cx, cy, r * 0.18f,
            intArrayOf(
                Color.argb((e * 230).toInt().coerceIn(0, 255), 255, 255, 255),
                Color.argb((e * 128).toInt().coerceIn(0, 255), 255, 255, 136),
                Color.TRANSPARENT,
            ),
            floatArrayOf(0f, 0.45f, 1f), Shader.TileMode.CLAMP
        )
        canvas.drawCircle(cx, cy, r * 0.18f, paint)
        paint.shader = null
    }
}
