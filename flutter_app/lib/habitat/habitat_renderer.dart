// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Renders a HabitatState as flat shapes on a canvas. Same CustomPaint/
// canvas.save-translate-rotate-restore pattern aurora_orb.dart's
// _FacePainter already established for this app -- the only other
// canvas-drawing widget here.
//
// Deliberately dumb: every visual property drawn here (color, opacity,
// shape_kind, rotation...) is read verbatim from HabitatEntity.
// visual_properties, which itself only ever holds whatever an
// EnvironmentAction's parameters explicitly set (spec section 7 -- no
// semantic mapping lives in this file, and none may be added to it).
import 'dart:math' as math;
import 'package:flutter/material.dart';

import 'habitat_model.dart';

class HabitatCanvas extends StatefulWidget {
  final List<HabitatEntity> entities;
  final String? selectedEntityId;
  final void Function(String entityId)? onEntityTapped;
  /// Fired once, with the final normalized position, when a drag ends --
  /// not on every frame. Committing continuously would both flood the
  /// bridge with an action per frame AND (since each commit round-trips
  /// through a parent setState/rebuild) reset this widget's own drag-
  /// tracking state mid-gesture.
  final void Function(String entityId, Offset finalNormalizedPosition)? onEntityDragged;
  final void Function()? onBackgroundTapped;

  const HabitatCanvas({
    super.key,
    required this.entities,
    this.selectedEntityId,
    this.onEntityTapped,
    this.onEntityDragged,
    this.onBackgroundTapped,
  });

  @override
  State<HabitatCanvas> createState() => _HabitatCanvasState();
}

class _HabitatCanvasState extends State<HabitatCanvas> {
  String? _dragTarget;
  Offset? _dragStartNormPos;
  Offset? _dragStartLocal;
  Offset? _dragPreviewNormPos; // live position shown while dragging, before commit

  HabitatEntity? _hitTest(Offset normalized) {
    // Topmost (highest layer, then most-recently-created) first.
    final sorted = [...widget.entities]..sort((a, b) {
        final byLayer = b.layer.compareTo(a.layer);
        return byLayer != 0 ? byLayer : b.createdAt.compareTo(a.createdAt);
      });
    for (final e in sorted) {
      if (e.entityType == 'connector' || e.entityType == 'group') continue;
      final halfW = e.dimensions[0] / 2, halfH = e.dimensions[1] / 2;
      final dx = (normalized.dx - e.position[0]).abs();
      final dy = (normalized.dy - e.position[1]).abs();
      if (dx <= halfW && dy <= halfH) return e;
    }
    return null;
  }

  List<HabitatEntity> _entitiesWithPreview() {
    if (_dragTarget == null || _dragPreviewNormPos == null) return widget.entities;
    return widget.entities.map((e) {
      if (e.id != _dragTarget) return e;
      return HabitatEntity(
        id: e.id, entityType: e.entityType, creator: e.creator, owner: e.owner, territory: e.territory,
        createdAt: e.createdAt, modifiedAt: e.modifiedAt,
        position: [_dragPreviewNormPos!.dx.clamp(0.0, 1.0), _dragPreviewNormPos!.dy.clamp(0.0, 1.0)],
        dimensions: e.dimensions, orientation: e.orientation, layer: e.layer,
        visualProperties: e.visualProperties, temporalProperties: e.temporalProperties,
        links: e.links, groupMembership: e.groupMembership, content: e.content,
        interactionPermissions: e.interactionPermissions, lineage: e.lineage,
        deleted: e.deleted, revisionCount: e.revisionCount,
      );
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      final size = Size(constraints.maxWidth, constraints.maxHeight);
      Offset normalize(Offset local) =>
          Offset((local.dx / size.width).clamp(0.0, 1.0), (local.dy / size.height).clamp(0.0, 1.0));

      return GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTapUp: (details) {
          final hit = _hitTest(normalize(details.localPosition));
          if (hit != null) {
            widget.onEntityTapped?.call(hit.id);
          } else {
            widget.onBackgroundTapped?.call();
          }
        },
        onPanStart: (details) {
          final hit = _hitTest(normalize(details.localPosition));
          setState(() {
            _dragTarget = hit?.id;
            _dragStartNormPos = hit != null ? Offset(hit.position[0], hit.position[1]) : null;
            _dragStartLocal = details.localPosition;
            _dragPreviewNormPos = _dragStartNormPos;
          });
        },
        onPanUpdate: (details) {
          if (_dragTarget == null || _dragStartNormPos == null || _dragStartLocal == null) return;
          final movedLocal = details.localPosition - _dragStartLocal!;
          final movedNorm = Offset(movedLocal.dx / size.width, movedLocal.dy / size.height);
          setState(() => _dragPreviewNormPos = _dragStartNormPos! + movedNorm);
        },
        onPanEnd: (_) {
          final target = _dragTarget;
          final finalPos = _dragPreviewNormPos;
          setState(() {
            _dragTarget = null;
            _dragStartNormPos = null;
            _dragStartLocal = null;
            _dragPreviewNormPos = null;
          });
          if (target != null && finalPos != null) {
            widget.onEntityDragged?.call(target, finalPos);
          }
        },
        child: CustomPaint(
          size: size,
          painter: _HabitatPainter(entities: _entitiesWithPreview(), selectedEntityId: widget.selectedEntityId),
        ),
      );
    });
  }
}

