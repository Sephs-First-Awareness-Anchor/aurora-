// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// face_motion.dart -- how her face moves (surface restructure 4, "Modelled
// on Face" and "Smooth, never twitchy").
//
// Pure Dart (dart:math only), so the motion can be tested without drawing.
//
// Three layers, kept apart on purpose:
//
//  1. FaceTargets.fromState -- every feature is a continuous function of her
//     own live state: the five axes (X/T/N/B/A, with their polarity around
//     the 0.5 midpoint) and her live pressure field.  There is no list of
//     moods, no named expression and no threshold that picks one.  What she
//     shows is whatever that state shapes, so expressions emerge.
//  2. SpringChannel -- her state arrives about once a second and only moves
//     targets.  Every drawn value glides toward its target on a damped
//     spring, with a dead-band (jitter too small to mean anything never
//     reaches the face) and caps on speed and acceleration (a sudden jump
//     becomes a quick, fluid swing, never a jerk).  Speech has its own
//     spring on top, so talking never jolts the rest of her.
//  3. ExpressionSettleGate -- animation frames stay transient.  Only a
//     meaningful change (a target moved past its dead-band) that has then
//     settled is offered to her continuity, with the state it came from.

import 'dart:math' as math;

double _clamp(double v, double lo, double hi) => v < lo ? lo : (v > hi ? hi : v);
double _relu(double v) => v > 0 ? v : 0.0;

/// One drawn quantity: a damped spring toward a target, with a dead-band and
/// caps on rate and acceleration.
class SpringChannel {
  final double stiffness;
  final double damping;
  final double deadBand;
  final double maxRate;
  final double maxAccel;
  final double lo;
  final double hi;

  double value;
  double velocity = 0.0;
  double target;
  double _accepted;

  SpringChannel({
    required double initial,
    this.stiffness = 60.0,
    this.damping = 14.0,
    this.deadBand = 0.02,
    this.maxRate = 2.5,
    this.maxAccel = 30.0,
    this.lo = -10.0,
    this.hi = 10.0,
  })  : value = initial,
        target = initial,
        _accepted = initial;

  /// Move the target only when the change is bigger than the dead-band.
  /// Returns true when the target moved.
  bool setTarget(double next) {
    final t = _clamp(next.isFinite ? next : _accepted, lo, hi);
    if ((t - _accepted).abs() < deadBand) return false;
    _accepted = t;
    target = t;
    return true;
  }

  /// Advance by [dt] seconds.  Long gaps (a dropped frame, the app coming
  /// back from the background) are walked in small steps so the motion is
  /// the same however the frames arrive.
  void step(double dt) {
    if (!(dt > 0)) return;
    var remaining = math.min(dt, 0.5);
    while (remaining > 1e-9) {
      final h = math.min(remaining, 1.0 / 240.0);
      var a = stiffness * (target - value) - damping * velocity;
      a = _clamp(a, -maxAccel, maxAccel);
      velocity = _clamp(velocity + a * h, -maxRate, maxRate);
      value += velocity * h;
      if (value < lo) {
        value = lo;
        if (velocity < 0) velocity = 0;
      } else if (value > hi) {
        value = hi;
        if (velocity > 0) velocity = 0;
      }
      remaining -= h;
    }
  }

  bool get settled =>
      (target - value).abs() <= math.max(deadBand * 0.5, 1e-4) && velocity.abs() <= maxRate * 0.02;
}

/// Her live state as the face reads it.
class FaceState {
  final Map<String, double> axes;      // X/T/N/B/A, 0..1, 0.5 is the midpoint
  final Map<String, double> pressure;  // her live pressure field, per axis
  final bool faceDetected;
  final double faceFraction;           // how much of the camera frame a person's face fills
  final double faceOffsetX;            // -1..1
  final double faceOffsetY;            // -1..1
  final String attention;              // camera, audio, screen or empty

  const FaceState({
    this.axes = const {'X': 0.5, 'T': 0.5, 'N': 0.5, 'B': 0.5, 'A': 0.5},
    this.pressure = const {},
    this.faceDetected = false,
    this.faceFraction = 0.0,
    this.faceOffsetX = 0.0,
    this.faceOffsetY = 0.0,
    this.attention = '',
  });

