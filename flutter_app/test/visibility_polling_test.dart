import 'dart:async';
import 'dart:convert';

import 'package:aurora_app/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('only the visible tab polls and a slow Hub refresh cannot overlap',
      (tester) async {
    final calls = <MethodCall>[];
    final slowStats = Completer<String>();
    final messenger = tester.binding.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(
        const MethodChannel('org.aurora.app/events'), (_) async => null);
    messenger.setMockMethodCallHandler(
      const MethodChannel('org.aurora.app/bridge'),
      (call) async {
        calls.add(call);
        return switch (call.method) {
          'getCognitiveStats' => await slowStats.future,
          'habitatGetHistory' => '[]',
          'getLiveTurnDiagnostics' => '[]',
          'hasScreenObserverPermission' || 'consumeOverlayTap' => false,
          _ => '{}',
        };
      },
    );

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpWidget(const AuroraApp());
    await tester.pump(const Duration(seconds: 12));
    expect(calls.where((call) => call.method == 'habitatGetState'), isEmpty);
    expect(calls.where((call) => call.method == 'getCognitiveStats'), isEmpty);

    final nav = find.byType(NavigationBar);
    await tester.tap(find.descendant(of: nav, matching: find.text('Space')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 3));
    final territoryReads = calls
        .where((call) => call.method == 'habitatGetState')
        .map((call) => jsonDecode(call.arguments['params'] as String)['territory']);
    expect(territoryReads, isNotEmpty);
    expect(territoryReads, everyElement('space'));

    await tester.tap(find.descendant(of: nav, matching: find.text('Hub')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 21));
    expect(calls.where((call) => call.method == 'getCognitiveStats'), hasLength(1));

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pump();
    slowStats.complete('{}');
    await tester.pump(const Duration(seconds: 12));
    expect(calls.where((call) => call.method == 'getRoomState'), isEmpty);

    await tester.pumpWidget(const SizedBox());
  });
}
