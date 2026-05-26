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
    return switch (widget.state) {
      OrbState.speaking  => 0.78 + widget.pulse.value * 0.22,
      OrbState.listening => 0.52 + widget.pulse.value * 0.12,
      OrbState.thinking  => 0.38 + widget.pulse.value * 0.10,
      OrbState.dormant   => 0.20 + widget.pulse.value * 0.08,
    };
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
            final b = _brightness.clamp(0.0, 1.15);
            return Stack(
              alignment: Alignment.center,
              children: [
                // ── Your actual photo, brightness-modulated with pulse ──────
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
                // ── Screen-blend light overlays (only adds light, never obscures) ──
                CustomPaint(
                  size: Size.infinite,
                  painter: _GlowPainter(
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

// ── Screen-blend glow painter — enhances the photo, never fights it ──────────
//
// BlendMode.screen: result = 1-(1-src)(1-dst)
// Everything drawn here can only BRIGHTEN the photo underneath.
// The photo's strands, colors, and ring stay exactly as you shot them.

class _GlowPainter extends CustomPainter {
  final double travel;
  final double pulse;
  final OrbState state;
  final double orbRadius;

  const _GlowPainter({
    required this.travel,
    required this.pulse,
    required this.state,
    required this.orbRadius,
  });

  static Color _hsl(double hue) =>
      HSLColor.fromAHSL(1.0, hue % 360, 1.0, 0.60).toColor();

  double get _energy => switch (state) {
    OrbState.speaking  => 0.55 + 0.45 * pulse,
    OrbState.listening => 0.32 + 0.22 * pulse,
    OrbState.thinking  => 0.18 + 0.12 * pulse,
    OrbState.dormant   => 0.06 + 0.06 * pulse,
  };

  @override
  void paint(Canvas canvas, Size size) {
    final cx     = size.width  / 2;
    final cy     = size.height / 2;
    final r      = orbRadius;
    final center = Offset(cx, cy);

    // All overlays are in a screen-blend layer
    canvas.saveLayer(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..blendMode = BlendMode.screen,
    );

    _drawCenterGlow(canvas, center, r);

    if (state != OrbState.dormant) {
      _drawOutwardRings(canvas, center, r);
    }

    canvas.restore();
  }

  // ── Center hot-spot — breathes with pulse ─────────────────────────────────

  void _drawCenterGlow(Canvas canvas, Offset center, double r) {
    final e = _energy;

    // Large ambient bloom around center
    canvas.drawCircle(center, r * 0.85,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(e * 0.28),
          const Color(0xFFFF8800).withOpacity(e * 0.12),
          Colors.transparent,
        ],
        stops: const [0.0, 0.38, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.85)));

    // Tight hot core
    canvas.drawCircle(center, r * 0.20,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(e * 0.90),
          const Color(0xFFFFFF88).withOpacity(e * 0.55),
          Colors.transparent,
        ],
        stops: const [0.0, 0.45, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.20)));
  }

  // ── Outward ring pulses — travel from center outward ──────────────────────

  void _drawOutwardRings(Canvas canvas, Offset center, double r) {
    final e = _energy;
    final nRings = state == OrbState.speaking ? 4 : 2;

    for (int i = 0; i < nRings; i++) {
      final phase = (travel + i / nRings) % 1.0;
      final ringR = r * 0.06 + r * 1.15 * phase;
      final op    = (1.0 - phase) * e * 0.55;
      if (op < 0.02) continue;

      final hue = (travel * 360 + i * 90) % 360;
      final col = _hsl(hue);

      // Soft bloom
      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity(op * 0.22)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.22);
      // Mid glow
      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity(op * 0.55)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.048);
      // Sharp ring edge
      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity(op * 0.85)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.012);
    }
  }

  @override
  bool shouldRepaint(_GlowPainter old) =>
      old.travel != travel || old.pulse != pulse ||
      old.state != state || old.orbRadius != orbRadius;
}
