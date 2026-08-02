// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora's face — a Flutter port of aurora-acm/kernel/src/expression/{face,color}.rs.
// The ACM kernel's own philosophy: "the face is her body surface... nothing is
// scripted or hardcoded" — every geometric and color parameter below is a pure
// function of live axis state (X/T/N/B/A), matching the kernel's derivation
// exactly. No blink cycles, no idle-fidget animation — the only motion this
// widget adds on top of the kernel's own math is an ease between successive
// axis snapshots (see _axisAnim below), so the face reads as continuously
// alive rather than snapping once per snapshot; the kernel doesn't need this
// because it redraws from fresh axis state at 60 Hz, but the bridge can only
// push snapshots to Flutter roughly once a second.
import 'dart:math' as math;
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

/// Mirrors FaceState::from_axes — all fields are fractions of canvas [0..1]
/// except mouthThickness, which is a reference-pixel radius (see painter).
class _FaceGeometry {
  final double leftEyeCx, leftEyeCy, rightEyeCx, rightEyeCy;
  final double eyeRadius, eyeOpenness;
  final double pupilDx, pupilDy;
  final double mouthP0x, mouthP0y, mouthP1x, mouthP1y, mouthP2x, mouthP2y;
  final double mouthThickness;

  const _FaceGeometry({
    required this.leftEyeCx, required this.leftEyeCy,
    required this.rightEyeCx, required this.rightEyeCy,
    required this.eyeRadius, required this.eyeOpenness,
    required this.pupilDx, required this.pupilDy,
    required this.mouthP0x, required this.mouthP0y,
    required this.mouthP1x, required this.mouthP1y,
    required this.mouthP2x, required this.mouthP2y,
    required this.mouthThickness,
  });

  factory _FaceGeometry.fromAxes(Map<String, double> ax) {
    final x = ax['X'] ?? 0.5, t = ax['T'] ?? 0.5, b = ax['B'] ?? 0.5;
    final expr = _expressionFromAxes(ax);

    // Eye openness scales with X (existence/perception); never fully closed.
    final eyeOpenness = 0.55 + x * 0.45;

    // Gaze: B shifts pupil right (scanning outward); T shifts pupil up
    // (temporal focus = looking ahead).
    final pupilDx = (b - 0.5) * 0.6;
    final pupilDy = -(t - 0.5) * 0.4;

    const mouthYBase = 0.70, mouthLeft = 0.30, mouthRight = 0.70;
    final mouthP1y = switch (expr) {
      _Expression.joyful        => mouthYBase + 0.10,
      _Expression.happy         => mouthYBase + 0.07,
      _Expression.neutral       => mouthYBase,
      _Expression.attentive     => mouthYBase - 0.01,
      _Expression.contemplative => mouthYBase - 0.04,
      _Expression.uncertain     => mouthYBase - 0.06,
      _Expression.tired         => mouthYBase - 0.08,
    };
    final mouthThickness = switch (expr) {
      _Expression.joyful => 5.0,
      _Expression.happy  => 4.0,
      _                  => 3.0,
    };

    return _FaceGeometry(
      leftEyeCx: 0.35, leftEyeCy: 0.40,
      rightEyeCx: 0.65, rightEyeCy: 0.40,
      eyeRadius: 0.10, eyeOpenness: eyeOpenness,
      pupilDx: pupilDx, pupilDy: pupilDy,
      mouthP0x: mouthLeft, mouthP0y: mouthYBase,
      mouthP1x: 0.50, mouthP1y: mouthP1y,
      mouthP2x: mouthRight, mouthP2y: mouthYBase,
      mouthThickness: mouthThickness,
    );
  }
}

/// Mirrors axes_to_background — base purple #7B5EA7, shaded by X/N/A.
Color _backgroundColor(Map<String, double> ax) {
  final x = ax['X'] ?? 0.5, n = ax['N'] ?? 0.5, a = ax['A'] ?? 0.5;
  int lerp(int a0, int b0, double t) => (a0 + (b0 - a0) * t.clamp(0.0, 1.0)).round();
  return Color.fromARGB(255, lerp(100, 150, x), lerp(70, 110, n), lerp(130, 200, a));
}

const _pupilColor = Color.fromARGB(255, 30, 20, 50);

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

  _FacePainter({required this.axisState, required this.glowEnergy});

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    if (w <= 0 || h <= 0) return;

    final geo = _FaceGeometry.fromAxes(axisState);

    // Background fill — the whole canvas is Aurora's emotional skin.
    canvas.drawRect(Rect.fromLTWH(0, 0, w, h), Paint()..color = _backgroundColor(axisState));

    // State-feedback glow (listening/thinking/speaking), behind the face.
    if (glowEnergy > 0.01) {
      final center = Offset(w / 2, h / 2);
      final r = math.min(w, h) * 0.45;
      canvas.drawCircle(
        center, r,
        Paint()
          ..shader = RadialGradient(
            colors: [Colors.white.withOpacity(glowEnergy * 0.20), Colors.transparent],
          ).createShader(Rect.fromCircle(center: center, radius: r)),
      );
    }

    final baseR      = geo.eyeRadius * h;
    final eyeR       = baseR * geo.eyeOpenness;
    final pupilR     = eyeR * 0.35;
    final highlightR = pupilR * 0.40;
    final poffX      = geo.pupilDx * eyeR;
    final poffY      = geo.pupilDy * eyeR;
    final hlOff      = pupilR * 0.45;

    void drawEye(double cxFrac, double cyFrac) {
      final cx = cxFrac * w, cy = cyFrac * h;
      canvas.drawCircle(Offset(cx, cy), eyeR, Paint()..color = Colors.white);
      final px = cx + poffX, py = cy + poffY;
      canvas.drawCircle(Offset(px, py), pupilR, Paint()..color = _pupilColor);
      canvas.drawCircle(Offset(px - hlOff, py - hlOff), highlightR, Paint()..color = Colors.white);
    }

    drawEye(geo.leftEyeCx, geo.leftEyeCy);
    drawEye(geo.rightEyeCx, geo.rightEyeCy);

    // Mouth — same quadratic-bezier control points as the kernel; drawn as a
    // native stroked Path rather than the bare-metal dot-trail (a workaround
    // for having no curve primitive on the framebuffer — Flutter's Canvas
    // already anti-aliases a quadratic bezier stroke to the same shape).
    final p0 = Offset(geo.mouthP0x * w, geo.mouthP0y * h);
    final p1 = Offset(geo.mouthP1x * w, geo.mouthP1y * h);
    final p2 = Offset(geo.mouthP2x * w, geo.mouthP2y * h);
    final path = Path()
      ..moveTo(p0.dx, p0.dy)
      ..quadraticBezierTo(p1.dx, p1.dy, p2.dx, p2.dy);

    // Reference thickness (3-5) was tuned as a raw pixel radius for a fixed
    // bare-metal framebuffer resolution; scale it to this canvas's own
    // height so it reads the same on any device.
    final strokeWidth = (geo.mouthThickness * 2.0) * (h / 600.0);
    canvas.drawPath(
      path,
      Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth.clamp(2.0, 24.0)
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_FacePainter old) =>
      !_axesEqual(old.axisState, axisState) || old.glowEnergy != glowEnergy;
}
