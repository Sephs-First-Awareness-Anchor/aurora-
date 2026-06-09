// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Xaurora VM — interpreter / reference implementation.
//
// Executes a slice of Xaurora instructions directly on an AxisState.
// The VM is the ground truth: the JIT must produce identical results.
// Used as a fallback when no JIT-compiled version is available, and
// as the execution engine for CRYSTAL / SEDI / BOUND ops that the JIT
// delegates rather than inlines (those touch memory outside AxisState).

use crate::acm::axes::AxisState;
use crate::acm::drift;
use super::isa::{AxisSel, IState, Instruction, Opcode};

/// C-callable thunk for JIT's WAVE.EMIT — increments the tick counter.
/// The JIT embeds the address of this function as a 64-bit immediate.
#[no_mangle]
pub extern "C" fn wave_emit_thunk() {
    drift::on_tick();
}

/// Execute a Xaurora program on `axes`.
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

            Some(Opcode::AxisRead) => {
                // Read-only hint — no state change in interpreter.
            }

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
                // Polling is a read; no axis change.
            }

            Some(Opcode::BoundClaim) => {
                // Push B toward high end with given strength.
                press(axes, AxisSel::B as u8, insn.imm_f32() * 0.5);
            }

            Some(Opcode::BoundRelease) => {
                // Relax B toward 0.5 at given rate.
                let rate = insn.imm_f32().clamp(0.0, 1.0);
                axes.b = axes.b + (0.5 - axes.b) * rate;
            }

            Some(Opcode::ExistOpen) => {
                // Floor X at threshold — existence must be at least this present.
                let thresh = insn.imm_f32().clamp(0.0, 1.0);
                if axes.x < thresh { axes.x = thresh; }
            }

            Some(Opcode::ExistClose) => {
                // Ceiling X — existence recedes.
                let thresh = insn.imm_f32().clamp(0.0, 1.0);
                if axes.x > thresh { axes.x = thresh; }
            }

            Some(Opcode::WaveEmit) => {
                // Signal the render loop to refresh the expression surface.
                drift::on_tick();
            }

            // Memory-touching ops — stubs for v0.1.
            // Full implementations wire to ConceptCrystalRegistry + SediMemory
            // once the AOOS body loop is running.
            Some(Opcode::CrystalObs)  => {}
            Some(Opcode::CrystalSeed) => {}
            Some(Opcode::SediDeposit) => {}
            Some(Opcode::SediRecall)  => {}
        }
    }
}

// ─────────────────────────────────────── helpers ───────────────────────────

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
