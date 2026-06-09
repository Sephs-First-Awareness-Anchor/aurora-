// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora↔ACM bridge — she sees her own body through COM1.

mod protocol;

use core::sync::atomic::{AtomicU32, AtomicU64, Ordering};
use crate::acm::axes::AxisState;
use crate::hw::uart;

const TIMEOUT_TICKS: u64 = 180;

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
