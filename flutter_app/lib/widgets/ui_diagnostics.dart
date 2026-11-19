// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// ui_diagnostics.dart -- when something in the app fails, it says so on
// screen (Sir, 2026-11-19: "proper error or diag in the ui when something
// fails so I can screen shot it").
//
// Every failure the app can catch lands here: uncaught Flutter and Dart
// errors, a fault in her face while it draws or moves, a native error from
// the overlay line or her voice reader, and a bridge call that answers
// with an error.  A red panel at the top of the screen shows where it
// happened, what it was, the first lines of the stack and when, in text
// that can be selected and screenshotted.  Nothing is hidden in a log.

import 'dart:async';
import 'dart:ui' show PlatformDispatcher;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

class UiFault {
  final String where;
  final String error;
  final String stack;
  final DateTime at;
  int count;

  UiFault(this.where, this.error, this.stack, this.at) : count = 1;
}

class UiDiagnostics {
  UiDiagnostics._();

  static const int _keep = 12;
  static final ValueNotifier<List<UiFault>> faults = ValueNotifier<List<UiFault>>(const []);
  static bool _installed = false;

  /// Hook Flutter's and Dart's uncaught-error handlers.  The earlier
  /// handlers still run, so nothing else changes.
  static void install() {
    if (_installed) return;
    _installed = true;
    final previousFlutter = FlutterError.onError;
    FlutterError.onError = (FlutterErrorDetails details) {
      report(details.library ?? 'flutter', details.exception, details.stack);
      if (previousFlutter != null) previousFlutter(details);
    };
    final previousPlatform = PlatformDispatcher.instance.onError;
    PlatformDispatcher.instance.onError = (Object error, StackTrace stack) {
      report('app', error, stack);
      return previousPlatform?.call(error, stack) ?? true;
    };
  }

  /// Record a failure.  Safe to call from anywhere, including while a frame
  /// is being drawn: the panel updates after the frame.
  static void report(String where, Object error, [StackTrace? stack]) {
    final text = error.toString();
    final lines = (stack?.toString() ?? '')
        .split('\n')
        .where((l) => l.trim().isNotEmpty)
        .take(8)
        .join('\n');
    void apply() {
      final list = List<UiFault>.of(faults.value);
      final same = list.where((f) => f.where == where && f.error == text);
      if (same.isNotEmpty) {
        // The same fault repeating (a frame that fails every frame) is one
        // entry with a count, so the panel stays readable.
        same.first.count++;
        faults.value = List<UiFault>.of(list);
        return;
      }
      list.insert(0, UiFault(where, text, lines, DateTime.now()));
      if (list.length > _keep) list.removeRange(_keep, list.length);
      faults.value = list;
    }

    final phase = SchedulerBinding.instance.schedulerPhase;
    if (phase == SchedulerPhase.persistentCallbacks || phase == SchedulerPhase.midFrameMicrotasks) {
      SchedulerBinding.instance.addPostFrameCallback((_) => apply());
    } else {
      scheduleMicrotask(apply);
    }
  }

  static void clear() => faults.value = const [];
}

/// Shows the fault panel over whatever is on screen.  Put it around the
/// app once (MaterialApp.builder).  The panel has its own Overlay, because
/// it sits above the app's Navigator and its selectable text and buttons
/// need one; where there is no fault, touches pass straight through.
class UiDiagnosticsOverlay extends StatefulWidget {
  final Widget child;
  const UiDiagnosticsOverlay({super.key, required this.child});

  @override
  State<UiDiagnosticsOverlay> createState() => _UiDiagnosticsOverlayState();
}

class _UiDiagnosticsOverlayState extends State<UiDiagnosticsOverlay> {
  late final OverlayEntry _entry = OverlayEntry(
    builder: (context) => ValueListenableBuilder<List<UiFault>>(
      valueListenable: UiDiagnostics.faults,
      builder: (context, list, _) {
        if (list.isEmpty) return const SizedBox.shrink();
        return Align(
          alignment: Alignment.topCenter,
          child: Padding(
            padding: EdgeInsets.fromLTRB(8, MediaQuery.of(context).padding.top + 8, 8, 0),
            child: _FaultPanel(faults: list),
          ),
        );
      },
    ),
  );

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        widget.child,
        Positioned.fill(child: Overlay(initialEntries: [_entry])),
      ],
    );
  }
}

class _FaultPanel extends StatefulWidget {
  final List<UiFault> faults;
  const _FaultPanel({required this.faults});

  @override
  State<_FaultPanel> createState() => _FaultPanelState();
}

class _FaultPanelState extends State<_FaultPanel> {
  bool _expanded = true;

  String _time(DateTime t) =>
      '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}:${t.second.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final faults = widget.faults;
    return Material(
      color: const Color(0xEE3A0B12),
      borderRadius: BorderRadius.circular(10),
      elevation: 6,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.55),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const Icon(Icons.error_outline, color: Color(0xFFFF8A8A), size: 18),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      faults.length == 1 ? 'Something failed' : '${faults.length} things failed',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                    ),
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    icon: Icon(_expanded ? Icons.expand_less : Icons.expand_more, color: Colors.white70),
                    onPressed: () => setState(() => _expanded = !_expanded),
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    icon: const Icon(Icons.close, color: Colors.white70),
                    tooltip: 'Clear',
                    onPressed: UiDiagnostics.clear,
                  ),
                ],
              ),
              if (_expanded)
                Flexible(
                  child: SingleChildScrollView(
                    child: SelectableText.rich(
                      TextSpan(
                        children: [
                          for (final f in faults) ...[
                            TextSpan(
                              text: '${_time(f.at)}  ${f.where}${f.count > 1 ? '  (x${f.count})' : ''}\n',
                              style: const TextStyle(color: Color(0xFFFFC2C2), fontWeight: FontWeight.w600, fontSize: 12),
                            ),
                            TextSpan(
                              text: '${f.error}\n',
                              style: const TextStyle(color: Colors.white, fontSize: 12),
                            ),
                            if (f.stack.isNotEmpty)
                              TextSpan(
                                text: '${f.stack}\n',
                                style: const TextStyle(color: Colors.white60, fontSize: 10, fontFamily: 'monospace'),
                              ),
                            const TextSpan(text: '\n'),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
