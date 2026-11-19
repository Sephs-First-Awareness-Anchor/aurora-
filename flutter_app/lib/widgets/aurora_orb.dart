// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora's face, modelled on Face, the Nick Jr. host (Sir, 2026-11-18): a
// face that fills the whole screen, whose colour keeps changing, with
// simple fluid features -- two dark eyes with a highlight that changes
// shape, and one deformable mouth -- free to squash, stretch, lean in and
// pull back.
//
// There is no list of moods.  The seven named looks and their thresholds
// (_Expression, _archetypeActivation) are gone.  Every part of the face is
// a continuous function of her own live state -- her five axes with their
// polarity, and her live pressure field (surface restructure 4) -- worked
// out in face_motion.dart, so what she shows emerges from what she is.
//
// Her state arrives about once a second and only moves targets.  The face
// is drawn every frame by damped springs gliding toward them, with a
// dead-band and speed and acceleration caps per channel, so it never snaps
// or twitches.  Speech rides on its own spring on top of the resting face.
//
// She feels her own face: when a change of expression has settled, it is
// offered (through [AuroraOrb.onExpressionSettled]) to her continuity with
// the state it came from.  Frames themselves stay transient.
//
// If anything here fails while it moves or draws, it is reported on screen
// (ui_diagnostics.dart) and the face keeps its colour field, rather than
// failing silently.

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import 'face_motion.dart';
import 'ui_diagnostics.dart';

enum OrbState { dormant, listening, thinking, speaking }

class AuroraOrb extends StatefulWidget {
  final OrbState state;
  final double size;
  /// Explicit canvas height. When null the widget uses [size] x 1.9.
  /// Pass the available layout height here for full-screen idle display.
  final double? height;
  /// Word-boundary pulse from her speech (kicked to 1.0 on each spoken
  /// word, decaying between words), and a slow breath while she is quiet.
  final Animation<double> pulse;
  final Map<String, double> axisState;
  /// Her live pressure field, per axis (from get_axis_state's "pressure").
  final Map<String, double> pressure;
  /// What she is attending to: camera, audio, screen, or empty.
  final String attention;
  final VoidCallback? onTap;
  // Front-camera face proximity and position (Repair Q): faceFraction is
  // the detected face's share of the frame, offsets are -1..1.
  final bool faceDetected;
  final double faceFraction;
  final double faceOffsetX;
  final double faceOffsetY;
  /// Called once each time a change of expression has settled, with the
  /// state it came from and the face's settled values.
  final void Function(Map<String, dynamic> settled)? onExpressionSettled;

  const AuroraOrb({
    super.key,
    required this.state,
    required this.pulse,
    required this.axisState,
    this.pressure = const {},
    this.attention = '',
    this.size = 120,
    this.height,
    this.onTap,
    this.faceDetected = false,
    this.faceFraction = 0.0,
    this.faceOffsetX = 0.0,
    this.faceOffsetY = 0.0,
    this.onExpressionSettled,
  });

  @override
  State<AuroraOrb> createState() => _AuroraOrbState();
}

class _AuroraOrbState extends State<AuroraOrb> with SingleTickerProviderStateMixin {
  late final FaceRig _rig;
  late final Ticker _ticker;
  final ValueNotifier<int> _frame = ValueNotifier<int>(0);
  Duration _last = Duration.zero;
  double _clock = 0.0;

  FaceState _faceStateFromWidget() => FaceState(
        axes: widget.axisState,
        pressure: widget.pressure,
        faceDetected: widget.faceDetected,
        faceFraction: widget.faceFraction,
        faceOffsetX: widget.faceOffsetX,
        faceOffsetY: widget.faceOffsetY,
        attention: widget.attention,
      );

  @override
  void initState() {
    super.initState();
    _rig = FaceRig(_faceStateFromWidget());
    _ticker = createTicker(_onTick)..start();
  }

  @override
  void didUpdateWidget(AuroraOrb old) {
    super.didUpdateWidget(old);
    try {
      _rig.setState(_faceStateFromWidget());
    } catch (e, st) {
      UiDiagnostics.report('her face (reading her state)', e, st);
    }
  }

