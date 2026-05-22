import 'dart:math' as math;
import 'package:flutter/material.dart';

enum OrbState { dormant, listening, thinking, speaking }

class AuroraOrb extends StatelessWidget {
  final OrbState state;
  final double size;
  final Animation<double> pulse;
  final VoidCallback? onTap;

  const AuroraOrb({
    super.key,
    required this.state,
    required this.pulse,
    this.size = 120,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedBuilder(
        animation: pulse,
        builder: (_, __) => CustomPaint(
          size: Size(size, size),
          painter: _OrbPainter(pulse: pulse.value, state: state),
        ),
      ),
    );
  }
}

class _OrbPainter extends CustomPainter {
  final double pulse; // 0.0 → 1.0
  final OrbState state;

  const _OrbPainter({required this.pulse, required this.state});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final r      = size.width / 2;

    // ── Outer glow rings (visible when active) ───────────────────────────
    if (state != OrbState.dormant) {
      for (int i = 3; i >= 1; i--) {
        final ringR   = r * (1.0 + i * 0.18 * pulse);
        final opacity = (0.25 / i) * pulse;
        canvas.drawCircle(
          center,
          ringR,
          Paint()
            ..color = const Color(0xFFA020F0).withOpacity(opacity)
            ..maskFilter = MaskFilter.blur(BlurStyle.normal, 12.0 * pulse),
        );
      }
    }

    // ── Main body gradient ───────────────────────────────────────────────
    final Color core;
    final Color edge;
    switch (state) {
      case OrbState.listening:
        core = const Color(0xFFD070FF);
        edge = const Color(0xFF5500AA);
      case OrbState.thinking:
        core = const Color(0xFF90D0FF);
        edge = const Color(0xFF003080);
      case OrbState.speaking:
        core = const Color(0xFFFFB0FF);
        edge = const Color(0xFF7700AA);
      case OrbState.dormant:
        core = const Color(0xFF7030C0);
        edge = const Color(0xFF1A0035);
    }

    final gradient = RadialGradient(
      center: Alignment(-0.3, -0.3),
      colors: [core.withOpacity(0.95), edge.withOpacity(0.90)],
    );
    canvas.drawCircle(
      center, r,
      Paint()
        ..shader = gradient.createShader(
          Rect.fromCircle(center: center, radius: r),
        ),
    );

    // ── Inner shimmer highlight ──────────────────────────────────────────
    final shimmerR = r * 0.38;
    canvas.drawCircle(
      Offset(center.dx - r * 0.22, center.dy - r * 0.22),
      shimmerR,
      Paint()
        ..color = Colors.white.withOpacity(0.18 + 0.08 * pulse)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
    );

    // ── Listening waveform arc (three arcs that grow/shrink) ─────────────
    if (state == OrbState.listening) {
      final arcPaint = Paint()
        ..color = Colors.white.withOpacity(0.55 * pulse)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0
        ..strokeCap = StrokeCap.round;
      for (int i = 0; i < 3; i++) {
        final arcR   = r * (0.62 + i * 0.14);
        final sweep  = math.pi * (0.35 + 0.15 * pulse);
        final start  = -sweep / 2 + math.pi / 2;
        canvas.drawArc(
          Rect.fromCircle(center: center, radius: arcR),
          start, sweep, false, arcPaint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state;
}
