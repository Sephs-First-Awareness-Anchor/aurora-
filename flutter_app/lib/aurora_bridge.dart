import 'dart:async';
import 'package:flutter/services.dart';

/// Dart wrapper around the Kotlin MethodChannel / EventChannel that talks to
/// AuroraService.kt → Chaquopy → aurora_bridge.py.
class AuroraBridge {
  static const _channel     = MethodChannel('org.aurora.app/bridge');
  static const _eventChannel = EventChannel('org.aurora.app/events');

  static Stream<Map<String, dynamic>>? _events;

  /// Stream of JSON events emitted by AuroraService (ready / response / error).
  static Stream<Map<String, dynamic>> get events {
    _events ??= _eventChannel
        .receiveBroadcastStream()
        .map((raw) {
          try {
            // raw is a JSON string: {"type":"response","text":"..."}
            final str = raw.toString();
            // Minimal JSON decode without importing dart:convert everywhere
            return _parseEvent(str);
          } catch (_) {
            return <String, dynamic>{'type': 'raw', 'text': raw.toString()};
          }
        });
    return _events!;
  }

  static Map<String, dynamic> _parseEvent(String json) {
    // Light JSON parsing — avoids a full import just for this
    final typeMatch = RegExp(r'"type"\s*:\s*"([^"]*)"').firstMatch(json);
    final textMatch = RegExp(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"').firstMatch(json);
    return {
      'type': typeMatch?.group(1) ?? 'unknown',
      'text': textMatch?.group(1)?.replaceAll(r'\"', '"') ?? '',
    };
  }

  /// Send a text message to Aurora and get a response back.
  static Future<String> sendMessage(String text) async {
    final result = await _channel.invokeMethod<String>(
      'sendMessage', {'text': text},
    );
    return result ?? '';
  }

  static Future<String> getState() async =>
      await _channel.invokeMethod<String>('getState') ?? 'DORMANT';

  static Future<void> setState(String state) =>
      _channel.invokeMethod('setState', {'state': state});

  static Future<bool> hasOverlayPermission() async =>
      await _channel.invokeMethod<bool>('hasOverlayPermission') ?? false;

  static Future<void> requestOverlayPermission() =>
      _channel.invokeMethod('requestOverlayPermission');
}