  double axis(String k) => _clamp(axes[k] ?? 0.5, 0.0, 1.0);

  /// Polarity: -1 at 0, 0 at the midpoint, +1 at 1.
  double signed(String k) => 2.0 * (axis(k) - 0.5);

  /// Overall strain in her pressure field, 0..1.
  double get strain {
    if (pressure.isEmpty) return 0.0;
    var sum = 0.0;
    var n = 0;
    for (final v in pressure.values) {
      if (v.isFinite) {
        sum += v.abs();
        n++;
      }
    }
    return n == 0 ? 0.0 : _clamp(sum / n, 0.0, 1.0);
  }

  /// Signed pressure on one axis, -1..1.
  double pressureOn(String k) => _clamp(pressure[k] ?? 0.0, -1.0, 1.0);
}

/// The channel names, in drawing order.  Each one is a number; none is a
/// mood.
class FaceChannel {
  static const hue = 'hue';                // degrees, unwrapped (150..390)
  static const saturation = 'saturation';  // 0..1
  static const brightness = 'brightness';  // 0..1
  static const faceScale = 'faceScale';    // whole-face size
  static const squash = 'squash';          // vertical over horizontal stretch
  static const leanX = 'leanX';            // face group offset, fraction of the short side
  static const leanY = 'leanY';
  static const headTurn = 'headTurn';      // radians
  static const eyeOpen = 'eyeOpen';        // 0 closed .. 1.3 wide
  static const eyeWidth = 'eyeWidth';
  static const eyeTilt = 'eyeTilt';        // radians, mirrored per eye
  static const eyeAsym = 'eyeAsym';        // -1..1, one eye more open than the other
  static const gazeX = 'gazeX';            // -1..1
  static const gazeY = 'gazeY';
  static const sparkle = 'sparkle';        // highlight shape: 0 round .. 1 star
  static const sparkleSize = 'sparkleSize';
  static const mouthWidth = 'mouthWidth';
  static const mouthCurve = 'mouthCurve';  // corners up (+) or down (-)
  static const mouthAsym = 'mouthAsym';    // one corner higher than the other
  static const mouthOpen = 'mouthOpen';    // resting openness
  static const mouthTilt = 'mouthTilt';    // radians

  static const all = <String>[
    hue, saturation, brightness, faceScale, squash, leanX, leanY, headTurn,
    eyeOpen, eyeWidth, eyeTilt, eyeAsym, gazeX, gazeY, sparkle, sparkleSize,
    mouthWidth, mouthCurve, mouthAsym, mouthOpen, mouthTilt,
  ];
}

/// Where each feature wants to be, as a continuous function of her state.
class FaceTargets {
  final Map<String, double> values;
  const FaceTargets(this.values);

  double operator [](String k) => values[k] ?? 0.0;

