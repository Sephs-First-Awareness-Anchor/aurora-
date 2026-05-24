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

  static const _phaseOff = [0.0, 1.26, 2.51, 3.77, 5.03];

  static const _colors = [
    Color(0xFF00DDFF),  // electric cyan
    Color(0xFFFF1199),  // hot magenta
    Color(0xFFFF6600),  // plasma orange
    Color(0xFFBB22FF),  // violet
    Color(0xFF00FF88),  // spring green
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final center = Offset(cx, cy);
    final r = orbRadius;

    // Dark interior — the sphere "background" visible through the energy strands.
    // Not a filled ball; just enough darkness to contrast the bands inside the ring.
    canvas.drawCircle(
      center, r * 1.02,
      Paint()
        ..shader = RadialGradient(
          colors: [const Color(0xDD080012), const Color(0x00080012)],
          stops: const [0.55, 1.0],
        ).createShader(Rect.fromCircle(center: center, radius: r * 1.02)),
    );

    // Horizontal convergence streams — fans out at edges, passes through sphere.
    _drawStreams(canvas, size, cx, cy, r);

    // Circular boundary ring — the ring of plasma strands that defines the sphere edge.
    _drawBoundaryRing(canvas, cx, cy, r);

    // Center energy flash.
    _drawFlash(canvas, center, r);
  }

  // ── Horizontal convergence streams ─────────────────────────────────────────

  void _drawStreams(Canvas canvas, Size size, double cx, double cy, double r) {
    final spread = switch (state) {
      OrbState.speaking  => r * 2.1,
      OrbState.listening => r * 1.7,
      OrbState.thinking  => r * 1.3,
      OrbState.dormant   => r * 0.85,
    };
    final baseAmp = switch (state) {
      OrbState.speaking  => r * 0.30,
      OrbState.listening => r * 0.16,
      OrbState.thinking  => r * 0.09,
      OrbState.dormant   => r * 0.025,
    };
    final baseOp = switch (state) {
      OrbState.speaking  => 0.92,
      OrbState.listening => 0.68,
      OrbState.thinking  => 0.42,
      OrbState.dormant   => 0.22,
    };

    const steps       = 160;
    const strandCount = 4;

    for (int i = 0; i < 5; i++) {
      final phi    = pulse * math.pi * 2 + _phaseOff[i];
      final sinPhi = math.sin(phi);
      final op     = (baseOp * (0.72 + 0.28 * (sinPhi + 1) / 2)).clamp(0.0, 1.0);
      final bandFrac = (i / 4.0) * 2.0 - 1.0;

      for (int s = 0; s < strandCount; s++) {
        final sFrac      = strandCount > 1 ? (s / (strandCount - 1.0)) - 0.5 : 0.0;
        final strandBias = sFrac * r * 0.16;
        final sPhase     = phi + s * 0.82 + i * 0.28;
        final strandOp   = op * (0.55 + 0.45 * (1.0 - sFrac.abs() * 1.6).clamp(0.0, 1.0));
        final strokeW    = state == OrbState.dormant ? 0.7 : (s == 1 || s == 2 ? 1.4 : 1.0);

        final path = Path();
        for (int p = 0; p <= steps; p++) {
          final t  = p / steps;
          final x  = size.width * t;
          final d  = (t - 0.5).abs() * 2.0;          // 0 at center, 1 at edges
          final ev = d * d;                            // quadratic taper

          final bandY = cy + (bandFrac * spread + strandBias) * ev;
          final amp   = baseAmp * (0.18 + 0.82 * d) *
                        (0.72 + 0.28 * ((math.sin(sPhase * 1.2 + s * 0.4) + 1) / 2));

          // Two harmonics → organic, non-mechanical look
          final y = bandY
              + amp       * math.sin(t * math.pi * 3.5 + sPhase)
              + amp * 0.4 * math.sin(t * math.pi * 7.5 + sPhase * 1.5);

          p == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
        }

        _drawGlowPath(canvas, path, _colors[i], strandOp, strokeW);
      }
    }
  }

  // ── Circular boundary ring ──────────────────────────────────────────────────

  void _drawBoundaryRing(Canvas canvas, double cx, double cy, double r) {
    final ringOp = switch (state) {
      OrbState.speaking  => 0.90,
      OrbState.listening => 0.65,
      OrbState.thinking  => 0.42,
      OrbState.dormant   => 0.22,
    };

    // 5 slightly-different-radius wobbly ellipses, one per axis color
    for (int i = 0; i < 5; i++) {
      final phi   = pulse * math.pi * 2 + _phaseOff[i];
      final ringR = r * (0.90 + i * 0.045);
      final op    = ringOp * (0.65 + 0.35 * math.sin(phi).abs());

      final path = Path();
      const steps = 200;
      for (int s = 0; s <= steps; s++) {
        final t     = s / steps;
        final angle = t * math.pi * 2;
        // Slight wobble so the ring feels alive, not static
        final wobble = 1.0
            + 0.055 * math.sin(angle * 3 + phi)
            + 0.025 * math.sin(angle * 7 + phi * 1.4);
        final x = cx + ringR * wobble * math.cos(angle);
        final y = cy + ringR * 0.86 * wobble * math.sin(angle); // slight flatness
        s == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
      }
      path.close();

      // Outer glow
      canvas.drawPath(path, Paint()
        ..color       = _colors[i].withOpacity(op * 0.10)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = 12.0);
      // Mid glow
      canvas.drawPath(path, Paint()
        ..color       = _colors[i].withOpacity(op * 0.32)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = 3.0);
      // Core ring
      canvas.drawPath(path, Paint()
        ..color       = _colors[i].withOpacity(op * 0.85)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = 0.85);
    }

    // Scattered energy sparks around the boundary
    _drawSparks(canvas, cx, cy, r, ringOp);
  }

  void _drawSparks(Canvas canvas, double cx, double cy, double r, double baseOp) {
    const sparkAngles = [0.3, 0.9, 1.5, 2.1, 2.7, 3.3, 3.9, 4.5, 5.1, 5.7,
                         0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8, 5.4, 6.0];
    const sparkDists  = [0.95, 1.08, 0.88, 1.15, 0.92, 1.05, 0.82, 1.12,
                         0.98, 1.02, 1.18, 0.85, 1.10, 0.90, 1.06, 0.80,
                         1.14, 0.94, 1.00, 1.08];
    const sparkSizes  = [1.8, 1.2, 2.2, 1.0, 1.6, 2.0, 1.4, 1.8,
                         1.0, 2.4, 1.2, 1.6, 2.0, 1.4, 1.8, 1.2,
                         2.2, 1.0, 1.6, 2.4];

    final count = state == OrbState.dormant ? 8 : 20;
    for (int p = 0; p < count && p < sparkAngles.length; p++) {
      final angle = sparkAngles[p] + pulse * 0.25;
      final dist  = r * sparkDists[p];
      final px    = cx + dist * math.cos(angle);
      final py    = cy + dist * 0.86 * math.sin(angle);
      final color = _colors[p % 5];
      final flicker = (math.sin(pulse * math.pi * 5 + p * 1.3) + 1) / 2;
      final op = (baseOp * (0.35 + 0.65 * flicker)).clamp(0.0, 1.0);
      canvas.drawCircle(Offset(px, py), sparkSizes[p], Paint()..color = color.withOpacity(op));
    }
  }

  // ── Center energy flash ─────────────────────────────────────────────────────

  void _drawFlash(Canvas canvas, Offset center, double r) {
    final op = state == OrbState.dormant ? 0.30 : (0.60 + 0.40 * pulse);

    // Radial bloom
    canvas.drawCircle(
      center, r * 0.60,
      Paint()
        ..shader = RadialGradient(
          colors: [
            Colors.white.withOpacity(op * 0.70),
            const Color(0xFFFF8800).withOpacity(op * 0.40),
            const Color(0x00000000),
          ],
          stops: const [0.0, 0.38, 1.0],
        ).createShader(Rect.fromCircle(center: center, radius: r * 0.60)),
    );

    // Tight bright kernel
    final flashR = r * (0.16 + 0.08 * pulse);
    canvas.drawCircle(
      center, flashR,
      Paint()
        ..color      = Colors.white.withOpacity(op)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, flashR * 0.5),
    );
    canvas.drawCircle(center, flashR * 0.35, Paint()..color = Colors.white);
  }

  // ── Shared glow draw helper ─────────────────────────────────────────────────

  void _drawGlowPath(Canvas canvas, Path path, Color color, double op, double w) {
    canvas.drawPath(path, Paint()
      ..color       = color.withOpacity(op * 0.11)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = w * 9.0
      ..strokeCap   = StrokeCap.round);
    canvas.drawPath(path, Paint()
      ..color       = color.withOpacity(op * 0.28)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = w * 3.2
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
