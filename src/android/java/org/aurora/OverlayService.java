package org.aurora.aurora;

import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.ImageView;

public class OverlayService extends Service {
    private static final String TAG            = "AuroraOverlay";
    private static final String ACTION_TAP     = "com.aurora.OVERLAY_TAP";
    private static final String ACTION_STATE   = "com.aurora.SET_STATE";
    // Movement threshold (dp) below which ACTION_UP is treated as a tap
    private static final int    TAP_SLOP_DP    = 8;

    private WindowManager              windowManager;
    private FrameLayout                orbContainer;
    private ImageView                  orbView;
    private BroadcastReceiver          stateReceiver;
    private WindowManager.LayoutParams params;
    private int                        tapSlopPx;

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "OverlayService onCreate");

        tapSlopPx     = (int)(TAP_SLOP_DP * getResources().getDisplayMetrics().density);
        windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);

        // Container + orb view
        orbContainer = new FrameLayout(this);
        orbView      = new ImageView(this);
        setOrbColor(0xCCAA22FF);   // default: aurora violet

        int resId = getResources().getIdentifier("orb_shape", "drawable", getPackageName());
        if (resId != 0) {
            orbView.setImageResource(resId);
        }

        orbContainer.addView(orbView, new FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT));

        int layoutFlag = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            : WindowManager.LayoutParams.TYPE_PHONE;

        int sizePx = (int)(96 * getResources().getDisplayMetrics().density);

        params = new WindowManager.LayoutParams(
            sizePx, sizePx,
            layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT);

        params.gravity = Gravity.TOP | Gravity.LEFT;
        params.x = 0;
        params.y = 100;

        orbContainer.setOnTouchListener(new View.OnTouchListener() {
            private int   startX, startY;
            private float startRawX, startRawY;

            @Override
            public boolean onTouch(View v, MotionEvent event) {
                switch (event.getAction()) {
                    case MotionEvent.ACTION_DOWN:
                        startX    = params.x;
                        startY    = params.y;
                        startRawX = event.getRawX();
                        startRawY = event.getRawY();
                        return true;

                    case MotionEvent.ACTION_MOVE:
                        params.x = startX + (int)(event.getRawX() - startRawX);
                        params.y = startY + (int)(event.getRawY() - startRawY);
                        windowManager.updateViewLayout(orbContainer, params);
                        return true;

                    case MotionEvent.ACTION_UP:
                        float dx = Math.abs(event.getRawX() - startRawX);
                        float dy = Math.abs(event.getRawY() - startRawY);
                        if (dx < tapSlopPx && dy < tapSlopPx) {
                            // Short tap — notify the Kivy layer
                            Intent tap = new Intent(ACTION_TAP);
                            tap.setPackage(getPackageName());
                            sendBroadcast(tap);
                            Log.d(TAG, "Overlay tap broadcast sent");
                        }
                        return true;
                }
                return false;
            }
        });

        // Register receiver for state updates from the Kivy layer
        stateReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String state = intent.getStringExtra("state");
                if (state != null) {
                    updateOrbForState(state);
                }
            }
        };
        IntentFilter filter = new IntentFilter(ACTION_STATE);
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(stateReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(stateReceiver, filter);
        }

        try {
            windowManager.addView(orbContainer, params);
            Log.d(TAG, "Overlay orb added to WindowManager");
        } catch (Exception e) {
            Log.e(TAG, "Failed to add overlay: " + e.getMessage());
        }
    }

    private void setOrbColor(int color) {
        orbView.setBackgroundColor(color);
    }

    private void updateOrbForState(String state) {
        switch (state) {
            case "LISTENING": setOrbColor(0xCCFF1560); break;  // Pink
            case "THINKING":  setOrbColor(0xCC00AAFF); break;  // Cyan
            case "SPEAKING":  setOrbColor(0xCCFFDD00); break;  // Yellow
            case "ONLINE":    setOrbColor(0xCCAA22FF); break;  // Violet
            default:          setOrbColor(0x663030A0); break;  // Dim dark
        }
        Log.d(TAG, "Orb state → " + state);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "OverlayService onDestroy");
        if (stateReceiver != null) {
            try { unregisterReceiver(stateReceiver); } catch (Exception ignored) {}
        }
        if (orbContainer != null) {
            try { windowManager.removeView(orbContainer); } catch (Exception ignored) {}
        }
    }
}
