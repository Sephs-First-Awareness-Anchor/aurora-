import 'dart:async';
import 'package:flutter/services.dart';

/// Dart wrapper around the Kotlin MethodChannel / EventChannel that talks to
/// AuroraService.kt → Chaquopy → aurora_bridge.py.
class AuroraBridge {
  static const _channel      = MethodChannel('org.aurora.app/bridge');
  static const _eventChannel = EventChannel('org.aurora.app/events');

  static Stream<Map<String, dynamic>>? _events;

  /// Stream of JSON events emitted by AuroraService (ready / response / error).
  static Stream<Map<String, dynamic>> get events {
    _events ??= _eventChannel
        .receiveBroadcastStream()
        .map((raw) => _parseEvent(raw.toString()));
    return _events!;
  }

  static Map<String, dynamic> _parseEvent(String json) {
    final typeMatch = RegExp(r'"type"\s*:\s*"([^"]*)"').firstMatch(json);
    final textMatch = RegExp(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"').firstMatch(json);
    return {
      'type': typeMatch?.group(1) ?? 'unknown',
      'text': textMatch?.group(1)?.replaceAll(r'\"', '"') ?? '',
    };
  }

  static Future<String> sendMessage(String text) async {
    final result = await _channel.invokeMethod<String>('sendMessage', {'text': text});
    return result ?? '';
  }

  static Future<String> getState() async =>
      await _channel.invokeMethod<String>('getState') ?? 'DORMANT';

  static Future<void> setState(String state) =>
      _channel.invokeMethod('setState', {'state': state});

  // ── Overlay (native Android OverlayService) ────────────────────────────

  static Future<bool> startOverlay() async =>
      await _channel.invokeMethod<bool>('startOverlay') ?? false;

  static Future<void> stopOverlay() =>
      _channel.invokeMethod('stopOverlay');

  static Future<bool> hasOverlayPermission() async =>
      await _channel.invokeMethod<bool>('hasOverlayPermission') ?? false;

  static Future<void> requestOverlayPermission() =>
      _channel.invokeMethod('requestOverlayPermission');

  /// Returns true (and clears the flag) if the overlay orb was tapped while
  /// the app was backgrounded.  Call this in onResume.
  static Future<bool> consumeOverlayTap() async =>
      await _channel.invokeMethod<bool>('consumeOverlayTap') ?? false;
}
