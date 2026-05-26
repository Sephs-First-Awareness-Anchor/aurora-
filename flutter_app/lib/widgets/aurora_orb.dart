import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
  ui.Image? _orbImage;

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
    _loadImage();
  }

  Future<void> _loadImage() async {
    final data  = await rootBundle.load('assets/aurora_orb.png');
    final codec = await ui.instantiateImageCodec(data.buffer.asUint8List());
    final frame = await codec.getNextFrame();
    if (mounted) setState(() => _orbImage = frame.image);
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
    _orbImage?.dispose();
    super.dispose();
  }

  double get _brightness => switch (widget.state) {
    OrbState.speaking  => 0.78 + widget.pulse.value * 0.22,
    OrbState.listening => 0.52 + widget.pulse.value * 0.14,
    OrbState.thinking  => 0.36 + widget.pulse.value * 0.10,
    OrbState.dormant   => 0.18 + widget.pulse.value * 0.07,
  };

  @override
  Widget build(BuildContext context) {
    final img = _orbImage;
    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: double.infinity,
        height: widget.size * 1.9,
        child: img == null
            ? const SizedBox.shrink()
            : AnimatedBuilder(
                animation: Listenable.merge([_travel, widget.pulse]),
                builder: (_, __) => CustomPaint(
                  painter: _WarpPainter(
                    image:      img,
                    travel:     _travel.value,
                    pulse:      widget.pulse.value,
                    state:      widget.state,
                    brightness: _brightness.clamp(0.0, 1.0),
                    orbRadius:  widget.size / 2,
                  ),
                ),
              ),
      ),
    );
  }
}

// ── Scanline-warp painter ─────────────────────────────────────────────────────
//
// Splits the photo into N vertical slices and displaces each slice vertically
// by a convergence sine wave. The photo's own pixels physically move —
// the strands genuinely undulate toward the center white-hot point.
// Warp amplitude is driven by the pulse value (word-kick from TTS onRangeStart).
//
// On top: a screen-blend center glow and outward ring pulses that only add
// light and never obscure the photo.

class _WarpPainter extends CustomPainter {
  final ui.Image image;
  final double travel;
  final double pulse;
  final OrbState state;
  final double brightness;
  final double orbRadius;

  _WarpPainter({
    required this.image,
    required this.travel,
    required this.pulse,
    required this.state,
    required this.brightness,
    required this.orbRadius,
  });

  // How much the strands physically move — zero when dormant, full when speaking.
  double get _warpAmp => switch (state) {
    OrbState.speaking  => 0.55 + 0.45 * pulse,
    OrbState.listening => 0.22 + 0.18 * pulse,
    OrbState.thinking  => 0.08 + 0.08 * pulse,
    OrbState.dormant   => 0.01 + 0.02 * pulse,
  };

  double get _glowEnergy => switch (state) {
    OrbState.speaking  => 0.55 + 0.45 * pulse,
    OrbState.listening => 0.30 + 0.22 * pulse,
    OrbState.thinking  => 0.16 + 0.12 * pulse,
    OrbState.dormant   => 0.05 + 0.05 * pulse,
  };

  static Color _hsl(double hue) =>
      HSLColor.fromAHSL(1.0, hue % 360, 1.0, 0.60).toColor();

  @override
  void paint(Canvas canvas, Size size) {
    final iw   = image.width.toDouble();
    final ih   = image.height.toDouble();
    final tRad = travel * math.pi * 2;
    final amp  = _warpAmp;
    final b    = brightness;

    // Replicate BoxFit.fitHeight: scale to fill height, center horizontally.
    final scale = size.height / ih;
    final imgW  = iw * scale;
    final imgH  = size.height;
    final imgX  = (size.width - imgW) / 2;

    // Brightness color filter — dims / brightens the photo with pulse.
    final paint = Paint()
      ..filterQuality = FilterQuality.medium
      ..colorFilter   = ColorFilter.matrix([
        b, 0, 0, 0, 0,
        0, b, 0, 0, 0,
        0, 0, b, 0, 0,
        0, 0, 0, 1, 0,
      ]);

    // ── Scanline warp ─────────────────────────────────────────────────────────
    // 160 vertical slices. Each is offset vertically by a dual-harmonic
    // converging wave. At the center (t=0.5) displacement is zero — the
    // white-hot core stays pinned. At the edges displacement is maximal.
    // Left half travels right, right half travels left → both converge inward.
    const nSlices  = 160;
    final srcSliceW = iw / nSlices;
    final dstSliceW = imgW / nSlices;

    for (int i = 0; i < nSlices; i++) {
      final t = i / nSlices;

      final srcRect = Rect.fromLTWH(t * iw, 0, srcSliceW, ih);
      final dstX    = imgX + t * imgW;

      // Convergence envelope: 0 at center, 1 at edges (quadratic).
      final d   = (t - 0.5).abs() * 2.0;
      final env = d * d;

      // Inward traveling wave phase.
      final inward = t < 0.5 ? -tRad : tRad;

      final dy = imgH * amp * (
          env * math.sin(t * math.pi * 3.8 + tRad       + inward        ) * 0.088
        + env * math.sin(t * math.pi * 8.5 + tRad * 1.5 + inward * 1.1  ) * 0.038
        +       math.sin(t * math.pi * 14.0 + tRad * 2.2 + inward * 0.7 ) * 0.011
      );

      canvas.drawImageRect(image, srcRect, Rect.fromLTWH(dstX, dy, dstSliceW, imgH), paint);
    }

    // ── Screen-blend glow on top ──────────────────────────────────────────────
    // Only adds light — never darkens or overwrites the photo pixels.
    final center = Offset(size.width / 2, size.height / 2);
    final r      = orbRadius;

    canvas.saveLayer(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..blendMode = BlendMode.screen,
    );
    _drawCenterGlow(canvas, center, r);
    if (state != OrbState.dormant) _drawOutwardRings(canvas, center, r, tRad);
    canvas.restore();
  }

  void _drawCenterGlow(Canvas canvas, Offset center, double r) {
    final e = _glowEnergy;
    // Large ambient bloom
    canvas.drawCircle(center, r * 0.85,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(e * 0.26),
          const Color(0xFFFF8800).withOpacity(e * 0.10),
          Colors.transparent,
        ],
        stops: const [0.0, 0.38, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.85)));
    // Tight hot core
    canvas.drawCircle(center, r * 0.18,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(e * 0.90),
          const Color(0xFFFFFF88).withOpacity(e * 0.50),
          Colors.transparent,
        ],
        stops: const [0.0, 0.45, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.18)));
  }

  void _drawOutwardRings(Canvas canvas, Offset center, double r, double tRad) {
    final e      = _glowEnergy;
    final nRings = state == OrbState.speaking ? 4 : 2;
    for (int i = 0; i < nRings; i++) {
      final phase = (travel + i / nRings) % 1.0;
      final ringR = r * 0.06 + r * 1.15 * phase;
      final op    = (1.0 - phase) * e * 0.55;
      if (op < 0.02) continue;

      final hue = (travel * 360 + i * 90) % 360;
      final col = _hsl(hue);

      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity(op * 0.20)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.22);
      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity(op * 0.55)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.046);
      canvas.drawCircle(center, ringR, Paint()
        ..color       = col.withOpacity(op * 0.85)
        ..style       = PaintingStyle.stroke
        ..strokeWidth = r * 0.012);
    }
  }

  @override
  bool shouldRepaint(_WarpPainter old) =>
      old.travel    != travel    ||
      old.pulse     != pulse     ||
      old.state     != state     ||
      old.brightness != brightness;
}
