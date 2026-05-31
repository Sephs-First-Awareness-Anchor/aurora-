import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../aurora_bridge.dart';

// ── Palette (matches app dark theme) ──────────────────────────────────────────
const _bg        = Color(0xFF0D0D0F);
const _panel     = Color(0xFF111118);
const _border    = Color(0xFF1E1E2E);
const _purple    = Color(0xFFA020F0);
const _purpleDim = Color(0xFF6B21A8);
const _cyan      = Color(0xFF06B6D4);
const _green     = Color(0xFF4ADE80);
const _amber     = Color(0xFFF59E0B);
const _red       = Color(0xFFEF4444);
const _text      = Color(0xFFE2E8F0);
const _textDim   = Color(0xFF64748B);

const _axisColors = {
  'X': Color(0xFF60A5FA),
  'T': Color(0xFFF59E0B),
  'N': Color(0xFF4ADE80),
  'B': Color(0xFFC084FC),
  'A': Color(0xFFF87171),
};
const _axisLabels = {
  'X': 'Existence',
  'T': 'Temporal',
  'N': 'Energy',
  'B': 'Boundary',
  'A': 'Agency',
};

class HubScreen extends StatefulWidget {
  const HubScreen({super.key});
  @override
  State<HubScreen> createState() => _HubScreenState();
}

class _HubScreenState extends State<HubScreen> {
  Map<String, dynamic> _stats    = {};
  Map<String, dynamic> _room     = {};
  List<dynamic>        _notes    = [];
  List<dynamic>        _messages = [];
  List<dynamic>        _activity = [];
  bool _loading = true;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _refresh();
    _timer = Timer.periodic(const Duration(seconds: 4), (_) => _refresh());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final stats = await AuroraBridge.getCognitiveStats();
      final roomRaw = await AuroraBridge.getRoomState();
      final roomJson = roomRaw['raw'] as String? ?? '{}';
      final room = jsonDecode(roomJson) as Map<String, dynamic>;
      if (mounted) {
        setState(() {
          _stats    = stats;
          _room     = room;
          _notes    = (room['notes']    as List<dynamic>?) ?? [];
          _messages = (room['messages'] as List<dynamic>?) ?? [];
          _activity = (room['activity'] as List<dynamic>?) ?? [];
          _loading  = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  // ── UI helpers ──────────────────────────────────────────────────────────────

  Widget _card({required Widget child, EdgeInsets? padding}) => Container(
    margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
    padding: padding ?? const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: _panel,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: _border),
    ),
    child: child,
  );

  Widget _sectionTitle(String t, {Color color = _purple}) => Padding(
    padding: const EdgeInsets.fromLTRB(12, 14, 12, 4),
    child: Text(t, style: TextStyle(
      color: color, fontSize: 11, fontWeight: FontWeight.w700,
      letterSpacing: 1.4,
    )),
  );

  Widget _statRow(String label, String value, {Color valueColor = _text}) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Row(children: [
      Text(label, style: const TextStyle(color: _textDim, fontSize: 12)),
      const Spacer(),
      Text(value, style: TextStyle(color: valueColor, fontSize: 12, fontWeight: FontWeight.w600)),
    ]),
  );

