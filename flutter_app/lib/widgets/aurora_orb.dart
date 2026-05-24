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

  static const _aurora = [
    Color(0xFF00FF88),  // spring green
    Color(0xFF00CCAA),  // teal
    Color(0xFF00DDFF),  // cyan
    Color(0xFF8833FF),  // violet
    Color(0xFFCC00FF),  // purple
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r  = orbRadius;

    _drawAuroraBg(canvas, size, cx, cy, r);
    _drawEqBars(canvas, size, cx, cy, r);
    _drawBeam(canvas, size, cx, cy, r);
    _drawOrb(canvas, Offset(cx, cy), r);
  }

  // ── Aurora borealis curtain bands (background) ──────────────────────────────

  void _drawAuroraBg(Canvas canvas, Size size, double cx, double cy, double r) {
    final op = switch (state) {
      OrbState.speaking  => 0.65,
      OrbState.listening => 0.44,
      OrbState.thinking  => 0.26,
      OrbState.dormant   => 0.10,
    };

    for (int i = 0; i < 5; i++) {
      final phi   = pulse * math.pi * 2 + _phaseOff[i];
      final bandY = size.height * (0.14 + i * 0.11);
      final amp   = size.height * 0.055;
      final color = _aurora[i];

      final path = Path();
      const steps = 120;
      for (int s = 0; s <= steps; s++) {
        final t = s / steps;
        final x = t * size.width;
        final y = bandY + amp * math.sin(t * math.pi * 2.8 + phi)
                        + amp * 0.4 * math.sin(t * math.pi * 5.5 + phi * 1.3);
        s == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
      }

      // Wide luminous band
      canvas.drawPath(path, Paint()
        ..color       = color.withOpacity(op * 0.20)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = size.height * 0.14
        ..strokeCap   = StrokeCap.round);
      // Bright core ribbon
      canvas.drawPath(path, Paint()
        ..color       = color.withOpacity(op * 0.60)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = 1.5);
    }
  }

  // ── EQ waveform bars (radiating outward from orb on both sides) ─────────────

  void _drawEqBars(Canvas canvas, Size size, double cx, double cy, double r) {
    final maxH = switch (state) {
      OrbState.speaking  => r * 1.40,
      OrbState.listening => r * 0.88,
      OrbState.thinking  => r * 0.52,
      OrbState.dormant   => r * 0.18,
    };

    final barW    = math.max(2.0, r * 0.065);
    final barGap  = math.max(1.0, r * 0.028);
    final barStep = barW + barGap;
    final nBars   = ((cx - r - barStep * 2) / barStep).floor().clamp(0, 40);

    for (final side in [-1, 1]) {
      for (int bi = 0; bi < nBars; bi++) {
        final distFrac = (bi + 0.5) / nBars;
        final barCx    = cx + side * (r + (bi + 1) * barStep);

        if (barCx < 0 || barCx > size.width) continue;

        // Height: peaked envelope × animated sine per bar
        final phi  = pulse * math.pi * 2 + bi * 0.24 + (side < 0 ? 0.9 : 0.0);
        final anim = (math.sin(phi) + 1) / 2;
        // Envelope: tallest in inner third, tapering to edges
        final env  = math.pow(1.0 - distFrac, 0.5).toDouble()
                   * (0.6 + 0.4 * math.sin(distFrac * math.pi));
        final h    = maxH * env * (0.22 + 0.78 * anim);

        if (h < 2) continue;

        // Color: white/orange at sphere edge → magenta → cyan → green at far edge
        final Color c;
        if (distFrac < 0.22) {
          c = Color.lerp(const Color(0xFFFFFFFF), const Color(0xFFFF8800), distFrac / 0.22)!;
        } else if (distFrac < 0.48) {
          c = Color.lerp(const Color(0xFFFF8800), const Color(0xFFFF1199), (distFrac - 0.22) / 0.26)!;
        } else if (distFrac < 0.74) {
          c = Color.lerp(const Color(0xFFFF1199), const Color(0xFF00DDFF), (distFrac - 0.48) / 0.26)!;
        } else {
          c = Color.lerp(const Color(0xFF00DDFF), const Color(0xFF00FF88), (distFrac - 0.74) / 0.26)!;
        }

        final op = (0.40 + 0.60 * anim).clamp(0.0, 1.0);

        // 3-pass glow: outer bloom, mid glow, core bar
        canvas.drawRect(
          Rect.fromLTRB(barCx - barW * 3.2, cy - h * 1.15, barCx + barW * 3.2, cy + h * 1.15),
          Paint()..color = c.withOpacity(op * 0.10));
        canvas.drawRect(
          Rect.fromLTRB(barCx - barW * 1.5, cy - h, barCx + barW * 1.5, cy + h),
          Paint()..color = c.withOpacity(op * 0.28));
        canvas.drawRect(
          Rect.fromLTRB(barCx - barW * 0.5, cy - h, barCx + barW * 0.5, cy + h),
          Paint()..color = c.withOpacity(op));
      }
    }
  }

  // ── Vertical energy beam through center ─────────────────────────────────────

  void _drawBeam(Canvas canvas, Size size, double cx, double cy, double r) {
    final op = state == OrbState.dormant ? 0.12 : (0.40 + 0.60 * pulse);
    final bw = r * 0.045;

    canvas.drawRect(
      Rect.fromLTRB(cx - bw * 9, 0, cx + bw * 9, size.height),
      Paint()..color = const Color(0xFFFF8800).withOpacity(op * 0.10));
    canvas.drawRect(
      Rect.fromLTRB(cx - bw * 3, 0, cx + bw * 3, size.height),
      Paint()..color = const Color(0xFFFF8800).withOpacity(op * 0.22));
    canvas.drawRect(
      Rect.fromLTRB(cx - bw, 0, cx + bw, size.height),
      Paint()..color = const Color(0xFFFF8800).withOpacity(op * 0.60));
  }

  // ── Central plasma orb ───────────────────────────────────────────────────────

  void _drawOrb(Canvas canvas, Offset center, double r) {
    // Violet corona bloom
    canvas.drawCircle(
      center, r * 2.2,
      Paint()..shader = RadialGradient(
        colors: [
          const Color(0xFF6633FF).withOpacity(0.38),
          const Color(0x000000FF),
        ],
      ).createShader(Rect.fromCircle(center: center, radius: r * 2.2)));

    // Sphere: white → sky blue → deep purple → near-black
    canvas.drawCircle(
      center, r,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white,
          const Color(0xFF88CCFF),
          const Color(0xFF4400CC),
          const Color(0xFF060015),
        ],
        stops: const [0.0, 0.26, 0.68, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r)));

    // Bright white flash kernel
    final flashR = r * (0.17 + 0.08 * pulse);
    canvas.drawCircle(
      center, flashR * 2.2,
      Paint()
        ..color      = Colors.white.withOpacity(0.32 + 0.28 * pulse)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, flashR));
    canvas.drawCircle(center, flashR * 0.45, Paint()..color = Colors.white);
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state || old.orbRadius != orbRadius;
}
