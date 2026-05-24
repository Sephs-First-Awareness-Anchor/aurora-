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
    // Canvas is 2.6× the orb so planetary waveform rings have room to flow.
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

  // Orbital inclination angles (radians) — each sound ring wraps at a different plane.
  static final _orbitAngles = [12.0, 34.0, 58.0, -24.0, -48.0]
      .map((d) => d * math.pi / 180.0)
      .toList();

  // Radius multipliers — slight variation so rings don't stack on each other.
  static const _radiusMul = [1.22, 1.34, 1.47, 1.60, 1.73];

  // Per-ring phase offsets so the waveform never stacks into one flat stripe.
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

    // ── Planetary waveform rings ─────────────────────────────────────────────
    // Drawn behind the orb so Aurora sits inside the surrounding sound field.
    _drawWaveformRings(canvas, center, r);

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
        core = const Color(0xFF7B38D8);
        edge = const Color(0xFF120026);
      case OrbState.thinking:
        core = const Color(0xFF2F7FD9);
        edge = const Color(0xFF061229);
      case OrbState.speaking:
        core = const Color(0xFFB83CFF);
        edge = const Color(0xFF170020);
      case OrbState.dormant:
        core = const Color(0xFF3B1C68);
        edge = const Color(0xFF08000F);
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
        ..color      = Colors.white.withOpacity(0.10 + 0.06 * pulse)
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

  void _drawWaveformRings(Canvas canvas, Offset center, double r) {
    // Base intensity drives the overall ring brightness per state.
    final baseIntensity = switch (state) {
      OrbState.speaking  => 0.90,
      OrbState.listening => 0.52,
      OrbState.thinking  => 0.36,
      OrbState.dormant   => 0.10,
    };
    final activeIndex = switch (state) {
      OrbState.listening => 0,
      OrbState.thinking  => 1,
      OrbState.speaking  => 4,
      OrbState.dormant   => -1,
    };

    for (int i = 0; i < 5; i++) {
      final active = i == activeIndex;
      final phi = pulse * math.pi * 2 + _phaseOff[i];
      final bandPulse = (math.sin(phi) + 1.0) / 2.0;
      final rippleAmp = active
          ? (state == OrbState.speaking ? 0.16 : 0.095)
          : (state == OrbState.dormant ? 0.012 : 0.032);
      final amplitude = r * rippleAmp * (0.75 + bandPulse * 0.55);
      final brightness = (active ? baseIntensity + bandPulse * 0.55 : baseIntensity * 0.55 + bandPulse * 0.16)
          .clamp(0.0, 1.0);
      final strokeAlpha = (brightness * 255).clamp(0, 255).toInt();
      final strokeW = active
          ? (2.0 + bandPulse * (state == OrbState.speaking ? 4.0 : 2.0))
          : (0.9 + bandPulse * 0.8);

      final path = Path();
      final major = r * _radiusMul[i];
      final minor = major * 0.24;
      const steps = 160;
      for (int s = 0; s <= steps; s++) {
        final theta = math.pi * 2.0 * s / steps;
        final wave = math.sin(theta * 18.0 + phi) * amplitude;
        final x = center.dx + math.cos(theta) * (major + wave);
        final y = center.dy + math.sin(theta) * (minor + wave * 0.28);
        if (s == 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
      }

      canvas.save();
      canvas.translate(center.dx, center.dy);
      canvas.rotate(_orbitAngles[i]);
      canvas.translate(-center.dx, -center.dy);

      final glowPaint = Paint()
        ..color = _colors[i].withOpacity((strokeAlpha * 0.34 / 255.0).clamp(0.0, 1.0))
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = strokeW * 5.2
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, strokeW * 2.6);
      canvas.drawPath(path, glowPaint);

      final linePaint = Paint()
        ..color = _colors[i].withOpacity(strokeAlpha / 255.0)
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = strokeW;
      canvas.drawPath(path, linePaint);
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state || old.orbRadius != orbRadius;
}
