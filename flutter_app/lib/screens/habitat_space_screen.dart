// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Space: shared manipulable world (spec section 3.2). Both Aurora and
// the human can affect what's here -- this screen carries no notion of
// what Space is FOR (not a drawing app, not a game); it is only the
// territory="space" view onto the one shared Habitat substrate.
import 'package:flutter/material.dart';
import '../habitat/habitat_gesture_layer.dart';

const _bg = Color(0xFF0D0D0F);
const _border = Color(0xFF1E1E2E);
const _purple = Color(0xFFA020F0);
const _text = Color(0xFFE2E8F0);
const _textDim = Color(0xFF64748B);

class SpaceScreen extends StatelessWidget {
  const SpaceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      body: SafeArea(
        child: Column(children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
            decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: _border))),
            child: Row(children: [
              const Icon(Icons.public, color: _purple, size: 20),
              const SizedBox(width: 8),
              const Text('Space', style: TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w600)),
              const Spacer(),
              Text('shared', style: TextStyle(color: _textDim, fontSize: 12)),
            ]),
          ),
          const Expanded(
            child: HabitatInteractiveView(territory: 'space', humanCanCreate: true),
          ),
        ]),
      ),
    );
  }
}
