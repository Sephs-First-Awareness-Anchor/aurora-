// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Self: Aurora-owned persistent territory (spec section 3.3). The
// human may not create here (aurora_habitat.py's own permission law
// rejects it) and may not modify what Aurora hasn't explicitly
// permitted -- humanCanCreate: false and the toolbar's own
// modifiable_by_human check are the ONLY special-casing this screen
// does; every actual boundary decision lives in HabitatRuntime, not
// here (Rule 10: ownership must be technically real, not decorative).
//
// Surface restructure 6: on the surface Self is her room, the place she
// lives in when she isn't talking. The floor is still the Self habitat
// territory. Above it, a small strip shows only what her own room state
// recorded (get_room_state: her activity, notes, messages and the
// intentions she queued) and where her study runs (get_field_status's
// growth block). Nothing here is animated by script and nothing is
// inferred: when her room recorded nothing, the strip says so. The
// phone keeps no record of which room she is in, so none is shown.
//
// Sir's old navigation chips became one small "Visit" control. It asks
// through provide_room_command; she perceives the ask and the choice of
// where she goes stays hers.
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import '../aurora_bridge.dart';
import '../habitat/habitat_gesture_layer.dart';
import '../widgets/ui_diagnostics.dart';

const _bg = Color(0xFF0D0D0F);
const _panel = Color(0xFF111118);
const _border = Color(0xFF1E1E2E);
const _purple = Color(0xFFA020F0);
const _green = Color(0xFF4ADE80);
const _cyan = Color(0xFF06B6D4);
const _amber = Color(0xFFF59E0B);
const _text = Color(0xFFE2E8F0);
const _textDim = Color(0xFF64748B);

const _rooms = [
  'Self', 'Awareness', 'Mind', 'Memory', 'Health', 'Energy',
  'Experiments', 'Growth', 'Response', 'Notes', 'Poedex',
];

class SelfScreen extends StatefulWidget {
  const SelfScreen({super.key});

  @override
  State<SelfScreen> createState() => _SelfScreenState();
}

class _SelfScreenState extends State<SelfScreen> {
  Timer? _timer;
  bool _open = true;
  bool _read = false;
  List<dynamic> _notes = [];
  List<dynamic> _messages = [];
  List<dynamic> _activity = [];
  List<dynamic> _intentions = [];
  Map<String, dynamic> _growth = {};

  bool _shown() => AuroraBridge.isTabShown(AuroraBridge.tabSelf);

  @override
  void initState() {
    super.initState();
    AuroraBridge.visibleTab.addListener(_onTabChanged);
    _timer = Timer.periodic(const Duration(seconds: 6), (_) => _refresh());
  }

  void _onTabChanged() {
    if (_shown()) _refresh();
  }

  @override
  void dispose() {
    AuroraBridge.visibleTab.removeListener(_onTabChanged);
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    if (!_shown()) return;
    try {
      final roomRaw = await AuroraBridge.getRoomState();
      final decoded = jsonDecode(roomRaw['raw'] as String? ?? '{}');
      final room = decoded is Map ? Map<String, dynamic>.from(decoded) : <String, dynamic>{};
      final field = await AuroraBridge.getFieldStatus();
      final roomState = room['room_state'];
      final pending = roomState is Map ? roomState['pending'] : null;
      if (!mounted) return;
      setState(() {
        _notes = (room['notes'] as List<dynamic>?) ?? [];
        _messages = (room['messages'] as List<dynamic>?) ?? [];
        _activity = (room['activity'] as List<dynamic>?) ?? [];
        _intentions = pending is List ? pending : [];
        final g = field['growth'];
        _growth = g is Map ? Map<String, dynamic>.from(g) : {};
        _read = true;
      });
    } catch (e, st) {
      UiDiagnostics.report('her room', e, st);
    }
  }

