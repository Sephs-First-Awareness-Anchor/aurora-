package org.aurora.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.view.*

class OverlayService : Service() {

    companion object {
        const val ACTION_OVERLAY_TAPPED = "org.aurora.app.OVERLAY_TAPPED"
        private const val CHANNEL_ID = "aurora_overlay_channel"
        private const val NOTIF_ID   = 42
    }

    private lateinit var windowManager: WindowManager
    private lateinit var orbView: View

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Log.i("Aurora", "OverlayService: onCreate")
        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification())
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        addOrb()
    }

    private fun addOrb() {
        Log.i("Aurora", "OverlayService: adding orb")
        orbView = View(this).apply {
            // Circular orb: radial gradient from bright violet-white core to deep purple edge
            val orb = GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                intArrayOf(0xFFE8D5FF.toInt(), 0xFFC060FF.toInt(), 0xFF7010C0.toInt())
            ).also {
                it.gradientType = GradientDrawable.RADIAL_GRADIENT
                it.gradientRadius = 90f   // matches the 60dp view diameter × 1.5 for soft bloom
                it.shape = GradientDrawable.OVAL
                it.alpha = 220            // slight transparency so it feels luminous
            }
            background = orb
        }

        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        else
            @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE

        val dp60 = (60 * resources.displayMetrics.density).toInt()
        val params = WindowManager.LayoutParams(
            dp60, dp60, layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                    or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply { 
            gravity = Gravity.TOP or Gravity.START
            x = 100
            y = 200 
        }

        var ix = 0; var iy = 0; var tx = 0f; var ty = 0f; var t0 = 0L
        val slop = 8f * resources.displayMetrics.density

        orbView.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> { 
                    ix = params.x; iy = params.y; tx = e.rawX; ty = e.rawY; t0 = System.currentTimeMillis()
                    true 
                }
                MotionEvent.ACTION_MOVE -> { 
                    params.x = ix + (e.rawX - tx).toInt()
                    params.y = iy + (e.rawY - ty).toInt()
                    try { windowManager.updateViewLayout(orbView, params) } catch(_: Exception) {}
                    true 
                }
                MotionEvent.ACTION_UP   -> {
                    if (Math.abs(e.rawX - tx) < slop && Math.abs(e.rawY - ty) < slop
                        && System.currentTimeMillis() - t0 < 300) {
                        Log.i("Aurora", "OverlayService: orb tapped")
                        bringAppToForeground()
                        sendBroadcast(Intent(ACTION_OVERLAY_TAPPED))
                    }
                    true
                }
                else -> false
            }
        }

        try { 
            windowManager.addView(orbView, params) 
            Log.i("Aurora", "OverlayService: orb added successfully")
        } catch (e: Exception) {
            Log.e("Aurora", "OverlayService: failed to add orb: ${e.message}")
        }
    }

    private fun bringAppToForeground() {
        packageManager.getLaunchIntentForPackage(packageName)?.apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT
            startActivity(this)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        try { windowManager.removeView(orbView) } catch (_: Exception) {}
    }

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
