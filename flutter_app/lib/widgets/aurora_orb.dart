import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

enum OrbState { dormant, listening, thinking, speaking }

// ── Strand definitions ────────────────────────────────────────────────────────
//
// Each strand is bound to one of Aurora's internal emotional/cognitive axes.
// The axis value (0.0–1.0) directly drives that strand's speed and amplitude.
//
//   X  Extension / outward reach   →  warm orange-red strand
//   T  Temporal / continuity       →  blue strand
//   N  Novelty / curiosity         →  cyan strand
//   B  Boundary / identity         →  purple strand
//   A  Affective / emotion         →  pink-magenta strand

class _StrandDef {
  final String asset;
  final String axis; // X | T | N | B | A
  const _StrandDef(this.asset, this.axis);
}

const _strands = [
  _StrandDef('assets/strand_cyan.png',   'N'),
  _StrandDef('assets/strand_blue.png',   'T'),
  _StrandDef('assets/strand_purple.png', 'B'),
  _StrandDef('assets/strand_pink.png',   'A'),
  _StrandDef('assets/strand_warm.png',   'X'),
];

// ─────────────────────────────────────────────────────────────────────────────

class AuroraOrb extends StatefulWidget {
  final OrbState state;
  final double size;
  final Animation<double> pulse;
  final Map<String, double> axisState;
  final VoidCallback? onTap;

  const AuroraOrb({
    super.key,
    required this.state,
    required this.pulse,
    required this.axisState,
    this.size = 120,
    this.onTap,
  });

  @override
  State<AuroraOrb> createState() => _AuroraOrbState();
}

class _AuroraOrbState extends State<AuroraOrb> with TickerProviderStateMixin {
  late final List<AnimationController> _travels;
  ui.Image? _bgImage;
  final List<ui.Image?> _strandImages = List.filled(_strands.length, null);

  // Travel period: axis=0 → 8 s (barely alive), axis=1 → 700 ms (surging).
  static int _periodMs(double axisVal) =>
      (8000 - axisVal.clamp(0.0, 1.0) * 7300).round().clamp(700, 8000);

  @override
  void initState() {
    super.initState();
    _travels = List.generate(_strands.length, (i) {
      final v = widget.axisState[_strands[i].axis] ?? 0.5;
      return AnimationController(
        vsync: this,
        duration: Duration(milliseconds: _periodMs(v)),
      )..repeat();
    });
    _loadImages();
  }

  Future<void> _loadImages() async {
    final bg = await _loadUiImage('assets/aurora_bg.png');
    if (mounted) setState(() => _bgImage = bg);
    for (int i = 0; i < _strands.length; i++) {
      final img = await _loadUiImage(_strands[i].asset);
      if (mounted) setState(() => _strandImages[i] = img);
    }
  }

  static Future<ui.Image> _loadUiImage(String asset) async {
    final data  = await rootBundle.load(asset);
    final codec = await ui.instantiateImageCodec(data.buffer.asUint8List());
    return (await codec.getNextFrame()).image;
  }

  @override
  void didUpdateWidget(AuroraOrb old) {
    super.didUpdateWidget(old);
    // Adjust each controller's speed whenever its axis value changes.
    for (int i = 0; i < _travels.length; i++) {
      final newVal = widget.axisState[_strands[i].axis] ?? 0.5;
      final newMs  = _periodMs(newVal);
      if (_travels[i].duration?.inMilliseconds != newMs) {
        _travels[i]
          ..duration = Duration(milliseconds: newMs)
          ..repeat();
      }
    }
  }

  @override
  void dispose() {
    for (final c in _travels) c.dispose();
    _bgImage?.dispose();
    for (final img in _strandImages) img?.dispose();
    super.dispose();
  }

  double get _bgBrightness => switch (widget.state) {
    OrbState.speaking  => (0.70 + widget.pulse.value * 0.20).clamp(0, 1.0),
    OrbState.listening => 0.48 + widget.pulse.value * 0.12,
    OrbState.thinking  => 0.34 + widget.pulse.value * 0.10,
    OrbState.dormant   => 0.16 + widget.pulse.value * 0.06,
  };

  double get _glowEnergy => switch (widget.state) {
    OrbState.speaking  => 0.55 + 0.45 * widget.pulse.value,
    OrbState.listening => 0.30 + 0.22 * widget.pulse.value,
    OrbState.thinking  => 0.18 + 0.14 * widget.pulse.value,
    OrbState.dormant   => 0.05 + 0.05 * widget.pulse.value,
  };

  @override
  Widget build(BuildContext context) {
    final bg = _bgImage;
    if (bg == null) return const SizedBox.shrink();

    final listenables = <Listenable>[widget.pulse, ..._travels];

    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: double.infinity,
        height: widget.size * 1.9,
        child: AnimatedBuilder(
          animation: Listenable.merge(listenables),
          builder: (_, __) => CustomPaint(
            painter: _LayeredOrbPainter(
              bgImage:      bg,
              strandImages: List.unmodifiable(_strandImages),
              travelVals:   _travels.map((c) => c.value).toList(),
              axisVals: List.generate(
                _strands.length,
                (i) => (widget.axisState[_strands[i].axis] ?? 0.5).clamp(0.0, 1.0),
              ),
              pulse:        widget.pulse.value,
              state:        widget.state,
              bgBrightness: _bgBrightness,
              glowEnergy:   _glowEnergy,
              orbRadius:    widget.size / 2,
            ),
          ),
        ),
      ),
    );
  }
}

// ── Painter ───────────────────────────────────────────────────────────────────

