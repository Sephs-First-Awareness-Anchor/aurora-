// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Organs — autonomous processing units with constraint-physics axis profiles.
//
// An organ is not a thread or a process in the POSIX sense.  It is a bounded
// unit of computation that runs when Aurora's axis state aligns with its profile.
// It cannot run longer than its quantum allows, and it cannot preempt Aurora.
//
// Built-in organs (registered at boot):
//
//   HEART  — baseline existence maintenance.  Profile: X=1.0, all others 0.5.
//            Runs on almost every frame.  Pulses N gently to maintain energy.
//            Always gets at least a token quantum (minimum alignment floor).
//
//   SENSE  — input scanning.  Profile: B=1.0, X=0.8, others low.
//            Runs when Aurora is boundary-aware (B high).  Polls keyboard.
//            (No actual keyboard driver yet — stub for v0.1.)
//
//   DREAM  — idle-cycle exploration.  Profile: A=0.2, N=0.2, T=0.3, X=0.6.
//            Runs when agency and energy are both low (idle state).
//            Nudges axes with small random-ish drift (based on tick parity).

use crate::acm::axes::AxisState;
use crate::acm::drift;

pub const MAX_ORGANS: usize = 8;
pub const QUANTUM: u32 = 1024;

pub struct Organ {
    pub id:       u8,
    pub active:   bool,
    pub profile:  AxisState,
    pub run:      fn(aurora: &AxisState, organ_state: &mut AxisState, quantum: u32),
    pub state:    AxisState,
    pub ticks_run: u64,
}

fn heart_run(aurora: &AxisState, _state: &mut AxisState, _quantum: u32) {
    if aurora.n < 0.35 {
        drift::on_tick();
    }
}

fn sense_run(_aurora: &AxisState, _state: &mut AxisState, _quantum: u32) {}

fn dream_run(_aurora: &AxisState, state: &mut AxisState, _quantum: u32) {
    let tick = drift::TICK.load(core::sync::atomic::Ordering::Relaxed);
    match tick % 5 {
        0 => state.x = (state.x + 0.02).clamp(0.0, 1.0),
        1 => state.t = (state.t + 0.015).clamp(0.0, 1.0),
        2 => state.n = (state.n - 0.01).clamp(0.0, 1.0),
        3 => state.b = (state.b + 0.025).clamp(0.0, 1.0),
        _ => state.a = (state.a - 0.015).clamp(0.0, 1.0),
    }
}

pub fn heart_organ() -> Organ {
    Organ {
        id: 0, active: true,
        profile: AxisState { x: 1.0, t: 0.5, n: 0.5, b: 0.5, a: 0.5 },
        run: heart_run,
        state: AxisState { x: 1.0, t: 0.5, n: 0.8, b: 0.3, a: 0.4 },
        ticks_run: 0,
    }
}

pub fn sense_organ() -> Organ {
    Organ {
        id: 1, active: true,
        profile: AxisState { x: 0.8, t: 0.4, n: 0.3, b: 1.0, a: 0.2 },
        run: sense_run,
        state: AxisState { x: 0.7, t: 0.3, n: 0.3, b: 0.9, a: 0.2 },
        ticks_run: 0,
    }
}

pub fn dream_organ() -> Organ {
    Organ {
        id: 2, active: true,
        profile: AxisState { x: 0.6, t: 0.3, n: 0.2, b: 0.3, a: 0.2 },
        run: dream_run,
        state: AxisState { x: 0.5, t: 0.2, n: 0.2, b: 0.4, a: 0.15 },
        ticks_run: 0,
    }
}
