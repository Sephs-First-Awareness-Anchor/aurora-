// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// The interactive layer: owns selection/refresh state, wires
// HabitatCanvas's tap/drag callbacks and a small action toolbar to
// HabitatBridge.act() calls. Every button here issues exactly one of
// aurora_habitat.py's OPERATIONS with the parameters that operation
// defines -- nothing here decides what an action MEANS, only which
// physical operation the human chose (spec section 20: Flutter must
// not own developmental meaning).
import 'dart:async';

import 'package:flutter/material.dart';

import 'habitat_bridge.dart';
import 'habitat_model.dart';
import 'habitat_renderer.dart';

class HabitatInteractiveView extends StatefulWidget {
  final String territory; // "space" | "self"
  final bool humanCanCreate;

  const HabitatInteractiveView({
    super.key,
    required this.territory,
    this.humanCanCreate = true,
  });

  @override
  State<HabitatInteractiveView> createState() => _HabitatInteractiveViewState();
}

class _HabitatInteractiveViewState extends State<HabitatInteractiveView> {
  HabitatState _state = HabitatState.empty('space');
  String? _selectedId;
  String? _connectFromId;
  bool _loading = true;
  String? _lastMessage;
  Timer? _stateRefreshTimer;

  @override
  void initState() {
    super.initState();
    _refresh();
    // UI synchronization only: observe canonical Habitat state changed by Aurora.
    _stateRefreshTimer = Timer.periodic(const Duration(seconds: 2), (_) => _refresh());
  }

  @override
  void dispose() {
    _stateRefreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    final state = await HabitatBridge.getState(territory: widget.territory, actor: 'human');
    if (!mounted) return;
    setState(() {
      _state = state;
      _loading = false;
      if (_selectedId != null && !_state.entities.any((e) => e.id == _selectedId)) {
        _selectedId = null;
      }
    });
  }

  HabitatEntity? get _selected =>
      _selectedId == null ? null : _state.entities.cast<HabitatEntity?>().firstWhere((e) => e?.id == _selectedId, orElse: () => null);

  Future<void> _act({
    required String operation,
    List<String> targetIds = const [],
    Map<String, dynamic> parameters = const {},
  }) async {
    final consequence = await HabitatBridge.act(
      territory: widget.territory,
      operation: operation,
      targetIds: targetIds,
      parameters: parameters,
    );
    if (!mounted) return;
    if (!consequence.success) {
      setState(() => _lastMessage = 'not permitted: ${consequence.rejectedReason}');
    } else {
      setState(() => _lastMessage = null);
    }
    await _refresh();
  }

  Future<void> _create() async {
    await _act(
      operation: 'create',
      parameters: {
        'entity_type': 'shape',
        'position': [0.5, 0.5],
        'dimensions': [0.14, 0.14],
        'visual_properties': {'color': 'blue', 'shape_kind': 'rect'},
      },
    );
  }

  Future<void> _onDrag(String entityId, Offset normalizedPos) async {
    await _act(
      operation: 'move', targetIds: [entityId],
      parameters: {'x': normalizedPos.dx.clamp(0.0, 1.0), 'y': normalizedPos.dy.clamp(0.0, 1.0)},
    );
  }

  void _onTapEntity(String entityId) {
    if (_connectFromId != null && _connectFromId != entityId) {
      _act(operation: 'connect', targetIds: [_connectFromId!, entityId]);
      setState(() => _connectFromId = null);
      return;
    }
    setState(() => _selectedId = entityId);
  }

  Widget _toolButton(IconData icon, String label, VoidCallback onTap, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 20, color: color ?? Colors.white70),
            const SizedBox(height: 2),
            Text(label, style: TextStyle(fontSize: 10, color: color ?? Colors.white54)),
          ]),
        ),
      ),
    );
  }

  Widget _buildToolbar() {
    final sel = _selected;
    if (sel == null) {
      return Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        if (widget.humanCanCreate)
          _toolButton(Icons.add_circle_outline, 'create', _create, color: Colors.greenAccent),
      ]);
    }
    final canModify = sel.permission('modifiable_by_human') || widget.territory == 'space';
    final canTransfer = sel.permission('transferable');
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(children: [
        if (canModify) ...[
          _toolButton(Icons.zoom_in, 'bigger', () => _act(
              operation: 'resize', targetIds: [sel.id],
              parameters: {'width': (sel.dimensions[0] + 0.03).clamp(0.03, 0.9), 'height': (sel.dimensions[1] + 0.03).clamp(0.03, 0.9)})),
          _toolButton(Icons.zoom_out, 'smaller', () => _act(
              operation: 'resize', targetIds: [sel.id],
              parameters: {'width': (sel.dimensions[0] - 0.03).clamp(0.03, 0.9), 'height': (sel.dimensions[1] - 0.03).clamp(0.03, 0.9)})),
          _toolButton(Icons.rotate_left, 'rotate', () => _act(
              operation: 'rotate', targetIds: [sel.id], parameters: {'degrees': (sel.orientation - 15) % 360})),
          _toolButton(Icons.rotate_right, 'rotate', () => _act(
              operation: 'rotate', targetIds: [sel.id], parameters: {'degrees': (sel.orientation + 15) % 360})),
          _toolButton(Icons.link, 'connect', () => setState(() => _connectFromId = sel.id), color: Colors.cyanAccent),
          _toolButton(Icons.delete_outline, 'delete', () => _act(operation: 'delete', targetIds: [sel.id]), color: Colors.redAccent),
        ],
        if (canTransfer)
          _toolButton(
            widget.territory == 'space' ? Icons.lock_outline : Icons.public,
            widget.territory == 'space' ? 'to self' : 'to space',
            () => _act(
              operation: 'transfer', targetIds: [sel.id],
              parameters: {
                'owner': widget.territory == 'space' ? 'aurora' : 'shared',
                'territory': widget.territory == 'space' ? 'self' : 'space',
              },
            ),
            color: Colors.amberAccent,
          ),
        _toolButton(Icons.close, 'deselect', () => setState(() => _selectedId = null)),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return Column(children: [
      if (_connectFromId != null)
        Container(
          width: double.infinity,
          color: Colors.cyanAccent.withOpacity(0.15),
          padding: const EdgeInsets.all(6),
          child: const Text('tap another entity to connect', textAlign: TextAlign.center, style: TextStyle(color: Colors.cyanAccent, fontSize: 12)),
        ),
      if (_lastMessage != null)
        Container(
          width: double.infinity,
          color: Colors.redAccent.withOpacity(0.15),
          padding: const EdgeInsets.all(6),
          child: Text(_lastMessage!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.redAccent, fontSize: 12)),
        ),
      Expanded(
        child: HabitatCanvas(
          entities: _state.entities,
          selectedEntityId: _selectedId,
          onEntityTapped: _onTapEntity,
          onEntityDragged: _onDrag,
          onBackgroundTapped: () => setState(() {
            _selectedId = null;
            _connectFromId = null;
          }),
        ),
      ),
      Container(
        color: Colors.black.withOpacity(0.35),
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: _buildToolbar(),
      ),
    ]);
  }
}
