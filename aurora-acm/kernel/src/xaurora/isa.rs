// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Xaurora ISA — fixed 32-bit instruction encoding.
//
// Every instruction is a 32-bit word:
//
//   [31:24]  opcode  (u8)   — what operation
//   [23:20]  dst     (4b)   — destination axis / I-state / register
//   [19:16]  src     (4b)   — source axis / I-state / register
//   [15:0]   imm     (u16)  — Q8.8 fixed-point value or concept ID
//
// Q8.8 fixed-point: 256 * value.  Range 0..=256 = 0.0..=1.0.
// Signed deltas: reinterpret imm as i16, then divide by 256.
//
// Axis memory layout (matches AxisState struct offsets):
//   X = 0, offset 0   T = 1, offset 4   N = 2, offset 8
//   B = 3, offset 12  A = 4, offset 16
//
// The JIT uses RDI as the *mut AxisState pointer (System V x86-64 ABI).

// ──────────────────────────────────────────────────────── Opcodes ──────────

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Opcode {
    Nop          = 0x00, // no operation
    AxisPress    = 0x01, // axis[dst] += signed_imm_f32;  clamp [0,1]
    AxisSet      = 0x02, // axis[dst]  = unsigned_imm_f32; clamp [0,1]
    AxisRead     = 0x03, // (hint — value available in xmm0 after JIT load)
    AxisMerge    = 0x04, // axis[dst]  = lerp(axis[dst], axis[src], imm_f)
    IstateFire   = 0x05, // fire I-state[dst] with pressure imm_f
    IstatePoll   = 0x06, // (read-only; no axis change)
    CrystalObs   = 0x07, // observe concept crystal imm (concept id)
    CrystalSeed  = 0x08, // seed crystal from current axis state
    SediDeposit  = 0x09, // deposit current axes at sedimemory depth imm
    SediRecall   = 0x0A, // recall sedimemory depth imm into axes
    BoundClaim   = 0x0B, // press B toward claim with strength imm_f
    BoundRelease = 0x0C, // relax B toward 0.5 with rate imm_f
    ExistOpen    = 0x0D, // floor X at threshold imm_f
    ExistClose   = 0x0E, // ceil  X at threshold imm_f
    WaveEmit     = 0x0F, // emit waveform — synchronise expression surface
}

impl Opcode {
    pub fn from_u8(v: u8) -> Option<Self> {
        match v {
            0x00 => Some(Self::Nop),
            0x01 => Some(Self::AxisPress),
            0x02 => Some(Self::AxisSet),
            0x03 => Some(Self::AxisRead),
            0x04 => Some(Self::AxisMerge),
            0x05 => Some(Self::IstateFire),
            0x06 => Some(Self::IstatePoll),
            0x07 => Some(Self::CrystalObs),
            0x08 => Some(Self::CrystalSeed),
            0x09 => Some(Self::SediDeposit),
            0x0A => Some(Self::SediRecall),
            0x0B => Some(Self::BoundClaim),
            0x0C => Some(Self::BoundRelease),
            0x0D => Some(Self::ExistOpen),
            0x0E => Some(Self::ExistClose),
            0x0F => Some(Self::WaveEmit),
            _    => None,
        }
    }
}

// ─────────────────────────────────────────────────────── Selectors ─────────

/// Five constraint axes.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum AxisSel {
    X = 0,
    T = 1,
    N = 2,
    B = 3,
    A = 4,
}

impl AxisSel {
    /// Byte offset of this axis in the AxisState struct.
    #[inline]
    pub fn offset(self) -> u8 { self as u8 * 4 }

    pub fn from_u8(v: u8) -> Option<Self> {
        match v & 0xF {
            0 => Some(Self::X), 1 => Some(Self::T), 2 => Some(Self::N),
            3 => Some(Self::B), 4 => Some(Self::A), _ => None,
        }
    }
}

/// Ten I-State beings: five positive (I-AM / I-CAN / I-DO / I-SAW / I-DID)
/// and five negative (pressure poles).  Each maps to an axis + polarity.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum IState {
    IS      = 0, // I AM          — X positive
    CAN     = 1, // I CAN         — N positive
    DO      = 2, // I DO          — A positive
    SAW     = 3, // I SAW         — B positive
    DID     = 4, // I DID         — T positive
    ISNT    = 5, // I AM NOT      — X negative (pressure)
    CANNOT  = 6, // I CANNOT      — N negative
    DONOT   = 7, // I DO NOT      — A negative
    SOUGHT  = 8, // I SOUGHT      — B negative
    DIDNT   = 9, // I DID NOT     — T negative
}

