import 'dart:math' as math;
import 'package:flutter/material.dart';

enum OrbState { dormant, listening, thinking, speaking }

class AuroraOrb extends StatefulWidget {
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
  State<AuroraOrb> createState() => _AuroraOrbState();
}

class _AuroraOrbState extends State<AuroraOrb>
    with SingleTickerProviderStateMixin {
  late AnimationController _travel;

  static int _ms(OrbState s) => switch (s) {
    OrbState.speaking  => 800,
    OrbState.listening => 1500,
    OrbState.thinking  => 3200,
    OrbState.dormant   => 7000,
  };

  @override
  void initState() {
    super.initState();
    _travel = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: _ms(widget.state)),
    )..repeat();
  }

  @override
  void didUpdateWidget(AuroraOrb old) {
    super.didUpdateWidget(old);
    if (old.state != widget.state) {
      _travel
        ..duration = Duration(milliseconds: _ms(widget.state))
        ..repeat();
    }
  }

  @override
  void dispose() {
    _travel.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: double.infinity,
        height: widget.size * 1.9,
        child: AnimatedBuilder(
          animation: Listenable.merge([_travel, widget.pulse]),
          builder: (_, __) => CustomPaint(
            painter: _PlasmaPainter(
              travel:    _travel.value,
              pulse:     widget.pulse.value,
              state:     widget.state,
              orbRadius: widget.size / 2,
            ),
          ),
        ),
      ),
    );
  }
}

// ── Fully procedural plasma ball — no base image ──────────────────────────────

class _PlasmaPainter extends CustomPainter {
  final double travel;   // 0→1 looping
  final double pulse;    // 0→1 oscillating
  final OrbState state;
  final double orbRadius;

  const _PlasmaPainter({
    required this.travel,
    required this.pulse,
    required this.state,
    required this.orbRadius,
  });

  static Color _hsl(double hue) =>
      HSLColor.fromAHSL(1.0, hue % 360, 1.0, 0.55).toColor();

  int get _nStrands => switch (state) {
    OrbState.speaking  => 16,
    OrbState.listening => 11,
    OrbState.thinking  => 7,
    OrbState.dormant   => 4,
  };

  double get _energy => switch (state) {
    OrbState.speaking  => 0.80 + 0.20 * pulse,
    OrbState.listening => 0.50 + 0.12 * pulse,
    OrbState.thinking  => 0.30 + 0.08 * pulse,
    OrbState.dormant   => 0.15 + 0.04 * pulse,
  };

  @override
  void paint(Canvas canvas, Size size) {
    final cx     = size.width / 2;
    final cy     = size.height / 2;
    final r      = orbRadius;
    final center = Offset(cx, cy);
    final tRad   = travel * math.pi * 2;
    final orbRect = Rect.fromCircle(center: center, radius: r);

    // ── Sphere clip ────────────────────────────────────────────────────────
    canvas.save();
    canvas.clipPath(Path()..addOval(orbRect));
    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..color = Colors.black,
    );

    // ── Additive plasma layer (strands accumulate to white at center) ──────
    // saveLayer with default blend; individual draws use BlendMode.plus
    // so each strand adds its light to what's already been drawn.
    canvas.saveLayer(orbRect, Paint());
    _drawStrands(canvas, cx, cy, r, tRad);
    if (state == OrbState.speaking || state == OrbState.listening) {
      _drawOutwardRings(canvas, center, r);
    }
    canvas.restore();

    // ── White-hot center (drawn on top of accumulated strands) ─────────────
    _drawCenter(canvas, center, r);

    canvas.restore(); // end sphere clip

