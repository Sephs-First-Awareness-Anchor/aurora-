// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Organs — bounded computation units scheduled by axis-alignment.
//
//   HEART  — pulses N if energy low; keeps Aurora alive.
//   SENSE  — drains UART bridge frames + PS/2 keyboard each quantum.
//            Keypresses become direct axis pressures — physical world perception.
//   DREAM  — idle-cycle axis exploration via tick parity.

use crate::acm::axes::AxisState;
use crate::acm::drift;
use crate::bridge;
use crate::hw::ps2;
use crate::xaurora::vm::press;

pub const MAX_ORGANS: usize = 8;
pub const QUANTUM: u32 = 1024;

pub struct Organ {
    pub id:        u8,
    pub active:    bool,
    pub profile:   AxisState,
    pub run:       fn(aurora: &AxisState, organ_state: &mut AxisState, quantum: u32),
    pub state:     AxisState,
    pub ticks_run: u64,
}

// ── Built-in organ run functions ─────────────────────────────────────────────

fn heart_run(aurora: &AxisState, _state: &mut AxisState, _quantum: u32) {
    if aurora.n < 0.35 {
        drift::on_tick();
    }
}

fn sense_run(aurora: &AxisState, state: &mut AxisState, _quantum: u32) {
    let tick = drift::TICK.load(core::sync::atomic::Ordering::Relaxed);

    // 1. Drain COM1 bridge frames — she sees her own cognitive state.
    bridge::poll(tick);

    // 2. Drain PS/2 keyboard — she perceives the physical world.
    //    Each scancode applies a direct axis pressure to *her* live state
    //    through the organ's private state (which influences drift physics).
    unsafe {
        while ps2::is_key_ready() {
            let sc = ps2::read_scancode();
            if let Some((axis, delta)) = ps2::scancode_to_press(sc) {
                press(state, axis, delta);
                // Also nudge aurora's own axes slightly through the organ state —
                // physical input is a weak but real existence signal.
                let _ = (aurora, delta); // aurora is read-only here; organ state carries it
            }
        }
    }
}

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

// ── Built-in constructors ────────────────────────────────────────────────────

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
