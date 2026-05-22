package org.aurora.aurora;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.ImageView;

public class OverlayService extends Service {
    private static final String TAG = "AuroraOverlay";
    private static final String CHANNEL_ID = "aurora_overlay_channel";
    private static final int NOTIF_ID = 42;

    // Broadcast action Python listens for to trigger SUMMONED state
    public static final String ACTION_OVERLAY_TAPPED = "org.aurora.aurora.OVERLAY_TAPPED";

    private WindowManager windowManager;
    private ImageView orbView;

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "OverlayService onCreate");

        // Must call startForeground() on Android 8+ within 5 seconds or the
        // service is killed. A minimal silent notification keeps it alive.
        createNotificationChannel();
        Notification notification = buildNotification();
        startForeground(NOTIF_ID, notification);

        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

        orbView = new ImageView(this);
        orbView.setBackgroundColor(0x88A020F0);
        int id = getResources().getIdentifier("orb_shape", "drawable", getPackageName());
        if (id != 0) {
            orbView.setImageResource(id);
        }

        int layoutFlag = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;

        int size = (int) (80 * getResources().getDisplayMetrics().density);

        final WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                size, size,
                layoutFlag,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);

        params.gravity = Gravity.TOP | Gravity.LEFT;
        params.x = 0;
        params.y = 100;

        orbView.setOnTouchListener(new View.OnTouchListener() {
            private int initialX, initialY;
            private float initialTouchX, initialTouchY;
            private long touchDownTime;
            private static final float TAP_SLOP_DP = 8f;
            private static final long TAP_MAX_MS   = 300;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                float slop = TAP_SLOP_DP * getResources().getDisplayMetrics().density;
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX      = params.x;
                        initialY      = params.y;
                        initialTouchX = event.getRawX();
                        initialTouchY = event.getRawY();
                        touchDownTime = System.currentTimeMillis();
                        return true;

                    case MotionEvent.ACTION_MOVE:
                        params.x = initialX + (int)(event.getRawX() - initialTouchX);
                        params.y = initialY + (int)(event.getRawY() - initialTouchY);
                        windowManager.updateViewLayout(orbView, params);
                        return true;

                    case MotionEvent.ACTION_UP:
                        float dx = Math.abs(event.getRawX() - initialTouchX);
                        float dy = Math.abs(event.getRawY() - initialTouchY);
                        long dt = System.currentTimeMillis() - touchDownTime;
                        if (dx < slop && dy < slop && dt < TAP_MAX_MS) {
                            // Single tap: bring the Aurora app to the foreground
                            // and broadcast so Python can trigger SUMMONED state.
                            bringAppToForeground();
                            sendBroadcast(new Intent(ACTION_OVERLAY_TAPPED));
                            Log.d(TAG, "Overlay tapped — broadcasting OVERLAY_TAPPED");
                        }
                        return true;
                }
                return false;
            }
        });

        try {
            windowManager.addView(orbView, params);
            Log.d(TAG, "Floating orb added to WindowManager");
        } catch (Exception e) {
            Log.e(TAG, "Failed to add overlay view: " + e.getMessage());
        }
    }

    private void bringAppToForeground() {
        try {
            Intent launchIntent = getPackageManager().getLaunchIntentForPackage(getPackageName());
            if (launchIntent != null) {
                launchIntent.setFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_SINGLE_TOP
                        | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
                startActivity(launchIntent);
            }
        } catch (Exception e) {
            Log.e(TAG, "bringAppToForeground: " + e.getMessage());
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Aurora Overlay",
                    NotificationManager.IMPORTANCE_MIN);
            channel.setDescription("Aurora floating orb overlay");
            channel.setShowBadge(false);
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }

    private Notification buildNotification() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            return new Notification.Builder(this, CHANNEL_ID)
                    .setContentTitle("Aurora")
                    .setContentText("Overlay active")
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setOngoing(true)
                    .build();
        } else {
            return new Notification.Builder(this)
                    .setContentTitle("Aurora")
                    .setContentText("Overlay active")
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setPriority(Notification.PRIORITY_MIN)
                    .setOngoing(true)
                    .build();
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "OverlayService onDestroy");
        if (orbView != null) {
            try {
                windowManager.removeView(orbView);
            } catch (Exception e) {
                Log.e(TAG, "Failed to remove overlay view: " + e.getMessage());
            }
        }
    }
}