    // ── Spectrum boundary ring ─────────────────────────────────────────────
    _drawRing(canvas, center, r, orbRect);
  }

  // ── Converging sine-wave strands ──────────────────────────────────────────

  void _drawStrands(Canvas canvas, double cx, double cy, double r, double tRad) {
    final n      = _nStrands;
    final energy = _energy;
    final spread = r * 0.80;
    const steps  = 140;

    for (int i = 0; i < n; i++) {
      final fi  = i / n;
      // Spectrum slowly rotates with travel so color constantly shifts
      final hue = (fi * 360 + travel * 80) % 360;
      final col = _hsl(hue);

      final phi   = tRad + fi * math.pi * 2;
      final vFrac = fi * 2.0 - 1.0;  // -1..+1, evenly spread at edges
      final amp   = r * 0.14 * energy * (0.5 + 0.5 * math.sin(phi + 1.3).abs());
      final op    = energy * (0.50 + 0.50 * math.cos(phi * 0.6).abs());

      final path = Path();
      for (int p = 0; p <= steps; p++) {
        final t = p / steps;
        // x spans slightly wider than orb diameter; clip handles the edges
        final x = cx + (t - 0.5) * r * 2.15;

        final d  = (t - 0.5).abs() * 2.0;  // 0 at center, 1 at edges
        final ev = d * d;                    // quadratic convergence envelope

        // Strands fan wide at edges, converge to center
        final baseY = cy + vFrac * spread * ev;

        // Inward traveling wave: left half moves right, right half moves left
        final inward = t < 0.5 ? -tRad : tRad;

        final y = baseY
            + amp * ev * math.sin(t * math.pi * 4.5 + phi + inward)
            + amp * 0.36 * ev * math.sin(t * math.pi * 9.8 + phi * 1.7 + inward * 1.1)
            + amp * 0.16 * math.sin(t * math.pi * 16.5 + phi * 2.5 + inward * 0.8);

        p == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
      }

      _glowStrand(canvas, path, col, op, r);
    }
  }

  void _glowStrand(Canvas canvas, Path path, Color col, double op, double r) {
    // Three passes accumulate additively: wide bloom → mid glow → sharp core
    canvas.drawPath(path, Paint()
      ..color       = col.withOpacity((op * 0.10).clamp(0.0, 1.0))
      ..blendMode   = BlendMode.plus
      ..style       = PaintingStyle.stroke
      ..strokeWidth = r * 0.26
      ..strokeCap   = StrokeCap.round);
    canvas.drawPath(path, Paint()
      ..color       = col.withOpacity((op * 0.36).clamp(0.0, 1.0))
      ..blendMode   = BlendMode.plus
      ..style       = PaintingStyle.stroke
      ..strokeWidth = r * 0.050
      ..strokeCap   = StrokeCap.round);
    canvas.drawPath(path, Paint()
      ..color       = col.withOpacity((op * 0.92).clamp(0.0, 1.0))
      ..blendMode   = BlendMode.plus
      ..style       = PaintingStyle.stroke
      ..strokeWidth = r * 0.010
      ..strokeCap   = StrokeCap.round);
  }

  // ── Outward expanding rings from center ───────────────────────────────────

  void _drawOutwardRings(Canvas canvas, Offset center, double r) {
    final energy = _energy;
    const nRings = 4;
    for (int i = 0; i < nRings; i++) {
      final phase = (travel + i / nRings) % 1.0;
      final ringR = r * 0.06 + r * 0.88 * phase;
      final op    = (1.0 - phase) * energy * 0.65;
      if (op < 0.015) continue;

      final hue = (travel * 360 + i * 45) % 360;
      final col = _hsl(hue);

      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity((op * 0.14).clamp(0.0, 1.0))
        ..blendMode   = BlendMode.plus
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.16);
      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity((op * 0.42).clamp(0.0, 1.0))
        ..blendMode   = BlendMode.plus
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.044);
      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity((op * 0.85).clamp(0.0, 1.0))
        ..blendMode   = BlendMode.plus
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.011);
    }
  }

  // ── Spectrum boundary ring ─────────────────────────────────────────────────

  void _drawRing(Canvas canvas, Offset center, double r, Rect rect) {
    final op = switch (state) {
      OrbState.speaking  => (0.60 + 0.40 * pulse).clamp(0.0, 1.0),
      OrbState.listening => 0.42 + 0.15 * pulse,
      OrbState.thinking  => 0.26,
      OrbState.dormant   => 0.13,
    };

    // Soft halo bloom around the edge
    canvas.drawCircle(center, r, Paint()
      ..color       = Colors.white.withOpacity(op * 0.07)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = r * 0.14);

    // Full-spectrum sweep gradient ring
    canvas.drawCircle(center, r, Paint()
      ..style       = PaintingStyle.stroke
      ..strokeWidth = r * 0.032
      ..shader      = SweepGradient(colors: [
        const Color(0xFF0055FF).withOpacity(op),
        const Color(0xFF00BBFF).withOpacity(op),
        const Color(0xFF00FF88).withOpacity(op),
        const Color(0xFFCCFF00).withOpacity(op),
        const Color(0xFFFF8800).withOpacity(op),
        const Color(0xFFFF0055).withOpacity(op),
        const Color(0xFFBB00FF).withOpacity(op),
        const Color(0xFF0055FF).withOpacity(op),
      ]).createShader(rect));
  }

  // ── White-hot center ───────────────────────────────────────────────────────

  void _drawCenter(Canvas canvas, Offset center, double r) {
    final op = switch (state) {
      OrbState.dormant => 0.22,
      _                => (0.52 + 0.48 * pulse).clamp(0.0, 1.0),
    };

    canvas.drawCircle(center, r * 0.52,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(op * 0.85),
          const Color(0xFFFFEE88).withOpacity(op * 0.42),
          const Color(0xFFFF4400).withOpacity(op * 0.15),
          Colors.transparent,
        ],
        stops: const [0.0, 0.20, 0.45, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.52)));

    final fr = r * (0.09 + 0.05 * pulse);
    canvas.drawCircle(center, fr * 1.6,
      Paint()
        ..color      = Colors.white.withOpacity(op * 0.65)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, fr * 0.8));
    canvas.drawCircle(center, fr * 0.35, Paint()..color = Colors.white);
  }

  @override
  bool shouldRepaint(_PlasmaPainter old) =>
      old.travel != travel || old.pulse != pulse ||
      old.state != state || old.orbRadius != orbRadius;
}