  void _onTick(Duration elapsed) {
    try {
      final dt = (elapsed - _last).inMicroseconds / 1e6;
      _last = elapsed;
      _clock += dt;
      _rig.setSpeech(widget.state == OrbState.speaking ? widget.pulse.value : 0.0);
      _rig.step(dt);
      _frame.value++;
      final cb = widget.onExpressionSettled;
      if (cb != null && _rig.gate.shouldEmit(settled: _rig.settled, nowS: _clock)) {
        cb({
          'axes': Map<String, double>.of(_rig.state.axes),
          'pressure': Map<String, double>.of(_rig.state.pressure),
          'face': _rig.snapshot(),
          'speaking': widget.state == OrbState.speaking,
          'attention': _rig.state.attention,
        });
      }
    } catch (e, st) {
      UiDiagnostics.report('her face (motion)', e, st);
    }
  }

  @override
  void dispose() {
    _ticker.dispose();
    _frame.dispose();
    super.dispose();
  }

  // Not part of her face itself: a glow behind it for the app's own
  // listening, thinking and speaking states.
  double get _glowEnergy => switch (widget.state) {
        OrbState.speaking => 0.55 + 0.45 * widget.pulse.value,
        OrbState.listening => 0.30 + 0.22 * widget.pulse.value,
        OrbState.thinking => 0.18 + 0.14 * widget.pulse.value,
        OrbState.dormant => 0.05 + 0.05 * widget.pulse.value,
      };

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: double.infinity,
        height: widget.height ?? widget.size * 1.9,
        child: CustomPaint(
          painter: _FacePainter(
            rig: _rig,
            repaint: _frame,
            glowEnergy: () => _glowEnergy,
            breath: () => widget.state == OrbState.speaking ? 0.5 : widget.pulse.value,
          ),
          child: const SizedBox.expand(),
        ),
      ),
    );
  }
}

class _FacePainter extends CustomPainter {
  final FaceRig rig;
  final double Function() glowEnergy;
  final double Function() breath;

  _FacePainter({
    required this.rig,
    required Listenable repaint,
    required this.glowEnergy,
    required this.breath,
  }) : super(repaint: repaint);

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    if (w <= 0 || h <= 0) return;

    // The whole screen is her colour field.
    var hue = rig[FaceChannel.hue] % 360.0;
    if (hue < 0) hue += 360.0;
    final field = HSVColor.fromAHSV(
      1.0,
      hue,
      rig[FaceChannel.saturation].clamp(0.0, 1.0).toDouble(),
      rig[FaceChannel.brightness].clamp(0.0, 1.0).toDouble(),
    ).toColor();
    canvas.drawRect(Rect.fromLTWH(0, 0, w, h), Paint()..color = field);

