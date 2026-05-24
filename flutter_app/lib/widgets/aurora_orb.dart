import 'dart:math' as math;
import 'package:flutter/material.dart';

enum OrbState { dormant, listening, thinking, speaking }

class AuroraOrb extends StatelessWidget {
  final OrbState state;
  /// Diameter of the orb sphere itself. Canvas is larger to fit orbital rings.
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
    // Canvas is 2.6× the orb so orbital rings have room at all inclinations.
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

  // Orbital inclination angles (radians) — each ring wraps at a different plane.
  static final _orbitAngles = [15.0, 48.0, 80.0, -22.0, -55.0]
      .map((d) => d * math.pi / 180.0)
      .toList();

  // Radius multipliers — slight variation so rings don't stack on each other.
  static const _radiusMul = [1.30, 1.42, 1.36, 1.24, 1.48];

  // Per-ring phase offsets so they ripple out of sync.
  static const _phaseOff = [0.0, 1.26, 2.51, 3.77, 5.03];

  // Axis colors: X=cyan, T=spring-green, N=amber, B=violet, A=gold
  static const _colors = [
    Color(0xFF00CFFF),
    Color(0xFF00FF88),
    Color(0xFFFF8800),
    Color(0xFFCC44FF),
    Color(0xFFFFD700),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final r      = orbRadius;

    // ── Planetary orbital rings ───────────────────────────────────────────────
    // Each ring is a very flat ellipse (7% minor/major ratio) rotated to its
    // orbital inclination. Speaking cycles ring activation through phases;
    // idle holds a low charged ripple on all rings.
    _drawOrbitalRings(canvas, center, r);

    // ── Outer glow pulse ─────────────────────────────────────────────────────
    if (state != OrbState.dormant) {
      for (int i = 3; i >= 1; i--) {
        final ringR   = r * (1.0 + i * 0.18 * pulse);
        final opacity = (0.22 / i) * pulse;
        canvas.drawCircle(
          center, ringR,
          Paint()
            ..color      = const Color(0xFFA020F0).withOpacity(opacity)
            ..maskFilter = MaskFilter.blur(BlurStyle.normal, 12.0 * pulse),
        );
      }
    }

    // ── Main orb body ─────────────────────────────────────────────────────────
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

    // ── Inner shimmer highlight ───────────────────────────────────────────────
    canvas.drawCircle(
      Offset(center.dx - r * 0.22, center.dy - r * 0.22),
      r * 0.38,
      Paint()
        ..color      = Colors.white.withOpacity(0.18 + 0.08 * pulse)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
    );

    // ── Listening waveform arcs ───────────────────────────────────────────────
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

  void _drawOrbitalRings(Canvas canvas, Offset center, double r) {
    // Base intensity drives the overall ring brightness per state.
    final baseIntensity = switch (state) {
      OrbState.speaking  => 0.90,
      OrbState.listening => 0.52,
      OrbState.thinking  => 0.36,
      OrbState.dormant   => 0.10,
    };

    for (int i = 0; i < 5; i++) {
      final phi    = pulse * math.pi * 2 + _phaseOff[i];
      final sinPhi = math.sin(phi);

      // Each ring's activation follows its own sinusoidal phase — rings cycle
      // through brightness independently so they never all peak at once.
      // When speaking the amplitude is much higher, creating a visible sweep.
      final rippleAmt  = state == OrbState.speaking ? 0.55 : 0.10;
      final activation = ((sinPhi + 1) / 2) * rippleAmt;  // 0..rippleAmt
      final brightness = baseIntensity + activation;

      final rMajor = r * _radiusMul[i];
      final rMinor = rMajor * 0.07;   // very flat — planetary ring proportions

      final strokeAlpha = (brightness * 255).clamp(0, 255).toInt();
      final strokeW = state == OrbState.speaking
          ? (1.8 + activation * 6.0)
          : (1.0 + activation * 2.0);

      canvas.save();
      // Rotate around the orb center to set the orbital inclination.
      canvas.translate(center.dx, center.dy);
      canvas.rotate(_orbitAngles[i]);

      final rect = Rect.fromCenter(
        center: Offset.zero,
        width:  rMajor * 2,
        height: rMinor * 2,
      );

      // Main ring edge — crisp stroke
      canvas.drawOval(
        rect,
        Paint()
          ..color       = _colors[i].withOpacity(strokeAlpha / 255.0)
          ..style       = PaintingStyle.stroke
          ..strokeWidth = strokeW,
      );

      // Glow pass — wider, very low alpha for the charged electric halo
      canvas.drawOval(
        rect,
        Paint()
          ..color       = _colors[i].withOpacity((strokeAlpha * 0.28 / 255.0).clamp(0.0, 1.0))
          ..style       = PaintingStyle.stroke
          ..strokeWidth = strokeW * 3.5
          ..maskFilter  = MaskFilter.blur(BlurStyle.normal, strokeW * 2.0),
      );

      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state || old.orbRadius != orbRadius;
}
