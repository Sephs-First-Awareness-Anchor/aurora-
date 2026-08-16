// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Self: Aurora-owned persistent territory (spec section 3.3). The
// human may not create here (aurora_habitat.py's own permission law
// rejects it) and may not modify what Aurora hasn't explicitly
// permitted -- humanCanCreate: false and the toolbar's own
// modifiable_by_human check are the ONLY special-casing this screen
// does; every actual boundary decision lives in HabitatRuntime, not
// here (Rule 10: ownership must be technically real, not decorative).
import 'package:flutter/material.dart';
import '../habitat/habitat_gesture_layer.dart';

const _bg = Color(0xFF0D0D0F);
const _border = Color(0xFF1E1E2E);
const _purple = Color(0xFFA020F0);
const _text = Color(0xFFE2E8F0);
const _textDim = Color(0xFF64748B);

class SelfScreen extends StatelessWidget {
  const SelfScreen({super.key});

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
              const Icon(Icons.self_improvement, color: _purple, size: 20),
              const SizedBox(width: 8),
              const Text('Self', style: TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w600)),
              const Spacer(),
              Text("Aurora's own", style: TextStyle(color: _textDim, fontSize: 12)),
            ]),
          ),
          // humanCanCreate: false -- Self only ever gets new entities from
          // Aurora's own actions or from something offered/transferred in
          // from Space (spec section 3.3: "Aurora controls what enters").
          const Expanded(
            child: HabitatInteractiveView(territory: 'self', humanCanCreate: false),
          ),
        ]),
      ),
    );
  }
}
