import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// The same bridge contract over an Android channel or a local Windows worker.
class PlatformBridge {
  const PlatformBridge();

  static const _android = MethodChannel('org.aurora.app/bridge');
  static const _androidEvents = EventChannel('org.aurora.app/events');
  static final _desktop = _DesktopRuntime();

  static bool get isWindows => defaultTargetPlatform == TargetPlatform.windows;

  static Stream<String> get events => isWindows
      ? _desktop.events
      : _androidEvents.receiveBroadcastStream().map((event) => event.toString());

  Future<T?> invokeMethod<T>(String method, [Map<String, Object?>? args]) =>
      isWindows ? _desktop.invoke<T>(method, args) : _android.invokeMethod<T>(method, args);
}

class _DesktopRuntime {
  late final _events = StreamController<String>.broadcast(onListen: _startForEvents);
  final _pending = <int, Completer<Object?>>{};
  Future<Process>? _starting;
  bool _closed = false;
  bool _bootErrorReported = false;
  int _nextId = 0;

  Stream<String> get events => _events.stream;

  Future<void> _startForEvents() async {
    try {
      await (_starting ??= _start());
    } catch (error) {
      _events.add(jsonEncode({'type': 'error', 'text': error.toString()}));
    }
  }

  Future<Process> _start() async {
    final env = Platform.environment;
    final executableDir = File(Platform.resolvedExecutable).parent.path;
    final python = env['AURORA_DESKTOP_PYTHON'] ?? '$executableDir/runtime/python/python.exe';
    final host = env['AURORA_DESKTOP_HOST'] ??
        '$executableDir/runtime/engine/flutter_app/desktop/aurora_desktop_host.py';
    final localData = env['LOCALAPPDATA'] ?? Directory.systemTemp.path;
    final state = '$localData/Aurora/aurora_state';
    final process = await Process.start(python, ['-I', '-X', 'utf8', '-u', host, state]);
    process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(_receive, onError: (Object error) => _disconnect(error.toString()),
            onDone: () async => _disconnect('Local Aurora stopped (exit ${await process.exitCode}).'));
    process.stderr
        .transform(const Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen((line) { if (kDebugMode) debugPrint(line); });
    unawaited(process.stdin.done.catchError((Object error) {
      _disconnect(error.toString());
    }));
    return process;
  }

  void _receive(String line) {
    Map<String, dynamic> message;
    try {
      message = jsonDecode(line) as Map<String, dynamic>;
    } catch (_) {
      _disconnect('The local Aurora runtime returned an invalid response.');
      return;
    }
    final event = message['event'] as Map<String, dynamic>?;
    if (event != null) {
      if (event['type'] == 'error') _bootErrorReported = true;
      _events.add(jsonEncode(event));
      return;
    }
    final response = _pending.remove(message['id']);
    if (response == null) return;
    final error = message['error'];
    if (error == null) {
      response.complete(message['value']);
    } else {
      response.completeError(PlatformException(code: 'AURORA_RUNTIME', message: '$error'));
    }
  }

  void _disconnect(String reason) {
    if (_closed) return;
    _closed = true;
    if (!_bootErrorReported) _events.add(jsonEncode({'type': 'error', 'text': reason}));
    for (final response in _pending.values) {
      response.completeError(PlatformException(code: 'AURORA_DISCONNECTED', message: reason));
    }
    _pending.clear();
  }

  Future<T?> invoke<T>(String method, Map<String, Object?>? args) async {
    final process = await (_starting ??= _start());
    if (_closed) {
      throw PlatformException(code: 'AURORA_DISCONNECTED', message: 'Restart Aurora to reconnect.');
    }
    final id = ++_nextId;
    final response = Completer<Object?>();
    _pending[id] = response;
    try {
      process.stdin.writeln(jsonEncode({
        'id': id,
        'method': method,
        if (args != null) 'args': args.map((key, value) =>
            MapEntry(key, value is Uint8List ? base64Encode(value) : value)),
      }));
      return await response.future.timeout(const Duration(minutes: 5)) as T?;
    } finally {
      _pending.remove(id);
    }
  }
}
