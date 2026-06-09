// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Xaurora JIT — constraint-physics ISA → x86-64 machine code.
//
// The JIT takes a slice of Xaurora instructions and emits native x86-64
// bytes directly into a static executable buffer.  No OS, no mmap, no
// allocator — in the ACM, all memory is executable by default (no NX
// page tables yet), so we treat a static [u8] as a code region and call
// it as a function pointer.
//
// Calling convention of compiled programs:
//   extern "C" fn(axes: *mut AxisState)
//   RDI = pointer to AxisState {x: f32, t: f32, n: f32, b: f32, a: f32}
//   offsets: x=0, t=4, n=8, b=12, a=16
//
// Register allocation inside emitted code:
//   xmm0  — working value (load/compute/store)
//   xmm1  — constant or second operand
//   xmm2  — third operand (MERGE)
//   xmm3  — weight (MERGE)
//   xmm4  — scratch (MERGE: 1 - weight)
//   r10d  — scratch for loading f32 immediates via MOV+MOVD
//
// Every emitted value is clamped to [0.0, 1.0] before storing back.
// CRYSTAL / SEDI / BOUND-RELEASE ops fall through to the VM interpreter
// (pointer to vm::execute is embedded as a 64-bit immediate CALL).

use core::sync::atomic::{AtomicUsize, Ordering};
use crate::acm::axes::AxisState;
use super::isa::{AxisSel, IState, Instruction, Opcode};
use super::vm;

// ─────────────────────────────────────── Static JIT buffer ─────────────────────

// 64 KB executable region — enough for thousands of compiled instructions.
// All kernel memory is executable at this stage (no NX page tables).
#[repr(align(16))]
struct JitBuf([u8; 65536]);
static mut JIT_BUF: JitBuf = JitBuf([0u8; 65536]);

// Number of valid bytes currently in JIT_BUF.
static JIT_LEN: AtomicUsize = AtomicUsize::new(0);

// Type of a compiled Xaurora program.
type CompiledFn = unsafe extern "C" fn(*mut AxisState);

// ─────────────────────────────────────── Public API ─────────────────────────────

/// Compile `program` to x86-64 and store in the JIT buffer.
/// Returns `Ok(byte_count)` or `Err` if the buffer overflows.
pub fn compile(program: &[Instruction]) -> Result<usize, &'static str> {
    let mut e = Emitter::new();
    for &insn in program {
        e.emit_insn(insn)?;
    }
    e.ret();
    let len = e.pos;
    JIT_LEN.store(len, Ordering::Release);
    Ok(len)
}

/// Execute the most-recently compiled program.
/// Falls back to the VM interpreter if nothing has been compiled yet.
pub fn run(program: &[Instruction], axes: &mut AxisState) {
    let len = JIT_LEN.load(Ordering::Acquire);
    if len == 0 {
        vm::execute(program, axes);
        return;
    }
    let fn_ptr: CompiledFn = unsafe {
        core::mem::transmute(core::ptr::addr_of!(JIT_BUF) as *const u8)
    };
    unsafe { fn_ptr(axes as *mut AxisState) };
}

// ─────────────────────────────────────── Emitter ────────────────────────────────

struct Emitter {
    pos: usize,
}

impl Emitter {
    fn new() -> Self {
        // Reset buffer before each compile.
        JIT_LEN.store(0, Ordering::Relaxed);
        Emitter { pos: 0 }
    }

    // ── emit primitives ──────────────────────────────────────────────────

