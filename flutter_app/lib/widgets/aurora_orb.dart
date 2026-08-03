// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora's face — minimal, Nick Jr "Face"-style: one solid black shape,
// no separate detailed eyes. The shape's form (round dot, elongated
// smile, colon-style double-dot, slanted cut) is a pure function of live
// axis state (X/T/N/B/A), and its openness pulses in sync with speech
// (the same word-boundary pulse home_screen.dart already drives TTS
// with) so it visibly moves while she talks instead of sitting static.
import 'package:flutter/material.dart';

enum OrbState { dormant, listening, thinking, speaking }

enum _Expression { joyful, happy, contemplative, attentive, uncertain, tired, neutral }

_Expression _expressionFromAxes(Map<String, double> ax) {
  final x = ax['X'] ?? 0.5, t = ax['T'] ?? 0.5, n = ax['N'] ?? 0.5, b = ax['B'] ?? 0.5, a = ax['A'] ?? 0.5;
  if (a > 0.80 && n > 0.65) return _Expression.joyful;
  if (a > 0.65) return _Expression.happy;
  if (b > 0.70 && t > 0.65 && a < 0.45) return _Expression.contemplative;
  if (x > 0.80 && a < 0.55) return _Expression.attentive;
  if (n < 0.40 && b < 0.45) return _Expression.uncertain;
  if (n < 0.35 && t < 0.45) return _Expression.tired;
  return _Expression.neutral;
}

enum _ShapeKind { dot, colon }

/// One shape config per expression: how wide/tall the base dot is (as a
/// fraction of the reference size) and how far it's rotated. `colon`
/// overrides width/height/rotation with two small stacked dots instead.
class _MouthShape {
  final _ShapeKind kind;
  final double widthScale;
  final double heightScale;
  final double rotation; // radians
  const _MouthShape(this.kind, this.widthScale, this.heightScale, this.rotation);

  factory _MouthShape.fromExpression(_Expression expr) {
    switch (expr) {
      case _Expression.joyful:
        return const _MouthShape(_ShapeKind.dot, 3.2, 1.0, 0.0); // wide open smile
      case _Expression.happy:
        return const _MouthShape(_ShapeKind.dot, 2.4, 1.0, 0.0); // elongated dot
      case _Expression.contemplative:
        return const _MouthShape(_ShapeKind.dot, 2.0, 0.85, -0.45); // slant cut
      case _Expression.attentive:
        return const _MouthShape(_ShapeKind.dot, 1.1, 1.1, 0.0); // slightly alert dot
      case _Expression.uncertain:
        return const _MouthShape(_ShapeKind.colon, 1.0, 1.0, 0.0); // colon-shaped
      case _Expression.tired:
        return const _MouthShape(_ShapeKind.dot, 3.0, 0.35, 0.0); // thin horizontal slit
      case _Expression.neutral:
        return const _MouthShape(_ShapeKind.dot, 1.0, 1.0, 0.0); // plain dot
    }
  }
}

/// Mirrors axes_to_background — base purple #7B5EA7, shaded by X/N/A.
Color _backgroundColor(Map<String, double> ax) {
  final x = ax['X'] ?? 0.5, n = ax['N'] ?? 0.5, a = ax['A'] ?? 0.5;
  int lerp(int a0, int b0, double t) => (a0 + (b0 - a0) * t.clamp(0.0, 1.0)).round();
  return Color.fromARGB(255, lerp(100, 150, x), lerp(70, 110, n), lerp(130, 200, a));
}

bool _axesEqual(Map<String, double> a, Map<String, double> b) {
  for (final k in const ['X', 'T', 'N', 'B', 'A']) {
    if ((a[k] ?? 0.5) != (b[k] ?? 0.5)) return false;
  }
  return true;
}

Map<String, double> _lerpAxes(Map<String, double> a, Map<String, double> b, double t) {
  final out = <String, double>{};
  for (final k in const ['X', 'T', 'N', 'B', 'A']) {
    final av = a[k] ?? 0.5, bv = b[k] ?? 0.5;
    out[k] = av + (bv - av) * t;
  }
  return out;
}

class AuroraOrb extends StatefulWidget {
  final OrbState state;
  final double size;
  /// Explicit canvas height. When null the widget uses [size] × 1.9.
  /// Pass the available layout height here for full-screen idle display.
  final double? height;
  final Animation<double> pulse;
  final Map<String, double> axisState;
  final VoidCallback? onTap;

  const AuroraOrb({
    super.key,
    required this.state,
    required this.pulse,
    required this.axisState,
    this.size = 120,
    this.height,
    this.onTap,
  });

  @override
  State<AuroraOrb> createState() => _AuroraOrbState();
}

