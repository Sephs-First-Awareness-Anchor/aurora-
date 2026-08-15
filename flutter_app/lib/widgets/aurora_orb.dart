// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora's face — Nick Jr "Face"-style: simple black eyes + a mouth on a
// flat color field, no photoreal detail. Reference: Face (Nick Jr's
// shape-shifting host) reads as unmistakably alive from two small dark
// eyes plus a mouth-line, even though every piece is a flat shape.
// Previously this widget drew a mouth shape only, with the "neutral"
// idle state landing on a plain filled circle — the state she spends
// most of her idle time in was also the one that read as just a dot
// instead of a face. Both eyes and mouth are now a pure function of live
// axis state (X/T/N/B/A). While speaking, the resting mouth is replaced
// by an articulated open/close mouth (see _drawTalkingMouth) driven by
// the same word-boundary pulse home_screen.dart already drives TTS
// with -- real jaw motion, not the resting shape breathing bigger and
// smaller.
//
// Sunni: "her expressions and everything should be tailored to her
// internal process ... people wear their expression on their face even
// when they aren't through words." The face used to snap between 7
// fixed looks the moment an axis crossed a hard threshold -- driven by
// real internal state, but discretely, with a hard ceiling of 7 possible
// faces no matter how nuanced the underlying axes actually were.
// _FaceSpec.blend() below replaces that hard switch with a continuous
// one: every one of the 7 looks below is kept as an exact reference
// point (_archetypeSpec), but each has a smooth (sigmoid, not step)
// activation function of the live axes, and the face actually rendered
// is the activation-weighted blend of ALL of them at once -- so a
// resting face doesn't sit on one frozen "neutral" pose, it continuously
// drifts with whatever her real axis state is doing, the way a person's
// face carries a trace of mood even at rest.
//
// Sunni: "I want her mouth to move like Face does -- varied gestures,
// tired into the resting expression, all with a gradient expressive
// applicator so she can express subtlety and high intensity depending
// on the underlying variable." The mouth used to be one of three rigid,
// mutually exclusive shapes (a filled stadium blob, two stacked dots, or
// a stroked curve) with a hard "whichever archetype is winning right
// now" switch between them -- Face's mouth is a single continuously
// deformable line that smirks, sags, purses, and opens, never three
// disconnected shapes. _MouthShape below is now ONE parametric lens
// (independent left/right corner lift + thickness + width + rotation)
// that every archetype expresses as different values of the SAME five
// numbers, so it blends smoothly across the whole vocabulary -- a smirk
// IS an open smile IS a tired sag, just different points on one
// continuous surface. On top of that, _FaceSpec.blend() applies an
// explicit intensity scalar (how far the live axis blend sits outside
// the calm neutral archetype) that scales how far the rendered face is
// allowed to swing from neutral's own baseline -- a barely-triggered
// mood reads as a subtle trace on top of resting neutral, a strongly
// triggered one reads as the full, unmuted expression.
import 'dart:math' as math;
import 'package:flutter/material.dart';

enum OrbState { dormant, listening, thinking, speaking }

enum _Expression { joyful, happy, contemplative, attentive, uncertain, tired, neutral }

/// Continuous (sigmoid, not step) stand-in for each archetype's old hard
/// threshold condition -- 0 far below the threshold, 1 far above it,
/// smoothly crossing 0.5 AT the original threshold value. [steepness]
/// controls how sharp that crossing is; lower = blends further.
double _activationSigmoid(double value, double center, [double steepness = 11.0]) =>
    1.0 / (1.0 + math.exp(-(value - center) * steepness));

