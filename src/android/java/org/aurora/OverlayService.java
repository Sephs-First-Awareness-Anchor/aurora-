package org.aurora.aurora;

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
    private WindowManager windowManager;
    private ImageView orbView;

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "OverlayService onCreate called");

        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

        orbView = new ImageView(this);
        // Fallback color in case drawable is missing
        orbView.setBackgroundColor(0x88A020F0); // Semi-transparent Purple
        
        int id = getResources().getIdentifier("orb_shape", "drawable", getPackageName());
        if (id != 0) {
            orbView.setImageResource(id);
        }

        int layoutFlag;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            layoutFlag = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY;
        } else {
            layoutFlag = WindowManager.LayoutParams.TYPE_PHONE;
        }

        // Use fixed pixel size for the overlay to ensure it is visible
        int size = (int) (80 * getResources().getDisplayMetrics().density);

        final WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                size, size,
                layoutFlag,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT);

        params.gravity = Gravity.TOP | Gravity.LEFT;
        params.x = 0;
        params.y = 100;

        // Implement dragging
        orbView.setOnTouchListener(new View.OnTouchListener() {
            private int initialX;
            private int initialY;
            private float initialTouchX;
            private float initialTouchY;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        initialX = params.x;
                        initialY = params.y;
                        initialTouchX = event.getRawX();
                        initialTouchY = event.getRawY();
                        return true;
                    case MotionEvent.ACTION_MOVE:
                        params.x = initialX + (int) (event.getRawX() - initialTouchX);
                        params.y = initialY + (int) (event.getRawY() - initialTouchY);
                        windowManager.updateViewLayout(orbView, params);
                        return true;
                }
                return false;
            }
        });

        try {
            windowManager.addView(orbView, params);
            Log.d(TAG, "Floating Orb added to WindowManager");
        } catch (Exception e) {
            Log.e(TAG, "Failed to add overlay view: " + e.getMessage());
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "OverlayService onDestroy called");
        if (orbView != null) {
            try {
                windowManager.removeView(orbView);
            } catch (Exception e) {
                Log.e(TAG, "Failed to remove overlay view: " + e.getMessage());
            }
        }
    }
}
