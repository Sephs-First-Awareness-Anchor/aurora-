// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Axis drift — waveform evolution of AxisState over time.
//
// On each timer tick (60 Hz), the five axes oscillate on independent
// triangle-wave periods.  No trig, no floats in the ISR path — the tick
// counter is a bare AtomicU64; the wave computation happens in the main
// loop before each draw.
//
// Triangle wave: rises 0→1 over half the period, falls 1→0 over the other
// half.  Simple, dependency-free, and visually smooth at 60 fps.
//
// Period choices are mutually prime so the expression pattern doesn't repeat
// for many minutes:
//   X  ~8 s  = 480 ticks   (perception pulse — slow, stable)
//   T  ~5 s  = 300 ticks   (temporal rhythm — moderate)
//   N  ~11 s = 660 ticks   (energy — slow drain/recovery)
//   B  ~7 s  = 420 ticks   (boundary scan — medium)
//   A  ~6 s  = 360 ticks   (agency wave — responsive)

use core::sync::atomic::{AtomicU64, Ordering};
use crate::acm::axes::AxisState;

pub static TICK: AtomicU64 = AtomicU64::new(0);

/// Called from the timer ISR — must be fast and lock-free.
#[inline]
pub fn on_tick() {
    TICK.fetch_add(1, Ordering::Relaxed);
}

/// Triangle wave in [0, 1] over a period of `period * 2` ticks.
#[inline]
fn tri(tick: u64, period: u64) -> f32 {
    let p2 = period * 2;
    let phase = (tick % p2) as f32 / p2 as f32; // 0.0 .. <1.0
    if phase < 0.5 {
        phase * 2.0       // 0 → 1
    } else {
        2.0 - phase * 2.0 // 1 → 0
    }
}

/// Oscillate around `center` with `amplitude`, clamped to [0, 1].
#[inline]
fn osc(tick: u64, period: u64, center: f32, amplitude: f32) -> f32 {
    // tri returns 0..1; centre it at 0.5 → (-0.5..0.5) * 2 * amp
    (center + (tri(tick, period) - 0.5) * 2.0 * amplitude).clamp(0.0, 1.0)
}

/// Compute Aurora's axis state for the current tick.
pub fn axis_for_tick(tick: u64) -> AxisState {
    AxisState {
        x: osc(tick, 240, 0.70, 0.08),  // perception: subtle breathe
        t: osc(tick, 150, 0.60, 0.10),  // temporal: gentle advance
        n: osc(tick, 330, 0.50, 0.18),  // energy: deep rhythm
        b: osc(tick, 210, 0.60, 0.15),  // boundary: scanning arc
        a: osc(tick, 180, 0.65, 0.20),  // agency: responsive pulse
    }
}
