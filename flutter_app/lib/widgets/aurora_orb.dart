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
    // Canvas is 3× the orb radius so the wave bands have horizontal breathing room.
    final canvas = size * 3.0;
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
  final double pulse;
  final OrbState state;
  final double orbRadius;

  const _OrbPainter({
    required this.pulse,
    required this.state,
    required this.orbRadius,
  });

  // Per-band phase offsets so waves move independently.
  static const _phaseOff = [0.0, 1.26, 2.51, 3.77, 5.03];

  // Axis colors: X=cyan  T=spring-green  N=amber  B=violet  A=gold
  static const _colors = [
    Color(0xFF00CFFF),
    Color(0xFF00FF88),
    Color(0xFFFF8800),
    Color(0xFFCC44FF),
    Color(0xFFFFD700),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width  / 2;
    final cy = size.height / 2;
    final center = Offset(cx, cy);
    final r = orbRadius;

    // 1. Wave bands behind the orb.
    _drawWaveBands(canvas, size, cx, cy, r);

    // 2. Soft glow bloom behind the orb (state-dependent).
    if (state != OrbState.dormant) {
      for (int i = 3; i >= 1; i--) {
        canvas.drawCircle(
          center,
          r * (1.0 + i * 0.20 * pulse),
          Paint()
            ..color      = const Color(0xFFA020F0).withOpacity((0.18 / i) * pulse)
            ..maskFilter = MaskFilter.blur(BlurStyle.normal, 14.0 * pulse),
        );
      }
    }

    // 3. Orb sphere — drawn on top so it sits inside the wave bands.
    final Color core;
    final Color edge;
    switch (state) {
      case OrbState.listening:
        core = const Color(0xFFD070FF); edge = const Color(0xFF5500AA);
      case OrbState.thinking:
        core = const Color(0xFF90D0FF); edge = const Color(0xFF003080);
      case OrbState.speaking:
        core = const Color(0xFFFFB0FF); edge = const Color(0xFF7700AA);
      case OrbState.dormant:
        core = const Color(0xFF7030C0); edge = const Color(0xFF1A0035);
    }

    canvas.drawCircle(
      center, r,
      Paint()..shader = RadialGradient(
        center: const Alignment(-0.3, -0.3),
        colors: [core.withOpacity(0.96), edge.withOpacity(0.92)],
      ).createShader(Rect.fromCircle(center: center, radius: r)),
    );

    // 4. Shimmer highlight.
    canvas.drawCircle(
      Offset(cx - r * 0.22, cy - r * 0.22), r * 0.36,
      Paint()
        ..color      = Colors.white.withOpacity(0.16 + 0.08 * pulse)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12),
    );

    // 5. Listening arcs.
    if (state == OrbState.listening) {
      final ap = Paint()
        ..color       = Colors.white.withOpacity(0.50 * pulse)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = 1.8
        ..strokeCap   = StrokeCap.round;
      for (int i = 0; i < 3; i++) {
        final sweep = math.pi * (0.32 + 0.14 * pulse);
        canvas.drawArc(
          Rect.fromCircle(center: center, radius: r * (0.64 + i * 0.14)),
          -sweep / 2 + math.pi / 2, sweep, false, ap,
        );
      }
    }

    // ── Front half of the bands ──────────────────────────────────────────────
    // Thin and partially transparent so the orb remains readable while the
    // waves still feel like they wrap around it.
    _drawElectricBands(canvas, center, r, frontPass: true);
  }

  void _drawWaveBands(Canvas canvas, Size size, double cx, double cy, double r) {
    // 5 horizontal sine-wave bands evenly distributed across ±1.0r from center.
    // Sphere is drawn on top — it naturally sits inside the band stack.
    //
    // Amplitude is very small at idle (barely a shimmer), rises when she speaks.
    // 1.5 cycles across the canvas width keeps the wave smooth and readable.

    final baseAmp = switch (state) {
      OrbState.speaking  => r * 0.22,
      OrbState.listening => r * 0.09,
      OrbState.thinking  => r * 0.06,
      OrbState.dormant   => r * 0.022,
    };

    final baseOpacity = switch (state) {
      OrbState.speaking  => 0.72,
      OrbState.listening => 0.40,
      OrbState.thinking  => 0.24,
      OrbState.dormant   => 0.08,
    };

    final strokeW = switch (state) {
      OrbState.speaking  => 2.0,
      OrbState.listening => 1.5,
      OrbState.thinking  => 1.4,
      OrbState.dormant   => 1.2,
    };
    final activeIndex = switch (state) {
      OrbState.listening => 0,
      OrbState.thinking  => 1,
      OrbState.speaking  => 4,
      OrbState.dormant   => -1,
    };

    for (int i = 0; i < 5; i++) {
      final phi    = pulse * math.pi * 2 + _phaseOff[i];
      final sinPhi = math.sin(phi);

      // Spread bands evenly: i=0 → top (−r), i=4 → bottom (+r)
      final yBand = cy + r * ((i / 4.0) * 2.0 - 1.0);

      // Amplitude breathes independently per band
      final amp = baseAmp * (0.78 + 0.22 * (sinPhi + 1) / 2);

      // Opacity modulated slightly per band
      final op = (baseOpacity * (0.82 + 0.18 * (sinPhi + 1) / 2)).clamp(0.0, 1.0);

      final path = Path();
      const steps = 120;
      for (int s = 0; s <= steps; s++) {
        final t = s / steps;
        final x = size.width * t;
        // 1.5 cycles — smooth, not jagged
        final y = yBand + amp * math.sin(t * math.pi * 3.0 + phi);
        s == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
      }

      // Crisp main edge
      canvas.drawPath(path, Paint()
        ..color       = _colors[i].withOpacity(op)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = strokeW
        ..strokeCap   = StrokeCap.round);

      // Soft glow — no heavy blur, just a wider very-transparent pass
      canvas.drawPath(path, Paint()
        ..color       = _colors[i].withOpacity(op * 0.15)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = strokeW * 4.0
        ..strokeCap   = StrokeCap.round);
    }
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state || old.orbRadius != orbRadius;
}
