# APK size: R8 keep rules for code shrinking (minifyEnabled true).
#
# Chaquopy's own AAR bundles consumer ProGuard rules that are
# automatically merged by AGP, but the Java-side bridge
# (com.chaquo.python.Python / PyObject.callAttr) is called by class/
# method name from AuroraService.kt, so it is kept here explicitly as
# defense in depth rather than relying solely on the consumer rules.
-keep class com.chaquo.python.** { *; }
-dontwarn com.chaquo.python.**

# No third-party Flutter plugins are used (camera/TTS/STT are
# hand-written Kotlin talking to Android platform APIs directly, not
# plugin packages) -- Flutter's own embedding AAR bundles its own
# consumer rules. This app's own classes are referenced from the
# manifest (Activity/Service/BroadcastReceiver, already covered by
# AGP's default rules) or only from Dart via MethodChannel/EventChannel
# method-name strings, not reflection, so no additional keep is needed
# for org.aurora.app.** beyond the defaults.