/// How strongly each archetype "wants" to be expressed right now, as a
/// continuous function of the live axes -- the same conditions
/// _expressionFromAxes used to gate on, just soft instead of hard.
/// [neutral] carries a constant floor rather than a condition: there is
/// always SOME baseline calm presence blended in, so even an axis state
/// that doesn't strongly match any archetype still renders as a face
/// with quiet character, not a null/undefined expression.
double _archetypeActivation(_Expression expr, double x, double t, double n, double b, double a) {
  switch (expr) {
    case _Expression.joyful:
      return _activationSigmoid(a, 0.80) * _activationSigmoid(n, 0.65);
    case _Expression.happy:
      return _activationSigmoid(a, 0.65);
    case _Expression.contemplative:
      return _activationSigmoid(b, 0.70) * _activationSigmoid(t, 0.65) * (1.0 - _activationSigmoid(a, 0.45));
    case _Expression.attentive:
      return _activationSigmoid(x, 0.80) * (1.0 - _activationSigmoid(a, 0.55));
    case _Expression.uncertain:
      return (1.0 - _activationSigmoid(n, 0.40)) * (1.0 - _activationSigmoid(b, 0.45));
    case _Expression.tired:
      return (1.0 - _activationSigmoid(n, 0.35)) * (1.0 - _activationSigmoid(t, 0.45));
    case _Expression.neutral:
      return 0.35;
  }
}

/// One continuously-deformable mouth, expressed as five numbers instead
/// of a choice between mutually exclusive shapes:
///
///   widthScale          how wide the mouth is
///   thickness           how "open" it reads, from a near-hairline
///                        closed-mouth curve up to a wide open cavity
///   leftLift/rightLift   how far each CORNER sits above (positive) or
///                        below (negative) center, INDEPENDENTLY -- this
///                        is what lets one shape cover a symmetric smile
///                        (both lifted), a symmetric frown/sag (both
///                        dropped), and an asymmetric smirk (one lifted,
///                        one flat or dropped) without a shape switch
///   rotation             overall tilt, radians
///
/// Rendered as a closed lens/vesica path (see _drawMouthLens): a top
/// curve and a bottom curve both running corner to corner, bowed apart
/// by [thickness]. At thickness near zero the two curves nearly
/// coincide and it reads as Face's default stroked smile-line; as
/// thickness grows it reads as an increasingly open mouth -- the same
/// shape machinery Face's own single continuous mouth-line uses,
/// covering the entire range this widget used to need three separate
/// shape kinds for.
class _MouthShape {
  final double widthScale;
  final double thickness;
  final double leftLift;
  final double rightLift;
  final double rotation; // radians
  const _MouthShape(this.widthScale, this.thickness, this.leftLift, this.rightLift, this.rotation);

  factory _MouthShape.fromExpression(_Expression expr) {
    switch (expr) {
      case _Expression.joyful:
        return const _MouthShape(3.0, 0.85, 0.55, 0.55, 0.0); // wide open, both corners high
      case _Expression.happy:
        return const _MouthShape(2.2, 0.55, 0.42, 0.42, 0.0); // smaller open smile
      case _Expression.contemplative:
        return const _MouthShape(1.4, 0.10, 0.05, 0.32, -0.18); // one corner lifted, tilted smirk
      case _Expression.attentive:
        return const _MouthShape(1.25, 0.10, 0.22, 0.22, 0.0); // small alert closed smile
      case _Expression.uncertain:
        return const _MouthShape(1.0, 0.08, -0.10, -0.22, 0.05); // asymmetric worried dip
      case _Expression.tired:
        return const _MouthShape(1.7, 0.06, -0.20, -0.20, 0.0); // thin, corners sagging
      case _Expression.neutral:
        return const _MouthShape(1.9, 0.14, 0.16, 0.16, 0.0); // calm resting baseline
    }
  }
}

enum _EyeKind { oval, arc, closed }