  Future<void> _visit(String room) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await AuroraBridge.provideRoomCommand(jsonEncode({'navigate': room}));
      messenger.showSnackBar(SnackBar(
        content: Text('Asked to visit $room with her. Where she goes is hers.'),
        duration: const Duration(seconds: 3),
      ));
    } catch (e, st) {
      UiDiagnostics.report('room visit', e, st);
    }
  }

  // Where her study runs, from her bridge's own growth status.
  (String, Color) _studyLine() {
    if (_growth.isEmpty) return ('', _textDim);
    if (_growth['paired_surface'] == true) {
      return ('Her study and experiments run at home', _cyan);
    }
    if (_growth['stepping_aside'] == true) {
      return ('Her study steps aside while you talk', _textDim);
    }
    if (_growth['waits_for_charging'] == true) {
      return ('Her study waits for the charger', _amber);
    }
    if (_growth['control_on'] == true && _growth['charging'] == null) {
      return ('Her study runs here (charger not read yet)', _textDim);
    }
    return ('Her study runs here', _green);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      body: SafeArea(
        child: Column(children: [
          _buildHeader(),
          if (_open) _buildRoomStrip(context),
          // humanCanCreate: false -- Self only ever gets new entities from
          // Aurora's own actions or from something offered/transferred in
          // from Space (spec section 3.3: "Aurora controls what enters").
          Expanded(
            child: HabitatInteractiveView(
              territory: 'self',
              humanCanCreate: false,
              isShown: _shown,
              isBusy: () => AuroraBridge.fieldBusy.value,
            ),
          ),
        ]),
      ),
    );
  }

  Widget _buildHeader() => Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(16, 6, 4, 6),
        decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: _border))),
        child: Row(children: [
          const Icon(Icons.self_improvement, color: _purple, size: 20),
          const SizedBox(width: 8),
          const Text('Self', style: TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w600)),
          const SizedBox(width: 8),
          const Text('her room', style: TextStyle(color: _textDim, fontSize: 12)),
          const Spacer(),
          PopupMenuButton<String>(
            tooltip: 'Visit',
            color: _panel,
            onSelected: _visit,
            itemBuilder: (_) => [
              for (final r in _rooms)
                PopupMenuItem<String>(
                  value: r,
                  child: Text(r, style: const TextStyle(color: _text, fontSize: 13)),
                ),
            ],
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(Icons.door_front_door_outlined, color: _textDim, size: 16),
                SizedBox(width: 4),
                Text('Visit', style: TextStyle(color: _textDim, fontSize: 12)),
              ]),
            ),
          ),
          IconButton(
            tooltip: _open ? 'Hide her room' : 'Show her room',
            icon: Icon(_open ? Icons.expand_less : Icons.expand_more, color: _textDim, size: 20),
            onPressed: () => setState(() => _open = !_open),
          ),
        ]),
      );

  Widget _buildRoomStrip(BuildContext context) {
    final (study, studyColor) = _studyLine();
    final nothing = _notes.isEmpty && _messages.isEmpty && _activity.isEmpty && _intentions.isEmpty;
    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.34),
      child: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          color: _panel,
          border: Border(bottom: BorderSide(color: _border)),
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (study.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text(study, style: TextStyle(color: studyColor, fontSize: 12, fontWeight: FontWeight.w600)),
              ),
            if (!_read)
              const Text('Reading her room…', style: TextStyle(color: _textDim, fontSize: 11))
            else if (nothing)
              const Text('Her room has recorded nothing yet.', style: TextStyle(color: _textDim, fontSize: 11)),
            if (_intentions.isNotEmpty) ...[
              _label(Icons.flag_outlined, 'WHAT SHE QUEUED'),
              Text(
                _intentions
                    .whereType<Map>()
                    .map((c) => '${c['type'] ?? ''}'.replaceAll('_', ' '))
                    .where((t) => t.isNotEmpty)
                    .join(' · '),
                style: const TextStyle(color: _text, fontSize: 11),
              ),
            ],
            if (_activity.isNotEmpty) ...[
              _label(Icons.history, 'WHAT SHE DID'),
              for (final a in _activity.take(5).whereType<Map>())
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 1.5),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${a['ts_str'] ?? ''}', style: const TextStyle(color: _textDim, fontSize: 10)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text('${a['action'] ?? ''}: ${a['detail'] ?? ''}',
                          maxLines: 2, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: _text, fontSize: 11)),
                    ),
                  ]),
                ),
            ],
            if (_notes.isNotEmpty) ...[
              _label(Icons.sticky_note_2_outlined, 'HER NOTES'),
              for (final n in _notes.take(3).whereType<Map>())
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text(
                    '${n['ts_str'] ?? ''}  ${n['content'] ?? ''}',
                    maxLines: 3, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: _text, fontSize: 11, height: 1.35),
                  ),
                ),
            ],
            if (_messages.isNotEmpty) ...[
              _label(Icons.mail_outline, 'LEFT FOR YOU'),
              for (final m in _messages.take(2).whereType<Map>())
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text('${m['body'] ?? ''}',
                      maxLines: 3, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: _text, fontSize: 11, height: 1.35)),
                ),
            ],
          ]),
        ),
      ),
    );
  }

  Widget _label(IconData icon, String text) => Padding(
        padding: const EdgeInsets.only(top: 8, bottom: 3),
        child: Row(children: [
          Icon(icon, size: 12, color: _textDim),
          const SizedBox(width: 6),
          Text(text, style: const TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
        ]),
      );
}
