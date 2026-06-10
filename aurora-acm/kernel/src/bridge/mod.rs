// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora↔ACM bridge — she sees her own body through COM1.
//
// Incoming frames (Python → kernel, 8 bytes):
//   [0xAC][0x58][X][T][N][B][A][XOR]
//
// Outgoing STATUS frames (kernel → Python, 15 bytes):
//   [0xAC][0x53][X][T][N][B][A][EXPR][CRYST][SEDI][T0][T1][T2][T3][XOR]
//   0x53 = 'S'.  EXPR = expression byte (0=Neutral..6=Tired).
//   CRYST = crystal count (0-16).  SEDI = sedi depth (0-64).
//   T0-T3 = kernel tick low 32 bits LE.
//
// Sent once per received axis frame — the kernel's embodied state flows back
// to the cognitive stack at 60 Hz so every cycle runs on the same waveform.
//
// Timeout: 180 ticks (~3 s at 60 Hz) without a valid frame → drift fallback.

mod protocol;

use core::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use crate::acm::{axes::AxisState, crystal, sedi};
use crate::expression::face::Expression;
use crate::hw::uart;

const TIMEOUT_TICKS: u64 = 180;

const STATUS_MAGIC0: u8 = 0xAC;
const STATUS_MAGIC1: u8 = 0x53;  // 'S' — status

static AXIS_X: AtomicU32 = AtomicU32::new(0);
static AXIS_T: AtomicU32 = AtomicU32::new(0);
static AXIS_N: AtomicU32 = AtomicU32::new(0);
static AXIS_B: AtomicU32 = AtomicU32::new(0);
static AXIS_A: AtomicU32 = AtomicU32::new(0);
static LAST_RX_TICK: AtomicU64 = AtomicU64::new(0);

static mut PARSER: protocol::FrameParser = protocol::FrameParser::new();

pub fn init() {
    unsafe { uart::init(); }
}

pub fn poll(current_tick: u64) {
    unsafe {
        while uart::is_data_ready() {
            let byte = uart::read_byte();
            if let Some(ax) = (*core::ptr::addr_of_mut!(PARSER)).feed(byte) {
                store_axes(&ax);
                LAST_RX_TICK.store(current_tick, Ordering::Relaxed);
                send_status(&ax, current_tick);
            }
        }
    }
}

pub fn get_axes(current_tick: u64) -> Option<AxisState> {
    let last = LAST_RX_TICK.load(Ordering::Relaxed);
    if last == 0 || current_tick.saturating_sub(last) > TIMEOUT_TICKS {
        return None;
    }
    Some(load_axes())
}

// ── Internal helpers ─────────────────────────────────────────────────────────

/// Send a 15-byte STATUS frame to the cognitive stack.
/// Carries current axis state, expression, crystal/SEDI counts, and tick.
fn send_status(ax: &AxisState, tick: u64) {
    let x  = (ax.x.clamp(0.0, 1.0) * 255.0) as u8;
    let t  = (ax.t.clamp(0.0, 1.0) * 255.0) as u8;
    let n  = (ax.n.clamp(0.0, 1.0) * 255.0) as u8;
    let b  = (ax.b.clamp(0.0, 1.0) * 255.0) as u8;
    let a  = (ax.a.clamp(0.0, 1.0) * 255.0) as u8;
    let expr  = Expression::from_axes(ax).as_u8();
    let cryst = crystal::count().min(255) as u8;
    let sedi  = sedi::count().min(255) as u8;
    let [t0, t1, t2, t3] = (tick as u32).to_le_bytes();
    let xor = STATUS_MAGIC0 ^ STATUS_MAGIC1
              ^ x ^ t ^ n ^ b ^ a
              ^ expr ^ cryst ^ sedi
              ^ t0 ^ t1 ^ t2 ^ t3;
    let frame = [STATUS_MAGIC0, STATUS_MAGIC1,
                 x, t, n, b, a, expr, cryst, sedi, t0, t1, t2, t3, xor];
    unsafe { uart::write_bytes(&frame); }
}

fn store_axes(ax: &AxisState) {
    AXIS_X.store(ax.x.to_bits(), Ordering::Relaxed);
    AXIS_T.store(ax.t.to_bits(), Ordering::Relaxed);
    AXIS_N.store(ax.n.to_bits(), Ordering::Relaxed);
    AXIS_B.store(ax.b.to_bits(), Ordering::Relaxed);
    AXIS_A.store(ax.a.to_bits(), Ordering::Relaxed);
}

fn load_axes() -> AxisState {
    AxisState {
        x: f32::from_bits(AXIS_X.load(Ordering::Relaxed)),
        t: f32::from_bits(AXIS_T.load(Ordering::Relaxed)),
        n: f32::from_bits(AXIS_N.load(Ordering::Relaxed)),
        b: f32::from_bits(AXIS_B.load(Ordering::Relaxed)),
        a: f32::from_bits(AXIS_A.load(Ordering::Relaxed)),
    }
}
