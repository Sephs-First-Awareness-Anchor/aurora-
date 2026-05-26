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
  ui.Image? _bgImage;
  ui.Image? _wavesImage;

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
    _loadImages();
  }

  Future<void> _loadImages() async {
    final bg    = await _loadUiImage('assets/aurora_bg.png');
    final waves = await _loadUiImage('assets/aurora_waves.png');
    if (mounted) setState(() { _bgImage = bg; _wavesImage = waves; });
  }

  static Future<ui.Image> _loadUiImage(String asset) async {
    final data  = await rootBundle.load(asset);
    final codec = await ui.instantiateImageCodec(data.buffer.asUint8List());
    return (await codec.getNextFrame()).image;
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
    _bgImage?.dispose();
    _wavesImage?.dispose();
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
    final bg    = _bgImage;
    final waves = _wavesImage;
    if (bg == null || waves == null) return const SizedBox.shrink();

    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: double.infinity,
        height: widget.size * 1.9,
        child: AnimatedBuilder(
          animation: Listenable.merge([_travel, widget.pulse]),
          builder: (_, __) => CustomPaint(
            painter: _LayeredOrbPainter(
              bgImage:    bg,
              wavesImage: waves,
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

// ── Two-layer orb painter ─────────────────────────────────────────────────────
//
// Layer 1 — aurora_bg.png:  static sphere/ring/glow, brightness-modulated only.
// Layer 2 — aurora_waves.png: ONLY the colorful strands, warped by a converging
//           sine wave driven by amplitude. The background never moves.
// Layer 3 — Screen-blend glow: center hot-spot + outward rings, adds light only.

class _LayeredOrbPainter extends CustomPainter {
  final ui.Image bgImage;
  final ui.Image wavesImage;
  final double travel;
  final double pulse;
  final OrbState state;
  final double brightness;
  final double orbRadius;

  _LayeredOrbPainter({
    required this.bgImage,
    required this.wavesImage,
    required this.travel,
    required this.pulse,
    required this.state,
    required this.brightness,
    required this.orbRadius,
  });

  // Warp amplitude — zero dormant, full when speaking.
  double get _warpAmp => switch (state) {
    OrbState.speaking  => 0.50 + 0.50 * pulse,
    OrbState.listening => 0.20 + 0.18 * pulse,
    OrbState.thinking  => 0.07 + 0.07 * pulse,
    OrbState.dormant   => 0.01 + 0.01 * pulse,
  };

  double get _glowEnergy => switch (state) {
    OrbState.speaking  => 0.55 + 0.45 * pulse,
    OrbState.listening => 0.30 + 0.22 * pulse,
    OrbState.thinking  => 0.16 + 0.12 * pulse,
    OrbState.dormant   => 0.05 + 0.05 * pulse,
  };

  static Color _hsl(double hue) =>
      HSLColor.fromAHSL(1.0, hue % 360, 1.0, 0.60).toColor();

  // Compute BoxFit.fitHeight geometry for an image inside the canvas.
  ({double x, double y, double w, double h}) _fitHeight(
      ui.Image image, Size canvas) {
    final scale = canvas.height / image.height;
    final w     = image.width  * scale;
    final h     = canvas.height;
    final x     = (canvas.width - w) / 2;
    return (x: x, y: 0.0, w: w, h: h);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final tRad = travel * math.pi * 2;
    final b    = brightness;

    final brightPaint = Paint()
      ..filterQuality = FilterQuality.medium
      ..colorFilter   = ColorFilter.matrix([
        b, 0, 0, 0, 0,
        0, b, 0, 0, 0,
        0, 0, b, 0, 0,
        0, 0, 0, 1, 0,
      ]);

    // ── Layer 1: static background ────────────────────────────────────────────
    final bg = _fitHeight(bgImage, size);
    canvas.drawImageRect(
      bgImage,
      Rect.fromLTWH(0, 0, bgImage.width.toDouble(), bgImage.height.toDouble()),
      Rect.fromLTWH(bg.x, bg.y, bg.w, bg.h),
      brightPaint,
    );

    // ── Layer 2: scanline-warped wave strands ─────────────────────────────────
    // The background stays perfectly still. Only the colorful strands move.
    final wv  = _fitHeight(wavesImage, size);
    final iw  = wavesImage.width.toDouble();
    final ih  = wavesImage.height.toDouble();
    final amp = _warpAmp;

    const nSlices   = 160;
    final srcSliceW = iw / nSlices;
    final dstSliceW = wv.w / nSlices;

    for (int i = 0; i < nSlices; i++) {
      final t = i / nSlices;

      final srcRect = Rect.fromLTWH(t * iw, 0, srcSliceW, ih);
      final dstX    = wv.x + t * wv.w;

      // Convergence envelope: 0 at centre, 1 at edges.
      final d   = (t - 0.5).abs() * 2.0;
      final env = d * d;

      // Inward traveling wave: left converges right, right converges left.
      final inward = t < 0.5 ? -tRad : tRad;

      final dy = wv.h * amp * (
          env * math.sin(t * math.pi * 3.8 + tRad       + inward       ) * 0.080
        + env * math.sin(t * math.pi * 8.5 + tRad * 1.5 + inward * 1.1) * 0.035
        +       math.sin(t * math.pi * 14.0 + tRad * 2.2               ) * 0.010
      );

      canvas.drawImageRect(
        wavesImage, srcRect,
        Rect.fromLTWH(dstX, dy, dstSliceW, wv.h),
        brightPaint,
      );
    }

    // ── Layer 3: screen-blend glow (only adds light) ──────────────────────────
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
    canvas.drawCircle(center, r * 0.85,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(e * 0.26),
          const Color(0xFFFF8800).withOpacity(e * 0.10),
          Colors.transparent,
        ],
        stops: const [0.0, 0.38, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.85)));

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

      final col = _hsl((travel * 360 + i * 90) % 360);
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
  bool shouldRepaint(_LayeredOrbPainter old) =>
      old.travel     != travel     ||
      old.pulse      != pulse      ||
      old.state      != state      ||
      old.brightness != brightness;
}