  static FaceTargets fromState(FaceState s) {
    final x = s.signed('X'), t = s.signed('T'), n = s.signed('N'), b = s.signed('B'), a = s.signed('A');
    final strain = s.strain;
    final pa = s.pressureOn('A'), pb = s.pressureOn('B');
    // How far her whole state sits from its midpoint: the intensity that
    // lets a faint state show faintly and a strong one fully.
    final intensity = _clamp(math.sqrt((x * x + t * t + n * n + b * b + a * a) / 5.0) + 0.5 * strain, 0.0, 1.0);

    // Proximity and attention: the person's face in the camera.
    var leanX = 0.0, leanY = 0.0, headTurn = 0.0, scaleBoost = 0.0, gazeX = 0.0, gazeY = 0.0;
    if (s.faceDetected) {
      // Attending to the camera makes her follow more fully.
      final follow = s.attention == 'camera' ? 1.0 : 0.6;
      final frac = _clamp(s.faceFraction, 0.0, 1.0);
      // Closeness reads as interest until it crowds her; the crossing is a
      // smooth blend, not a switch.
      final near = _clamp((frac - 0.03) / 0.21, 0.0, 1.0);
      final crowd = _clamp((frac - 0.24) / 0.76, 0.0, 1.0);
      final toward = near * (1.0 - crowd);
      gazeX = follow * (s.faceOffsetX * (0.6 * toward + 0.35 * (1.0 - near)) - s.faceOffsetX * 0.7 * crowd);
      gazeY = follow * (s.faceOffsetY * (0.5 * toward + 0.3 * (1.0 - near)) - s.faceOffsetY * 0.5 * crowd);
      leanX = s.faceOffsetX * (0.06 * toward - 0.10 * crowd);
      leanY = s.faceOffsetY * (0.04 * toward - 0.06 * crowd);
      headTurn = -s.faceOffsetX * 0.22 * crowd;
      scaleBoost = 0.12 * toward - 0.08 * crowd;
    }

    final v = <String, double>{
      FaceChannel.hue: 270.0 + 55.0 * a - 35.0 * b + 25.0 * t + 15.0 * pa,
      FaceChannel.saturation: _clamp(0.42 + 0.22 * a.abs() + 0.12 * x + 0.20 * strain, 0.15, 0.95),
      FaceChannel.brightness: _clamp(0.46 + 0.20 * n + 0.10 * x + 0.06 * a, 0.18, 0.90),
      FaceChannel.faceScale: _clamp(1.0 + 0.08 * x + 0.05 * n + scaleBoost, 0.75, 1.45),
      FaceChannel.squash: _clamp(1.0 + 0.10 * n - 0.14 * strain + 0.05 * a, 0.75, 1.25),
      FaceChannel.leanX: leanX,
      FaceChannel.leanY: leanY + 0.02 * _relu(-n),
      FaceChannel.headTurn: headTurn + 0.08 * t * b,
      FaceChannel.eyeOpen: _clamp(0.78 + 0.28 * n + 0.14 * x - 0.12 * strain + 0.06 * a, 0.04, 1.3),
      FaceChannel.eyeWidth: _clamp(1.0 + 0.10 * x + 0.08 * a - 0.06 * strain, 0.7, 1.3),
      FaceChannel.eyeTilt: _clamp(-0.22 * b - 0.12 * pb + 0.10 * a * _relu(b), -0.45, 0.45),
      FaceChannel.eyeAsym: _clamp(0.35 * t * b + 0.15 * pa, -0.6, 0.6),
      FaceChannel.gazeX: _clamp(gazeX, -1.0, 1.0),
      FaceChannel.gazeY: _clamp(gazeY, -1.0, 1.0),
      FaceChannel.sparkle: _clamp((intensity - 0.25) / 0.6, 0.0, 1.0),
      FaceChannel.sparkleSize: _clamp(0.20 + 0.06 * a + 0.04 * x, 0.08, 0.34),
      FaceChannel.mouthWidth: _clamp(1.7 + 0.55 * a + 0.25 * n + 0.15 * x, 0.8, 3.0),
      FaceChannel.mouthCurve: _clamp(0.16 + 0.42 * a + 0.12 * x - 0.18 * strain, -0.6, 0.7),
      FaceChannel.mouthAsym: _clamp(0.28 * t * (1.0 - a.abs()) + 0.10 * pb, -0.4, 0.4),
      FaceChannel.mouthOpen: _clamp(0.10 + 0.55 * _relu(a) * _relu(n) + 0.12 * _relu(x) + 0.08 * strain, 0.03, 0.9),
      FaceChannel.mouthTilt: _clamp(-0.14 * t * b, -0.3, 0.3),
    };
    return FaceTargets(v);
  }
}