class _AuroraOrbState extends State<AuroraOrb> with SingleTickerProviderStateMixin {
  // Axis snapshots arrive discretely (bridge pushes ~1/s, and the underlying
  // state itself only drifts every ~12-20 s while idle) — easing between the
  // last two snapshots is what makes the face read as continuously alive
  // rather than snapping to a new expression once a second.
  late final AnimationController _axisAnim;
  late Map<String, double> _prevAxis;
  late Map<String, double> _targetAxis;

  Map<String, double> get _liveAxis => _lerpAxes(_prevAxis, _targetAxis, Curves.easeInOut.transform(_axisAnim.value));

  @override
  void initState() {
    super.initState();
    _prevAxis = widget.axisState;
    _targetAxis = widget.axisState;
    _axisAnim = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
      value: 1.0,
    );
  }

  @override
  void didUpdateWidget(AuroraOrb old) {
    super.didUpdateWidget(old);
    if (!_axesEqual(_targetAxis, widget.axisState)) {
      _prevAxis = _liveAxis;
      _targetAxis = widget.axisState;
      _axisAnim
        ..stop()
        ..value = 0.0
        ..forward();
    }
  }

  @override
  void dispose() {
    _axisAnim.dispose();
    super.dispose();
  }

  // Not part of the ACM face itself — a state-feedback glow layered behind
  // it, since listening/thinking/speaking are app-level STT/TTS states the
  // bare-metal kernel has no concept of.
  double get _glowEnergy => switch (widget.state) {
    OrbState.speaking  => 0.55 + 0.45 * widget.pulse.value,
    OrbState.listening => 0.30 + 0.22 * widget.pulse.value,
    OrbState.thinking  => 0.18 + 0.14 * widget.pulse.value,
    OrbState.dormant   => 0.05 + 0.05 * widget.pulse.value,
  };

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: double.infinity,
        height: widget.height ?? widget.size * 1.9,
        child: AnimatedBuilder(
          animation: Listenable.merge([widget.pulse, _axisAnim]),
          builder: (_, __) => CustomPaint(
            painter: _FacePainter(
              axisState:  _liveAxis,
              glowEnergy: _glowEnergy,
              speaking:   widget.state == OrbState.speaking,
              pulse:      widget.pulse.value,
            ),
            child: const SizedBox.expand(),
          ),
        ),
      ),
    );
  }
}

class _FacePainter extends CustomPainter {
  final Map<String, double> axisState;
  final double glowEnergy;
  final bool speaking;
  final double pulse;

  _FacePainter({
    required this.axisState,
    required this.glowEnergy,
    required this.speaking,
    required this.pulse,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    if (w <= 0 || h <= 0) return;

    final expr = _expressionFromAxes(axisState);
    final shape = _MouthShape.fromExpression(expr);

    // Background fill — the whole canvas is Aurora's emotional skin.
    canvas.drawRect(Rect.fromLTWH(0, 0, w, h), Paint()..color = _backgroundColor(axisState));

    // State-feedback glow (listening/thinking/speaking), behind the shape.
    if (glowEnergy > 0.01) {
      final center = Offset(w / 2, h / 2);
      final r = (w < h ? w : h) * 0.45;
      canvas.drawCircle(
        center, r,
        Paint()
          ..shader = RadialGradient(
            colors: [Colors.white.withOpacity(glowEnergy * 0.20), Colors.transparent],
          ).createShader(Rect.fromCircle(center: center, radius: r)),
      );
    }

    // While speaking, the pulse (already kicked to 1.0 on each TTS word
    // boundary, see home_screen.dart's _kickPulse) opens the shape taller
    // in sync with speech instead of it sitting static.
    final speakOpen = speaking ? (1.0 + pulse * 0.9) : 1.0;

    final refSize = (w < h ? w : h) * 0.16;
    final paint = Paint()..color = Colors.black;

    if (shape.kind == _ShapeKind.colon) {
      final dotR = refSize * 0.32;
      final gap = refSize * 0.9 * speakOpen;
      final cx = w / 2, cy = h / 2;
      canvas.drawCircle(Offset(cx, cy - gap / 2), dotR, paint);
      canvas.drawCircle(Offset(cx, cy + gap / 2), dotR, paint);
      return;
    }

    final rw = refSize * shape.widthScale;
    final rh = refSize * shape.heightScale * speakOpen;
    canvas.save();
    canvas.translate(w / 2, h / 2);
    canvas.rotate(shape.rotation);
    final rrect = RRect.fromRectAndRadius(
      Rect.fromCenter(center: Offset.zero, width: rw, height: rh),
      Radius.circular((rw < rh ? rw : rh) / 2), // fully rounded ends -> stadium/dot shape
    );
    canvas.drawRRect(rrect, paint);
    canvas.restore();
  }

  @override
  bool shouldRepaint(_FacePainter old) =>
      !_axesEqual(old.axisState, axisState) ||
      old.glowEnergy != glowEnergy ||
      old.speaking != speaking ||
      old.pulse != pulse;
}
