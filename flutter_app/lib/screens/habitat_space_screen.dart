// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Space: shared manipulable world (spec section 3.2). Both Aurora and
// the human can affect what's here -- this screen carries no notion of
// what Space is FOR (not a drawing app, not a game); it is only the
// territory="space" view onto the one shared Habitat substrate.
//
// Surface restructure 6: on the surface Space opens straight to the
// canvas (the header is a small floating label, not a bar), and the
// canvas draws at a lighter pace while her field is held. The pace is
// this screen's own reading of get_field_status; it never changes what
// she does here. While Space is out of sight it asks her nothing.
import 'dart:async';

import 'package:flutter/material.dart';
import '../aurora_bridge.dart';
import '../habitat/habitat_gesture_layer.dart';
import '../widgets/ui_diagnostics.dart';

const _bg = Color(0xFF0D0D0F);
const _border = Color(0xFF1E1E2E);
const _panel = Color(0xFF111118);
const _purple = Color(0xFFA020F0);
const _textDim = Color(0xFF64748B);

class SpaceScreen extends StatefulWidget {
  const SpaceScreen({super.key});

  @override
  State<SpaceScreen> createState() => _SpaceScreenState();
}

class _SpaceScreenState extends State<SpaceScreen> {
  Timer? _fieldTimer;

  bool _shown() => AuroraBridge.isTabShown(AuroraBridge.tabSpace);

  @override
  void initState() {
    super.initState();
    // Her field is read every 6 s while Space is on screen, so the
    // canvas knows when to draw lighter.
    _fieldTimer = Timer.periodic(const Duration(seconds: 6), (_) => _readField());
  }

  Future<void> _readField() async {
    if (!_shown()) return;
    try {
      await AuroraBridge.getFieldStatus();
    } catch (e, st) {
      UiDiagnostics.report('space field read', e, st);
    }
  }

  @override
  void dispose() {
    _fieldTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      body: SafeArea(
        child: Stack(children: [
          Positioned.fill(
            child: HabitatInteractiveView(
              territory: 'space',
              humanCanCreate: true,
              isShown: _shown,
              isBusy: () => AuroraBridge.fieldBusy.value,
            ),
          ),
          Positioned(
            top: 8,
            right: 10,
            child: IgnorePointer(
              child: ValueListenableBuilder<bool>(
                valueListenable: AuroraBridge.fieldBusy,
                builder: (context, busy, _) => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(
                    color: _panel.withOpacity(0.85),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: _border),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.public, color: _purple, size: 13),
                    const SizedBox(width: 5),
                    Text(busy ? 'Space · shared · her field is busy' : 'Space · shared',
                        style: const TextStyle(color: _textDim, fontSize: 11)),
                  ]),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
