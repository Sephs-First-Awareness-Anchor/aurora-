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

class _AuroraOrbState extends State<AuroraOrb> with SingleTickerProviderStateMixin {
  late AnimationController _travel;

  static int _durationMs(OrbState s) => switch (s) {
    OrbState.speaking  => 900,
    OrbState.listening => 1800,
    OrbState.thinking  => 3200,
    OrbState.dormant   => 6000,
  };

  @override
  void initState() {
    super.initState();
    _travel = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: _durationMs(widget.state)),
    )..repeat();
  }

  @override
  void didUpdateWidget(AuroraOrb old) {
    super.didUpdateWidget(old);
    if (old.state != widget.state) {
      _travel
        ..duration = Duration(milliseconds: _durationMs(widget.state))
        ..repeat();
    }
  }

  @override
  void dispose() {
    _travel.dispose();
    super.dispose();
  }

  double get _brightness {
    final b = switch (widget.state) {
      OrbState.speaking  => 0.78 + widget.pulse.value * 0.22,
      OrbState.listening => 0.52 + widget.pulse.value * 0.12,
      OrbState.thinking  => 0.38 + widget.pulse.value * 0.10,
      OrbState.dormant   => 0.20 + widget.pulse.value * 0.08,
    };
    return b.clamp(0.0, 1.15);
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
          builder: (_, __) {
            final b = _brightness;
            return Stack(
              alignment: Alignment.center,
              children: [
                // ── Base image ───────────────────────────────────────────────
                ColorFiltered(
                  colorFilter: ColorFilter.matrix([
                    b, 0, 0, 0, 0,
                    0, b, 0, 0, 0,
                    0, 0, b, 0, 0,
                    0, 0, 0, 1, 0,
                  ]),
                  child: Image.asset(
                    'assets/aurora_orb.png',
                    fit: BoxFit.fitHeight,
                  ),
                ),
                // ── Traveling pulse overlay ──────────────────────────────────
                CustomPaint(
                  size: Size.infinite,
                  painter: _PulsePainter(
                    travel:    _travel.value,
                    pulse:     widget.pulse.value,
                    state:     widget.state,
                    orbRadius: widget.size / 2,
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

// ── Overlay painter — traveling rings + convergence bands ────────────────────

class _PulsePainter extends CustomPainter {
  final double travel;   // 0→1 continuously looping
  final double pulse;    // 0→1 oscillating
  final OrbState state;
  final double orbRadius;

  const _PulsePainter({
    required this.travel,
    required this.pulse,
    required this.state,
    required this.orbRadius,
  });

  static const _phases = [0.0, 0.70, 1.40, 2.09, 2.79, 3.49, 4.19, 4.88, 5.58];

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

  @override
  void paint(Canvas canvas, Size size) {
    final cx     = size.width  / 2;
    final cy     = size.height / 2;
    final r      = orbRadius;
    final center = Offset(cx, cy);

    switch (state) {
      case OrbState.speaking:
        // Outward rings from center
        _drawOutwardRings(canvas, center, r);
        // Inward bands from both sides simultaneously
        _drawInwardBands(canvas, size, cx, cy, r);
      case OrbState.listening:
        _drawOutwardRings(canvas, center, r);
        _drawIdleGlow(canvas, center, r, 0.45);
      case OrbState.thinking:
        _drawIdleGlow(canvas, center, r, 0.30);
      case OrbState.dormant:
        _drawIdleGlow(canvas, center, r, 0.16);
    }

    _drawCenterFlash(canvas, center, r);
  }

  // ── Rings that expand outward from the center ─────────────────────────────

  void _drawOutwardRings(Canvas canvas, Offset center, double r) {
    const nRings = 4;
    for (int i = 0; i < nRings; i++) {
      final phase  = (travel + i / nRings) % 1.0;
      final ringR  = r * 0.08 + r * 1.35 * phase;
      final op     = (1.0 - phase) * (state == OrbState.speaking ? 0.72 : 0.45);
      if (op < 0.02) continue;

      final ci = ((travel * 9).floor() + i * 2) % 9;

      // Outer bloom
      canvas.drawCircle(center, ringR, Paint()
        ..color       = _colors[ci].withOpacity(op * 0.20)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.20);
      // Mid glow
      canvas.drawCircle(center, ringR, Paint()
        ..color       = _colors[ci].withOpacity(op * 0.45)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.055);
      // Core ring
      canvas.drawCircle(center, ringR, Paint()
        ..color       = _colors[ci].withOpacity(op * 0.90)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.014);
    }
  }

  // ── Sine bands sweeping INWARD from left and right toward center ───────────

  void _drawInwardBands(Canvas canvas, Size size, double cx, double cy, double r) {
    const nBands = 6;
    final spread  = r * 1.60;
    final baseAmp = r * 0.22;
    const steps   = 140;

    final travelRad = travel * math.pi * 2;

    for (int i = 0; i < nBands; i++) {
      final phi      = travelRad + _phases[i % 9];
      final bandFrac = (i / (nBands - 1.0)) * 2.0 - 1.0;  // −1 .. +1
      final op       = 0.65 * (0.65 + 0.35 * math.sin(phi).abs());
      final strokeW  = i == nBands ~/ 2 ? 1.6 : 1.1;

      final path = Path();
      for (int p = 0; p <= steps; p++) {
        final t = p / steps;
        final x = size.width * t;
        final d  = (t - 0.5).abs() * 2.0;   // 0 at center, 1 at edges
        final ev = d * d;

        final bandY = cy + bandFrac * spread * ev;
        final amp   = baseAmp * (0.18 + 0.82 * d)
                    * (0.70 + 0.30 * ((math.sin(phi * 1.2) + 1) / 2));

        // Traveling INWARD: left half moves right, right half moves left.
        // Standard traveling wave: sin(kx − ωt) moves right; sin(kx + ωt) moves left.
        final inward = t < 0.5 ? -travelRad : travelRad;

        final y = bandY
            + amp       * math.sin(t * math.pi * 3.8 + phi + inward)
            + amp * 0.4 * math.sin(t * math.pi * 8.0 + phi * 1.5 + inward);

        p == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
      }

      _drawGlowPath(canvas, path, _colors[i % 9], op, strokeW);
    }
  }

  // ── Gentle alive glow when not speaking ──────────────────────────────────────

  void _drawIdleGlow(Canvas canvas, Offset center, double r, double maxOp) {
    // Slow outward rings at very low opacity — still moving, just languid
    const nRings = 2;
    for (int i = 0; i < nRings; i++) {
      final phase = (travel + i * 0.5) % 1.0;
      final ringR = r * 0.05 + r * 1.25 * phase;
      final op    = (1.0 - phase) * maxOp;
      if (op < 0.01) continue;
      final ci = ((travel * 9).floor() + i * 3) % 9;
      canvas.drawCircle(center, ringR, Paint()
        ..color       = _colors[ci].withOpacity(op * 0.18)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.16);
      canvas.drawCircle(center, ringR, Paint()
        ..color       = _colors[ci].withOpacity(op * 0.55)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.012);
    }

    // Very faint slow inward drift at edges — presence without energy
    if (state != OrbState.dormant) {
      _drawInwardBandsFaint(canvas,
        Size(center.dx * 2, center.dy * 2), center.dx, center.dy, r, maxOp * 0.5);
    }
  }

  void _drawInwardBandsFaint(
      Canvas canvas, Size size, double cx, double cy, double r, double opScale) {
    const nBands = 3;
    final spread  = r * 1.1;
    final baseAmp = r * 0.09;
    const steps   = 100;
    final tRad    = travel * math.pi * 2;

    for (int i = 0; i < nBands; i++) {
      final phi      = tRad + _phases[i * 3 % 9];
      final bandFrac = (i / (nBands - 1.0)) * 2.0 - 1.0;
      final op       = opScale * (0.5 + 0.5 * math.sin(phi).abs());

      final path = Path();
      for (int p = 0; p <= steps; p++) {
        final t    = p / steps;
        final x    = size.width * t;
        final d    = (t - 0.5).abs() * 2.0;
        final ev   = d * d;
        final bandY = cy + bandFrac * spread * ev;
        final amp   = baseAmp * (0.2 + 0.8 * d);
        final inward = t < 0.5 ? -tRad : tRad;
        final y    = bandY + amp * math.sin(t * math.pi * 3.2 + phi + inward);
        p == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
      }
      _drawGlowPath(canvas, path, _colors[i * 3 % 9], op, 0.9);
    }
  }

  // ── White-hot center flash ─────────────────────────────────────────────────

  void _drawCenterFlash(Canvas canvas, Offset center, double r) {
    final op = state == OrbState.dormant ? 0.20 : (0.48 + 0.52 * pulse);

    canvas.drawCircle(center, r * 0.48,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(op * 0.75),
          const Color(0xFFFF8800).withOpacity(op * 0.38),
          Colors.transparent,
        ],
        stops: const [0.0, 0.32, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.48)));

    final fr = r * (0.13 + 0.06 * pulse);
    canvas.drawCircle(center, fr * 1.8,
      Paint()
        ..color      = Colors.white.withOpacity(op * 0.55)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, fr * 0.6));
    canvas.drawCircle(center, fr * 0.38, Paint()..color = Colors.white);
  }

  // ── Shared glow path helper ────────────────────────────────────────────────

  void _drawGlowPath(Canvas canvas, Path path, Color color, double op, double w) {
    canvas.drawPath(path, Paint()
      ..color       = color.withOpacity(op * 0.10)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = w * 9.0
      ..strokeCap   = StrokeCap.round);
    canvas.drawPath(path, Paint()
      ..color       = color.withOpacity(op * 0.30)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = w * 3.0
      ..strokeCap   = StrokeCap.round);
    canvas.drawPath(path, Paint()
      ..color       = color.withOpacity(op)
      ..style       = PaintingStyle.stroke
      ..strokeWidth = w
      ..strokeCap   = StrokeCap.round);
  }

  @override
  bool shouldRepaint(_PulsePainter old) =>
      old.travel != travel || old.pulse != pulse ||
      old.state != state || old.orbRadius != orbRadius;
}