/// One eye config. `oval` is a filled almond with an optional highlight
/// dot (Face's default open eye); `arc` is a thin curved brow-line (no
/// fill, used for thoughtful/worried looks); `closed` is a flat stroked
/// line (drowsy/tired). `dy` and sizes are fractions of the shared
/// reference size so both eyes stay proportional to the mouth.
/// `highlightOpacity` (0..1, not a bool) is what lets the continuous
/// blend below fade the glare in/out smoothly across archetypes instead
/// of snapping it on or off.
class _EyeSpec {
  final _EyeKind kind;
  final double widthScale;
  final double heightScale;
  final double rotation;
  final double dy;
  final double highlightOpacity;
  const _EyeSpec({
    this.kind = _EyeKind.oval,
    this.widthScale = 1.0,
    this.heightScale = 1.0,
    this.rotation = 0.0,
    this.dy = 0.0,
    this.highlightOpacity = 1.0,
  });
}

class _FaceSpec {
  final _EyeSpec leftEye;
  final _EyeSpec rightEye;
  final _MouthShape mouth;
  const _FaceSpec(this.leftEye, this.rightEye, this.mouth);

  /// The archetype's exact, hand-tuned reference look -- still used
  /// directly as one of the inputs [blend] mixes, never rendered as-is
  /// anymore (see [blend] below).
  factory _FaceSpec._archetype(_Expression expr) {
    final mouth = _MouthShape.fromExpression(expr);
    switch (expr) {
      case _Expression.joyful:
        return _FaceSpec(
          const _EyeSpec(widthScale: 1.05, heightScale: 1.05),
          const _EyeSpec(widthScale: 1.05, heightScale: 1.05),
          mouth,
        );
      case _Expression.happy:
        return _FaceSpec(
          const _EyeSpec(widthScale: 1.0, heightScale: 0.95),
          const _EyeSpec(widthScale: 1.0, heightScale: 0.95),
          mouth,
        );
      case _Expression.contemplative:
        // One thoughtful raised brow-arc, one half-lidded eye -- a
        // gentle asymmetry reads as "considering something" the way a
        // perfectly symmetric face can't.
        return _FaceSpec(
          const _EyeSpec(kind: _EyeKind.arc, widthScale: 0.85, heightScale: 0.9, rotation: -0.12, highlightOpacity: 0.0),
          const _EyeSpec(kind: _EyeKind.oval, widthScale: 0.8, heightScale: 0.5, rotation: 0.08, dy: 0.05, highlightOpacity: 0.0),
          mouth,
        );
      case _Expression.attentive:
        return _FaceSpec(
          const _EyeSpec(widthScale: 1.1, heightScale: 1.15, dy: -0.08),
          const _EyeSpec(widthScale: 1.1, heightScale: 1.15, dy: -0.08),
          mouth,
        );
      case _Expression.uncertain:
        // Both brows knit inward and up -- the classic worried look --
        // paired with the existing asymmetric-dip mouth.
        return _FaceSpec(
          const _EyeSpec(kind: _EyeKind.arc, widthScale: 0.65, heightScale: 0.55, rotation: 0.28, highlightOpacity: 0.0),
          const _EyeSpec(kind: _EyeKind.arc, widthScale: 0.65, heightScale: 0.55, rotation: -0.28, highlightOpacity: 0.0),
          mouth,
        );
      case _Expression.tired:
        return _FaceSpec(
          const _EyeSpec(kind: _EyeKind.closed, dy: 0.12, highlightOpacity: 0.0),
          const _EyeSpec(kind: _EyeKind.closed, dy: 0.12, highlightOpacity: 0.0),
          mouth,
        );
      case _Expression.neutral:
        return _FaceSpec(
          const _EyeSpec(widthScale: 0.85, heightScale: 0.85),
          const _EyeSpec(widthScale: 0.85, heightScale: 0.85),
          mouth,
        );
    }
  }