/// Spring settings per channel.  The dead-band is in the channel's own
/// units; speed and acceleration caps scale with each channel's range.
SpringChannel _channelFor(String name, double initial) {
  switch (name) {
    case FaceChannel.hue:
      return SpringChannel(initial: initial, stiffness: 18, damping: 8.5, deadBand: 2.0, maxRate: 90, maxAccel: 600, lo: 120, hi: 420);
    case FaceChannel.saturation:
    case FaceChannel.brightness:
      return SpringChannel(initial: initial, stiffness: 18, damping: 8.5, deadBand: 0.01, maxRate: 0.6, maxAccel: 4, lo: 0, hi: 1);
    case FaceChannel.gazeX:
    case FaceChannel.gazeY:
      // Eyes lead the head: quicker, still sprung.
      return SpringChannel(initial: initial, stiffness: 120, damping: 20, deadBand: 0.02, maxRate: 4.0, maxAccel: 60, lo: -1, hi: 1);
    case FaceChannel.leanX:
    case FaceChannel.leanY:
      return SpringChannel(initial: initial, stiffness: 50, damping: 11, deadBand: 0.004, maxRate: 0.4, maxAccel: 4, lo: -0.3, hi: 0.3);
    case FaceChannel.headTurn:
    case FaceChannel.eyeTilt:
    case FaceChannel.mouthTilt:
      return SpringChannel(initial: initial, stiffness: 55, damping: 11, deadBand: 0.01, maxRate: 1.5, maxAccel: 18, lo: -0.6, hi: 0.6);
    case FaceChannel.mouthWidth:
      return SpringChannel(initial: initial, stiffness: 55, damping: 10, deadBand: 0.03, maxRate: 4.0, maxAccel: 40, lo: 0.5, hi: 3.2);
    case FaceChannel.faceScale:
    case FaceChannel.squash:
      // A little less damping: squash and stretch overshoots and settles.
      return SpringChannel(initial: initial, stiffness: 70, damping: 9, deadBand: 0.008, maxRate: 1.2, maxAccel: 14, lo: 0.6, hi: 1.6);
    case FaceChannel.eyeOpen:
      return SpringChannel(initial: initial, stiffness: 70, damping: 12, deadBand: 0.02, maxRate: 3.0, maxAccel: 40, lo: 0.0, hi: 1.4);
    default:
      return SpringChannel(initial: initial, stiffness: 60, damping: 12, deadBand: 0.015, maxRate: 2.5, maxAccel: 30, lo: -1.5, hi: 3.5);
  }
}

/// Offers a change of expression to her continuity once it has settled.
class ExpressionSettleGate {
  final double minSpacingS;
  bool _changed = false;
  double _lastEmitAt = -1e9;

  ExpressionSettleGate({this.minSpacingS = 2.0});

  void noteTargetMoved() => _changed = true;

  /// True once, when a change has settled and enough time has passed.
  bool shouldEmit({required bool settled, required double nowS}) {
    if (!_changed || !settled) return false;
    if (nowS - _lastEmitAt < minSpacingS) return false;
    _changed = false;
    _lastEmitAt = nowS;
    return true;
  }
}

/// The whole moving face: one spring per channel, plus the speaking mouth.
class FaceRig {
  final Map<String, SpringChannel> channels = {};
  // Speech rides on top of the resting mouth with its own spring.
  final SpringChannel talk = SpringChannel(
      initial: 0, stiffness: 260, damping: 26, deadBand: 0.0, maxRate: 9.0, maxAccel: 160, lo: 0, hi: 1);
  final ExpressionSettleGate gate = ExpressionSettleGate();
  FaceState state;

  FaceRig([this.state = const FaceState()]) {
    final t = FaceTargets.fromState(state);
    for (final name in FaceChannel.all) {
      channels[name] = _channelFor(name, t[name]);
    }
  }

  /// A new reading of her state moves the targets, never the drawn values.
  void setState(FaceState next) {
    state = next;
    final t = FaceTargets.fromState(next);
    var moved = false;
    for (final name in FaceChannel.all) {
      if (channels[name]!.setTarget(t[name])) moved = true;
    }
    if (moved) gate.noteTargetMoved();
  }

  /// The speaking mouth: [openness] 0..1 from her voice (each word's pulse).
  void setSpeech(double openness) {
    talk.setTarget(_clamp(openness, 0.0, 1.0));
  }

  void step(double dt) {
    for (final c in channels.values) {
      c.step(dt);
    }
    talk.step(dt);
  }

  double operator [](String k) => channels[k]?.value ?? 0.0;

  bool get settled => channels.values.every((c) => c.settled);

  Map<String, double> snapshot() => {for (final e in channels.entries) e.key: e.value.value};

  Map<String, double> targetSnapshot() => {for (final e in channels.entries) e.key: e.value.target};
}
