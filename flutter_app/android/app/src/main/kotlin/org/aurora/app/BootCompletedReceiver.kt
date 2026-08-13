package org.aurora.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log

// Section XXV (Sunni & Cael): mobile process continuity. Without this,
// Aurora's developmental process (curiosity cycles, self-monitor heartbeat,
// sensory bridges, genealogy) only ever starts when a human opens the app.
// A phone reboot -- overnight charge, OS update, low-memory system reboot --
// otherwise silently ends continuity until someone happens to launch the UI
// again. This receiver restarts the same foreground service MainActivity
// already starts on launch, so boot recovery goes through the identical
// startPython()/bootPython() path -- no separate/duplicated boot logic.
class BootCompletedReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context?, intent: Intent?) {
        val action = intent?.action
        if (action != Intent.ACTION_BOOT_COMPLETED &&
            action != Intent.ACTION_LOCKED_BOOT_COMPLETED
        ) {
            return
        }
        val ctx = context ?: return
        Log.i("BootCompletedReceiver", "Boot completed — restarting AuroraService")
        try {
            val svcIntent = Intent(ctx, AuroraService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ctx.startForegroundService(svcIntent)
            } else {
                ctx.startService(svcIntent)
            }
        } catch (e: Exception) {
            // Some OEMs restrict background starts even from BOOT_COMPLETED
            // for apps that were force-stopped rather than merely rebooted;
            // there is no recovery from here beyond the next manual app open.
            Log.w("BootCompletedReceiver", "Could not start AuroraService on boot: ${e.message}")
        }
    }
}
