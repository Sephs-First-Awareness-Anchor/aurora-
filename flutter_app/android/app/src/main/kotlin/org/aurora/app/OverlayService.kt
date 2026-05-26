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
// Displays aurora_orb.png with a scanline vertical-warp so the photo's own
// plasma strands appear to undulate.  Dark pixels (the photo's black background)
// are made transparent on load so the overlay floats without a black box.
// Warp amplitude and speed are driven by the average of Aurora's axis values.
// =============================================================================

class AuroraOrbView(context: Context) : View(context) {

    private companion object {
        const val N_SLICES = 80
    }

    private var orbBitmap: Bitmap? = null
    private var travelPhase = 0f
    private val axes     = floatArrayOf(0.5f, 0.5f, 0.5f, 0.5f, 0.5f) // X T N B A
    private var speaking = false

    private val paint    = Paint(Paint.ANTI_ALIAS_FLAG).apply { isFilterBitmap = true }
    private val srcRect  = Rect()
    private val dstRectF = RectF()

    init {
        setLayerType(LAYER_TYPE_HARDWARE, null)
        Thread {
            orbBitmap = loadAsset("aurora_orb.png")
            postInvalidate()
        }.start()
    }

    private fun loadAsset(name: String): Bitmap? {
        return try {
            val opts = BitmapFactory.Options().apply { inSampleSize = 2 }
            val src = context.assets.open("flutter_assets/assets/$name").use {
                BitmapFactory.decodeStream(it, null, opts)
            } ?: return null
            // Make dark/black background pixels transparent — no black box on the overlay
            val mutable = src.copy(Bitmap.Config.ARGB_8888, true)
            src.recycle()
            if (mutable == null) return null
            val pixels = IntArray(mutable.width * mutable.height)
            mutable.getPixels(pixels, 0, mutable.width, 0, 0, mutable.width, mutable.height)
            for (i in pixels.indices) {
                val r = Color.red(pixels[i])
                val g = Color.green(pixels[i])
                val b = Color.blue(pixels[i])
                if ((r * 299 + g * 587 + b * 114) / 1000 < 30) pixels[i] = Color.TRANSPARENT
            }
            mutable.setPixels(pixels, 0, mutable.width, 0, 0, mutable.width, mutable.height)
            mutable
        } catch (_: Exception) { null }
    }

    fun tickAnimation() {
        val energy   = axes.average().toFloat().coerceIn(0f, 1f)
        val periodMs = (8000f - energy * 7300f).coerceIn(700f, 8000f)
        travelPhase  = (travelPhase + 50f / periodMs) % 1f
        invalidate()
    }

    fun updateAxisState(x: Float, t: Float, n: Float, b: Float, a: Float, speaking: Boolean) {
        axes[0] = x; axes[1] = t; axes[2] = n; axes[3] = b; axes[4] = a
        this.speaking = speaking
    }

    override fun onDraw(canvas: Canvas) {
        val bmp = orbBitmap ?: return
        val vw  = width.toFloat()
        val vh  = height.toFloat()

        // Clear to transparent so black-removed areas show the screen behind
        canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR)

        val scale     = vh / bmp.height
        val bw        = bmp.width * scale
        val ox        = (vw - bw) / 2f
        val energy    = axes.average().toFloat().coerceIn(0f, 1f)
        val amp       = energy * 0.10f + if (speaking) energy * 0.08f else 0f
        val tRad      = travelPhase * kPI.toFloat() * 2f
        val dstSliceW = bw / N_SLICES

        for (s in 0 until N_SLICES) {
            val t      = s.toFloat() / N_SLICES
            // env peaks at edges where strands radiate; zero at the stable core
            val d      = Math.abs(t - 0.5f) * 2f
            val env    = d * d
            val inward = if (t < 0.5f) -tRad else tRad

            val dy = vh * amp * (
                env * ksin(t * kPI.toFloat() * 3.8f  + tRad        + inward       ) * 0.080f
              + env * ksin(t * kPI.toFloat() * 8.5f  + tRad * 1.5f + inward * 1.1f) * 0.035f
              +       ksin(t * kPI.toFloat() * 14.0f + tRad * 2.2f                 ) * 0.010f
            )

            srcRect.set(
                (t * bmp.width).toInt(), 0,
                ((t + 1f / N_SLICES) * bmp.width + 1).toInt().coerceAtMost(bmp.width),
                bmp.height
            )
            dstRectF.set(ox + t * bw, dy, ox + t * bw + dstSliceW, vh + dy)
            canvas.drawBitmap(bmp, srcRect, dstRectF, paint)
        }
    }
}