class _HabitatPainter extends CustomPainter {
  final List<HabitatEntity> entities;
  final String? selectedEntityId;

  _HabitatPainter({required this.entities, required this.selectedEntityId});

  Color _parseColor(dynamic value, Color fallback) {
    if (value is String) {
      final named = _namedColors[value.toLowerCase()];
      if (named != null) return named;
      if (value.startsWith('#')) {
        final hex = value.substring(1);
        final full = hex.length == 6 ? 'FF$hex' : hex;
        final parsed = int.tryParse(full, radix: 16);
        if (parsed != null) return Color(parsed);
      }
    }
    return fallback;
  }

  static const Map<String, Color> _namedColors = {
    'purple': Color(0xFFA020F0), 'blue': Colors.blue, 'green': Colors.green,
    'red': Colors.red, 'yellow': Colors.yellow, 'orange': Colors.orange,
    'teal': Colors.teal, 'gold': Color(0xFFFFD700), 'pink': Colors.pink,
    'white': Colors.white, 'black': Colors.black, 'gray': Colors.grey, 'grey': Colors.grey,
  };

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = const Color(0xFF171022));

    final live = entities.where((e) => !e.deleted).toList();

    // Group bounding boxes first (behind members).
    for (final group in live.where((e) => e.entityType == 'group')) {
      final members = live.where((e) => e.groupMembership == group.id).toList();
      if (members.isEmpty) continue;
      double minX = 1, minY = 1, maxX = 0, maxY = 0;
      for (final m in members) {
        minX = math.min(minX, m.position[0] - m.dimensions[0] / 2);
        minY = math.min(minY, m.position[1] - m.dimensions[1] / 2);
        maxX = math.max(maxX, m.position[0] + m.dimensions[0] / 2);
        maxY = math.max(maxY, m.position[1] + m.dimensions[1] / 2);
      }
      final rect = Rect.fromLTRB(
        (minX - 0.02) * size.width, (minY - 0.02) * size.height,
        (maxX + 0.02) * size.width, (maxY + 0.02) * size.height,
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(8)),
        Paint()
          ..color = Colors.white.withOpacity(0.15)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.2,
      );
    }

    // Connector lines: any linked pair, drawn once.
    final drawnPairs = <String>{};
    for (final e in live) {
      for (final linkedId in e.links) {
        final key = ([e.id, linkedId]..sort()).join('|');
        if (drawnPairs.contains(key)) continue;
        drawnPairs.add(key);
        final other = live.cast<HabitatEntity?>().firstWhere((x) => x?.id == linkedId, orElse: () => null);
        if (other == null) continue;
        canvas.drawLine(
          Offset(e.position[0] * size.width, e.position[1] * size.height),
          Offset(other.position[0] * size.width, other.position[1] * size.height),
          Paint()
            ..color = Colors.white.withOpacity(0.35)
            ..strokeWidth = 1.5,
        );
      }
    }

    // Entities, by layer then creation order (deterministic, no
    // interpretation of z-order intent).
    final drawable = live.where((e) => e.entityType != 'group').toList()
      ..sort((a, b) {
        final byLayer = a.layer.compareTo(b.layer);
        return byLayer != 0 ? byLayer : a.createdAt.compareTo(b.createdAt);
      });

    for (final e in drawable) {
      _drawEntity(canvas, size, e);
    }

    if (selectedEntityId != null) {
      final sel = live.cast<HabitatEntity?>().firstWhere((e) => e?.id == selectedEntityId, orElse: () => null);
      if (sel != null) _drawSelectionRing(canvas, size, sel);
    }
  }

  void _drawEntity(Canvas canvas, Size size, HabitatEntity e) {
    final center = Offset(e.position[0] * size.width, e.position[1] * size.height);
    final w = e.dimensions[0] * size.width, h = e.dimensions[1] * size.height;
    final color = _parseColor(e.visual('color'), const Color(0xFF9B7BD8));
    final opacity = (e.visual('opacity') is num) ? (e.visual('opacity') as num).toDouble().clamp(0.0, 1.0) : 1.0;

    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(e.orientation * math.pi / 180.0);

    final paint = Paint()..color = color.withOpacity(opacity);
    final borderStyle = e.visual('border');

    switch (e.entityType) {
      case 'text':
        final text = (e.content['text'] as String?) ?? '';
        final painter = TextPainter(
          text: TextSpan(text: text, style: TextStyle(color: color.withOpacity(opacity), fontSize: math.max(10.0, h * 0.6))),
          textDirection: TextDirection.ltr,
          maxLines: 3,
          ellipsis: '…',
        )..layout(maxWidth: math.max(20.0, w));
        painter.paint(canvas, Offset(-painter.width / 2, -painter.height / 2));
        break;
      case 'mark_path':
        final points = (e.content['points'] as List?) ?? const [];
        if (points.length >= 2) {
          final path = Path();
          for (var i = 0; i < points.length; i++) {
            final p = points[i];
            if (p is! List || p.length < 2) continue;
            final px = ((p[0] as num).toDouble() - 0.5) * w;
            final py = ((p[1] as num).toDouble() - 0.5) * h;
            if (i == 0) {
              path.moveTo(px, py);
            } else {
              path.lineTo(px, py);
            }
          }
          canvas.drawPath(
            path,
            Paint()
              ..color = color.withOpacity(opacity)
              ..style = PaintingStyle.stroke
              ..strokeWidth = 2.5
              ..strokeCap = StrokeCap.round,
          );
        }
        break;
      case 'shape':
      default:
        final rect = Rect.fromCenter(center: Offset.zero, width: w, height: h);
        final kind = (e.visual('shape_kind') as String?) ?? 'rect';
        if (kind == 'circle' || kind == 'oval') {
          canvas.drawOval(rect, paint);
        } else if (kind == 'triangle') {
          final path = Path()
            ..moveTo(0, -h / 2)
            ..lineTo(w / 2, h / 2)
            ..lineTo(-w / 2, h / 2)
            ..close();
          canvas.drawPath(path, paint);
        } else {
          canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(6)), paint);
        }
        if (borderStyle == true || borderStyle == 'solid') {
          canvas.drawRRect(
            RRect.fromRectAndRadius(rect, const Radius.circular(6)),
            Paint()
              ..color = Colors.white.withOpacity(0.6 * opacity)
              ..style = PaintingStyle.stroke
              ..strokeWidth = 1.5,
          );
        }
    }
    canvas.restore();
  }

  void _drawSelectionRing(Canvas canvas, Size size, HabitatEntity e) {
    final center = Offset(e.position[0] * size.width, e.position[1] * size.height);
    final w = e.dimensions[0] * size.width, h = e.dimensions[1] * size.height;
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(e.orientation * math.pi / 180.0);
    final rect = Rect.fromCenter(center: Offset.zero, width: w + 10, height: h + 10);
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(8)),
      Paint()
        ..color = Colors.cyanAccent.withOpacity(0.85)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(_HabitatPainter old) =>
      old.entities != entities || old.selectedEntityId != selectedEntityId;
}
