import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../aurora_bridge.dart';
import '../habitat/habitat_bridge.dart';

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

const _gauntletStageOrder = [
  'ground', 'study', 'curiosity', 'evo_chain',
  'identity', 'voice', 'evo_burst', 'consolidate', 'simulation',
];
const _gauntletStageLabels = {
  'ground':      'Ground Sensory Field',
  'study':       'Study Cycle',
  'curiosity':   'Curiosity Exploration',
  'evo_chain':   'Evo Chain',
  'identity':    'Identity Evolution',
  'voice':       'Voice Evolution',
  'evo_burst':   'Evolutionary Burst',
  'consolidate': 'Consolidation',
  'simulation':  'Simulation Burst',
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

  // Build 774 live turn diagnostics -- on-device visibility into which of
  // the ten Surface/Subsurface states each recent live turn reached
  // (surface_received/processing/expressed, subsurface_active/integrated,
  // suppressed_by_aurora, empty_expression, transport_failure, timeout,
  // late_completion), so a hung or silent turn is diagnosable from the
  // phone itself without a computer/adb.
  List<dynamic> _turnDiagnostics = [];

  // Habitat diagnostics (Aurora Build 712) -- raw counts only, see
  // aurora_habitat.py's HabitatRuntime.integrity_report(): "for us", per
  // spec section 46, never a developmental judgment.
  Map<String, dynamic> _habitatReport = {};
  String? _lastHabitatBackupPath;

  // Gauntlet state
  bool   _gauntletRunning = false;
  String _gauntletStage   = '';
  List<Map<String, dynamic>> _gauntletLog = [];
  Timer? _gauntletTimer;

  @override
  void initState() {
    super.initState();
    _refresh();
    _timer = Timer.periodic(const Duration(seconds: 4), (_) => _refresh());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _gauntletTimer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final stats = await AuroraBridge.getCognitiveStats();
      final roomRaw = await AuroraBridge.getRoomState();
      final roomJson = roomRaw['raw'] as String? ?? '{}';
      final room = jsonDecode(roomJson) as Map<String, dynamic>;
      final habitatReport = await HabitatBridge.integrityReport();
      final turnDiagnostics = await AuroraBridge.getLiveTurnDiagnostics();
      if (mounted) {
        setState(() {
          _stats    = stats;
          _room     = room;
          _notes    = (room['notes']    as List<dynamic>?) ?? [];
          _messages = (room['messages'] as List<dynamic>?) ?? [];
          _activity = (room['activity'] as List<dynamic>?) ?? [];
          _habitatReport = habitatReport;
          _turnDiagnostics = turnDiagnostics;
          _loading  = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _onHabitatBackup() async {
    final result = await HabitatBridge.backup();
    if (result['success'] == true) {
      _lastHabitatBackupPath = result['path'] as String?;
      _showSnack('Habitat backed up');
    } else {
      _showSnack('Habitat backup failed');
    }
  }

  Future<void> _onHabitatRestoreLast() async {
    if (_lastHabitatBackupPath == null) {
      _showSnack('No backup taken this session yet');
      return;
    }
    final ok = await HabitatBridge.restore(_lastHabitatBackupPath!);
    _showSnack(ok ? 'Habitat restored from backup' : 'Restore failed');
    _refresh();
  }

  Future<void> _onHabitatIsolateCorrupt() async {
    final isolated = await HabitatBridge.isolateCorrupt();
    _showSnack(isolated.isEmpty ? 'No corrupt entities found' : '${isolated.length} entity(ies) isolated');
    _refresh();
  }

  Future<void> _onHabitatReset() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: _panel,
        title: const Text('Reset Habitat?', style: TextStyle(color: _text)),
        content: const Text(
          'This permanently clears all Space and Self entities and history. This cannot be undone.',
          style: TextStyle(color: _textDim),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Reset', style: TextStyle(color: _red)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await HabitatBridge.reset();
    _showSnack('Habitat reset');
    _refresh();
  }

  Future<void> _refreshGauntlet() async {
    try {
      final raw = await AuroraBridge.getGauntletStatus();
      final data = jsonDecode(raw) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _gauntletRunning = data['running'] as bool? ?? false;
        _gauntletStage   = data['stage']   as String? ?? '';
        _gauntletLog     = ((data['log'] as List<dynamic>?) ?? [])
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
      });
      if (!_gauntletRunning) {
        _gauntletTimer?.cancel();
        _gauntletTimer = null;
      }
    } catch (_) {}
  }

  void _startGauntletPolling() {
    _gauntletTimer?.cancel();
    _gauntletTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) => _refreshGauntlet(),
    );
  }

  Future<void> _onStartGauntlet() async {
    final result = await AuroraBridge.startGauntlet();
    if (result['status'] == 'started') {
      setState(() { _gauntletRunning = true; _gauntletStage = 'ground'; _gauntletLog = []; });
      _startGauntletPolling();
    } else if (result['status'] == 'already_running') {
      _startGauntletPolling();
    }
    _showSnack(result['status'] == 'started' ? 'Gauntlet started' : 'Already running');
  }

  Future<void> _onStopGauntlet() async {
    await AuroraBridge.stopGauntlet();
    _showSnack('Gauntlet stopping after current stage…');
  }

  Future<void> _onCuriosityCycle() async {
    _showSnack('Running curiosity cycle…');
    final raw = await AuroraBridge.triggerCuriosityCycle(n: 5);
    try {
      final d = jsonDecode(raw) as Map<String, dynamic>;
      _showSnack(d['status'] as String? ?? 'done');
    } catch (_) {
      _showSnack('Curiosity cycle done');
    }
  }

  Future<void> _onEvoCycle() async {
    _showSnack('Running evo cycle…');
    final raw = await AuroraBridge.triggerEvoCycle(ticks: 20);
    try {
      final d = jsonDecode(raw) as Map<String, dynamic>;
      _showSnack(d['status'] as String? ?? 'done');
    } catch (_) {
      _showSnack('Evo cycle done');
    }
  }

  void _showSnack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg, style: const TextStyle(fontSize: 12)),
      backgroundColor: _panel,
      duration: const Duration(seconds: 2),
    ));
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

  // ── Build 773 (Canonical Hub Telemetry) ─────────────────────────────────
  // get_cognitive_stats() now omits a key entirely when its subsystem is
  // unavailable, instead of substituting a fake default (e.g. avg_n_cost
  // used to default to 1.0, understanding_index to 0.0) -- so "the key is
  // missing" and "the key was measured as zero" must render differently.
  // These three helpers are the one place that distinction is made;
  // every stat-reading call site below uses them instead of `?? default`.
  bool _statAvailable(String key) => _stats.containsKey(key) && _stats[key] != null;

  String _intStat(String key) => _statAvailable(key) ? '${_stats[key]}' : '—';

  String _dblStat(String key, {int decimals = 3}) {
    if (!_statAvailable(key)) return '—';
    final v = _stats[key];
    final d = (v is num) ? v.toDouble() : (double.tryParse('$v') ?? 0.0);
    return d.toStringAsFixed(decimals);
  }

  double? _dblOrNull(String key) {
    final v = _stats[key];
    return (v is num) ? v.toDouble() : null;
  }

  /// A stat's normal color when measured, dimmed to _textDim when the key
  /// never arrived -- same "missing looks visibly different" rule applied
  /// to color, not just text.
  Color _availColor(String key, Color color) => _statAvailable(key) ? color : _textDim;

  // Build 773 (Canonical Hub Telemetry): value is nullable -- the identity
  // field genuinely not having reported this axis yet must render as "—"
  // and an empty bar, never as a measurement-shaped 0.10 (the old
  // fallback). A real reading of 0.0 still renders as 0.000 with an empty
  // bar, which looks identical -- that's correct, since a real zero and
  // an empty bar are the same picture; only the LABEL distinguishes
  // "measured zero" from "not measured", same as every other stat here.
  Widget _axisBar(String axis, double? value) {
    final color = _axisColors[axis] ?? _purple;
    final label = _axisLabels[axis] ?? axis;
    final available = value != null;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 8, height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 6),
          Text('$axis  $label', style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w600)),
          const Spacer(),
          Text(available ? value.toStringAsFixed(3) : '—',
            style: TextStyle(color: available ? color : _textDim, fontSize: 11)),
        ]),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: LinearProgressIndicator(
            value: available ? value.clamp(0.0, 1.0) : 0.0,
            minHeight: 5,
            backgroundColor: _border,
            valueColor: AlwaysStoppedAnimation(available ? color : _border),
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

  // Aurora Build 712, App Developmental Habitat, spec section 46: raw
  // evidence counts only ("Aurora created 7 entities. 4 were later
  // modified by the human...") -- never a developmental judgment
  // ("Aurora is becoming artistic"). Section 32: maintenance controls
  // (backup/restore/isolate-corrupt/reset) live here, human-only, never
  // reachable through a normal environmental action.
  Widget _buildHabitatPanel() {
    final r = _habitatReport;
    int _i(String key) => (r[key] as num?)?.toInt() ?? 0;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('HABITAT', color: _green),
      _card(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: _habitatStat('Renderable', _i('surface_renderable_count'))),
          Expanded(child: _habitatStat('Deleted', _i('deleted_count'))),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _habitatStat('Aurora visible', _i('surface_aurora_created'))),
          Expanded(child: _habitatStat('Human visible', _i('surface_human_created'))),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _habitatStat('Incomplete legacy', _i('incomplete_live_count'))),
          Expanded(child: _habitatStat('Canonical live', _i('entity_count'))),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _habitatStat('Territory transitions', _i('territory_transitions'))),
          Expanded(child: _habitatStat('Events logged', _i('event_count_on_disk'))),
        ]),
        const SizedBox(height: 10),
        Row(children: [
          Text('persistence: ', style: const TextStyle(color: _textDim, fontSize: 11)),
          Text(r['persistence_health'] as String? ?? 'unknown',
            style: TextStyle(
              color: r['persistence_health'] == 'ok' ? _green : _amber,
              fontSize: 11, fontWeight: FontWeight.w600)),
        ]),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          _actionButton(label: 'Backup', icon: Icons.save_outlined, color: _cyan, onTap: _onHabitatBackup, compact: true),
          _actionButton(label: 'Restore Last', icon: Icons.restore, color: _amber, onTap: _onHabitatRestoreLast, compact: true),
          _actionButton(label: 'Isolate Corrupt', icon: Icons.healing_outlined, color: _amber, onTap: _onHabitatIsolateCorrupt, compact: true),
          _actionButton(label: 'Reset', icon: Icons.delete_forever_outlined, color: _red, onTap: _onHabitatReset, compact: true),
        ]),
      ])),
    ]);
  }

  Widget _habitatStat(String label, int value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text('$value', style: const TextStyle(color: _text, fontSize: 18, fontWeight: FontWeight.w700)),
      Text(label, style: const TextStyle(color: _textDim, fontSize: 10)),
    ],
  );

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
                  _buildDevelopmentPanel(),
                  _buildLiveTurnDiagnosticsPanel(),
                  _buildEvolutionPanel(),
                  _buildGenealogyPanel(),
                  _buildQuasiarchPanel(),
                  _buildGauntletPanel(),
                  _buildHabitatPanel(),
                  _buildRoomPanel(),
                  const SizedBox(height: 24),
                ]),
              ),
      ),
    );
  }

  Widget _buildHeader() {
    final turnCount = _stats['turn_count'] as int? ?? 0;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Row(children: [
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Aurora Hub', style: TextStyle(
            color: _text, fontSize: 20, fontWeight: FontWeight.w700)),
          Text('Turn $turnCount  •  Live',
            style: const TextStyle(color: _textDim, fontSize: 12)),
        ]),
        const Spacer(),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: _green.withOpacity(0.12),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: _green, width: 0.8),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.circle, size: 7, color: _green),
            const SizedBox(width: 5),
            Text('Live',
              style: TextStyle(color: _green, fontSize: 11,
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
          _axisBar(ax, (_stats[ax] as num?)?.toDouble()),
      ])),
    ]);
  }

  Widget _buildCognitivePanel() {
    final histDone = _stats['historical_events_experienced'] as int? ?? 0;
    final histTotal = _stats['historical_total_events'] as int? ?? 0;
    final histProgress = _stats['historical_progress'] as double? ?? 0.0;
    final histStatus = (_stats['historical_status'] as String?)?.replaceAll('_', ' ') ?? 'not initialized';

    // Concept Crystal / Noncomp mini-stats mix several fields into one
    // string -- rendered as a whole '—' when their primary field is
    // unavailable, rather than a half-real half-dash string.
    final crAvailable = _statAvailable('concept_crystal_nodes');
    final crText = crAvailable
        ? '${_intStat('concept_crystal_promoted')} promoted / ${_intStat('concept_crystal_nodes')} total '
          '(${(( _dblOrNull('concept_crystal_maturity') ?? 0.0) * 100).toStringAsFixed(0)}%)'
        : '—';
    final noncAvailable = _statAvailable('noncomp_loaded');
    final noncDAvailable = _statAvailable('noncomp_diagonal_live');

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('COGNITIVE FIELD'),
      _card(child: Column(children: [
        Row(children: [
          Expanded(child: _miniStat('LSA Paths', _intStat('lsa_paths'), _availColor('lsa_paths', _purple))),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Avg N-Cost', _dblStat('avg_n_cost'),
              _statAvailable('avg_n_cost') ? _nCostColor(_dblOrNull('avg_n_cost') ?? 1.0) : _textDim)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('SediMemory',
              _statAvailable('sedimemory_depth') ? '${_intStat('sedimemory_depth')} frags' : '—',
              _availColor('sedimemory_depth', _cyan))),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Concept Crystals', crText, crAvailable ? _green : _textDim)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Noncomp',
              noncAvailable ? '${_intStat('noncomp_loaded')} loaded' : '—',
              _availColor('noncomp_loaded', _textDim))),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Diagonal Live',
              noncDAvailable ? '${_intStat('noncomp_diagonal_live')} active' : '—',
              _availColor('noncomp_diagonal_live', _purpleDim))),
        ]),
        const Divider(color: _border, height: 20),
        _statRow('Understanding', _dblStat('understanding_index'), valueColor: _availColor('understanding_index', _green)),
        _statRow('Coherence',     _dblStat('coherence_index'),     valueColor: _availColor('coherence_index', _cyan)),
        _statRow('Grounding',     _dblStat('grounding_index'),     valueColor: _availColor('grounding_index', _amber)),
        _statRow('Topic Tracking',_dblStat('topic_tracking'),      valueColor: _availColor('topic_tracking', _purple)),
        const Divider(color: _border, height: 20),
        _statRow(
          'Historical Experience',
          histTotal > 0
              ? '$histDone / $histTotal (${(histProgress * 100).toStringAsFixed(1)}%) · $histStatus'
              : histStatus,
          valueColor: histStatus == 'completed' ? _green : _cyan,
        ),
      ])),
    ]);
  }

  // Build 772 (Historical Lexical Consequence Attribution and
  // Developmental Replay): live surface for the diagnostics that build
  // already produces -- AuroraLexicalGrounding.status()["historical"]
  // plus the historical environment's own backfill cursor and promoted
  // count, flat-mirrored by get_cognitive_stats(). Observability only,
  // same as the QUASIARCH/HABITAT panels above: raw counts, no
  // developmental judgment invented at this layer.
  Widget _buildDevelopmentPanel() {
    final histTotal   = _stats['historical_total_events'] as int? ?? 0;
    final histWitnessed = _stats['historical_events_experienced'] as int? ?? 0;
    final backfillThrough = _stats['lexical_backfill_examined_through_event_index'] as int? ?? 0;

    final pairsExamined      = _stats['historical_pairs_examined'] as int? ?? 0;
    final outcomesAttributed = _stats['historical_outcomes_attributed'] as int? ?? 0;
    final corrections        = _stats['explicit_corrections_detected'] as int? ?? 0;
    final discriminating     = _stats['discriminating_historical_consequences'] as int? ?? 0;

    final candidatesFormed   = _stats['lexical_candidates_formed_historical'] as int? ?? 0;
    final candidatesPromoted = _stats['candidates_promoted_with_historical_contribution'] as int? ?? 0;
    final promotedTotal      = _stats['promoted_lexical_candidates'] as int? ?? 0;
    final unresolvedGaps     = _stats['unresolved_historical_lexical_gaps'] as int? ?? 0;

    final replayEligible     = _stats['replay_eligible_observations'] as int? ?? 0;
    final replayed           = _stats['replayed_observations'] as int? ?? 0;
    final newDistinctions    = _stats['new_distinctions_from_replay'] as int? ?? 0;
    final promotionsFromReplay = _stats['promotions_from_replay'] as int? ?? 0;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('DEVELOPMENT', color: _cyan),
      _card(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Historical witnessing position (events witnessed / archive total).
        Row(children: [
          Text('Historical witness', style: const TextStyle(color: _textDim, fontSize: 11)),
          const Spacer(),
          Text(histTotal > 0 ? '$histWitnessed / $histTotal' : '—',
              style: const TextStyle(color: _text, fontSize: 11, fontWeight: FontWeight.w600)),
        ]),
        const SizedBox(height: 6),
        // Codex review, PR #193: backfilled_through_event_index only ever
        // advances inside the one-time _backfill_lexical_grounding() catch-
        // up pass at boot -- every event witnessed LIVE after that also
        // reaches lexical grounding (via _observe_communication_possibility's
        // own direct call), but through a path that never touches this
        // cursor. So this is a one-time migration marker, not an ongoing
        // coverage fraction -- showing it as "$backfillThrough / $histWitnessed"
        // with a progress bar would read as live progress and then appear
        // stuck once the migration pass finishes, even while every new pair
        // keeps reaching lexical grounding untracked by this number.
        Row(children: [
          Text('Lexical backfill (migration)', style: const TextStyle(color: _textDim, fontSize: 11)),
          const Spacer(),
          Text('$backfillThrough events',
              style: const TextStyle(color: _cyan, fontSize: 11, fontWeight: FontWeight.w600)),
        ]),
        const SizedBox(height: 2),
        Text(
          'One-time catch-up over already-witnessed history at boot. '
          'New pairs reach lexical grounding live as they\'re witnessed, '
          'independent of this count.',
          style: const TextStyle(color: _textDim, fontSize: 9, height: 1.4),
        ),
        const Divider(color: _border, height: 20),
        Align(
          alignment: Alignment.centerLeft,
          child: Text('CONSEQUENCE ATTRIBUTION',
              style: TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
        ),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Pairs Examined', '$pairsExamined', _text)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Outcomes Attributed', '$outcomesAttributed', _purple)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Corrections Detected', '$corrections', _amber)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Discriminating', '$discriminating', _green)),
        ]),
        const Divider(color: _border, height: 20),
        Align(
          alignment: Alignment.centerLeft,
          child: Text('CANDIDATES & GAPS',
              style: TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
        ),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Formed (historical)', '$candidatesFormed', _text)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Promoted (historical)', '$candidatesPromoted', _green)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Promoted (total)', '$promotedTotal', _green)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Unresolved Gaps', '$unresolvedGaps', _amber)),
        ]),
        const Divider(color: _border, height: 20),
        Align(
          alignment: Alignment.centerLeft,
          child: Text('DEVELOPMENTAL REPLAY',
              style: TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
        ),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Replay Eligible', '$replayEligible', _text)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Replayed', '$replayed', _cyan)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('New Distinctions', '$newDistinctions', _purple)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Promotions', '$promotionsFromReplay', _green)),
        ]),
      ])),
    ]);
  }

  // Build 774: raw on-device visibility into recent live turns' recorded
  // states, so a hung/silent turn is diagnosable from the phone alone.
  // Newest first; an entry whose last_state is still surface_received or
  // surface_processing (never reached a terminal state) means that turn
  // is/was genuinely stuck at that exact point -- the single most useful
  // fact for triaging "she went silent."
  static const _terminalGoodStates = {
    'subsurface_integrated', 'suppressed_by_aurora', 'late_completion',
  };
  static const _terminalBadStates = {
    'transport_failure', 'timeout', 'empty_expression',
  };

  Widget _buildLiveTurnDiagnosticsPanel() {
    final entries = List<Map<String, dynamic>>.from(
      _turnDiagnostics.whereType<Map>().map((e) => Map<String, dynamic>.from(e)),
    )..sort((a, b) => (b['last_ts'] as num? ?? 0).compareTo(a['last_ts'] as num? ?? 0));
    final recent = entries.take(6).toList();

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('LIVE TURN DIAGNOSTICS', color: _cyan),
      _card(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (recent.isEmpty)
          const Text(
            'No live turns recorded yet this session -- send Aurora a '
            'message, then pull down to refresh.',
            style: const TextStyle(color: _textDim, fontSize: 11, height: 1.4),
          )
        else
          for (int i = 0; i < recent.length; i++) ...[
            if (i > 0) const Divider(color: _border, height: 16),
            Builder(builder: (_) {
              final e = recent[i];
              final states = List<dynamic>.from(e['states'] as List? ?? []);
              final lastState = e['last_state'] as String? ?? '';
              final turnId = (e['turn_id'] as String? ?? '');
              final shortId = turnId.length > 8 ? turnId.substring(turnId.length - 8) : turnId;
              final Color stateColor = _terminalGoodStates.contains(lastState)
                  ? _green
                  : _terminalBadStates.contains(lastState)
                      ? Colors.redAccent
                      : _cyan; // still mid-flight (or a live-only state like surface_expressed)
              final sequence = states.map((s) {
                final m = Map<String, dynamic>.from(s as Map);
                return m['state']?.toString() ?? '?';
              }).join(' → ');
              String? userText;
              if (states.isNotEmpty) {
                final first = Map<String, dynamic>.from(states.first as Map);
                userText = first['user_text'] as String?;
              }
              // Diagnostic-only: when a turn was suppressed_by_aurora, show
              // what resp_A.content actually was BEFORE _sanitize_response()
              // ran -- distinguishes "Aurora genuinely had nothing to say"
              // (pre_sanitize_content also empty) from "she said something
              // and Android's cleanup discarded it" (pre_sanitize_content
              // non-empty), which are very different bugs to chase.
              String? preSanitizePreview;
              if (lastState == 'suppressed_by_aurora') {
                for (final s in states.reversed) {
                  final m = Map<String, dynamic>.from(s as Map);
                  if (m['state'] == 'suppressed_by_aurora' && m.containsKey('pre_sanitize_content')) {
                    final raw = (m['pre_sanitize_content'] as String? ?? '');
                    final len = m['pre_sanitize_len'] as int? ?? raw.length;
                    preSanitizePreview = raw.isEmpty
                        ? 'aurora.py itself produced empty content -- genuine silence'
                        : 'aurora.py produced $len chars, discarded by sanitize: "$raw${len > raw.length ? "…" : ""}"';
                    break;
                  }
                }
              }
              return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Text('…$shortId', style: const TextStyle(color: _textDim, fontSize: 10, fontFamily: 'monospace')),
                  const Spacer(),
                  Text(lastState.isEmpty ? '—' : lastState,
                      style: TextStyle(color: stateColor, fontSize: 11, fontWeight: FontWeight.w600)),
                ]),
                if (userText != null && userText.isNotEmpty) ...[
                  const SizedBox(height: 3),
                  Text('"$userText"',
                      style: const TextStyle(color: _purpleDim, fontSize: 10, fontStyle: FontStyle.italic)),
                ],
                const SizedBox(height: 3),
                Text(sequence.isEmpty ? '—' : sequence,
                    style: const TextStyle(color: _text, fontSize: 10, height: 1.4)),
                if (preSanitizePreview != null) ...[
                  const SizedBox(height: 4),
                  Text(preSanitizePreview,
                      style: const TextStyle(color: Colors.orangeAccent, fontSize: 10, height: 1.4, fontStyle: FontStyle.italic)),
                ],
              ]);
            }),
          ],
      ])),
    ]);
  }

  Widget _buildEvolutionPanel() {
    // Build 773: evo_cycles/sentence_target only ever land in the JSON
    // together, inside evo_status()'s own success path -- evo_available's
    // absence (not just its being false) is what "unavailable" means here.
    final avail = _stats['evo_available'] == true;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('EMERGENCE & EVOLUTION', color: _green),
      _card(child: Column(children: [
        Row(children: [
          Expanded(child: _miniStat('Evo Cycles', avail ? _intStat('evo_cycles') : '—', avail ? _green : _textDim)),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Sentence Target',
              avail ? '${_intStat('sentence_target')} words' : '—',
              avail ? _text : _textDim)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _miniStat('Chamber Fossils', _intStat('chamber_fossils'), _availColor('chamber_fossils', _amber))),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Live Evo', 'every 15 turns', _cyan)),
        ]),
        const Divider(color: _border, height: 20),
        // Quick-fire training cycle buttons
        Row(children: [
          Expanded(
            child: _actionButton(
              label: 'Curiosity Cycle',
              icon: Icons.explore_outlined,
              color: _cyan,
              onTap: _onCuriosityCycle,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _actionButton(
              label: 'Evo Cycle',
              icon: Icons.auto_awesome_outlined,
              color: _green,
              onTap: _onEvoCycle,
            ),
          ),
        ]),
      ])),
    ]);
  }

  // Repair R (per Sunni, 2026-08-19): genealogy mapping + WarpField
  // routing history, for the deeper auditing surface she asked for --
  // real ability admission data (axis distribution, most-recently-
  // admitted abilities with their actual tags), not a synthetic summary.
  Widget _buildGenealogyPanel() {
    final axisCounts = Map<String, dynamic>.from(
        _stats['genealogy_axis_counts'] as Map? ?? {});
    final recentAbilities = List<dynamic>.from(
        _stats['genealogy_recent_abilities'] as List? ?? []);
    final warpDemands = List<dynamic>.from(
        _stats['warp_recent_demands'] as List? ?? []);

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('GENEALOGY', color: _amber),
      _card(child: Column(children: [
        Row(children: [
          Expanded(child: _miniStat('Total Abilities', _intStat('genealogy_ability_count'), _availColor('genealogy_ability_count', _amber))),
          const SizedBox(width: 10),
          Expanded(child: _miniStat('Actuators', _intStat('warp_actuator_count'), _availColor('warp_actuator_count', _cyan))),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          for (final ax in ['X', 'T', 'N', 'B', 'A'])
            Expanded(child: _miniStat(ax, '${axisCounts[ax] ?? 0}', _purple)),
        ]),
        if (recentAbilities.isNotEmpty) ...[
          const Divider(color: _border, height: 20),
          Align(
            alignment: Alignment.centerLeft,
            child: Text('RECENTLY ADMITTED',
                style: TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
          ),
          const SizedBox(height: 6),
          for (final a in recentAbilities.take(5))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(children: [
                Container(
                  width: 20, height: 20,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: _purple.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text((a['axis'] as String? ?? '?'),
                      style: const TextStyle(color: _purple, fontSize: 10, fontWeight: FontWeight.w700)),
                ),
                const SizedBox(width: 8),
                Expanded(child: Text(
                  (a['id'] as String? ?? ''),
                  style: const TextStyle(color: _text, fontSize: 11),
                  overflow: TextOverflow.ellipsis,
                )),
              ]),
            ),
        ],
        if (warpDemands.isNotEmpty) ...[
          const Divider(color: _border, height: 20),
          Align(
            alignment: Alignment.centerLeft,
            child: Text('RECENT WARP DEMANDS',
                style: TextStyle(color: _textDim, fontSize: 10, letterSpacing: 1.2)),
          ),
          const SizedBox(height: 6),
          for (final d in warpDemands.take(5))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(children: [
                Expanded(child: Text(
                  '${d['source'] ?? ''} → ${d['trigger'] ?? ''} (${d['pathway'] ?? ''})',
                  style: const TextStyle(color: _text, fontSize: 11),
                  overflow: TextOverflow.ellipsis,
                )),
                Text('${((d['severity'] as num?) ?? 0.0).toStringAsFixed(2)}',
                    style: const TextStyle(color: _textDim, fontSize: 10)),
              ]),
            ),
        ],
      ])),
    ]);
  }

  // Repair R: quasiarch self-repair diagnostics -- what she noticed was
  // going wrong with her own dialogue/articulation, what she tried, and
  // whether it actually resolved. Real intervention records, not a
  // health-check summary invented at this layer.
  Widget _buildQuasiarchPanel() {
    final interventions = List<dynamic>.from(
        _stats['quasiarch_recent_interventions'] as List? ?? []);

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('QUASIARCH DIAGNOSTICS', color: _cyan),
      _card(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: _miniStat('Total Events', _intStat('quasiarch_event_count'), _availColor('quasiarch_event_count', _cyan))),
        ]),
        if (interventions.isEmpty)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text('No self-repair interventions yet this session.',
                style: TextStyle(color: _textDim, fontSize: 11)),
          )
        else ...[
          const Divider(color: _border, height: 20),
          for (final ev in interventions.take(5))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if ((ev['target'] as String? ?? '').isNotEmpty)
                  Text(ev['target'] as String,
                      style: const TextStyle(color: _textDim, fontSize: 10)),
                if ((ev['issue'] as String? ?? '').isNotEmpty)
                  Text('issue: ${ev['issue']}',
                      style: const TextStyle(color: _amber, fontSize: 11)),
                if ((ev['intervention'] as String? ?? '').isNotEmpty)
                  Text('tried: ${ev['intervention']}',
                      style: const TextStyle(color: _text, fontSize: 11)),
                if ((ev['observed_effect'] as String? ?? '').isNotEmpty)
                  Text('effect: ${ev['observed_effect']}',
                      style: TextStyle(
                        color: (ev['observed_effect'] as String) == 'resolved_partially'
                            ? _amber : _green,
                        fontSize: 11,
                      )),
              ]),
            ),
        ],
      ])),
    ]);
  }

  Widget _buildGauntletPanel() {
    final doneIds = _gauntletLog.map((e) => e['stage_id'] as String? ?? '').toSet();
    final total   = _gauntletStageOrder.length;
    final done    = doneIds.length;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('GAUNTLET TRAINING', color: _amber),
      _card(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Header row: status + start/stop
        Row(children: [
          _gauntletStatusChip(),
          const Spacer(),
          _gauntletRunning
              ? _actionButton(
                  label: 'Stop',
                  icon: Icons.stop_circle_outlined,
                  color: _red,
                  onTap: _onStopGauntlet,
                  compact: true,
                )
              : _actionButton(
                  label: 'Start Gauntlet',
                  icon: Icons.rocket_launch_outlined,
                  color: _amber,
                  onTap: _onStartGauntlet,
                  compact: true,
                ),
        ]),
        if (_gauntletRunning || doneIds.isNotEmpty) ...[
          const SizedBox(height: 10),
          // Overall progress bar
          Row(children: [
            Text('$done / $total stages', style: const TextStyle(color: _textDim, fontSize: 11)),
            const Spacer(),
            Text('${(done / total * 100).toStringAsFixed(0)}%',
              style: const TextStyle(color: _amber, fontSize: 11, fontWeight: FontWeight.w600)),
          ]),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: done / total,
              minHeight: 5,
              backgroundColor: _border,
              valueColor: const AlwaysStoppedAnimation(_amber),
            ),
          ),
          const SizedBox(height: 12),
        ],
        // Stage list
        for (int i = 0; i < _gauntletStageOrder.length; i++)
          _buildStageRow(i),
        // About text when idle and no history
        if (!_gauntletRunning && doneIds.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(
              'Runs all 9 training stages in sequence — each one builds on the last.',
              style: const TextStyle(color: _textDim, fontSize: 11, height: 1.5),
            ),
          ),
      ])),
    ]);
  }

  Widget _gauntletStatusChip() {
    final label = _gauntletRunning
        ? 'Running: ${_gauntletStageLabels[_gauntletStage] ?? _gauntletStage}'
        : 'Idle';
    final color = _gauntletRunning ? _amber : _textDim;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.10),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.30)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (_gauntletRunning)
          Padding(
            padding: const EdgeInsets.only(right: 5),
            child: SizedBox(
              width: 8, height: 8,
              child: CircularProgressIndicator(strokeWidth: 1.5, color: _amber),
            ),
          ),
        Text(label,
          style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600),
          overflow: TextOverflow.ellipsis),
      ]),
    );
  }

  Widget _buildStageRow(int index) {
    final id    = _gauntletStageOrder[index];
    final label = _gauntletStageLabels[id] ?? id;
    final isCurrent = _gauntletRunning && _gauntletStage == id;
    final logEntry  = _gauntletLog.where((e) => e['stage_id'] == id).firstOrNull;
    final isDone    = logEntry != null;
    final result    = logEntry?['result'] as String? ?? '';

    Color dotColor;
    IconData dotIcon;
    if (isDone)        { dotColor = _green;  dotIcon = Icons.check_circle_rounded; }
    else if (isCurrent){ dotColor = _amber;  dotIcon = Icons.play_circle_rounded; }
    else               { dotColor = _border; dotIcon = Icons.circle_outlined; }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // Stage number
        SizedBox(
          width: 22,
          child: Text('${index + 1}',
            style: TextStyle(color: _textDim, fontSize: 10),
            textAlign: TextAlign.right,
          ),
        ),
        const SizedBox(width: 8),
        // Status icon
        Icon(dotIcon, size: 14, color: dotColor),
        const SizedBox(width: 8),
        // Label + result
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: TextStyle(
            color: isCurrent ? _amber : (isDone ? _text : _textDim),
            fontSize: 12,
            fontWeight: isCurrent ? FontWeight.w700 : FontWeight.w500,
          )),
          if (isDone && result.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(result,
                style: const TextStyle(color: _textDim, fontSize: 10, height: 1.3),
                maxLines: 2, overflow: TextOverflow.ellipsis),
            ),
        ])),
      ]),
    );
  }

  Widget _buildRoomPanel() {
    final daemonStatus = _room['daemon_status'] as Map<String, dynamic>? ?? {};
    final heat   = daemonStatus['heat'] as String? ?? '—';
    final epoch  = daemonStatus['epoch'] as int? ?? 0;

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _sectionTitle('AURORA\'S ROOM', color: _green),
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

  // ── Shared widget helpers ───────────────────────────────────────────────────

  Widget _actionButton({
    required String label,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
    bool compact = false,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: compact ? 10 : 12,
          vertical: compact ? 7 : 9,
        ),
        decoration: BoxDecoration(
          color: color.withOpacity(0.10),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withOpacity(0.35)),
        ),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(
            color: color, fontSize: 11, fontWeight: FontWeight.w600)),
        ]),
      ),
    );
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

  void _navRoom(String tab) {
    AuroraBridge.provideRoomCommand('{"navigate":"$tab"}');
    _showSnack('Sent Aurora to $tab tab');
  }
}
