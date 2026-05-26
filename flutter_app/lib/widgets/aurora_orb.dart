import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

enum OrbState { dormant, listening, thinking, speaking }

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

class _AuroraOrbState extends State<AuroraOrb> with SingleTickerProviderStateMixin {
  late final AnimationController _travel;
  ui.Image? _orbImage;

  // Average of all axis values drives animation energy
  double get _energy {
    if (widget.axisState.isEmpty) return 0.5;
    return widget.axisState.values.reduce((a, b) => a + b) / widget.axisState.length;
  }

  // axis=0 → 8 s per cycle (barely alive), axis=1 → 700 ms (surging)
  static int _periodMs(double e) =>
      (8000 - e.clamp(0.0, 1.0) * 7300).round().clamp(700, 8000);

  @override
  void initState() {
    super.initState();
    _travel = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: _periodMs(_energy)),
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
    final newMs = _periodMs(_energy);
    if (_travel.duration?.inMilliseconds != newMs) {
      _travel
        ..duration = Duration(milliseconds: newMs)
        ..repeat();
    }
  }

  @override
  void dispose() {
    _travel.dispose();
    _orbImage?.dispose();
    super.dispose();
  }

  double get _glowEnergy => switch (widget.state) {
    OrbState.speaking  => 0.55 + 0.45 * widget.pulse.value,
    OrbState.listening => 0.30 + 0.22 * widget.pulse.value,
    OrbState.thinking  => 0.18 + 0.14 * widget.pulse.value,
    OrbState.dormant   => 0.05 + 0.05 * widget.pulse.value,
  };

  @override
  Widget build(BuildContext context) {
    final img = _orbImage;
    if (img == null) return const SizedBox.shrink();

    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: double.infinity,
        height: widget.size * 1.9,
        child: AnimatedBuilder(
          animation: Listenable.merge([widget.pulse, _travel]),
          builder: (_, __) => CustomPaint(
            painter: _OrbPainter(
              image:      img,
              travelVal:  _travel.value,
              energy:     _energy,
              pulse:      widget.pulse.value,
              state:      widget.state,
              glowEnergy: _glowEnergy,
              orbRadius:  widget.size / 2,
            ),
          ),
        ),
      ),
    );
  }
}

class _OrbPainter extends CustomPainter {
  final ui.Image image;
  final double travelVal;
  final double energy;
  final double pulse;
  final OrbState state;
  final double glowEnergy;
  final double orbRadius;

  _OrbPainter({
    required this.image,
    required this.travelVal,
    required this.energy,
    required this.pulse,
    required this.state,
    required this.glowEnergy,
    required this.orbRadius,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final iw    = image.width.toDouble();
    final ih    = image.height.toDouble();
    final scale = size.height / ih;
    final w     = iw * scale;
    final ox    = (size.width - w) / 2;

    final tRad = travelVal * math.pi * 2;
    // Warp amplitude driven by axis energy; speaking pulse adds a kick
    final amp  = energy * 0.10
        + (state == OrbState.speaking ? pulse * energy * 0.08 : 0.0);

    const nSlices   = 120;
    final srcSliceW = iw / nSlices;
    final dstSliceW = w  / nSlices;

    // Screen-blend layer: black pixels in the photo vanish against any background.
    // screen(black, dst) = dst — the app background shows through wherever the photo is black.
    canvas.saveLayer(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..blendMode = BlendMode.screen,
    );

    final imgPaint = Paint()..filterQuality = FilterQuality.medium;

    for (int i = 0; i < nSlices; i++) {
      final t = i / nSlices;
      // env peaks at the edges where strands radiate, drops to 0 at the stable core
      final d      = (t - 0.5).abs() * 2.0;
      final env    = d * d;
      final inward = t < 0.5 ? -tRad : tRad;

      final dy = size.height * amp * (
          env * math.sin(t * math.pi * 3.8  + tRad       + inward       ) * 0.080
        + env * math.sin(t * math.pi * 8.5  + tRad * 1.5 + inward * 1.1 ) * 0.035
        +       math.sin(t * math.pi * 14.0 + tRad * 2.2                 ) * 0.010
      );

      canvas.drawImageRect(
        image,
        Rect.fromLTWH(t * iw, 0, srcSliceW, ih),
        Rect.fromLTWH(ox + t * w, dy, dstSliceW, size.height),
        imgPaint,
      );
    }

    canvas.restore();

    // Subtle atmospheric glow over the core — screen blend only adds light, never obscures
    final center = Offset(size.width / 2, size.height / 2);
    final r      = orbRadius;
    final e      = glowEnergy;

    canvas.saveLayer(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..blendMode = BlendMode.screen,
    );
    canvas.drawCircle(
      center, r * 0.85,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(e * 0.22),
          const Color(0xFFFF8800).withOpacity(e * 0.08),
          Colors.transparent,
        ],
        stops: const [0.0, 0.38, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.85)),
    );
    canvas.drawCircle(
      center, r * 0.15,
      Paint()..shader = RadialGradient(
        colors: [
          Colors.white.withOpacity(e * 0.80),
          const Color(0xFFFFFF88).withOpacity(e * 0.40),
          Colors.transparent,
        ],
        stops: const [0.0, 0.45, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: r * 0.15)),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(_OrbPainter old) =>
      old.travelVal  != travelVal  ||
      old.energy     != energy     ||
      old.pulse      != pulse      ||
      old.state      != state      ||
      old.glowEnergy != glowEnergy;
}
