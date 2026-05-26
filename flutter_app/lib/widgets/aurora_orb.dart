import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

enum OrbState { dormant, listening, thinking, speaking }

// ── Per-strand config ─────────────────────────────────────────────────────────
//
// Each strand has a primary state where it comes alive.
// When dormant: all strands near-still.
// When listening: cyan + blue active, others dim.
// When thinking:  blue + purple active, others dim.
// When speaking:  all strands surge — full expression.

class _StrandDef {
  final String asset;
  final OrbState primaryState;
  final OrbState? secondaryState;

  const _StrandDef(this.asset, this.primaryState, [this.secondaryState]);
}

const _strands = [
  _StrandDef('assets/strand_cyan.png',   OrbState.listening, null),
  _StrandDef('assets/strand_blue.png',   OrbState.listening, OrbState.thinking),
  _StrandDef('assets/strand_purple.png', OrbState.thinking,  null),
  _StrandDef('assets/strand_pink.png',   OrbState.speaking,  OrbState.thinking),
  _StrandDef('assets/strand_warm.png',   OrbState.speaking,  null),
];

// ─────────────────────────────────────────────────────────────────────────────

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

class _AuroraOrbState extends State<AuroraOrb> with TickerProviderStateMixin {
  // One travel controller per strand
  late final List<AnimationController> _travels;
  ui.Image? _bgImage;
  final List<ui.Image?> _strandImages = List.filled(_strands.length, null);

  // Travel duration (ms) for each strand in each state
  static int _travelMs(int idx, OrbState state) {
    final def = _strands[idx];
    final isPrimary   = state == def.primaryState;
    final isSecondary = def.secondaryState != null && state == def.secondaryState;
    final isSpeaking  = state == OrbState.speaking;

    if (isSpeaking)               return 700 + idx * 80;   // all fast when speaking
    if (isPrimary)                return 1200 + idx * 100;  // primary state speed
    if (isSecondary)              return 2400 + idx * 120;  // secondary: slower
    if (state == OrbState.dormant) return 9000 + idx * 500; // barely alive
    return 5000 + idx * 300;                                // background drift
  }

  // Warp amplitude for each strand in current state
  static double _amp(int idx, OrbState state, double pulse) {
    final def = _strands[idx];
    final isPrimary   = state == def.primaryState;
    final isSecondary = def.secondaryState != null && state == def.secondaryState;
    final isSpeaking  = state == OrbState.speaking;

    if (isSpeaking)                return 0.52 + 0.48 * pulse;
    if (isPrimary)                 return 0.32 + 0.22 * pulse;
    if (isSecondary)               return 0.14 + 0.10 * pulse;
    if (state == OrbState.dormant) return 0.01 + 0.01 * pulse;
    return 0.05 + 0.04 * pulse;   // not active — very faint drift
  }

  // Brightness for each strand in current state
  static double _brightness(int idx, OrbState state, double pulse) {
    final def = _strands[idx];
    final isPrimary   = state == def.primaryState;
    final isSecondary = def.secondaryState != null && state == def.secondaryState;
    final isSpeaking  = state == OrbState.speaking;

    if (isSpeaking)                return (0.80 + 0.20 * pulse).clamp(0, 1.0);
    if (isPrimary)                 return (0.62 + 0.18 * pulse).clamp(0, 1.0);
    if (isSecondary)               return (0.38 + 0.12 * pulse).clamp(0, 1.0);
    if (state == OrbState.dormant) return 0.10 + 0.04 * pulse;
    return 0.18 + 0.06 * pulse;
  }

  @override
  void initState() {
    super.initState();
    _travels = List.generate(_strands.length, (i) {
      return AnimationController(
        vsync: this,
        duration: Duration(milliseconds: _travelMs(i, widget.state)),
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
    if (old.state != widget.state) {
      for (int i = 0; i < _travels.length; i++) {
        _travels[i]
          ..duration = Duration(milliseconds: _travelMs(i, widget.state))
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
    OrbState.speaking  => 0.70 + widget.pulse.value * 0.20,
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

    // Merge all travel animations + pulse into one listenable
    final animations = <Listenable>[widget.pulse, ...
        _travels.where((c) => _strandImages[_travels.indexOf(c)] != null)];
    final merged = Listenable.merge(animations);

    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: double.infinity,
        height: widget.size * 1.9,
        child: AnimatedBuilder(
          animation: merged,
          builder: (_, __) {
            final travelVals = _travels.map((c) => c.value).toList();
            return CustomPaint(
              painter: _LayeredOrbPainter(
                bgImage:      bg,
                strandImages: _strandImages,
                travelVals:   travelVals,
                pulse:        widget.pulse.value,
                state:        widget.state,
                bgBrightness: _bgBrightness.clamp(0, 1.0),
                glowEnergy:   _glowEnergy,
                orbRadius:    widget.size / 2,
              ),
            );
          },
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
  final double pulse;
  final OrbState state;
  final double bgBrightness;
  final double glowEnergy;
  final double orbRadius;

  _LayeredOrbPainter({
    required this.bgImage,
    required this.strandImages,
    required this.travelVals,
    required this.pulse,
    required this.state,
    required this.bgBrightness,
    required this.glowEnergy,
    required this.orbRadius,
  });

  static Color _hsl(double hue) =>
      HSLColor.fromAHSL(1.0, hue % 360, 1.0, 0.60).toColor();

  ({double x, double w, double h}) _fitHeight(ui.Image img, Size canvas) {
    final scale = canvas.height / img.height;
    final w     = img.width * scale;
    return (x: (canvas.width - w) / 2, w: w, h: canvas.height);
  }

  @override
  void paint(Canvas canvas, Size size) {
    // ── Background (static) ───────────────────────────────────────────────────
    final bgFit = _fitHeight(bgImage, size);
    canvas.drawImageRect(
      bgImage,
      Rect.fromLTWH(0, 0, bgImage.width.toDouble(), bgImage.height.toDouble()),
      Rect.fromLTWH(bgFit.x, 0, bgFit.w, bgFit.h),
      _brightPaint(bgBrightness),
    );

    // ── Each strand with its own travel + amplitude ───────────────────────────
    for (int i = 0; i < _strands.length; i++) {
      final img = strandImages[i];
      if (img == null) continue;

      final travel = travelVals[i];
      final tRad   = travel * math.pi * 2;
      final amp    = _AuroraOrbState._amp(i, state, pulse);
      final bright = _AuroraOrbState._brightness(i, state, pulse);

      _drawStrand(canvas, size, img, tRad, amp, bright);
    }

    // ── Screen-blend glow (adds light only) ───────────────────────────────────
    final tRad0 = travelVals.isNotEmpty ? travelVals[0] * math.pi * 2 : 0.0;
    final center = Offset(size.width / 2, size.height / 2);
    final r      = orbRadius;

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
    final fit = _fitHeight(img, size);
    final iw  = img.width.toDouble();
    final ih  = img.height.toDouble();
    final paint = _brightPaint(bright);

    const nSlices   = 160;
    final srcSliceW = iw / nSlices;
    final dstSliceW = fit.w / nSlices;

    for (int i = 0; i < nSlices; i++) {
      final t = i / nSlices;

      final d     = (t - 0.5).abs() * 2.0;
      final env   = d * d;
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
      old.pulse      != pulse      ||
      old.state      != state      ||
      old.bgBrightness != bgBrightness ||
      old.travelVals.toString() != travelVals.toString();
}