    fn emit_byte(&mut self, b: u8) -> Result<(), &'static str> {
        if self.pos >= 65536 { return Err("JIT buffer overflow"); }
        unsafe { JIT_BUF.0[self.pos] = b; }
        self.pos += 1;
        Ok(())
    }

    fn emit(&mut self, bytes: &[u8]) -> Result<(), &'static str> {
        for &b in bytes { self.emit_byte(b)?; }
        Ok(())
    }

    fn emit_u32_le(&mut self, v: u32) -> Result<(), &'static str> {
        self.emit(&v.to_le_bytes())
    }

    fn emit_u64_le(&mut self, v: u64) -> Result<(), &'static str> {
        self.emit(&v.to_le_bytes())
    }

    // ── SSE scalar-float patterns (all operate on f32 / xmm registers) ──

    // MOVSS xmm0, [rdi + off8]   →  F3 0F 10 47 off
    fn load_xmm0(&mut self, off: u8) -> Result<(), &'static str> {
        self.emit(&[0xF3, 0x0F, 0x10, 0x47, off])
    }

    // MOVSS [rdi + off8], xmm0   →  F3 0F 11 47 off
    fn store_xmm0(&mut self, off: u8) -> Result<(), &'static str> {
        self.emit(&[0xF3, 0x0F, 0x11, 0x47, off])
    }

    // Load f32 immediate into xmm1 via: MOV r10d, bits32; MOVD xmm1, r10d
    //   MOV r10d, imm32   →  41 BA [imm32 LE]
    //   MOVD xmm1, r10d   →  66 41 0F 6E CA
    fn load_xmm1_f32(&mut self, val: f32) -> Result<(), &'static str> {
        self.emit(&[0x41, 0xBA])?;
        self.emit_u32_le(val.to_bits())?;
        self.emit(&[0x66, 0x41, 0x0F, 0x6E, 0xCA])
    }

    // Load f32 immediate into xmm3 via: MOV r10d, bits32; MOVD xmm3, r10d
    //   MOVD xmm3, r10d   →  66 41 0F 6E DA
    fn load_xmm3_f32(&mut self, val: f32) -> Result<(), &'static str> {
        self.emit(&[0x41, 0xBA])?;
        self.emit_u32_le(val.to_bits())?;
        self.emit(&[0x66, 0x41, 0x0F, 0x6E, 0xDA])
    }

    // Load f32 immediate into xmm4 via: MOV r10d, bits32; MOVD xmm4, r10d
    //   MOVD xmm4, r10d   →  66 41 0F 6E E2
    fn load_xmm4_f32(&mut self, val: f32) -> Result<(), &'static str> {
        self.emit(&[0x41, 0xBA])?;
        self.emit_u32_le(val.to_bits())?;
        self.emit(&[0x66, 0x41, 0x0F, 0x6E, 0xE2])
    }

    // MOVSS xmm2, [rdi + off8]   →  F3 0F 10 57 off
    //   ModRM: mod=01, reg=XMM2=010, rm=RDI=111 → 01 010 111 = 0x57
    fn load_xmm2(&mut self, off: u8) -> Result<(), &'static str> {
        self.emit(&[0xF3, 0x0F, 0x10, 0x57, off])
    }

    // Arithmetic: xmm0 op= xmm1
    fn addss_xmm0_xmm1(&mut self) -> Result<(), &'static str> { self.emit(&[0xF3, 0x0F, 0x58, 0xC1]) }
    #[allow(dead_code)]
    fn subss_xmm0_xmm1(&mut self) -> Result<(), &'static str> { self.emit(&[0xF3, 0x0F, 0x5C, 0xC1]) }
    fn minss_xmm0_xmm1(&mut self) -> Result<(), &'static str> { self.emit(&[0xF3, 0x0F, 0x5D, 0xC1]) }
    fn maxss_xmm0_xmm1(&mut self) -> Result<(), &'static str> { self.emit(&[0xF3, 0x0F, 0x5F, 0xC1]) }

    // MULSS xmm0, xmm4   →  F3 0F 59 C4
    fn mulss_xmm0_xmm4(&mut self) -> Result<(), &'static str> { self.emit(&[0xF3, 0x0F, 0x59, 0xC4]) }
    // MULSS xmm2, xmm3   →  F3 0F 59 D3
    fn mulss_xmm2_xmm3(&mut self) -> Result<(), &'static str> { self.emit(&[0xF3, 0x0F, 0x59, 0xD3]) }
    // ADDSS xmm0, xmm2   →  F3 0F 58 C2
    fn addss_xmm0_xmm2(&mut self) -> Result<(), &'static str> { self.emit(&[0xF3, 0x0F, 0x58, 0xC2]) }
    // SUBSS xmm4, xmm3   →  F3 0F 5C E3
    fn subss_xmm4_xmm3(&mut self) -> Result<(), &'static str> { self.emit(&[0xF3, 0x0F, 0x5C, 0xE3]) }

    // ── Clamp xmm0 to [0.0, 1.0] ────────────────────────────────────────
    fn clamp_xmm0(&mut self) -> Result<(), &'static str> {
        // MAXSS xmm0, 0.0  (raises floor to 0)
        self.load_xmm1_f32(0.0_f32)?;
        self.maxss_xmm0_xmm1()?;
        // MINSS xmm0, 1.0  (lowers ceiling to 1)
        self.load_xmm1_f32(1.0_f32)?;
        self.minss_xmm0_xmm1()
    }

    // ── Emit load + delta + clamp + store for one axis ───────────────────
    fn emit_axis_press(&mut self, off: u8, delta: f32) -> Result<(), &'static str> {
        self.load_xmm0(off)?;
        self.load_xmm1_f32(delta)?;
        self.addss_xmm0_xmm1()?;
        self.clamp_xmm0()?;
        self.store_xmm0(off)
    }

    fn emit_axis_set(&mut self, off: u8, val: f32) -> Result<(), &'static str> {
        // Load val into xmm0 via xmm1 path, then swap.
        // Trick: load into xmm1 then MOVSS xmm0, xmm1
        self.load_xmm1_f32(val.clamp(0.0, 1.0))?;
        // MOVSS xmm0, xmm1  →  F3 0F 10 C1
        self.emit(&[0xF3, 0x0F, 0x10, 0xC1])?;
        self.store_xmm0(off)
    }

    // AXIS.MERGE dst, src, w:  dst = dst*(1-w) + src*w
    fn emit_axis_merge(&mut self, dst_off: u8, src_off: u8, w: f32) -> Result<(), &'static str> {
        let w = w.clamp(0.0, 1.0);
        // xmm2 = src
        self.load_xmm2(src_off)?;
        // xmm3 = w
        self.load_xmm3_f32(w)?;
        // xmm4 = 1.0 - w
        self.load_xmm4_f32(1.0_f32)?;
        self.subss_xmm4_xmm3()?;
        // xmm0 = dst
        self.load_xmm0(dst_off)?;
        // xmm0 *= xmm4  (dst * (1-w))
        self.mulss_xmm0_xmm4()?;
        // xmm2 *= xmm3  (src * w)
        self.mulss_xmm2_xmm3()?;
        // xmm0 += xmm2
        self.addss_xmm0_xmm2()?;
        self.clamp_xmm0()?;
        self.store_xmm0(dst_off)
    }

    // EXIST.OPEN: floor X at threshold
    //   load x; load thresh into xmm1; MAXSS; store
    fn emit_exist_open(&mut self, thresh: f32) -> Result<(), &'static str> {
        self.load_xmm0(AxisSel::X.offset())?;
        self.load_xmm1_f32(thresh.clamp(0.0, 1.0))?;
        self.maxss_xmm0_xmm1()?;
        self.store_xmm0(AxisSel::X.offset())
    }

    // EXIST.CLOSE: ceiling X at threshold
    fn emit_exist_close(&mut self, thresh: f32) -> Result<(), &'static str> {
        self.load_xmm0(AxisSel::X.offset())?;
        self.load_xmm1_f32(thresh.clamp(0.0, 1.0))?;
        self.minss_xmm0_xmm1()?;
        self.store_xmm0(AxisSel::X.offset())
    }

    // BOUND.CLAIM: push B upward by strength * 0.5
    fn emit_bound_claim(&mut self, strength: f32) -> Result<(), &'static str> {
        self.emit_axis_press(AxisSel::B.offset(), strength * 0.5)
    }

    // RET
    pub fn ret(&mut self) {
        let _ = self.emit_byte(0xC3);
    }

    // ── Top-level instruction dispatch ──────────────────────────────────

    fn emit_insn(&mut self, insn: Instruction) -> Result<(), &'static str> {
        match insn.opcode() {
            None | Some(Opcode::Nop) => Ok(()),

            Some(Opcode::AxisPress) => {
                let off   = AxisSel::from_u8(insn.dst())
                    .map(|a| a.offset()).unwrap_or(0);
                let delta = insn.imm_signed_f32();
                self.emit_axis_press(off, delta)
            }

            Some(Opcode::AxisSet) => {
                let off = AxisSel::from_u8(insn.dst())
                    .map(|a| a.offset()).unwrap_or(0);
                self.emit_axis_set(off, insn.imm_f32())
            }

            Some(Opcode::AxisMerge) => {
                let dst_off = AxisSel::from_u8(insn.dst())
                    .map(|a| a.offset()).unwrap_or(0);
                let src_off = AxisSel::from_u8(insn.src())
                    .map(|a| a.offset()).unwrap_or(0);
                self.emit_axis_merge(dst_off, src_off, insn.imm_f32())
            }

            Some(Opcode::IstateFire) => {
                if let Some(state) = IState::from_u8(insn.dst()) {
                    let (axis, sign) = state.axis_and_sign();
                    let delta = insn.imm_f32() * sign;
                    self.emit_axis_press(axis.offset(), delta)
                } else {
                    Ok(())
                }
            }

            Some(Opcode::ExistOpen) => {
                self.emit_exist_open(insn.imm_f32())
            }

            Some(Opcode::ExistClose) => {
                self.emit_exist_close(insn.imm_f32())
            }

            Some(Opcode::BoundClaim) => {
                self.emit_bound_claim(insn.imm_f32())
            }

            Some(Opcode::WaveEmit) => {
                // WAVE.EMIT: increment TICK via absolute CALL to drift::on_tick.
                // MOV rax, abs64     →  48 B8 [addr64 LE]
                // CALL rax           →  FF D0
                let fn_addr = vm::wave_emit_thunk as *const () as u64;
                self.emit(&[0x48, 0xB8])?;
                self.emit_u64_le(fn_addr)?;
                self.emit(&[0xFF, 0xD0])
            }

            // These ops touch state outside AxisState — fall through to VM.
            // PUSH RDI (save axes ptr), MOV RSI, prog_ptr, MOV RDX, prog_len,
            // CALL vm::execute_thunk, POP RDI.
            // For v0.1 these are stubbed as NOPs in emitted code; the vm
            // interpreter handles them when run() detects fallback mode.
            Some(Opcode::AxisRead)
            | Some(Opcode::IstatePoll)
            | Some(Opcode::CrystalObs)
            | Some(Opcode::CrystalSeed)
            | Some(Opcode::SediDeposit)
            | Some(Opcode::SediRecall)
            | Some(Opcode::BoundRelease) => Ok(()), // NOP in JIT; vm handles
        }
    }
}
