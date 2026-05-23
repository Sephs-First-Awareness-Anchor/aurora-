import 'dart:math' as math;
import 'package:flutter/material.dart';

enum OrbState { dormant, listening, thinking, speaking }

class AuroraOrb extends StatelessWidget {
  final OrbState state;
  /// Diameter of the orb sphere itself. The full widget is larger to fit
  /// the aurora bands that radiate outward.
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
    // Canvas is 2.6× the orb so aurora bands have room without clipping.
    final canvas = size * 2.6;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedBuilder(
        animation: pulse,
        builder: (_, __) => CustomPaint(
          size: Size(canvas, canvas),
          painter: _OrbPainter(
            pulse:     pulse.value,
            state:     state,
            orbRadius: size / 2,
          ),
        ),
      ),
    );
  }
}

class _OrbPainter extends CustomPainter {
  final double pulse;       // 0.0 → 1.0 (easeInOut, repeating reverse)
  final OrbState state;
  final double orbRadius;   // radius of the sphere, NOT half of canvas

  const _OrbPainter({
    required this.pulse,
    required this.state,
    required this.orbRadius,
  });

  // Band descriptors: (radiusMult, phaseOffset, color, strokeWidth)
  static const _bands = [
    (1.30, 0.00, Color(0xFF00FFCC), 4.5),   // cyan-green
    (1.58, 1.26, Color(0xFFAA00FF), 3.5),   // violet
    (1.18, 2.51, Color(0xFF00AAFF), 3.0),   // sky blue
    (1.80, 3.77, Color(0xFF44FF88), 3.0),   // aurora green
    (1.45, 5.03, Color(0xFFFF44DD), 2.5),   // magenta pink
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final r      = orbRadius;

    // 1. Aurora bands (drawn beneath everything else)
    _drawAuroraBands(canvas, center, r);

    // 2. Outer glow rings
    if (state != OrbState.dormant) {
      for (int i = 3; i >= 1; i--) {
        final ringR   = r * (1.0 + i * 0.18 * pulse);
        final opacity = (0.25 / i) * pulse;
        canvas.drawCircle(
          center,
          ringR,
          Paint()
            ..color      = const Color(0xFFA020F0).withOpacity(opacity)
            ..maskFilter = MaskFilter.blur(BlurStyle.normal, 12.0 * pulse),
        );
      }
    }

    // 3. Main body gradient
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

    canvas.drawCircle(
      center, r,
      Paint()..shader = RadialGradient(
        center: const Alignment(-0.3, -0.3),
        colors: [core.withOpacity(0.95), edge.withOpacity(0.90)],
      ).createShader(Rect.fromCircle(center: center, radius: r)),
    );

    // 4. Inner shimmer highlight
    canvas.drawCircle(
      Offset(center.dx - r * 0.22, center.dy - r * 0.22),
      r * 0.38,
      Paint()
        ..color      = Colors.white.withOpacity(0.18 + 0.08 * pulse)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
    );

    // 5. Listening waveform arcs
    if (state == OrbState.listening) {
      final arcPaint = Paint()
        ..color       = Colors.white.withOpacity(0.55 * pulse)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = 2.0
        ..strokeCap   = StrokeCap.round;
      for (int i = 0; i < 3; i++) {
        final arcR  = r * (0.62 + i * 0.14);
        final sweep = math.pi * (0.35 + 0.15 * pulse);
        canvas.drawArc(
          Rect.fromCircle(center: center, radius: arcR),
          -sweep / 2 + math.pi / 2,
          sweep,
          false,
          arcPaint,
        );
      }
    }
  }

  void _drawAuroraBands(Canvas canvas, Offset center, double r) {
    // Intensity rises with activity so bands "come alive" when she speaks.
    final intensity = switch (state) {
      OrbState.speaking  => 0.80 + 0.20 * pulse,
      OrbState.listening => 0.45 + 0.30 * pulse,
      OrbState.thinking  => 0.30 + 0.25 * pulse,
      OrbState.dormant   => 0.08 + 0.07 * pulse,
    };

    for (final (rMult, phase, color, strokeW) in _bands) {
      final bandR  = r * rMult;
      // Wobble amplitude grows with pulse so bands breathe
      final wobble = r * (0.12 + 0.12 * pulse);

      final path = Path();
      const steps = 80;
      for (var i = 0; i <= steps; i++) {
        final t     = i / steps;
        final angle = t * math.pi * 2;
        // Sinusoidal ripple — phase and pulse keep each band moving differently
        final wave = wobble * math.sin(angle * 4 + phase + pulse * math.pi * 2);
        final px   = center.dx + (bandR + wave) * math.cos(angle);
        final py   = center.dy + (bandR + wave) * math.sin(angle);
        i == 0 ? path.moveTo(px, py) : path.lineTo(px, py);
      }
      path.close();

      canvas.drawPath(
        path,
        Paint()
          ..color       = color.withOpacity((intensity * 0.60).clamp(0.0, 1.0))
          ..style       = PaintingStyle.stroke
          ..strokeWidth = strokeW + pulse * 2.5
          ..maskFilter  = MaskFilter.blur(
                            BlurStyle.normal,
                            (4 + pulse * 12).clamp(1.0, 20.0),
                          ),
      );
    }
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state || old.orbRadius != orbRadius;
}