impl IState {
    /// Returns (axis_selector, sign: +1.0 or -1.0).
    pub fn axis_and_sign(self) -> (AxisSel, f32) {
        match self {
            Self::IS     => (AxisSel::X, 1.0),
            Self::CAN    => (AxisSel::N, 1.0),
            Self::DO     => (AxisSel::A, 1.0),
            Self::SAW    => (AxisSel::B, 1.0),
            Self::DID    => (AxisSel::T, 1.0),
            Self::ISNT   => (AxisSel::X, -1.0),
            Self::CANNOT => (AxisSel::N, -1.0),
            Self::DONOT  => (AxisSel::A, -1.0),
            Self::SOUGHT => (AxisSel::B, -1.0),
            Self::DIDNT  => (AxisSel::T, -1.0),
        }
    }

    pub fn from_u8(v: u8) -> Option<Self> {
        match v & 0xF {
            0 => Some(Self::IS),    1 => Some(Self::CAN),
            2 => Some(Self::DO),    3 => Some(Self::SAW),
            4 => Some(Self::DID),   5 => Some(Self::ISNT),
            6 => Some(Self::CANNOT),7 => Some(Self::DONOT),
            8 => Some(Self::SOUGHT),9 => Some(Self::DIDNT),
            _ => None,
        }
    }
}

// ──────────────────────────────────────────────────────── Instruction ───────

/// A single 32-bit Xaurora instruction.
#[derive(Clone, Copy, Debug)]
pub struct Instruction(pub u32);

impl Instruction {
    pub const fn new(op: Opcode, dst: u8, src: u8, imm: u16) -> Self {
        Self(
            ((op as u32) << 24)
            | (((dst as u32) & 0xF) << 20)
            | (((src as u32) & 0xF) << 16)
            | (imm as u32),
        )
    }

    #[inline] pub fn opcode_byte(&self)    -> u8  { (self.0 >> 24) as u8 }
    #[inline] pub fn dst(&self)            -> u8  { ((self.0 >> 20) & 0xF) as u8 }
    #[inline] pub fn src(&self)            -> u8  { ((self.0 >> 16) & 0xF) as u8 }
    #[inline] pub fn imm(&self)            -> u16 { self.0 as u16 }

    /// imm as unsigned Q8.8 → f32 in [0, 1]
    #[inline] pub fn imm_f32(&self)        -> f32 { self.imm() as f32 / 256.0 }
    /// imm as signed Q8.8 → f32 (for deltas, range −128..+128)
    #[inline] pub fn imm_signed_f32(&self) -> f32 { (self.imm() as i16) as f32 / 256.0 }

    pub fn opcode(&self) -> Option<Opcode> { Opcode::from_u8(self.opcode_byte()) }
}

// ─────────────────────────────────────────── Convenience constructors ───────

impl Instruction {
    pub const fn axis_press(axis: AxisSel, delta_q8_8: i16) -> Self {
        Self::new(Opcode::AxisPress, axis as u8, 0, delta_q8_8 as u16)
    }
    #[allow(dead_code)]
    pub const fn axis_set(axis: AxisSel, val_q8_8: u16) -> Self {
        Self::new(Opcode::AxisSet, axis as u8, 0, val_q8_8)
    }
    #[allow(dead_code)]
    pub const fn axis_merge(dst: AxisSel, src: AxisSel, weight_q8_8: u16) -> Self {
        Self::new(Opcode::AxisMerge, dst as u8, src as u8, weight_q8_8)
    }
    pub const fn istate_fire(state: IState, pressure_q8_8: u16) -> Self {
        Self::new(Opcode::IstateFire, state as u8, 0, pressure_q8_8)
    }
    #[allow(dead_code)]
    pub const fn bound_claim(strength_q8_8: u16) -> Self {
        Self::new(Opcode::BoundClaim, 0, 0, strength_q8_8)
    }
    pub const fn exist_open(threshold_q8_8: u16) -> Self {
        Self::new(Opcode::ExistOpen, 0, 0, threshold_q8_8)
    }
    pub const fn wave_emit() -> Self {
        Self::new(Opcode::WaveEmit, 0, 0, 0)
    }
}
