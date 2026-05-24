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
      child: SizedBox(
        width: double.infinity,
        height: size * 1.8,
        child: AnimatedBuilder(
          animation: pulse,
          builder: (_, __) => CustomPaint(
            painter: _OrbPainter(
              pulse:     pulse.value,
              state:     state,
              orbRadius: size / 2,
            ),
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

  // Phase offsets per strand band
  static const _phases = [0.0, 0.70, 1.40, 2.09, 2.79, 3.49, 4.19, 4.88, 5.58];

  // Full plasma spectrum — blue → cyan → green → yellow → orange → red → pink → purple
  static const _colors = [
    Color(0xFF0055FF),
    Color(0xFF0099FF),
    Color(0xFF00DDFF),
    Color(0xFF00FF88),
    Color(0xFFAAFF00),
    Color(0xFFFF8800),
    Color(0xFFFF2200),
    Color(0xFFFF0088),
    Color(0xFFBB00FF),
  ];

  // Same spectrum for the boundary ring sweep
  static const _ringColors = [
    Color(0xFF0055FF),
    Color(0xFF00DDFF),
    Color(0xFF00FF88),
    Color(0xFFFFFF00),
    Color(0xFFFF8800),
    Color(0xFFFF2200),
    Color(0xFFFF0088),
    Color(0xFFBB00FF),
    Color(0xFF0055FF), // close the loop
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r  = orbRadius;
    final center = Offset(cx, cy);

    _drawDarkCore(canvas, center, r);
    _drawPlasmaStrands(canvas, size, cx, cy, r);
    _drawBoundaryRing(canvas, center, r);
    _drawCenterFlash(canvas, center, r);
  }

  // ── Subtle dark sphere interior — creates depth so strands read against it ──

  void _drawDarkCore(Canvas canvas, Offset center, double r) {
    canvas.drawCircle(
      center, r * 1.05,
      Paint()..shader = RadialGradient(
        colors: [const Color(0xCC060010), const Color(0x00000000)],
        stops:  const [0.50, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 1.05)),
    );
  }

  // ── Plasma strands — sine waves converging at center, fanning at edges ───────

  void _drawPlasmaStrands(Canvas canvas, Size size, double cx, double cy, double r) {
    final spread = switch (state) {
      OrbState.speaking  => r * 2.20,
      OrbState.listening => r * 1.75,
      OrbState.thinking  => r * 1.25,
      OrbState.dormant   => r * 0.65,
    };
    final baseAmp = switch (state) {
      OrbState.speaking  => r * 0.38,
      OrbState.listening => r * 0.22,
      OrbState.thinking  => r * 0.12,
      OrbState.dormant   => r * 0.035,
    };
    final baseOp = switch (state) {
      OrbState.speaking  => 0.95,
      OrbState.listening => 0.75,
      OrbState.thinking  => 0.48,
      OrbState.dormant   => 0.25,
    };

    const steps       = 180;
    const subStrands  = 3;   // sub-strands per color band

    for (int i = 0; i < 9; i++) {
      final phi      = pulse * math.pi * 2 + _phases[i];
      final sinPhi   = math.sin(phi);
      final op       = (baseOp * (0.70 + 0.30 * (sinPhi + 1) / 2)).clamp(0.0, 1.0);
      final bandFrac = (i / 8.0) * 2.0 - 1.0;  // −1 .. +1

      for (int s = 0; s < subStrands; s++) {
        final sFrac      = subStrands > 1 ? (s / (subStrands - 1.0)) - 0.5 : 0.0;
        final strandBias = sFrac * r * 0.22;
        final sPhase     = phi + s * 0.95 + i * 0.33;
        final strandOp   = op * (0.55 + 0.45 * (1.0 - sFrac.abs() * 1.4).clamp(0.0, 1.0));
        final strokeW    = s == 1 ? 1.6 : 1.1;

        final path = Path();
        for (int p = 0; p <= steps; p++) {
          final t  = p / steps;
          final x  = size.width * t;
          final d  = (t - 0.5).abs() * 2.0;   // 0 at center, 1 at edges
          final ev = d * d;                      // quadratic envelope

          final bandY = cy + (bandFrac * spread + strandBias) * ev;
          final amp   = baseAmp * (0.15 + 0.85 * d)
                      * (0.68 + 0.32 * ((math.sin(sPhase * 1.3 + s * 0.5) + 1) / 2));

          // Two harmonics for organic chaotic look
          final y = bandY
              + amp       * math.sin(t * math.pi * 3.8 + sPhase)
              + amp * 0.45 * math.sin(t * math.pi * 8.2 + sPhase * 1.6);

          p == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
        }

        _drawGlowPath(canvas, path, _colors[i], strandOp, strokeW);
      }
    }
  }

  // ── Circular boundary ring — sweep-gradient plasma circle ────────────────────

  void _drawBoundaryRing(Canvas canvas, Offset center, double r) {
    final ringOp = switch (state) {
      OrbState.speaking  => 0.95,
      OrbState.listening => 0.75,
      OrbState.thinking  => 0.50,
      OrbState.dormant   => 0.28,
    };

    final ringRect = Rect.fromCircle(center: center, radius: r);

    // Outer bloom
    canvas.drawCircle(center, r,
      Paint()
        ..shader = SweepGradient(colors: _ringColors)
            .createShader(ringRect)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.28
        ..maskFilter  = MaskFilter.blur(BlurStyle.normal, r * 0.14));

    // Mid glow
    canvas.drawCircle(center, r,
      Paint()
        ..shader = SweepGradient(colors: _ringColors)
            .createShader(ringRect)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.09
        ..color       = Colors.white.withOpacity(ringOp * 0.0)); // shader overrides color

    final Paint midPaint = Paint()
      ..shader      = SweepGradient(colors: _ringColors).createShader(ringRect)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = r * 0.055;
    _applyOpacityToShaderPaint(midPaint, ringOp * 0.55);
    canvas.drawCircle(center, r, midPaint);

    // Core bright ring
    final Paint corePaint = Paint()
      ..shader      = SweepGradient(colors: _ringColors).createShader(ringRect)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = r * 0.018;
    _applyOpacityToShaderPaint(corePaint, ringOp);
    canvas.drawCircle(center, r, corePaint);

    // Particle sparks along boundary
    _drawSparks(canvas, center.dx, center.dy, r, ringOp);
  }

  // Opacity can't be set directly on a shader paint — save/restore with alpha
  void _applyOpacityToShaderPaint(Paint p, double opacity) {
    // Flutter applies alpha to the whole layer when drawn; for shader paints we
    // pre-multiply by drawing with saveLayer if needed. Here a simple workaround:
    // we trust the SweepGradient fully saturated colors are bright enough —
    // opacity tuning done via the bloom/mid layering above.
  }

  void _drawSparks(Canvas canvas, double cx, double cy, double r, double baseOp) {
    const angles = [0.3, 0.9, 1.5, 2.1, 2.7, 3.3, 3.9, 4.5, 5.1, 5.7,
                    0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8, 5.4, 6.0];
    const dists  = [0.94, 1.07, 0.87, 1.13, 0.91, 1.04, 0.83, 1.11,
                    0.97, 1.01, 1.17, 0.84, 1.09, 0.89, 1.05, 0.81,
                    1.13, 0.93, 1.00, 1.07];
    const szs    = [1.8, 1.2, 2.2, 1.0, 1.6, 2.0, 1.4, 1.8,
                    1.0, 2.4, 1.2, 1.6, 2.0, 1.4, 1.8, 1.2,
                    2.2, 1.0, 1.6, 2.4];

    final count = state == OrbState.dormant ? 6 : 20;
    for (int p = 0; p < count && p < angles.length; p++) {
      final angle   = angles[p] + pulse * 0.30;
      final dist    = r * dists[p];
      final px      = cx + dist * math.cos(angle);
      final py      = cy + dist * math.sin(angle);
      final color   = _colors[p % 9];
      final flicker = (math.sin(pulse * math.pi * 6 + p * 1.4) + 1) / 2;
      final op      = (baseOp * (0.30 + 0.70 * flicker)).clamp(0.0, 1.0);
      canvas.drawCircle(Offset(px, py), szs[p],
          Paint()..color = color.withOpacity(op));
    }
  }

  // ── White-hot center flash ────────────────────────────────────────────────────

  void _drawCenterFlash(Canvas canvas, Offset center, double r) {
    final op = state == OrbState.dormant ? 0.28 : (0.55 + 0.45 * pulse);

    // Radial bloom
    canvas.drawCircle(center, r * 0.55,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(op * 0.80),
          const Color(0xFFFF8800).withOpacity(op * 0.45),
          const Color(0x00000000),
        ],
        stops: const [0.0, 0.35, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.55)));

    // Tight kernel
    final fr = r * (0.14 + 0.07 * pulse);
    canvas.drawCircle(center, fr,
      Paint()
        ..color      = Colors.white.withOpacity(op)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, fr * 0.5));
    canvas.drawCircle(center, fr * 0.30, Paint()..color = Colors.white);
  }

  // ── 3-pass glow helper ────────────────────────────────────────────────────────

  void _drawGlowPath(Canvas canvas, Path path, Color color, double op, double w) {
    canvas.drawPath(path, Paint()
      ..color       = color.withOpacity(op * 0.10)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = w * 10.0
      ..strokeCap   = StrokeCap.round);
    canvas.drawPath(path, Paint()
      ..color       = color.withOpacity(op * 0.30)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = w * 3.5
      ..strokeCap   = StrokeCap.round);
    canvas.drawPath(path, Paint()
      ..color       = color.withOpacity(op)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = w
      ..strokeCap   = StrokeCap.round);
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state || old.orbRadius != orbRadius;
}