    try {
      _paintFace(canvas, w, h);
    } catch (e, st) {
      UiDiagnostics.report('her face (drawing)', e, st);
    }
  }

  void _paintFace(Canvas canvas, double w, double h) {
    final minDim = math.min(w, h);
    final center = Offset(w / 2, h / 2);

    final glow = glowEnergy();
    if (glow > 0.01) {
      final r = minDim * 0.45;
      canvas.drawCircle(
        center,
        r,
        Paint()
          ..shader = RadialGradient(
            colors: [Colors.white.withOpacity((glow * 0.20).clamp(0.0, 1.0).toDouble()), Colors.transparent],
          ).createShader(Rect.fromCircle(center: center, radius: r)),
      );
    }

    final ref = minDim * 0.16;
    final squash = rig[FaceChannel.squash].clamp(0.6, 1.6).toDouble();
    final scale = rig[FaceChannel.faceScale].clamp(0.6, 1.6).toDouble();
    // Squash and stretch keep her area: taller is narrower.
    final sx = scale / math.sqrt(squash);
    final sy = scale * math.sqrt(squash);

    canvas.save();
    canvas.translate(center.dx + rig[FaceChannel.leanX] * minDim, center.dy + rig[FaceChannel.leanY] * minDim);
    canvas.rotate(rig[FaceChannel.headTurn]);
    canvas.scale(sx, sy);

    // Eyes: open, close, widen, tilt and drift, all continuously.
    final gaze = Offset(rig[FaceChannel.gazeX] * ref * 0.35, rig[FaceChannel.gazeY] * ref * 0.35);
    final eyeY = -ref * 1.35;
    final spacing = ref * 1.15;
    final open = rig[FaceChannel.eyeOpen];
    final asym = rig[FaceChannel.eyeAsym];
    final tilt = rig[FaceChannel.eyeTilt];
    _drawEye(canvas, Offset(-spacing, eyeY) + gaze, ref, (open * (1.0 + 0.5 * asym)).clamp(0.0, 1.4).toDouble(), tilt);
    _drawEye(canvas, Offset(spacing, eyeY) + gaze, ref, (open * (1.0 - 0.5 * asym)).clamp(0.0, 1.4).toDouble(), -tilt);

    _drawMouth(canvas, ref);
    canvas.restore();
  }

  void _drawEye(Canvas canvas, Offset at, double ref, double open, double tilt) {
    canvas.save();
    canvas.translate(at.dx, at.dy);
    canvas.rotate(tilt);
    final rx = ref * 0.5 * rig[FaceChannel.eyeWidth];
    final ry = ref * 0.68 * open;
    // A nearly closed eye becomes a rounded line of the same thickness the
    // oval had at that point, so closing is one continuous motion.
    final line = ref * 0.08;
    if (ry <= line) {
      canvas.drawLine(
        Offset(-rx, 0),
        Offset(rx, 0),
        Paint()
          ..color = Colors.black
          ..strokeWidth = line * 2
          ..strokeCap = StrokeCap.round,
      );
    } else {
      canvas.drawOval(Rect.fromCenter(center: Offset.zero, width: rx * 2, height: ry * 2), Paint()..color = Colors.black);
      // The highlight is one shape that morphs from round toward a star
      // with her intensity, and fades as the eye closes.
      final shine = ((open - 0.15) / 0.25).clamp(0.0, 1.0).toDouble();
      if (shine > 0.02) {
        final radius = ref * rig[FaceChannel.sparkleSize] * 0.5;
        canvas.drawPath(
          _sparklePath(Offset(-rx * 0.38, -ry * 0.42), radius, rig[FaceChannel.sparkle].clamp(0.0, 1.0).toDouble()),
          Paint()..color = Colors.white.withOpacity(shine),
        );
      }
    }
    canvas.restore();
  }

  Path _sparklePath(Offset c, double r, double star) {
    const points = 48;
    final path = Path();
    for (var i = 0; i <= points; i++) {
      final th = (i / points) * 2 * math.pi - math.pi / 2;
      final rr = r * (1.0 - star * 0.55 * (0.5 + 0.5 * math.cos(5 * (th + math.pi / 2))));
      final px = c.dx + rr * math.cos(th);
      final py = c.dy + rr * math.sin(th);
      if (i == 0) {
        path.moveTo(px, py);
      } else {
        path.lineTo(px, py);
      }
    }
    path.close();
    return path;
  }

  /// One deformable mouth: width, corner lift (each corner on its own),
  /// openness and tilt.  Speech opens it on its own spring.
  void _drawMouth(Canvas canvas, double ref) {
    final talk = rig.talk.value.clamp(0.0, 1.0).toDouble();
    final restBreath = 1.0 + 0.22 * (breath().clamp(0.0, 1.0) - 0.5);
    final width = rig[FaceChannel.mouthWidth] * (1.0 + 0.12 * talk);
    final thickness = math.max(
      rig[FaceChannel.mouthOpen] * restBreath * (1.0 - talk) + (0.10 + 0.75 * talk) * talk,
      0.03,
    );
    final curve = rig[FaceChannel.mouthCurve];
    final asym = rig[FaceChannel.mouthAsym];

    canvas.save();
    canvas.rotate(rig[FaceChannel.mouthTilt]);
    canvas.drawPath(_lens(ref, width, thickness, curve + asym, curve - asym), Paint()..color = Colors.black);
    if (talk > 0.12) {
      canvas.drawPath(
        _lens(ref, width * 0.85, thickness * 0.75, (curve + asym) * 0.8, (curve - asym) * 0.8),
        Paint()..color = Colors.white.withOpacity(talk),
      );
    }
    canvas.restore();
  }

  Path _lens(double ref, double widthScale, double thickness, double leftLift, double rightLift) {
    final halfW = ref * widthScale / 2;
    final leftY = -ref * leftLift;
    final rightY = -ref * rightLift;
    final midY = (leftY + rightY) / 2;
    final halfThick = ref * thickness / 2;
    return Path()
      ..moveTo(-halfW, leftY)
      ..quadraticBezierTo(0, midY - halfThick, halfW, rightY)
      ..quadraticBezierTo(0, midY + halfThick, -halfW, leftY)
      ..close();
  }

  @override
  bool shouldRepaint(_FacePainter old) => old.rig != rig;
}