  /// The face actually rendered: every archetype's exact look, blended
  /// by how strongly the live axes activate it (see
  /// _archetypeActivation), THEN scaled by an explicit intensity applied
  /// around the neutral archetype's own baseline.
  ///
  /// Two separate continuous mechanisms stack here:
  ///  1. Numeric shape parameters (size, rotation, droop, glare opacity,
  ///     mouth lift/thickness) are weighted averages across all 7
  ///     archetypes, so they glide rather than snap.
  ///  2. `intensity` -- how much of the current blend's total weight
  ///     sits OUTSIDE the neutral archetype -- then scales how far that
  ///     blended result is allowed to travel from neutral's own
  ///     hand-tuned baseline. At intensity ~0 (nothing strongly
  ///     activated, neutral dominates the blend) the face is pulled
  ///     almost all the way back to plain resting neutral; as intensity
  ///     climbs toward 1 the face is allowed the FULL computed blend.
  ///     This is what makes a barely-triggered mood read as a subtle
  ///     trace on the resting face and a strongly-triggered one read as
  ///     visibly, proportionately more expressive -- a gradient, not a
  ///     fixed-size nudge every time something crosses zero.
  ///
  /// `kind` (oval vs arc vs closed eye -- there's no meaningful halfway
  /// shape between a stroked arc and a filled oval) is a genuinely
  /// categorical choice and stays taken from whichever single archetype
  /// currently has the highest activation, same as before; the mouth no
  /// longer has a categorical `kind` at all (see _MouthShape).
  factory _FaceSpec.blend(Map<String, double> ax) {
    final x = ax['X'] ?? 0.5, t = ax['T'] ?? 0.5, n = ax['N'] ?? 0.5, b = ax['B'] ?? 0.5, a = ax['A'] ?? 0.5;

    _Expression dominant = _Expression.neutral;
    double dominantActivation = -1.0;
    double totalActivation = 0.0;
    final activations = <_Expression, double>{};
    for (final expr in _Expression.values) {
      final act = _archetypeActivation(expr, x, t, n, b, a);
      activations[expr] = act;
      totalActivation += act;
      if (act > dominantActivation) {
        dominantActivation = act;
        dominant = expr;
      }
    }
    if (totalActivation <= 0.0) totalActivation = 1.0;

    double lw = 0, lh = 0, lr = 0, ldy = 0, lhi = 0;
    double rw = 0, rh = 0, rr = 0, rdy = 0, rhi = 0;
    double mWidth = 0, mThick = 0, mLeftLift = 0, mRightLift = 0, mRot = 0;
    for (final expr in _Expression.values) {
      final weight = activations[expr]! / totalActivation;
      final spec = _FaceSpec._archetype(expr);
      lw += spec.leftEye.widthScale * weight;
      lh += spec.leftEye.heightScale * weight;
      lr += spec.leftEye.rotation * weight;
      ldy += spec.leftEye.dy * weight;
      lhi += spec.leftEye.highlightOpacity * weight;
      rw += spec.rightEye.widthScale * weight;
      rh += spec.rightEye.heightScale * weight;
      rr += spec.rightEye.rotation * weight;
      rdy += spec.rightEye.dy * weight;
      rhi += spec.rightEye.highlightOpacity * weight;
      mWidth += spec.mouth.widthScale * weight;
      mThick += spec.mouth.thickness * weight;
      mLeftLift += spec.mouth.leftLift * weight;
      mRightLift += spec.mouth.rightLift * weight;
      mRot += spec.mouth.rotation * weight;
    }

    final neutralWeight = activations[_Expression.neutral]! / totalActivation;
    final intensity = (1.0 - neutralWeight).clamp(0.0, 1.0);
    final neutralSpec = _FaceSpec._archetype(_Expression.neutral);
    double applied(double blended, double neutralValue) => neutralValue + (blended - neutralValue) * intensity;

    final dominantSpec = _FaceSpec._archetype(dominant);
    return _FaceSpec(
      _EyeSpec(
        kind: dominantSpec.leftEye.kind,
        widthScale: applied(lw, neutralSpec.leftEye.widthScale),
        heightScale: applied(lh, neutralSpec.leftEye.heightScale),
        rotation: applied(lr, neutralSpec.leftEye.rotation),
        dy: applied(ldy, neutralSpec.leftEye.dy),
        highlightOpacity: applied(lhi, neutralSpec.leftEye.highlightOpacity),
      ),
      _EyeSpec(
        kind: dominantSpec.rightEye.kind,
        widthScale: applied(rw, neutralSpec.rightEye.widthScale),
        heightScale: applied(rh, neutralSpec.rightEye.heightScale),
        rotation: applied(rr, neutralSpec.rightEye.rotation),
        dy: applied(rdy, neutralSpec.rightEye.dy),
        highlightOpacity: applied(rhi, neutralSpec.rightEye.highlightOpacity),
      ),
      _MouthShape(
        applied(mWidth, neutralSpec.mouth.widthScale),
        applied(mThick, neutralSpec.mouth.thickness),
        applied(mLeftLift, neutralSpec.mouth.leftLift),
        applied(mRightLift, neutralSpec.mouth.rightLift),
        applied(mRot, neutralSpec.mouth.rotation),
      ),
    );
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

  void _drawEye(Canvas canvas, Offset center, double refSize, _EyeSpec spec) {
    canvas.save();
    canvas.translate(center.dx, center.dy + refSize * spec.dy);
    canvas.rotate(spec.rotation);

    if (spec.kind == _EyeKind.arc) {
      final w = refSize * 1.0 * spec.widthScale;
      final path = Path()
        ..moveTo(-w / 2, 0)
        ..quadraticBezierTo(0, -refSize * 0.55 * spec.heightScale, w / 2, 0);
      canvas.drawPath(
        path,
        Paint()
          ..color = Colors.black
          ..style = PaintingStyle.stroke
          ..strokeWidth = refSize * 0.22
          ..strokeCap = StrokeCap.round,
      );
    } else if (spec.kind == _EyeKind.closed) {
      final w = refSize * 1.0 * spec.widthScale;
      canvas.drawLine(
        Offset(-w / 2, 0), Offset(w / 2, 0),
        Paint()
          ..color = Colors.black
          ..strokeWidth = refSize * 0.22
          ..strokeCap = StrokeCap.round,
      );
    } else {
      final rw = refSize * 0.5 * spec.widthScale;
      final rh = refSize * 0.68 * spec.heightScale;
      canvas.drawOval(
        Rect.fromCenter(center: Offset.zero, width: rw * 2, height: rh * 2),
        Paint()..color = Colors.black,
      );
      if (spec.highlightOpacity > 0.02) {
        // A glare -- a reflected catch-light tucked into the upper-left
        // corner of an otherwise solid eye -- not an iris/pupil, so it
        // stays small and off-center rather than a second centered dot
        // that could read as a colored eye center. Opacity itself is
        // continuous (blended across archetypes) rather than an on/off
        // bool, so the glare fades in and out smoothly.
        canvas.drawCircle(
          Offset(-rw * 0.38, -rh * 0.42), rw * 0.20,
          Paint()..color = Colors.white.withOpacity(spec.highlightOpacity.clamp(0.0, 1.0).toDouble()),
        );
      }
    }
    canvas.restore();
  }

  /// The lens/vesica path a mouth shape traces: a top curve and a bottom
  /// curve, each running from the left corner to the right corner, bowed
  /// apart by [halfThick] on either side of the corners' own midline.
  /// [leftY]/[rightY] let the two corners sit at different heights
  /// (independently), which is what a symmetric smile, a symmetric sag,
  /// and an asymmetric smirk all turn out to be -- just different corner
  /// heights on the same two-curve shape.
  Path _lensPath(double halfW, double leftY, double rightY, double halfThick) {
    final midY = (leftY + rightY) / 2;
    return Path()
      ..moveTo(-halfW, leftY)
      ..quadraticBezierTo(0, midY - halfThick, halfW, rightY)
      ..quadraticBezierTo(0, midY + halfThick, -halfW, leftY)
      ..close();
  }

  /// Draws one _MouthShape as a filled lens, in [color]. Used both for
  /// the resting mouth and (called twice, for an outer and a smaller
  /// inner copy) the talking mouth's open-cavity reveal.
  void _drawMouthLens(Canvas canvas, Offset center, double refSize, _MouthShape shape, {Color color = Colors.black}) {
    final halfW = refSize * shape.widthScale / 2;
    final leftY = -refSize * shape.leftLift;
    final rightY = -refSize * shape.rightLift;
    // A floor on thickness, not zero -- at exactly zero the two curves
    // fully coincide and can render as an invisible hairline at some
    // pixel densities rather than the thin closed-mouth line it should
    // read as.
    final halfThick = refSize * math.max(shape.thickness, 0.03) / 2;

    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(shape.rotation);
    canvas.drawPath(_lensPath(halfW, leftY, rightY, halfThick), Paint()..color = color);
    canvas.restore();
  }

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    if (w <= 0 || h <= 0) return;

    final face = _FaceSpec.blend(axisState);
    final shape = face.mouth;

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

    final refSize = (w < h ? w : h) * 0.16;
    final faceCenter = Offset(w / 2, h / 2);

    // Eyes sit above the mouth, spaced symmetrically around the shared
    // face center -- fixed layout, only their own shape/rotation/droop
    // varies by expression.
    final eyeY = faceCenter.dy - refSize * 1.35;
    final eyeSpacing = refSize * 1.15;
    _drawEye(canvas, Offset(faceCenter.dx - eyeSpacing, eyeY), refSize, face.leftEye);
    _drawEye(canvas, Offset(faceCenter.dx + eyeSpacing, eyeY), refSize, face.rightEye);

    // Sunni: "her mouth should ... operate like a mouth" -- real talking
    // is jaw motion (mostly a height/thickness change, revealing the
    // inside), not the whole resting shape breathing bigger and smaller.
    // While speaking, the resting expression's mouth is replaced by an
    // articulated open/close mouth driven by pulse (already kicked to
    // 1.0 on each TTS word boundary, see home_screen.dart's
    // _kickPulse, and decaying between words) -- width/lift/rotation
    // still carry the expression's character (a smirk stays tilted,
    // "tired" stays sagging), but thickness is what actually animates.
    if (speaking) {
      _drawTalkingMouth(canvas, faceCenter, refSize, shape, pulse);
      return;
    }

    _drawMouthLens(canvas, faceCenter, refSize, shape);
  }