  Widget _axisBar(String axis, double value) {
    final color = _axisColors[axis] ?? _purple;
    final label = _axisLabels[axis] ?? axis;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 8, height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Text('$axis  $label', style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
          const Spacer(),
          Text(value.toStringAsFixed(3), style: TextStyle(color: color, fontSize: 11)),
        ]),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: LinearProgressIndicator(
            value: value.clamp(0.0, 1.0),
            minHeight: 5,
            backgroundColor: _border,
            valueColor: AlwaysStoppedAnimation(color),
          ),
        ),
      ]),
    );
  }

  Color _nCostColor(double cost) {
    if (cost >= 0.85) return _red;
    if (cost >= 0.65) return _amber;
    return _green;
  }

  // ── Build ───────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: _purple))
            : RefreshIndicator(
                color: _purple,
                backgroundColor: _panel,
                onRefresh: _refresh,
                child: ListView(children: [
                  _buildHeader(),
                  _buildAxisPanel(),
                  _buildCognitivePanel(),
                  _buildEvolutionPanel(),
                  _buildRoomPanel(),
                  const SizedBox(height: 24),
                ]),
              ),
      ),
    );
  }

  Widget _buildHeader() {
    final training = _stats['training_active'] == true;
    final turnCount = _stats['turn_count'] as int? ?? 0;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Row(children: [
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aurora Hub', style: TextStyle(
            color: _text, fontSize: 20, fontWeight: FontWeight.w700)),
          Text('Turn $turnCount  •  ${training ? "Training active" : "Live"}',
            style: const TextStyle(color: _textDim, fontSize: 12)),
        ]),
        const Spacer(),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: training ? _amber.withOpacity(0.15) : _green.withOpacity(0.12),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: training ? _amber : _green, width: 0.8),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.circle, size: 7, color: training ? _amber : _green),
            const SizedBox(width: 5),
            Text(training ? 'Training' : 'Live',
              style: TextStyle(color: training ? _amber : _green, fontSize: 11,
                fontWeight: FontWeight.w600)),
          ]),
        ),
      ]),
    );
  }

  Widget _buildAxisPanel() {
    final axes = ['X', 'T', 'N', 'B', 'A'];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('CONSTRAINT AXES', color: _cyan),
      _card(child: Column(children: [
        for (final ax in axes)
          _axisBar(ax, (_stats[ax] as double?) ?? 0.10),
      ])),
    ]);
  }

  Widget _buildCognitivePanel() {
    final lsa    = _stats['lsa_paths']   as int?    ?? 0;
    final nCost  = _stats['avg_n_cost']  as double? ?? 1.0;
    final sedi   = _stats['sedimemory_depth'] as int? ?? 0;
    final crMat  = _stats['crystal_maturity']  as double? ?? 0.0;
    final crN    = _stats['crystal_nodes']     as int?    ?? 0;
    final nonc   = _stats['noncomp_loaded']    as int?    ?? 0;
    final noncD  = _stats['noncomp_diagonal_live'] as int? ?? 0;
    final uIdx   = _stats['understanding_index'] as double? ?? 0.0;
    final coh    = _stats['coherence_index']     as double? ?? 0.0;
    final grd    = _stats['grounding_index']     as double? ?? 0.0;
    final tpc    = _stats['topic_tracking']      as double? ?? 0.0;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('COGNITIVE FIELD'),
      _card(child: Column(children: [
        Row(children: [
          Expanded(child: _miniStat('LSA Paths', '$lsa', _purple)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Avg N-Cost', nCost.toStringAsFixed(3),
              _nCostColor(nCost))),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('SediMemory', '$sedi frags', _cyan)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Crystal', '${(crMat * 100).toStringAsFixed(0)}% / $crN nodes', _green)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Noncomp', '$nonc loaded', _textDim)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Diagonal Live', '$noncD active', _purpleDim)),
        ]),
        const Divider(color: _border, height: 20),
        _statRow('Understanding', uIdx.toStringAsFixed(3), valueColor: _green),
        _statRow('Coherence',     coh.toStringAsFixed(3),  valueColor: _cyan),
        _statRow('Grounding',     grd.toStringAsFixed(3),  valueColor: _amber),
        _statRow('Topic Tracking',tpc.toStringAsFixed(3),  valueColor: _purple),
      ])),
    ]);
  }

  Widget _buildEvolutionPanel() {
    final evoC  = _stats['evo_cycles']    as int?    ?? 0;
    final evoS  = _stats['sentence_target'] as int?  ?? 10;
    final fossi = _stats['chamber_fossils'] as int?  ?? 0;
    final avail = _stats['evo_available'] == true;
    final train = _stats['training_active'] == true;
    final tTurn = _stats['training_turn']   as int?  ?? 0;
    final tTot  = _stats['training_total_secs'] as int? ?? 0;
    final tElap = _stats['training_elapsed']    as int? ?? 0;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('EMERGENCE & EVOLUTION', color: _green),
      _card(child: Column(children: [
        Row(children: [
          Expanded(child: _miniStat('Evo Cycles', '$evoC', _green)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Sentence Target', '$evoS words',
              avail ? _text : _textDim)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Chamber Fossils', '$fossi', _amber)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Live Evo', 'every 15 turns', _cyan)),
        ]),
        if (train) ...[
          const Divider(color: _border, height: 20),
          Row(children: [
            const Icon(Icons.play_circle_outline, color: _amber, size: 14),
            const SizedBox(width: 6),
            Text('Training  turn $tTurn',
              style: const TextStyle(color: _amber, fontSize: 12, fontWeight: FontWeight.w600)),
            const Spacer(),
            Text('${_fmt(tElap)} / ${_fmt(tTot)}',
              style: const TextStyle(color: _textDim, fontSize: 11)),
          ]),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: tTot > 0 ? (tElap / tTot).clamp(0.0, 1.0) : 0,
              minHeight: 5,
              backgroundColor: _border,
              valueColor: const AlwaysStoppedAnimation(_amber),
            ),
          ),
        ],
      ])),
    ]);
  }

  Widget _buildRoomPanel() {
    final daemonStatus = _room['daemon_status'] as Map<String, dynamic>? ?? {};
    final heat   = daemonStatus['heat'] as String? ?? '—';
    final epoch  = daemonStatus['epoch'] as int? ?? 0;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('AURORA\'S ROOM', color: _green),
      // Daemon status strip
      if (daemonStatus.isNotEmpty)
        _card(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          child: Row(children: [
            _heatDot(heat),
            const SizedBox(width: 8),
            Text('Daemon  •  epoch $epoch  •  heat $heat',
              style: const TextStyle(color: _textDim, fontSize: 11)),
          ]),
        ),
      // Room notes
      if (_notes.isNotEmpty) ...[
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 2),
          child: Row(children: [
            const Icon(Icons.sticky_note_2_outlined, size: 12, color: _textDim),
            const SizedBox(width: 6),
            const Text('ROOM NOTES', style: TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
          ]),
        ),
        for (final n in _notes.take(3)) _noteCard(n as Map<String, dynamic>),
      ],
      // Room messages
      if (_messages.isNotEmpty) ...[
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 2),
          child: Row(children: [
            const Icon(Icons.mail_outline, size: 12, color: _textDim),
            const SizedBox(width: 6),
            const Text('MESSAGES', style: TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
          ]),
        ),
        for (final m in _messages.take(2)) _msgCard(m as Map<String, dynamic>),
      ],
      // Activity log
      if (_activity.isNotEmpty) ...[
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 2),
          child: Row(children: [
            const Icon(Icons.history, size: 12, color: _textDim),
            const SizedBox(width: 6),
            const Text('ACTIVITY', style: TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
          ]),
        ),
        _card(child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final a in _activity.take(5))
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(children: [
                  Text(a['ts_str'] as String? ?? '', style: const TextStyle(color: _textDim, fontSize: 10)),
                  const SizedBox(width: 8),
                  Expanded(child: Text(
                    '${a['action'] ?? ''}: ${a['detail'] ?? ''}',
                    style: const TextStyle(color: _text, fontSize: 11),
                    overflow: TextOverflow.ellipsis,
                  )),
                ]),
              ),
          ],
        )),
      ],
      // Room command buttons
      _sectionTitle('ROOM NAVIGATION', color: _textDim),
      _card(child: Wrap(spacing: 8, runSpacing: 6, children: [
        for (final tab in ['Self', 'Awareness', 'Mind', 'Memory', 'Health',
                           'Energy', 'Experiments', 'Growth', 'Response', 'Notes', 'Poedex'])
          ActionChip(
            label: Text(tab, style: const TextStyle(fontSize: 11)),
            backgroundColor: _border,
            side: const BorderSide(color: _border),
            labelStyle: const TextStyle(color: _text),
            onPressed: () => _navRoom(tab),
          ),
      ])),
    ]);
  }

  Widget _noteCard(Map<String, dynamic> n) => _card(
    padding: const EdgeInsets.all(10),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: _green.withOpacity(0.12),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(n['type'] as String? ?? 'note',
            style: const TextStyle(color: _green, fontSize: 9, fontWeight: FontWeight.w600)),
        ),
        const SizedBox(width: 8),
        Text(n['ts_str'] as String? ?? '', style: const TextStyle(color: _textDim, fontSize: 10)),
      ]),
      const SizedBox(height: 4),
      Text(n['content'] as String? ?? '',
        style: const TextStyle(color: _text, fontSize: 11, height: 1.4),
        maxLines: 4, overflow: TextOverflow.ellipsis),
    ]),
  );

  Widget _msgCard(Map<String, dynamic> m) => _card(
    padding: const EdgeInsets.all(10),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Icon(Icons.mail_outline, size: 12, color: _cyan),
      const SizedBox(width: 8),
      Expanded(child: Text(m['body'] as String? ?? '',
        style: const TextStyle(color: _text, fontSize: 11, height: 1.4),
        maxLines: 3, overflow: TextOverflow.ellipsis)),
    ]),
  );

  Widget _miniStat(String label, String value, Color color) => Container(
    padding: const EdgeInsets.all(8),
    decoration: BoxDecoration(
      color: color.withOpacity(0.07),
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: color.withOpacity(0.20)),
    ),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label, style: const TextStyle(color: _textDim, fontSize: 9, letterSpacing: 0.8)),
      const SizedBox(height: 2),
      Text(value, style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w700)),
    ]),
  );

  Widget _heatDot(String heat) {
    final color = heat == 'CRITICAL' ? _red
        : heat == 'HIGH'     ? _amber
        : heat == 'ELEVATED' ? _amber
        : _green;
    return Container(width: 8, height: 8,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle));
  }

  String _fmt(int secs) {
    final m = secs ~/ 60; final s = secs % 60;
    return '${m}m ${s.toString().padLeft(2, '0')}s';
  }

  void _navRoom(String tab) {
    AuroraBridge.provideRoomCommand('{"navigate":"$tab"}');
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Sent Aurora to $tab tab', style: const TextStyle(fontSize: 12)),
        backgroundColor: _panel,
        duration: const Duration(seconds: 2),
      ),
    );
  }
}
