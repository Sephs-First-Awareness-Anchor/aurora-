import 'dart:async';
import 'package:flutter/services.dart';

/// Dart wrapper around the Kotlin MethodChannel / EventChannel that talks to
/// AuroraService.kt → Chaquopy → aurora_bridge.py.
class AuroraBridge {
  static const _channel      = MethodChannel('org.aurora.app/bridge');
  static const _eventChannel = EventChannel('org.aurora.app/events');

  static Stream<Map<String, dynamic>>? _events;

  /// Stream of JSON events from AuroraService (ready/response/error),
  /// native STT (source:"stt"), native TTS (source:"tts"), and
  /// permission results (source:"permission").
  static Stream<Map<String, dynamic>> get events {
    _events ??= _eventChannel
        .receiveBroadcastStream()
        .map((raw) => _parseEvent(raw.toString()));
    return _events!;
  }

  static Map<String, dynamic> _parseEvent(String json) {
    final sourceMatch   = RegExp(r'"source"\s*:\s*"([^"]*)"').firstMatch(json);
    final typeMatch     = RegExp(r'"type"\s*:\s*"([^"]*)"').firstMatch(json);
    final textMatch     = RegExp(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"').firstMatch(json);
    final errorMatch    = RegExp(r'"error"\s*:\s*(\d+)').firstMatch(json);
    final summaryMatch  = RegExp(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"').firstMatch(json);
    final partnerMatch  = RegExp(r'"partner"\s*:\s*"((?:[^"\\]|\\.)*)"').firstMatch(json);
    final auroraMatch   = RegExp(r'"aurora"\s*:\s*"((?:[^"\\]|\\.)*)"').firstMatch(json);
    final lsaMatch      = RegExp(r'"lsa_paths"\s*:\s*(\d+)').firstMatch(json);
    final turnMatch     = RegExp(r'"turn"\s*:\s*(\d+)').firstMatch(json);
    final elapsedMatch  = RegExp(r'"elapsed"\s*:\s*(\d+)').firstMatch(json);
    final totalMatch    = RegExp(r'"total_secs"\s*:\s*(\d+)').firstMatch(json);
    return {
      'source':    sourceMatch?.group(1) ?? 'aurora',
      'type':      typeMatch?.group(1)   ?? 'unknown',
      'text':      textMatch?.group(1)?.replaceAll(r'\"', '"') ?? '',
      'summary':   summaryMatch?.group(1)?.replaceAll(r'\"', '"') ?? '',
      'error':     errorMatch != null ? int.tryParse(errorMatch.group(1)!) : null,
      'final':     json.contains('"final":true'),
      'granted':   json.contains('"granted":true'),
      // Emotional axis values — present on type=="axis_state" events
      'X': _parseDouble(json, 'X'),
      'T': _parseDouble(json, 'T'),
      'N': _parseDouble(json, 'N'),
      'B': _parseDouble(json, 'B'),
      'A': _parseDouble(json, 'A'),
      // Training turn fields — present on type=="training_turn"/"training_done" events
      'partner':    partnerMatch?.group(1)?.replaceAll(r'\"', '"') ?? '',
      'aurora_msg': auroraMatch?.group(1)?.replaceAll(r'\"', '"') ?? '',
      'lsa_paths':  lsaMatch  != null ? int.tryParse(lsaMatch.group(1)!)    : null,
      'turn_num':   turnMatch  != null ? int.tryParse(turnMatch.group(1)!)   : null,
      'elapsed':    elapsedMatch != null ? int.tryParse(elapsedMatch.group(1)!) : null,
      'total_secs': totalMatch   != null ? int.tryParse(totalMatch.group(1)!)  : null,
      'avg_n_cost': _parseDouble(json, 'avg_n_cost'),
    };
  }

  static double? _parseDouble(String json, String key) {
    final m = RegExp('"$key"\\s*:\\s*([0-9]+\\.?[0-9]*)').firstMatch(json);
    return m != null ? double.tryParse(m.group(1)!) : null;
  }

  static Future<String> sendMessage(String text) async {
    final result = await _channel.invokeMethod<String>('sendMessage', {'text': text});
    return result ?? '';
  }

  static Future<String> getState() async =>
      await _channel.invokeMethod<String>('getState') ?? 'DORMANT';

  static Future<void> setState(String state) =>
      _channel.invokeMethod('setState', {'state': state});

  // ── STT (native Android SpeechRecognizer) ─────────────────────────────────

  static Future<void> startListening() =>
      _channel.invokeMethod('startListening');

  static Future<void> stopListening() =>
      _channel.invokeMethod('stopListening');

  // ── TTS (native Android TextToSpeech) ────────────────────────────────────

  static Future<void> speak(String text) =>
      _channel.invokeMethod('speak', {'text': text});

  static Future<void> stopSpeaking() =>
      _channel.invokeMethod('stopSpeaking');

  static Future<void> captureVision() =>
      _channel.invokeMethod('captureVision');

  // ── Overlay (native Android OverlayService) ───────────────────────────────

  static Future<bool> startOverlay() async =>
      await _channel.invokeMethod<bool>('startOverlay') ?? false;

  static Future<void> stopOverlay() =>
      _channel.invokeMethod('stopOverlay');

  static Future<bool> hasOverlayPermission() async =>
      await _channel.invokeMethod<bool>('hasOverlayPermission') ?? false;

  static Future<void> requestOverlayPermission() =>
      _channel.invokeMethod('requestOverlayPermission');

  // ── Screen observer (Android Accessibility surface observation) ───────────

  static Future<bool> hasScreenObserverPermission() async =>
      await _channel.invokeMethod<bool>('hasScreenObserverPermission') ?? false;

  static Future<void> requestScreenObserverPermission() =>
      _channel.invokeMethod('requestScreenObserverPermission');

  /// Returns true (and clears the flag) if the overlay orb was tapped while
  /// the app was backgrounded.  Call this in onResume.
  static Future<bool> consumeOverlayTap() async =>
      await _channel.invokeMethod<bool>('consumeOverlayTap') ?? false;

  // ── Conversation training ─────────────────────────────────────────────────

  static Future<String> startTraining({
    required String apiKey,
    String model = 'gemini-2.5-flash',
    double durationMinutes = 10.0,
  }) async {
    final result = await _channel.invokeMethod<String>(
      'startTraining',
      {'apiKey': apiKey, 'model': model, 'durationMinutes': durationMinutes},
    );
    return result ?? 'error';
  }

  static Future<void> stopTraining() =>
      _channel.invokeMethod('stopTraining');

  static Future<Map<String, dynamic>> getTrainingStatus() async {
    final json = await _channel.invokeMethod<String>('getTrainingStatus') ?? '{}';
    return _parseEvent(json);
  }
}
