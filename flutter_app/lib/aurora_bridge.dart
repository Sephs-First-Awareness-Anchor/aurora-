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
    final errMsgMatch   = RegExp(r'"error_msg"\s*:\s*"((?:[^"\\]|\\.)*)"').firstMatch(json);
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
      'partner':    partnerMatch?.group(1)?.replaceAll(r'\"', '"').replaceAll(r'\n', '\n') ?? '',
      'aurora_msg': auroraMatch?.group(1)?.replaceAll(r'\"', '"').replaceAll(r'\n', '\n') ?? '',
      'lsa_paths':  lsaMatch  != null ? int.tryParse(lsaMatch.group(1)!)    : null,
      'turn_num':   turnMatch  != null ? int.tryParse(turnMatch.group(1)!)   : null,
      'elapsed':    elapsedMatch != null ? int.tryParse(elapsedMatch.group(1)!) : null,
      'total_secs': totalMatch   != null ? int.tryParse(totalMatch.group(1)!)  : null,
      'avg_n_cost': _parseDouble(json, 'avg_n_cost'),
      'error_msg':  errMsgMatch?.group(1)?.replaceAll(r'\"', '"') ?? '',
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

  // ── Self-model (simulated self + hardware body) ───────────────────────────

  /// Aurora's live self-model: axis state, hardware body (battery/motion/light),
  /// self-entity telemetry, LSA paths, SediMemory depth.
  static Future<Map<String, dynamic>> getSelfModel() async {
    final json = await _channel.invokeMethod<String>('getSelfModel') ?? '{}';
    return _parseSelfModel(json);
  }

  static Map<String, dynamic> _parseSelfModel(String json) {
    final domMatch      = RegExp(r'"dominant"\s*:\s*"([^"]+)"').firstMatch(json);
    final batteryMatch  = RegExp(r'"battery_pct"\s*:\s*([0-9.]+)').firstMatch(json);
    final motionMatch   = RegExp(r'"motion"\s*:\s*([0-9.]+)').firstMatch(json);
    final lightMatch    = RegExp(r'"light_lux"\s*:\s*([0-9.]+)').firstMatch(json);
    final chargingMatch = RegExp(r'"charging"\s*:\s*([0-9.]+)').firstMatch(json);
    final expMatch      = RegExp(r'"experiences"\s*:\s*(\d+)').firstMatch(json);
    final insMatch      = RegExp(r'"insights"\s*:\s*(\d+)').firstMatch(json);
    final genMatch      = RegExp(r'"generation"\s*:\s*(\d+)').firstMatch(json);
    final lsaMatch      = RegExp(r'"lsa_paths"\s*:\s*(\d+)').firstMatch(json);
    final sediMatch     = RegExp(r'"sedi_depth"\s*:\s*(\d+)').firstMatch(json);
    return {
      'X': _parseDouble(json, 'X') ?? 0.5,
      'T': _parseDouble(json, 'T') ?? 0.5,
      'N': _parseDouble(json, 'N') ?? 0.5,
      'B': _parseDouble(json, 'B') ?? 0.5,
      'A': _parseDouble(json, 'A') ?? 0.5,
      'dominant':    domMatch?.group(1) ?? 'X',
      'battery_pct': batteryMatch  != null ? double.tryParse(batteryMatch.group(1)!)  : null,
      'motion':      motionMatch   != null ? double.tryParse(motionMatch.group(1)!)   : null,
      'light_lux':   lightMatch    != null ? double.tryParse(lightMatch.group(1)!)    : null,
      'charging':    chargingMatch != null ? (chargingMatch.group(1) == '1.0') : null,
      'experiences': expMatch != null ? int.tryParse(expMatch.group(1)!) : 0,
      'insights':    insMatch != null ? int.tryParse(insMatch.group(1)!) : 0,
      'generation':  genMatch != null ? int.tryParse(genMatch.group(1)!) : 0,
      'lsa_paths':   lsaMatch  != null ? int.tryParse(lsaMatch.group(1)!)  : 0,
      'sedi_depth':  sediMatch != null ? int.tryParse(sediMatch.group(1)!) : 0,
    };
  }

  // ── Hub: cognitive stats + room state ─────────────────────────────────────

  /// Live cognitive metrics: LSA paths, N-cost, evo cycles, axis pressures,
  /// understanding/coherence/grounding, SediMemory depth, crystal maturity,
  /// chamber fossils, and training status if a session is running.
  static Future<Map<String, dynamic>> getCognitiveStats() async {
    final json = await _channel.invokeMethod<String>('getCognitiveStats') ?? '{}';
    return _parseCognitiveStats(json);
  }

  static Map<String, dynamic> _parseCognitiveStats(String json) {
    int    _i(String key) { final m = RegExp('"$key"\\s*:\\s*(\\d+)').firstMatch(json); return m != null ? (int.tryParse(m.group(1)!) ?? 0) : 0; }
    double _d(String key) { final m = RegExp('"$key"\\s*:\\s*([0-9.]+)').firstMatch(json); return m != null ? (double.tryParse(m.group(1)!) ?? 0.0) : 0.0; }
    bool   _b(String key) => json.contains('"$key":true');
    return {
      'lsa_paths':          _i('lsa_paths'),
      'avg_n_cost':         _d('avg_n_cost'),
      'evo_cycles':         _i('evo_cycles'),
      'sentence_target':    _i('sentence_target'),
      'evo_available':      _b('evo_available'),
      'understanding_index':_d('understanding_index'),
      'coherence_index':    _d('coherence_index'),
      'grounding_index':    _d('grounding_index'),
      'topic_tracking':     _d('topic_tracking'),
      'sedimemory_depth':   _i('sedimemory_depth'),
      'crystal_maturity':   _d('crystal_maturity'),
      'crystal_nodes':      _i('crystal_nodes'),
      'chamber_fossils':    _i('chamber_fossils'),
      'noncomp_loaded':     _i('noncomp_loaded'),
      'noncomp_diagonal_live': _i('noncomp_diagonal_live'),
      'turn_count':         _i('turn_count'),
      'training_active':    _b('training_active'),
      'training_turn':      _i('training_turn'),
      'training_total_secs':_i('training_total_secs'),
      'training_elapsed':   _i('training_elapsed'),
      // Axis pressures nested
      'X': _d('X'), 'T': _d('T'), 'N': _d('N'), 'B': _d('B'), 'A': _d('A'),
    };
  }

  /// Room state: recent notes, messages, activity log, room intentions,
  /// daemon status from aurora_state/ JSON files.
  static Future<Map<String, dynamic>> getRoomState() async {
    final json = await _channel.invokeMethod<String>('getRoomState') ?? '{}';
    // Return raw — hub screen parses the nested arrays itself
    return {'raw': json};
  }

  /// Send a navigation or Poedex command to Aurora's room.
  /// cmd: JSON string e.g. '{"navigate":"Health"}' or '{"poedex":"define N"}'
  static Future<void> provideRoomCommand(String cmd) =>
      _channel.invokeMethod('provideRoomCommand', {'cmd': cmd});

  // ── Gauntlet training pipeline ────────────────────────────────────────────

  static Future<Map<String, dynamic>> startGauntlet() async {
    final json = await _channel.invokeMethod<String>('startGauntlet') ?? '{}';
    try {
      // Use basic parsing — no dart:convert dependency in bridge
      return {'status': json.contains('"started"') ? 'started' : 'error', 'raw': json};
    } catch (_) { return {'raw': json}; }
  }

  static Future<void> stopGauntlet() =>
      _channel.invokeMethod('stopGauntlet');

  static Future<String> getGauntletStatus() async =>
      await _channel.invokeMethod<String>('getGauntletStatus') ?? '{}';

  static Future<String> triggerCuriosityCycle({int n = 5}) async =>
      await _channel.invokeMethod<String>('triggerCuriosityCycle', {'n': n}) ?? '{}';

  static Future<String> triggerEvoCycle({int ticks = 20}) async =>
      await _channel.invokeMethod<String>('triggerEvoCycle', {'ticks': ticks}) ?? '{}';
}
