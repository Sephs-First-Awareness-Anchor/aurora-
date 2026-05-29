import 'dart:async';
import 'package:flutter/material.dart';
import '../aurora_bridge.dart';

const _purple = Color(0xFFA020F0);
const _bg     = Color(0xFF0D0D0F);
const _card   = Color(0xFF1A1A2E);

class _Turn {
  final String role;  // 'partner' or 'aurora'
  final String text;
  final int turn;
  _Turn(this.role, this.text, this.turn);
}

class SocializeScreen extends StatefulWidget {
  const SocializeScreen({super.key});
  @override
  State<SocializeScreen> createState() => _SocializeScreenState();
}

class _SocializeScreenState extends State<SocializeScreen> {

  final _keyCtrl      = TextEditingController();
  final _minutesCtrl  = TextEditingController(text: '10');
  final _scrollCtrl   = ScrollController();

  String _model          = 'gemini-2.5-flash';
  bool   _active         = false;
  bool   _keyVisible     = false;

  // Live telemetry
  int    _lsaPaths       = 0;
  double _avgNCost       = 1.0;
  int    _turn           = 0;
  int    _totalSecs      = 0;
  int    _elapsed        = 0;

  final List<_Turn> _turns = [];

  StreamSubscription? _sub;

  @override
  void initState() {
    super.initState();
    _sub = AuroraBridge.events.listen(_onEvent);
  }

