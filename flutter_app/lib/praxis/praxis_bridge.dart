// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Dart wrapper around the SAME Kotlin MethodChannel AuroraBridge uses
// (org.aurora.app/bridge) -- a second static const MethodChannel with the
// same name is a supported Flutter pattern, not a second channel, exactly as
// HabitatBridge does it.
//
// Every call is a thin pass-through to aurora_bridge.py's praxis trio
// (get_praxis_status / pause_praxis / resume_praxis).  Three methods and no
// more, deliberately: Flutter renders and switches, it never owns
// developmental meaning.  There is no method here that could send Aurora a
// situation, read what she concluded, or describe how she is doing -- Praxis
// has no notion of her doing well, so there is nothing of the kind to fetch.
import 'dart:convert';
import 'package:flutter/services.dart';

class PraxisStatus {
  final String status;
  final bool online;
  final bool paused;
  final bool threadAlive;
  final String endpoint;
  final String episodeId;
  final int situationsWitnessed;
  final int pressureInjections;
  final int sedimentDeposits;
  final int contractBreaches;
  final String lastError;

  const PraxisStatus({
    required this.status,
    this.online = false,
    this.paused = false,
    this.threadAlive = false,
    this.endpoint = '',
    this.episodeId = '',
    this.situationsWitnessed = 0,
    this.pressureInjections = 0,
    this.sedimentDeposits = 0,
    this.contractBreaches = 0,
    this.lastError = '',
  });

  static const unavailable = PraxisStatus(status: 'not_initialized');

  factory PraxisStatus.fromJson(Map<String, dynamic> json) {
    int asInt(Object? v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
    return PraxisStatus(
      status: (json['status'] as String?) ?? 'not_initialized',
      online: json['online'] == true,
      paused: json['paused'] == true,
      threadAlive: json['thread_alive'] == true,
      endpoint: (json['endpoint'] as String?) ?? '',
      episodeId: (json['episode_id'] as String?) ?? '',
      situationsWitnessed: asInt(json['situations_witnessed']),
      pressureInjections: asInt(json['pressure_injections']),
      sedimentDeposits: asInt(json['sediment_deposits']),
      contractBreaches: asInt(json['contract_breaches']),
      lastError: (json['last_error'] as String?) ?? '',
    );
  }

  bool get available => status != 'not_initialized' && status != 'error';
}

class PraxisBridge {
  static const _channel = MethodChannel('org.aurora.app/bridge');

  static PraxisStatus _decode(String? raw) {
    try {
      final decoded = jsonDecode(raw ?? '{}');
      if (decoded is Map<String, dynamic>) return PraxisStatus.fromJson(decoded);
    } catch (_) {}
    return PraxisStatus.unavailable;
  }

  static Future<PraxisStatus> status() async =>
      _decode(await _channel.invokeMethod<String>('getPraxisStatus'));

  static Future<PraxisStatus> pause() async =>
      _decode(await _channel.invokeMethod<String>('pausePraxis'));

  static Future<PraxisStatus> resume() async =>
      _decode(await _channel.invokeMethod<String>('resumePraxis'));
}
