// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// PhoneHands -- the phone's own abilities, reached from inside her app.
//
// Before this, every one of these lived behind termux-api, so in the APK she
// could open apps and links and nothing else.  Each call here uses Android's
// own API and the permission Sir grants once (MainActivity asks for them
// together on first start).  Nothing here decides what she does or says: it
// only gives her the reach.  Every call returns one JSON object,
//   {"ok": true, "data": ...}  or  {"ok": false, "error": "..."}
// so the Python side (aurora_internal/tool_registry.py, via Chaquopy) reads
// one shape whatever happened.
//
// Sending a text and placing a call are outward acts in Sir's name.  The
// code makes them possible; whether one happens is decided upstream, at the
// tool's call, never here.

package org.aurora.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.location.Location
import android.location.LocationManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.BatteryManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.CallLog
import android.provider.ContactsContract
import android.provider.Telephony
import android.telephony.SmsManager
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONArray
import org.json.JSONObject

object PhoneHands {

    private const val WORDS_CHANNEL = "aurora_her_words"

    /** The runtime permissions these abilities need, asked for once. */
    @JvmStatic
    fun runtimePermissions(): Array<String> {
        val perms = mutableListOf(
            Manifest.permission.SEND_SMS,
            Manifest.permission.READ_SMS,
            Manifest.permission.CALL_PHONE,
            Manifest.permission.READ_CALL_LOG,
            Manifest.permission.READ_CONTACTS,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
        return perms.toTypedArray()
    }

    private fun granted(ctx: Context, perm: String): Boolean =
        ContextCompat.checkSelfPermission(ctx, perm) == PackageManager.PERMISSION_GRANTED

    private fun ok(data: Any?): String = JSONObject().put("ok", true).put("data", data ?: JSONObject.NULL).toString()

    private fun fail(error: String): String = JSONObject().put("ok", false).put("error", error).toString()

    private fun needs(perm: String): String =
        fail("permission_not_granted:" + perm.substringAfterLast('.'))

    /** Which of the abilities' permissions Sir has granted. */
    @JvmStatic
    fun permissionState(ctx: Context): String {
        val out = JSONObject()
        for (p in runtimePermissions()) out.put(p.substringAfterLast('.'), granted(ctx, p))
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            out.put("POST_NOTIFICATIONS", granted(ctx, Manifest.permission.POST_NOTIFICATIONS))
        }
        out.put("screen_hands", ScreenObserverService.isRunning())
        return ok(out)
    }

    // ── Texts ────────────────────────────────────────────────────────────────

