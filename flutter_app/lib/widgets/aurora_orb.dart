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

  // Stacked horizontal bands. The orb sits inside this field like a planet
  // inside electrified rings.
  static const _bandOffsets = [-0.66, -0.34, 0.0, 0.34, 0.66];

  // Per-band phase offsets so the waveform never stacks into one flat stripe.
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

    // ── Back half of the electric sound bands ────────────────────────────────
    _drawElectricBands(canvas, center, r, frontPass: false);

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

    // ── Front half of the bands ──────────────────────────────────────────────
    // Thin and partially transparent so the orb remains readable while the
    // waves still feel like they wrap around it.
    _drawElectricBands(canvas, center, r, frontPass: true);
  }

  void _drawElectricBands(
    Canvas canvas,
    Offset center,
    double r, {
    required bool frontPass,
  }) {
    // Base intensity drives the overall band brightness per state.
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
          ? (state == OrbState.speaking ? 0.24 : 0.15)
          : (state == OrbState.dormant ? 0.025 : 0.065);
      final amplitude = r * rippleAmp * (0.75 + bandPulse * 0.55);
      final brightness = (active ? baseIntensity + bandPulse * 0.55 : baseIntensity * 0.55 + bandPulse * 0.16)
          .clamp(0.0, 1.0);
      final alphaScale = frontPass ? 0.66 : 1.0;
      final strokeAlpha = (brightness * 255 * alphaScale).clamp(0, 255).toInt();
      final strokeW = (active
              ? (2.2 + bandPulse * (state == OrbState.speaking ? 4.6 : 2.4))
              : (1.0 + bandPulse * 1.0)) *
          (frontPass ? 0.76 : 1.0);

      final path = Path();
      final major = r * 1.82;
      final yBase = center.dy + r * _bandOffsets[i];
      final start = frontPass ? -0.58 : -1.0;
      final end = frontPass ? 0.58 : 1.0;
      const steps = 132;
      for (int s = 0; s <= steps; s++) {
        final u = start + (end - start) * s / steps;
        final x = center.dx + u * major;
        final ringCurve = math.sin(u * math.pi) * r * 0.12;
        final envelope = 0.34 + 0.66 * math.sqrt((1.0 - u * u).clamp(0.0, 1.0));
        final carrier = math.sin((u + 1.0) * math.pi * 7.0 + phi);
        final jitter = math.sin((u + 1.0) * math.pi * 19.0 + phi * 1.7) * amplitude * 0.22;
        final y = yBase + ringCurve + carrier * amplitude * envelope + jitter;
        if (s == 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
      }

      final separatorPaint = Paint()
        ..color = Colors.black.withOpacity(frontPass ? 0.58 : 0.82)
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = strokeW + (active ? 4.4 : 3.2);
      canvas.drawPath(path, separatorPaint);

      final glowPaint = Paint()
        ..color = _colors[i].withOpacity((strokeAlpha * 0.34 / 255.0).clamp(0.0, 1.0))
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = strokeW * (frontPass ? 3.0 : 5.4)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, strokeW * 2.4);
      canvas.drawPath(path, glowPaint);

      final linePaint = Paint()
        ..color = _colors[i].withOpacity(strokeAlpha / 255.0)
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = strokeW;
      canvas.drawPath(path, linePaint);
    }
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state || old.orbRadius != orbRadius;
}