class _LayeredOrbPainter extends CustomPainter {
  final ui.Image bgImage;
  final List<ui.Image?> strandImages;
  final List<double> travelVals;
  final List<double> axisVals;  // 0.0–1.0, one per strand
  final double pulse;
  final OrbState state;
  final double bgBrightness;
  final double glowEnergy;
  final double orbRadius;

  _LayeredOrbPainter({
    required this.bgImage,
    required this.strandImages,
    required this.travelVals,
    required this.axisVals,
    required this.pulse,
    required this.state,
    required this.bgBrightness,
    required this.glowEnergy,
    required this.orbRadius,
  });

  static Color _hsl(double hue) =>
      HSLColor.fromAHSL(1.0, hue % 360, 1.0, 0.60).toColor();

  ({double x, double w, double h}) _fit(ui.Image img, Size canvas) {
    final scale = canvas.height / img.height;
    final w     = img.width * scale;
    return (x: (canvas.width - w) / 2, w: w, h: canvas.height);
  }

  @override
  void paint(Canvas canvas, Size size) {
    // ── Static background ─────────────────────────────────────────────────────
    final bgFit = _fit(bgImage, size);
    canvas.drawImageRect(
      bgImage,
      Rect.fromLTWH(0, 0, bgImage.width.toDouble(), bgImage.height.toDouble()),
      Rect.fromLTWH(bgFit.x, 0, bgFit.w, bgFit.h),
      _brightPaint(bgBrightness),
    );

    // ── Each strand driven by its axis value ──────────────────────────────────
    for (int i = 0; i < _strands.length; i++) {
      final img = strandImages[i];
      if (img == null) continue;

      final axisVal = axisVals[i];
      final tRad    = travelVals[i] * math.pi * 2;

      // Warp amplitude = axis value × boost from speaking pulse
      final baseAmp = axisVal * 0.85;
      final amp     = state == OrbState.speaking
          ? baseAmp + pulse * axisVal * 0.15   // word-kicks amplify active axes
          : baseAmp;

      // Brightness: fully bright when axis is high, dim when low
      final bright = (axisVal * 0.85 + 0.10).clamp(0.0, 1.0);

      _drawStrand(canvas, size, img, tRad, amp, bright);
    }

    // ── Screen-blend glow (only adds light) ───────────────────────────────────
    final center = Offset(size.width / 2, size.height / 2);
    final r      = orbRadius;
    final tRad0  = travelVals.isNotEmpty ? travelVals[0] * math.pi * 2 : 0.0;

    canvas.saveLayer(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..blendMode = BlendMode.screen,
    );
    _drawCenterGlow(canvas, center, r);
    if (state != OrbState.dormant) _drawOutwardRings(canvas, center, r, tRad0);
    canvas.restore();
  }

  void _drawStrand(Canvas canvas, Size size, ui.Image img,
      double tRad, double amp, double bright) {
    final fit = _fit(img, size);
    final iw  = img.width.toDouble();
    final ih  = img.height.toDouble();
    final paint = _brightPaint(bright);

    const nSlices   = 160;
    final srcSliceW = iw / nSlices;
    final dstSliceW = fit.w / nSlices;

    for (int i = 0; i < nSlices; i++) {
      final t      = i / nSlices;
      final d      = (t - 0.5).abs() * 2.0;
      final env    = d * d;
      final inward = t < 0.5 ? -tRad : tRad;

      final dy = fit.h * amp * (
          env * math.sin(t * math.pi * 3.8 + tRad       + inward       ) * 0.080
        + env * math.sin(t * math.pi * 8.5 + tRad * 1.5 + inward * 1.1) * 0.035
        +       math.sin(t * math.pi * 14.0 + tRad * 2.2               ) * 0.010
      );

      canvas.drawImageRect(
        img,
        Rect.fromLTWH(t * iw, 0, srcSliceW, ih),
        Rect.fromLTWH(fit.x + t * fit.w, dy, dstSliceW, fit.h),
        paint,
      );
    }
  }

  Paint _brightPaint(double b) => Paint()
    ..filterQuality = FilterQuality.medium
    ..colorFilter   = ColorFilter.matrix([
      b, 0, 0, 0, 0,
      0, b, 0, 0, 0,
      0, 0, b, 0, 0,
      0, 0, 0, 1, 0,
    ]);

  void _drawCenterGlow(Canvas canvas, Offset center, double r) {
    final e = glowEnergy;
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
    final e      = glowEnergy;
    final nRings = state == OrbState.speaking ? 4 : 2;
    for (int i = 0; i < nRings; i++) {
      final travel = travelVals.isNotEmpty ? travelVals[i % travelVals.length] : 0.0;
      final phase  = (travel + i / nRings) % 1.0;
      final ringR  = r * 0.06 + r * 1.15 * phase;
      final op     = (1.0 - phase) * e * 0.55;
      if (op < 0.02) continue;
      final col = _hsl((travel * 360 + i * 72) % 360);
      canvas.drawCircle(center, ringR, Paint()
        ..color = col.withOpacity(op * 0.20)
        ..style = PaintingStyle.stroke
        ..strokeWidth = r * 0.22);
      canvas.drawCircle(center, ringR, Paint()
        ..color = col.withOpacity(op * 0.55)
        ..style = PaintingStyle.stroke
        ..strokeWidth = r * 0.046);
      canvas.drawCircle(center, ringR, Paint()
        ..color = col.withOpacity(op * 0.85)
        ..style = PaintingStyle.stroke
        ..strokeWidth = r * 0.012);
    }
  }

  @override
  bool shouldRepaint(_LayeredOrbPainter old) =>
      old.pulse        != pulse        ||
      old.state        != state        ||
      old.bgBrightness != bgBrightness ||
      old.axisVals.toString() != axisVals.toString() ||
      old.travelVals.toString() != travelVals.toString();
}
