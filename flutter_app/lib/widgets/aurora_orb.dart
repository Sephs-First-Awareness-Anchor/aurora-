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
    // Fill available width; height is proportional to the orb size.
    // Using SizedBox(infinity) lets the painter adapt to the screen width so
    // the bands always flow edge-to-edge, not just across a fixed small canvas.
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

  // Vivid plasma palette — axis identity preserved, saturation maximised
  static const _colors = [
    Color(0xFF00DDFF),  // X – electric cyan
    Color(0xFFFF1199),  // T – hot magenta
    Color(0xFFFF6600),  // N – plasma orange
    Color(0xFFBB22FF),  // B – violet
    Color(0xFF00FF88),  // A – spring green
  ];

  // Neon accent colors for extra pop
  static const _neonAccents = [
    Color(0xFF00FFFF),
    Color(0xFF00FF99),
    Color(0xFFFFAA00),
    Color(0xFFFF00FF),
    Color(0xFFFFFF00),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width  / 2;
    final cy = size.height / 2;
    final center = Offset(cx, cy);
    final r = orbRadius;

    // 1. Plasma bands BEHIND the orb — bands converge into the sphere.
    _drawPlasmaBands(canvas, size, cx, cy, r);

    // 2. Outer corona bloom.
    final bloomR = r * (1.8 + 0.4 * pulse);
    final bloomColor = switch (state) {
      OrbState.speaking  => const Color(0xFFFF6600),
      OrbState.listening => const Color(0xFF8822FF),
      OrbState.thinking  => const Color(0xFF0066FF),
      OrbState.dormant   => const Color(0xFF440088),
    };
    canvas.drawCircle(
      center, bloomR,
      Paint()
        ..shader = RadialGradient(
          colors: [
            bloomColor.withOpacity(0.45 * (0.6 + 0.4 * pulse)),
            bloomColor.withOpacity(0.0),
          ],
        ).createShader(Rect.fromCircle(center: center, radius: bloomR)),
    );

    // 3. Orb sphere — explosive plasma core.
    final Color coreInner;
    final Color coreMid;
    final Color coreEdge;
    switch (state) {
      case OrbState.speaking:
        coreInner = const Color(0xFFFFFFFF);
        coreMid   = const Color(0xFFFF8800);
        coreEdge  = const Color(0xFF6600CC);
      case OrbState.listening:
        coreInner = const Color(0xFFFFFFFF);
        coreMid   = const Color(0xFF9933FF);
        coreEdge  = const Color(0xFF220055);
      case OrbState.thinking:
        coreInner = const Color(0xFFEEFFFF);
        coreMid   = const Color(0xFF2266FF);
        coreEdge  = const Color(0xFF001144);
      case OrbState.dormant:
        coreInner = const Color(0xFFCCAAFF);
        coreMid   = const Color(0xFF5522AA);
        coreEdge  = const Color(0xFF110022);
    }

    canvas.drawCircle(
      center, r,
      Paint()..shader = RadialGradient(
        colors: [coreInner, coreMid, coreEdge],
        stops: const [0.0, 0.42, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r)),
    );

    // 4. Bright center flash — the "energy source" focal point.
    final flashR = r * (0.22 + 0.10 * pulse);
    final flashOp = state == OrbState.dormant ? 0.25 : (0.55 + 0.45 * pulse);
    canvas.drawCircle(
      center, flashR,
      Paint()
        ..color      = Colors.white.withOpacity(flashOp)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, flashR),
    );
  }

  void _drawPlasmaBands(Canvas canvas, Size size, double cx, double cy, double r) {
    // Each band fans out at the screen edges and CONVERGES into the orb center.
    // At x=cx the band y-offset → 0 (all bands meet at center height).
    // At x=0 or x=width the band y-offset is ±spread.
    // This creates the signature look: plasma emerging from / flowing through a sphere.

    final spread = switch (state) {
      OrbState.speaking  => r * 1.9,
      OrbState.listening => r * 1.5,
      OrbState.thinking  => r * 1.1,
      OrbState.dormant   => r * 0.7,
    };

    final baseAmp = switch (state) {
      OrbState.speaking  => r * 0.26,
      OrbState.listening => r * 0.13,
      OrbState.thinking  => r * 0.07,
      OrbState.dormant   => r * 0.020,
    };

    final baseOpacity = switch (state) {
      OrbState.speaking  => 0.88,
      OrbState.listening => 0.60,
      OrbState.thinking  => 0.36,
      OrbState.dormant   => 0.16,
    };

    const steps = 140;

    for (int i = 0; i < 5; i++) {
      final phi    = pulse * math.pi * 2 + _phaseOff[i];
      final sinPhi = math.sin(phi);
      final op     = (baseOpacity * (0.78 + 0.22 * (sinPhi + 1) / 2)).clamp(0.0, 1.0);
      final strokeW = state == OrbState.dormant ? 1.1 : 1.5 + (sinPhi + 1) * 0.35;

      // Band's vertical fraction: -1 (top) to +1 (bottom)
      final bandFrac = (i / 4.0) * 2.0 - 1.0;

      for (int strand = 0; strand < 2; strand++) {
        final strandPhase  = phi + strand * 1.1;
        final strandBias   = (strand == 0 ? -1.0 : 1.0) * r * 0.06;

        final path = Path();
        for (int s = 0; s <= steps; s++) {
          final t = s / steps;
          final x = size.width * t;

          // Convergence envelope: 0 at center, 1 at edges (quadratic falloff)
          final d = (t - 0.5).abs() * 2.0;      // 0 → 1 from center to edge
          final envelope = d * d;                 // squared: slow taper near center

          // Band center converges to cy at orb, fans to ±spread at edges
          final bandY = cy + bandFrac * spread * envelope + strandBias;

          // Amplitude also smaller near center — bands slide smoothly through orb
          final amp = baseAmp * (0.25 + 0.75 * d) * (0.78 + 0.22 * (sinPhi + 1) / 2);
          final y   = bandY + amp * math.sin(t * math.pi * 3.5 + strandPhase);

          s == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
        }

        // Outer glow pass
        canvas.drawPath(path, Paint()
          ..color       = _colors[i].withOpacity(op * 0.14)
          ..style       = PaintingStyle.stroke
          ..strokeWidth = strokeW * 7.0
          ..strokeCap   = StrokeCap.round);

        // Mid glow pass
        canvas.drawPath(path, Paint()
          ..color       = _colors[i].withOpacity(op * 0.32)
          ..style       = PaintingStyle.stroke
          ..strokeWidth = strokeW * 2.8
          ..strokeCap   = StrokeCap.round);

        // Crisp core line
        canvas.drawPath(path, Paint()
          ..color       = _colors[i].withOpacity(op)
          ..style       = PaintingStyle.stroke
          ..strokeWidth = strokeW
          ..strokeCap   = StrokeCap.round);
      }
    }
  }

  void _drawOrbitalFrequencyRings(Canvas canvas, Offset center, double r) {
    // Living orbital system: 4 concentric rings, each with 5 sine-wave frequency bands
    // Rings rotate independently at different speeds for chaotic planetary effect
    // Professional color contrast + neon pop for visual presence

    final baseOpacity = switch (state) {
      OrbState.speaking  => 0.70,
      OrbState.listening => 0.45,
      OrbState.thinking  => 0.30,
      OrbState.dormant   => 0.12,
    };

    final baseAmplitude = switch (state) {
      OrbState.speaking  => r * 0.18,
      OrbState.listening => r * 0.10,
      OrbState.thinking  => r * 0.07,
      OrbState.dormant   => r * 0.03,
    };

    // 4 orbital rings at increasing radii with chaotic rotation
    for (int ringIdx = 0; ringIdx < 4; ringIdx++) {
      final ringRadius = r * (1.2 + ringIdx * 0.20);
      
      // Each ring rotates at different speed (chaotic planetary dynamics)
      final ringRotation = pulse * math.pi * 2 * (0.8 + ringIdx * 0.4);
      
      // Per-ring frequency modulation (inner rings = higher frequency)
      final frequencyMultiplier = 2.0 + (ringIdx * 0.6);
      
      // Per-ring opacity breathing
      final ringOpacityMod = 0.7 + 0.3 * math.sin(ringRotation * 0.5);

      // Draw 5 sine-wave frequency bands per ring
      for (int bandIdx = 0; bandIdx < 5; bandIdx++) {
        final bandPhase = ringRotation + _phaseOff[bandIdx];
        final sinMod = math.sin(bandPhase);
        
        // Amplitude modulates per band for living energy feel
        final bandAmplitude = baseAmplitude * (0.8 + 0.2 * sinMod);
        
        // Opacity modulates for breathing effect
        final bandOpacity = (baseOpacity * ringOpacityMod * (0.85 + 0.15 * sinMod)).clamp(0.0, 1.0);

        // Build the sine-wave path around the orbital ring
        final path = Path();
        const pathSteps = 180;
        
        for (int step = 0; step <= pathSteps; step++) {
          final angle = (step / pathSteps) * math.pi * 2;
          
          // Base circular orbit
          final baseX = center.dx + math.cos(angle) * ringRadius;
          final baseY = center.dy + math.sin(angle) * ringRadius;
          
          // Sine-wave modulation perpendicular to orbit (radial breathing)
          final radialMod = bandAmplitude * math.sin(angle * frequencyMultiplier + bandPhase);
          final modX = baseX + math.cos(angle) * radialMod;
          final modY = baseY + math.sin(angle) * radialMod;
          
          step == 0 ? path.moveTo(modX, modY) : path.lineTo(modX, modY);
        }
        
        // Close the path for continuous orbital ring
        path.close();

        // Crisp neon stroke
        canvas.drawPath(
          path,
          Paint()
            ..color = _neonAccents[bandIdx].withOpacity(bandOpacity * 0.85)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.4 + pulse * 0.5
            ..strokeCap = StrokeCap.round
            ..strokeJoin = StrokeJoin.round,
        );

        // Ethereal glow layer for professional depth
        canvas.drawPath(
          path,
          Paint()
            ..color = _colors[bandIdx].withOpacity(bandOpacity * 0.35)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 3.5 + pulse * 0.8
            ..strokeCap = StrokeCap.round
            ..strokeJoin = StrokeJoin.round
            ..maskFilter = MaskFilter.blur(BlurStyle.normal, 5.0 + pulse * 3.5),
        );
      }
    }
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.pulse != pulse || old.state != state || old.orbRadius != orbRadius;
}