  /// Articulated talking mouth: the same lens shape the resting mouth
  /// uses, with THICKNESS interpolating from a near-closed sliver up to
  /// a wide-open cavity as [openAmount] (the word-boundary pulse, 0..1)
  /// rises, plus a small width increase (mouths widen a little as they
  /// open, not just deepen) and a white inner lens revealed once it
  /// opens enough to read as inside-the-mouth rather than a second
  /// glare. Corner lift and rotation come straight from the resting
  /// expression's mouth so a smirk still reads as a smirk mid-sentence.
  void _drawTalkingMouth(Canvas canvas, Offset center, double refSize, _MouthShape shape, double openAmount) {
    final open = openAmount.clamp(0.0, 1.0).toDouble();

    const closedThickness = 0.10;
    const openThickness = 0.85;
    final talkShape = _MouthShape(
      shape.widthScale * (1.0 + 0.12 * open),
      closedThickness + (openThickness - closedThickness) * open,
      shape.leftLift,
      shape.rightLift,
      shape.rotation,
    );
    _drawMouthLens(canvas, center, refSize, talkShape);

    if (open > 0.12) {
      final innerShape = _MouthShape(
        talkShape.widthScale * 0.85,
        talkShape.thickness * 0.75,
        talkShape.leftLift * 0.8,
        talkShape.rightLift * 0.8,
        talkShape.rotation,
      );
      _drawMouthLens(canvas, center, refSize, innerShape, color: Colors.white.withOpacity(open));
    }
  }

  @override
  bool shouldRepaint(_FacePainter old) =>
      !_axesEqual(old.axisState, axisState) ||
      old.glowEnergy != glowEnergy ||
      old.speaking != speaking ||
      old.pulse != pulse;
}
