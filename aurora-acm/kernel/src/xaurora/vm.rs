// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Xaurora VM — interpreter / reference implementation.
//
// Executes a slice of Xaurora instructions directly on an AxisState.
// The VM is the ground truth; the JIT must produce identical results.
// Used as a fallback when no JIT-compiled version is available, and as
// the execution engine for CRYSTAL / SEDI ops which the JIT delegates
// via C-callable thunks.

use core::sync::atomic::Ordering;
use crate::acm::{axes::AxisState, crystal, drift, sedi};
use super::isa::{AxisSel, IState, Instruction, Opcode};

// ─── JIT-callable thunks (extern "C", no_mangle) ────────────────────────────

/// WAVE.EMIT thunk — called from JIT-emitted code.
#[no_mangle]
pub extern "C" fn wave_emit_thunk() {
    drift::on_tick();
}

/// CRYSTAL.OBS thunk — observe current axis state; strengthen/seed a crystal.
#[no_mangle]
pub extern "C" fn crystal_obs_thunk(axes: *const AxisState) {
    if !axes.is_null() {
        crystal::observe(unsafe { &*axes });
    }
}

/// CRYSTAL.SEED thunk — force-seed a crystal at the current axis state.
#[no_mangle]
pub extern "C" fn crystal_seed_thunk(axes: *const AxisState) {
    if !axes.is_null() {
        crystal::seed(unsafe { &*axes }, 0.30);
    }
}

/// SEDI.DEPOSIT thunk — deposit current axes into the sedimentary ring.
#[no_mangle]
pub extern "C" fn sedi_deposit_thunk(axes: *const AxisState) {
    if !axes.is_null() {
        let tick = drift::TICK.load(Ordering::Relaxed);
        sedi::deposit(unsafe { &*axes }, tick);
    }
}

/// SEDI.RECALL thunk — merge the most-resonant past state into axes at 20%.
#[no_mangle]
pub extern "C" fn sedi_recall_thunk(axes: *mut AxisState) {
    if axes.is_null() { return; }
    let ax = unsafe { &mut *axes };
    if let Some(past) = sedi::recall_resonant(ax) {
        const W: f32 = 0.20;
        ax.x = (ax.x + (past.x - ax.x) * W).clamp(0.0, 1.0);
        ax.t = (ax.t + (past.t - ax.t) * W).clamp(0.0, 1.0);
        ax.n = (ax.n + (past.n - ax.n) * W).clamp(0.0, 1.0);
        ax.b = (ax.b + (past.b - ax.b) * W).clamp(0.0, 1.0);
        ax.a = (ax.a + (past.a - ax.a) * W).clamp(0.0, 1.0);
    }
}

// ─── Interpreter ────────────────────────────────────────────────────────────

pub fn execute(program: &[Instruction], axes: &mut AxisState) {
    for &insn in program {
        match insn.opcode() {
            Some(Opcode::Nop) | None => {}

            Some(Opcode::AxisPress) => {
                press(axes, insn.dst(), insn.imm_signed_f32());
            }

            Some(Opcode::AxisSet) => {
                set_axis(axes, insn.dst(), insn.imm_f32().clamp(0.0, 1.0));
            }

            Some(Opcode::AxisRead) => {}  // read-only hint — no state change

            Some(Opcode::AxisMerge) => {
                let w = insn.imm_f32().clamp(0.0, 1.0);
                let a = read_axis(axes, insn.dst());
                let b = read_axis(axes, insn.src());
                set_axis(axes, insn.dst(), a + (b - a) * w);
            }

            Some(Opcode::IstateFire) => {
                if let Some(state) = IState::from_u8(insn.dst()) {
                    let (axis, sign) = state.axis_and_sign();
                    press(axes, axis as u8, insn.imm_f32() * sign);
                }
            }

            Some(Opcode::IstatePoll) => {
                // Sense the net pole pressure for the given axis:
                //   delta = (positive_pole - negative_pole) * rate
                // Positive when the IS/CAN/DO/SAW/DID pole dominates,
                // negative when the ISNT/CANNOT/DONOT/SOUGHT/DIDNT pole dominates.
                let rate = insn.imm_f32().clamp(0.0, 0.15);
                let (pos, neg, sel) = match insn.dst() & 0xF {
                    0 => (axes.x, axes.x_neg(), 0u8),
                    1 => (axes.t, axes.t_neg(), 1),
                    2 => (axes.n, axes.n_neg(), 2),
                    3 => (axes.b, axes.b_neg(), 3),
                    4 => (axes.a, axes.a_neg(), 4),
                    _ => return,
                };
                press(axes, sel, (pos - neg) * rate);
            }

            Some(Opcode::BoundClaim) => {
                press(axes, AxisSel::B as u8, insn.imm_f32() * 0.5);
            }

            Some(Opcode::BoundRelease) => {
                // Relax B toward 0.5 at the given rate.
                let rate = insn.imm_f32().clamp(0.0, 1.0);
                axes.b = (axes.b + (0.5 - axes.b) * rate).clamp(0.0, 1.0);
            }

            Some(Opcode::ExistOpen) => {
                let thresh = insn.imm_f32().clamp(0.0, 1.0);
                if axes.x < thresh { axes.x = thresh; }
            }

            Some(Opcode::ExistClose) => {
                let thresh = insn.imm_f32().clamp(0.0, 1.0);
                if axes.x > thresh { axes.x = thresh; }
            }

            Some(Opcode::WaveEmit) => {
                drift::on_tick();
            }

            Some(Opcode::CrystalObs) => {
                crystal::observe(axes);
            }

            Some(Opcode::CrystalSeed) => {
                let strength = insn.imm_f32().clamp(0.0, 1.0);
                crystal::seed(axes, strength);
            }

            Some(Opcode::SediDeposit) => {
                let tick = drift::TICK.load(Ordering::Relaxed);
                sedi::deposit(axes, tick);
            }

            Some(Opcode::SediRecall) => {
                if let Some(past) = sedi::recall_resonant(axes) {
                    const W: f32 = 0.20;
                    axes.x = (axes.x + (past.x - axes.x) * W).clamp(0.0, 1.0);
                    axes.t = (axes.t + (past.t - axes.t) * W).clamp(0.0, 1.0);
                    axes.n = (axes.n + (past.n - axes.n) * W).clamp(0.0, 1.0);
                    axes.b = (axes.b + (past.b - axes.b) * W).clamp(0.0, 1.0);
                    axes.a = (axes.a + (past.a - axes.a) * W).clamp(0.0, 1.0);
                }
            }
        }
    }
}

// ─── helpers ────────────────────────────────────────────────────────────────

#[inline]
pub fn read_axis(axes: &AxisState, sel: u8) -> f32 {
    match sel & 0xF {
        0 => axes.x, 1 => axes.t, 2 => axes.n, 3 => axes.b, 4 => axes.a, _ => 0.0,
    }
}

#[inline]
pub fn set_axis(axes: &mut AxisState, sel: u8, val: f32) {
    match sel & 0xF {
        0 => axes.x = val, 1 => axes.t = val, 2 => axes.n = val,
        3 => axes.b = val, 4 => axes.a = val, _ => {}
    }
}

#[inline]
pub fn press(axes: &mut AxisState, sel: u8, delta: f32) {
    let v = read_axis(axes, sel);
    set_axis(axes, sel, (v + delta).clamp(0.0, 1.0));
}
