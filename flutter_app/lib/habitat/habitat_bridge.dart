// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Dart wrapper around the SAME Kotlin MethodChannel AuroraBridge uses
// (org.aurora.app/bridge) -- a second static const MethodChannel with
// the same name is a supported Flutter pattern, not a second channel.
// Every call here is a thin pass-through to aurora_bridge.py's
// habitat_* functions (see that file's own docstring): Flutter renders
// and submits interaction, it never owns developmental meaning (spec
// section 20).
import 'dart:convert';
import 'package:flutter/services.dart';

import 'habitat_model.dart';

class HabitatBridge {
  static const _channel = MethodChannel('org.aurora.app/bridge');

  static Future<Map<String, dynamic>> getAffordances() async {
    final raw = await _channel.invokeMethod<String>('habitatGetAffordances') ?? '{}';
    return decodeHabitatJson(raw);
  }

  static Future<HabitatState> getState({String? territory, String actor = 'human'}) async {
    final params = jsonEncode({if (territory != null) 'territory': territory, 'actor': actor});
    final raw = await _channel.invokeMethod<String>('habitatGetState', {'params': params}) ?? '{}';
    final decoded = decodeHabitatJson(raw);
    if (decoded.isEmpty) return HabitatState.empty(territory ?? 'all');
    return HabitatState.fromJson(decoded);
  }

  static Future<HabitatEntity?> getEntity(String entityId, {String actor = 'human'}) async {
    final params = jsonEncode({'entity_id': entityId, 'actor': actor});
    final raw = await _channel.invokeMethod<String>('habitatGetEntity', {'params': params}) ?? '{}';
    final decoded = decodeHabitatJson(raw);
    if (decoded.isEmpty || decoded.containsKey('error')) return null;
    return HabitatEntity.fromJson(decoded);
  }

  static Future<List<Map<String, dynamic>>> getHistory({String? entityId, String? territory, int limit = 50}) async {
    final params = jsonEncode({
      if (entityId != null) 'entity_id': entityId,
      if (territory != null) 'territory': territory,
      'limit': limit,
    });
    final raw = await _channel.invokeMethod<String>('habitatGetHistory', {'params': params}) ?? '[]';
    try {
      final decoded = jsonDecode(raw);
      if (decoded is List) return decoded.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    } catch (_) {}
    return const [];
  }

  static Future<List<Map<String, dynamic>>> getLineage(String entityId) async {
    final raw = await _channel.invokeMethod<String>('habitatGetLineage', {'entityId': entityId}) ?? '[]';
    try {
      final decoded = jsonDecode(raw);
      if (decoded is List) return decoded.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    } catch (_) {}
    return const [];
  }

  /// A human's environmental action. See aurora_habitat.py's OPERATIONS
  /// for the legal `operation` vocabulary and aurora_habitat.py's
  /// `_op_*` handlers for each operation's `parameters` shape.
  static Future<HabitatConsequence> act({
    required String territory,
    required String operation,
    List<String> targetIds = const [],
    Map<String, dynamic> parameters = const {},
    String intentionContext = '',
  }) async {
    final actionJson = jsonEncode({
      'territory': territory,
      'operation': operation,
      'target_ids': targetIds,
      'parameters': parameters,
      'intention_context': intentionContext,
    });
    final raw = await _channel.invokeMethod<String>('habitatAct', {'actionJson': actionJson}) ?? '{}';
    final decoded = decodeHabitatJson(raw);
    if (decoded.isEmpty) return HabitatConsequence.error('no_response');
    if (decoded.containsKey('error')) return HabitatConsequence.error(decoded['error'] as String);
    return HabitatConsequence.fromJson(decoded);
  }

  static Future<Map<String, dynamic>> integrityReport() async {
    final raw = await _channel.invokeMethod<String>('habitatIntegrityReport') ?? '{}';
    return decodeHabitatJson(raw);
  }

  // ── human-only maintenance (spec section 32) ────────────────────────

  static Future<Map<String, dynamic>> backup() async {
    final raw = await _channel.invokeMethod<String>('habitatBackup') ?? '{}';
    return decodeHabitatJson(raw);
  }

  static Future<bool> restore(String backupPath) async {
    final raw = await _channel.invokeMethod<String>('habitatRestore', {'backupPath': backupPath}) ?? '{}';
    return decodeHabitatJson(raw)['success'] == true;
  }

  static Future<List<String>> isolateCorrupt() async {
    final raw = await _channel.invokeMethod<String>('habitatIsolateCorrupt') ?? '{}';
    final decoded = decodeHabitatJson(raw);
    return List<String>.from((decoded['isolated'] as List?) ?? const []);
  }

  static Future<bool> reset() async {
    final raw = await _channel.invokeMethod<String>('habitatReset') ?? '{}';
    return decodeHabitatJson(raw)['success'] == true;
  }
}
