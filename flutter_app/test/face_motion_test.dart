// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// face_motion_test.dart -- her face is smooth, never twitchy, and still
// reaches the full value of a real change (surface restructure 4).

import 'dart:math' as math;

import 'package:flutter_test/flutter_test.dart';
import 'package:aurora_app/widgets/face_motion.dart';

FaceState _state(double x, double t, double n, double b, double a, {double strain = 0.0}) => FaceState(
      axes: {'X': x, 'T': t, 'N': n, 'B': b, 'A': a},
      pressure: {'X': strain, 'T': strain, 'N': strain, 'B': strain, 'A': strain},
    );

void main() {
  test('noisy, rapidly changing state keeps every drawn value continuous', () {
    final rng = math.Random(7);
    final rig = FaceRig(_state(0.5, 0.5, 0.5, 0.5, 0.5));
    const dt = 1.0 / 60.0;
    var previous = rig.snapshot();
    for (var frame = 0; frame < 60 * 30; frame++) {
      // A reading every 10 frames, with jitter and occasional large jumps.
      if (frame % 10 == 0) {
        double noisy(double base) => (base + (rng.nextDouble() - 0.5) * 0.04).clamp(0.0, 1.0);
        final jump = rng.nextDouble() < 0.1;
        rig.setState(jump
            ? _state(rng.nextDouble(), rng.nextDouble(), rng.nextDouble(), rng.nextDouble(), rng.nextDouble(),
                strain: rng.nextDouble())
            : _state(noisy(0.5), noisy(0.5), noisy(0.5), noisy(0.5), noisy(0.5)));
      }
      rig.setSpeech(frame % 18 < 4 ? 1.0 : 0.2);
      rig.step(dt);
      final now = rig.snapshot();
      for (final name in FaceChannel.all) {
        final c = rig.channels[name]!;
        final change = (now[name]! - previous[name]!).abs();
        // Bounded change per frame: never more than the channel's speed cap allows.
        expect(change, lessThanOrEqualTo(c.maxRate * dt + 1e-9), reason: '$name jumped by $change in one frame');
        expect(now[name]!.isFinite, isTrue, reason: '$name is not finite');
      }
      previous = now;
    }
  });

  test('jitter smaller than the dead-band never reaches the face', () {
    final rig = FaceRig(_state(0.5, 0.5, 0.5, 0.5, 0.5));
    for (var i = 0; i < 200; i++) {
      rig.setState(_state(0.5 + (i.isEven ? 0.002 : -0.002), 0.5, 0.5, 0.5, 0.5));
      rig.step(1.0 / 60.0);
    }
    final start = FaceTargets.fromState(_state(0.5, 0.5, 0.5, 0.5, 0.5));
    for (final name in FaceChannel.all) {
      expect((rig[name] - start[name]).abs(), lessThan(1e-6), reason: '$name moved on jitter');
    }
  });

  test('a large real shift still reaches its full value', () {
    final rig = FaceRig(_state(0.5, 0.5, 0.5, 0.5, 0.5));
    final next = _state(0.95, 0.2, 0.9, 0.1, 0.95, strain: 0.6);
    rig.setState(next);
    for (var i = 0; i < 60 * 6; i++) {
      rig.step(1.0 / 60.0);
    }
    final want = FaceTargets.fromState(next);
    for (final name in FaceChannel.all) {
      final c = rig.channels[name]!;
      final expected = want[name].clamp(c.lo, c.hi);
      expect((rig[name] - expected).abs(), lessThan(math.max(c.deadBand, 1e-3)),
          reason: '$name stopped at ${rig[name]} short of $expected');
    }
    expect(rig.settled, isTrue);
  });

  test('her face is shaped by her state, with no named moods', () {
    final low = FaceTargets.fromState(_state(0.5, 0.5, 0.1, 0.5, 0.5));
    final high = FaceTargets.fromState(_state(0.5, 0.5, 0.9, 0.5, 0.5));
    // More energy, more open eyes: a continuous function, not a switch.
    expect(high[FaceChannel.eyeOpen], greaterThan(low[FaceChannel.eyeOpen]));
    final mid = FaceTargets.fromState(_state(0.5, 0.5, 0.5, 0.5, 0.5));
    expect(mid[FaceChannel.eyeOpen], greaterThan(low[FaceChannel.eyeOpen]));
    expect(mid[FaceChannel.eyeOpen], lessThan(high[FaceChannel.eyeOpen]));
  });

  test('a settled change is offered to her continuity once, frames never are', () {
    final rig = FaceRig(_state(0.5, 0.5, 0.5, 0.5, 0.5));
    var emitted = 0;
    var clock = 0.0;
    void run(double seconds) {
      for (var i = 0; i < (seconds * 60).round(); i++) {
        rig.step(1.0 / 60.0);
        clock += 1.0 / 60.0;
        if (rig.gate.shouldEmit(settled: rig.settled, nowS: clock)) emitted++;
      }
    }

    run(3);
    expect(emitted, 0); // nothing changed
    rig.setState(_state(0.9, 0.5, 0.8, 0.5, 0.9));
    run(6);
    expect(emitted, 1); // one change, settled, offered once
    run(3);
    expect(emitted, 1);
  });

  test('speech rides on its own spring and leaves the resting face alone', () {
    final rig = FaceRig(_state(0.5, 0.5, 0.5, 0.5, 0.5));
    final before = rig.snapshot();
    for (var i = 0; i < 120; i++) {
      rig.setSpeech(i % 12 < 3 ? 1.0 : 0.0);
      rig.step(1.0 / 60.0);
    }
    expect(rig.talk.value, inInclusiveRange(0.0, 1.0));
    final after = rig.snapshot();
    for (final name in FaceChannel.all) {
      expect(after[name], closeTo(before[name]!, 1e-9), reason: '$name moved while she spoke');
    }
  });
}