    @JvmStatic
    fun sendSms(ctx: Context, number: String, message: String): String {
        if (number.isBlank() || message.isBlank()) return fail("number and message required")
        if (!granted(ctx, Manifest.permission.SEND_SMS)) return needs(Manifest.permission.SEND_SMS)
        return try {
            @Suppress("DEPRECATION")
            val sms: SmsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S)
                ctx.getSystemService(SmsManager::class.java) else SmsManager.getDefault()
            val parts = sms.divideMessage(message)
            if (parts.size > 1) sms.sendMultipartTextMessage(number, null, parts, null, null)
            else sms.sendTextMessage(number, null, message, null, null)
            ok(JSONObject().put("to", number).put("parts", parts.size))
        } catch (e: Exception) {
            fail("sms_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    @JvmStatic
    fun readSms(ctx: Context, limit: Int): String {
        if (!granted(ctx, Manifest.permission.READ_SMS)) return needs(Manifest.permission.READ_SMS)
        val out = JSONArray()
        return try {
            ctx.contentResolver.query(
                Telephony.Sms.Inbox.CONTENT_URI,
                arrayOf(Telephony.Sms.ADDRESS, Telephony.Sms.BODY, Telephony.Sms.DATE, Telephony.Sms.READ),
                null, null, Telephony.Sms.DATE + " DESC"
            )?.use { c ->
                while (c.moveToNext() && out.length() < limit.coerceIn(1, 100)) {
                    out.put(JSONObject()
                        .put("from", c.getString(0) ?: "")
                        .put("body", c.getString(1) ?: "")
                        .put("at", c.getLong(2) / 1000.0)
                        .put("read", c.getInt(3) == 1))
                }
            }
            ok(out)
        } catch (e: Exception) {
            fail("sms_read_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    // ── Calls ────────────────────────────────────────────────────────────────

    @JvmStatic
    fun makeCall(ctx: Context, number: String): String {
        if (number.isBlank()) return fail("phone number required")
        if (!granted(ctx, Manifest.permission.CALL_PHONE)) return needs(Manifest.permission.CALL_PHONE)
        return try {
            val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:" + Uri.encode(number)))
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ctx.startActivity(intent)
            ok(JSONObject().put("calling", number))
        } catch (e: Exception) {
            fail("call_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    @JvmStatic
    fun callLog(ctx: Context, limit: Int): String {
        if (!granted(ctx, Manifest.permission.READ_CALL_LOG)) return needs(Manifest.permission.READ_CALL_LOG)
        val out = JSONArray()
        return try {
            ctx.contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.CACHED_NAME, CallLog.Calls.TYPE,
                        CallLog.Calls.DATE, CallLog.Calls.DURATION),
                null, null, CallLog.Calls.DATE + " DESC"
            )?.use { c ->
                while (c.moveToNext() && out.length() < limit.coerceIn(1, 100)) {
                    val kind = when (c.getInt(2)) {
                        CallLog.Calls.INCOMING_TYPE -> "incoming"
                        CallLog.Calls.OUTGOING_TYPE -> "outgoing"
                        CallLog.Calls.MISSED_TYPE -> "missed"
                        CallLog.Calls.REJECTED_TYPE -> "rejected"
                        else -> "other"
                    }
                    out.put(JSONObject()
                        .put("number", c.getString(0) ?: "")
                        .put("name", c.getString(1) ?: "")
                        .put("type", kind)
                        .put("at", c.getLong(3) / 1000.0)
                        .put("seconds", c.getLong(4)))
                }
            }
            ok(out)
        } catch (e: Exception) {
            fail("call_log_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    // ── Contacts ─────────────────────────────────────────────────────────────

    @JvmStatic
    fun contacts(ctx: Context, query: String, limit: Int): String {
        if (!granted(ctx, Manifest.permission.READ_CONTACTS)) return needs(Manifest.permission.READ_CONTACTS)
        val out = JSONArray()
        val q = query.trim()
        return try {
            val sel = if (q.isNotEmpty())
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " LIKE ?" else null
            val args = if (q.isNotEmpty()) arrayOf("%$q%") else null
            ctx.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                arrayOf(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                        ContactsContract.CommonDataKinds.Phone.NUMBER),
                sel, args, ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC"
            )?.use { c ->
                while (c.moveToNext() && out.length() < limit.coerceIn(1, 200)) {
                    out.put(JSONObject().put("name", c.getString(0) ?: "").put("number", c.getString(1) ?: ""))
                }
            }
            ok(out)
        } catch (e: Exception) {
            fail("contacts_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    // ── Location ─────────────────────────────────────────────────────────────

    @SuppressLint("MissingPermission")
    @JvmStatic
    fun location(ctx: Context, timeoutMs: Long): String {
        val fine = granted(ctx, Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = granted(ctx, Manifest.permission.ACCESS_COARSE_LOCATION)
        if (!fine && !coarse) return needs(Manifest.permission.ACCESS_COARSE_LOCATION)
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val providers = lm.getProviders(true)
        var best: Location? = null
        for (p in providers) {
            val l = try { lm.getLastKnownLocation(p) } catch (_: Exception) { null } ?: continue
            if (best == null || l.time > best.time) best = l
        }
        val fresh = best != null && System.currentTimeMillis() - best.time < 120_000L
        if (!fresh && Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            val provider = when {
                fine && providers.contains(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
                providers.contains(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
                else -> providers.firstOrNull()
            }
            if (provider != null) {
                val got = AtomicReference<Location?>(null)
                val latch = CountDownLatch(1)
                val exec = Executors.newSingleThreadExecutor()
                try {
                    lm.getCurrentLocation(provider, null, exec) { l -> got.set(l); latch.countDown() }
                    latch.await(timeoutMs.coerceIn(2_000L, 30_000L), TimeUnit.MILLISECONDS)
                } catch (_: Exception) {
                } finally {
                    exec.shutdown()
                }
                val g = got.get()
                if (g != null) best = g
            }
        }
        val l = best ?: return fail("location_unavailable")
        return ok(JSONObject()
            .put("latitude", l.latitude)
            .put("longitude", l.longitude)
            .put("accuracy_m", l.accuracy.toDouble())
            .put("provider", l.provider ?: "")
            .put("age_s", (System.currentTimeMillis() - l.time) / 1000.0))
    }

    // ── Clipboard (main thread: ClipboardManager needs a Looper) ─────────────

    private fun <T> onMain(timeoutMs: Long, block: () -> T): T? {
        if (Looper.myLooper() == Looper.getMainLooper()) return block()
        val ref = AtomicReference<T?>(null)
        val latch = CountDownLatch(1)
        Handler(Looper.getMainLooper()).post {
            try { ref.set(block()) } catch (_: Exception) {} finally { latch.countDown() }
        }
        latch.await(timeoutMs, TimeUnit.MILLISECONDS)
        return ref.get()
    }

    @JvmStatic
    fun clipboardGet(ctx: Context): String {
        val text = onMain(3_000L) {
            val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip = cm.primaryClip
            if (clip == null || clip.itemCount == 0) null
            else clip.getItemAt(0).coerceToText(ctx)?.toString()
        }
        // Android 10+ shows the clipboard only to the app in front; read
        // from the background, it comes back empty rather than failing.
        return if (text == null) fail("clipboard_empty_or_not_in_front") else ok(text)
    }

    @JvmStatic
    fun clipboardSet(ctx: Context, text: String): String {
        val done = onMain(3_000L) {
            val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newPlainText("Aurora", text))
            true
        }
        return if (done == true) ok("written") else fail("clipboard_write_failed")
    }

    // ── Notifications ────────────────────────────────────────────────────────

    @SuppressLint("MissingPermission")
    @JvmStatic
    fun notify(ctx: Context, title: String, message: String): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            !granted(ctx, Manifest.permission.POST_NOTIFICATIONS)) {
            return needs(Manifest.permission.POST_NOTIFICATIONS)
        }
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val nm = ctx.getSystemService(NotificationManager::class.java)
                if (nm.getNotificationChannel(WORDS_CHANNEL) == null) {
                    nm.createNotificationChannel(NotificationChannel(
                        WORDS_CHANNEL, "Her notes to you", NotificationManager.IMPORTANCE_DEFAULT))
                }
            }
            val id = (System.currentTimeMillis() % Int.MAX_VALUE).toInt()
            val n = NotificationCompat.Builder(ctx, WORDS_CHANNEL)
                .setSmallIcon(ctx.applicationInfo.icon)
                .setContentTitle(title)
                .setContentText(message)
                .setStyle(NotificationCompat.BigTextStyle().bigText(message))
                .setAutoCancel(true)
                .build()
            NotificationManagerCompat.from(ctx).notify(id, n)
            ok(JSONObject().put("posted", title))
        } catch (e: Exception) {
            fail("notification_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    // ── Torch and vibration ──────────────────────────────────────────────────

    @JvmStatic
    fun torch(ctx: Context, on: Boolean): String {
        return try {
            val cm = ctx.getSystemService(Context.CAMERA_SERVICE) as CameraManager
            val id = cm.cameraIdList.firstOrNull { cid ->
                cm.getCameraCharacteristics(cid).get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
            } ?: return fail("no_flash_on_this_phone")
            cm.setTorchMode(id, on)
            ok(if (on) "on" else "off")
        } catch (e: Exception) {
            // The torch shares the camera: while her eyes have it open some
            // phones refuse, and that is said rather than hidden.
            fail("torch_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    @JvmStatic
    fun vibrate(ctx: Context, durationMs: Long): String {
        return try {
            val ms = durationMs.coerceIn(10L, 5_000L)
            @Suppress("DEPRECATION")
            val v: Vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S)
                (ctx.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager).defaultVibrator
            else ctx.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
            if (!v.hasVibrator()) return fail("no_vibrator")
            v.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE))
            ok(ms)
        } catch (e: Exception) {
            fail("vibrate_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    // ── Wi-Fi and battery ────────────────────────────────────────────────────

    @SuppressLint("MissingPermission")
    @JvmStatic
    fun wifi(ctx: Context): String {
        return try {
            val out = JSONObject()
            val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val net = cm.activeNetwork
            val caps = net?.let { cm.getNetworkCapabilities(it) }
            out.put("connected", caps != null)
            out.put("on_wifi", caps?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true)
            out.put("on_cellular", caps?.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) == true)
            val link = net?.let { cm.getLinkProperties(it) }
            val ips = JSONArray()
            link?.linkAddresses?.forEach { ips.put(it.address.hostAddress ?: "") }
            out.put("ip", ips)
            val wm = ctx.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            @Suppress("DEPRECATION")
            val info = wm.connectionInfo
            if (info != null) {
                // The network's name needs location permission; without it
                // Android reports "<unknown ssid>".
                out.put("ssid", (info.ssid ?: "").trim('"'))
                out.put("signal_dbm", info.rssi)
                out.put("link_mbps", info.linkSpeed)
            }
            ok(out)
        } catch (e: Exception) {
            fail("wifi_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }

    @JvmStatic
    fun battery(ctx: Context): String {
        return try {
            val i = ctx.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
                ?: return fail("battery_unavailable")
            val level = i.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
            val scale = i.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
            val status = i.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
            val plugged = i.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0)
            ok(JSONObject()
                .put("percent", if (level >= 0 && scale > 0) level * 100.0 / scale else JSONObject.NULL)
                .put("charging", status == BatteryManager.BATTERY_STATUS_CHARGING ||
                                 status == BatteryManager.BATTERY_STATUS_FULL)
                .put("plugged", when (plugged) {
                    BatteryManager.BATTERY_PLUGGED_AC -> "ac"
                    BatteryManager.BATTERY_PLUGGED_USB -> "usb"
                    BatteryManager.BATTERY_PLUGGED_WIRELESS -> "wireless"
                    else -> "none"
                })
                .put("temperature_c", i.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, 0) / 10.0))
        } catch (e: Exception) {
            fail("battery_failed:" + (e.message ?: e.javaClass.simpleName))
        }
    }
}
