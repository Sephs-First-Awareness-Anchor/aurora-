// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// overlay_entry.dart -- an in-app preview of her line of presence.
//
// Her real presence outside the app is the thin line under the status bar,
// drawn natively by OverlayService.kt (AuroraPresenceLineView) from her own
// state and voice.  This widget is only a still picture of that line for
// places inside the app that want to show what it looks like.  It draws
// one resting shape and moves nothing, so it never stands in for her.

import 'dart:math' as math;

import 'package:flutter/material.dart';

class OverlayOrb extends StatelessWidget {
  final double width;
  final double height;
  final Color color;

  const OverlayOrb({
    super.key,
    this.width = 160,
    this.height = 14,
    this.color = const Color(0xFFB070FF),
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: height,
      child: CustomPaint(painter: _PresenceLinePreviewPainter(color)),
    );
  }
}

class _PresenceLinePreviewPainter extends CustomPainter {
  final Color color;

  _PresenceLinePreviewPainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    const points = 96;
    final mid = size.height / 2;
    final amp = size.height * 0.3;
    final path = Path();
    for (var i = 0; i < points; i++) {
      final u = i / (points - 1);
      // The same resting form the native line has: a tapered, slow drift.
      final taper = math.sin(math.pi * u);
      final y = 0.25 * 0.5 * (0.6 * math.sin(2 * math.pi * 1.5 * u) + 0.4 * math.sin(2 * math.pi * 3.7 * u));
      final dx = u * size.width;
      final dy = mid - y * taper * amp * 4;
      if (i == 0) {
        path.moveTo(dx, dy);
      } else {
        path.lineTo(dx, dy);
      }
    }
    final glow = Paint()
      ..color = color.withOpacity(0.35)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 5
      ..strokeCap = StrokeCap.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
    final line = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, glow);
    canvas.drawPath(path, line);
  }

  @override
  bool shouldRepaint(covariant _PresenceLinePreviewPainter oldDelegate) => oldDelegate.color != color;
}