  void _onEvent(Map<String, dynamic> ev) {
    final type = ev['type'] as String? ?? '';

    if (type == 'training_turn') {
      final t       = (ev['turn_num']   as int?) ?? 0;
      final partner = (ev['partner']    as String?) ?? '';
      final aurora  = (ev['aurora_msg'] as String?) ?? '';

      if (!mounted) return;
      setState(() {
        if (partner.isNotEmpty) _turns.add(_Turn('partner', partner, t));
        if (aurora.isNotEmpty)  _turns.add(_Turn('aurora',  aurora,  t));
        _lsaPaths  = (ev['lsa_paths']  as int?)    ?? _lsaPaths;
        _avgNCost  = (ev['avg_n_cost'] as double?)  ?? _avgNCost;
        _turn      = t;
        _elapsed   = (ev['elapsed']    as int?)    ?? _elapsed;
        _totalSecs = (ev['total_secs'] as int?)    ?? _totalSecs;
      });
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollCtrl.hasClients) {
          _scrollCtrl.animateTo(
            _scrollCtrl.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    } else if (type == 'training_done') {
      if (!mounted) return;
      setState(() {
        _active   = false;
        _lsaPaths = (ev['lsa_paths']  as int?)    ?? _lsaPaths;
        _avgNCost = (ev['avg_n_cost'] as double?)  ?? _avgNCost;
        _turn     = (ev['turn_num']   as int?)    ?? _turn;
      });
    }
  }

  Future<void> _startSession() async {
    final key     = _keyCtrl.text.trim();
    final minutes = double.tryParse(_minutesCtrl.text.trim()) ?? 10.0;
    if (key.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter your Gemini API key first')),
      );
      return;
    }
    final result = await AuroraBridge.startTraining(
      apiKey: key, model: _model, durationMinutes: minutes,
    );
    if (result == 'started' && mounted) {
      setState(() {
        _active    = true;
        _turns.clear();
        _lsaPaths  = 0;
        _avgNCost  = 1.0;
        _turn      = 0;
        _elapsed   = 0;
        _totalSecs = (minutes * 60).toInt();
      });
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result)),
      );
    }
  }

  Future<void> _stopSession() async {
    await AuroraBridge.stopTraining();
    if (mounted) setState(() => _active = false);
  }

  @override
  void dispose() {
    _sub?.cancel();
    _keyCtrl.dispose();
    _minutesCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            _buildTelemetry(),
            Expanded(child: _buildChat()),
            _buildControls(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
      child: Row(
        children: [
          const Text('Socialize',
            style: TextStyle(
              color: _purple, fontSize: 22,
              fontWeight: FontWeight.w300, letterSpacing: 3,
            ),
          ),
          const Spacer(),
          if (_active)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: _purple.withOpacity(0.2),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: _purple.withOpacity(0.5)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 7, height: 7,
                    decoration: const BoxDecoration(color: _purple, shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 6),
                  const Text('Live', style: TextStyle(color: _purple, fontSize: 12)),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTelemetry() {
    final progress = _totalSecs > 0 ? (_elapsed / _totalSecs).clamp(0.0, 1.0) : 0.0;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: _card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        children: [
          Row(
            children: [
              _statChip('LSA Paths', '$_lsaPaths', Icons.account_tree_outlined),
              const SizedBox(width: 12),
              _statChip('Avg N-Cost', _avgNCost.toStringAsFixed(3), Icons.trending_down_rounded,
                color: _avgNCost < 0.7 ? Colors.greenAccent : Colors.white70),
              const Spacer(),
              _statChip('Turn', '$_turn', Icons.repeat_rounded),
            ],
          ),
          if (_active) ...[
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 3,
                backgroundColor: Colors.white10,
                valueColor: AlwaysStoppedAnimation<Color>(_purple),
              ),
            ),
            const SizedBox(height: 4),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                '${_elapsed ~/ 60}m ${_elapsed % 60}s / ${_totalSecs ~/ 60}m',
                style: const TextStyle(color: Colors.white38, fontSize: 11),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _statChip(String label, String value, IconData icon, {Color color = Colors.white70}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 12, color: Colors.white38),
            const SizedBox(width: 4),
            Text(label, style: const TextStyle(color: Colors.white38, fontSize: 10)),
          ],
        ),
        Text(value, style: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.w600)),
      ],
    );
  }

  Widget _buildChat() {
    if (_turns.isEmpty) {
      return Center(
        child: Text(
          _active ? 'Waiting for first turn…' : 'Run a session to watch Aurora converse.',
          style: const TextStyle(color: Colors.white38, fontSize: 14),
          textAlign: TextAlign.center,
        ),
      );
    }
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      itemCount: _turns.length,
      itemBuilder: (_, i) => _TurnBubble(turn: _turns[i]),
    );
  }

  Widget _buildControls() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: Colors.white10)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // API key row
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _keyCtrl,
                  obscureText: !_keyVisible,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Gemini API Key',
                    hintStyle: const TextStyle(color: Colors.white30),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    filled: true,
                    fillColor: _card,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                    suffixIcon: IconButton(
                      icon: Icon(_keyVisible ? Icons.visibility_off : Icons.visibility,
                        color: Colors.white38, size: 18),
                      onPressed: () => setState(() => _keyVisible = !_keyVisible),
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              // Model selector
              Expanded(
                flex: 3,
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _model,
                    dropdownColor: _card,
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                    icon: const Icon(Icons.expand_more, color: Colors.white38, size: 16),
                    items: const [
                      DropdownMenuItem(value: 'gemini-2.5-flash', child: Text('2.5 Flash')),
                      DropdownMenuItem(value: 'gemini-2.5-pro',   child: Text('2.5 Pro')),
                    ],
                    onChanged: _active ? null : (v) => setState(() => _model = v ?? _model),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              // Duration input
              SizedBox(
                width: 64,
                child: TextField(
                  controller: _minutesCtrl,
                  enabled: !_active,
                  keyboardType: TextInputType.number,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'min',
                    hintStyle: const TextStyle(color: Colors.white30),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
                    filled: true,
                    fillColor: _card,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                    suffixText: 'm',
                    suffixStyle: const TextStyle(color: Colors.white38, fontSize: 11),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              // Start / Stop
              Expanded(
                flex: 2,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _active ? Colors.red.shade900 : _purple,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  onPressed: _active ? _stopSession : _startSession,
                  child: Text(_active ? 'Stop' : 'Run Session',
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TurnBubble extends StatelessWidget {
  final _Turn turn;
  const _TurnBubble({required this.turn});

  @override
  Widget build(BuildContext context) {
    final isAurora  = turn.role == 'aurora';
    final bubbleClr = isAurora ? const Color(0xFF2A0A4A) : const Color(0xFF0F1E3A);
    final nameClr   = isAurora ? _purple : const Color(0xFF4A8FD4);
    final name      = isAurora ? 'Aurora' : 'Gemini';

    return Align(
      alignment: isAurora ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.80),
        margin: const EdgeInsets.symmetric(vertical: 3),
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 10),
        decoration: BoxDecoration(
          color: bubbleClr,
          borderRadius: BorderRadius.only(
            topLeft:     const Radius.circular(14),
            topRight:    const Radius.circular(14),
            bottomLeft:  Radius.circular(isAurora ? 14 : 3),
            bottomRight: Radius.circular(isAurora ? 3  : 14),
          ),
          border: Border.all(color: nameClr.withOpacity(0.25)),
        ),
        child: Column(
          crossAxisAlignment: isAurora ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Text(name,
              style: TextStyle(color: nameClr, fontSize: 10, fontWeight: FontWeight.w700,
                letterSpacing: 1.2)),
            const SizedBox(height: 3),
            Text(turn.text,
              style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.4)),
          ],
        ),
      ),
    );
  }
}
