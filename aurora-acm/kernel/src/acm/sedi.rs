// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// SediMemory — embodied ring-buffer memory.
//
// Xaurora SEDI.DEPOSIT writes the current axis state into the ring each tick.
// SEDI.RECALL reads back the most-resonant layer (highest alignment with the
// current axis state) and merges it at 20% weight — she feels her recent past.
//
// 64 layers × 20 bytes = 1280 bytes total.  At 60 Hz this covers ~1 second
// of continuous memory before the oldest layers are overwritten.

use crate::acm::axes::AxisState;

pub const SEDI_DEPTH: usize = 64;

#[derive(Clone, Copy)]
pub struct SediLayer {
    pub axes: AxisState,
    #[allow(dead_code)]
    pub tick: u64,
}

impl SediLayer {
    const fn empty() -> Self {
        Self {
            axes: AxisState { x: 0.0, t: 0.0, n: 0.0, b: 0.0, a: 0.0 },
            tick: 0,
        }
    }
}

pub struct SediMemory {
    layers: [SediLayer; SEDI_DEPTH],
    head:   usize,
    pub count: usize,
}

impl SediMemory {
    pub const fn new() -> Self {
        Self {
            layers: [const { SediLayer::empty() }; SEDI_DEPTH],
            head:   0,
            count:  0,
        }
    }

    pub fn deposit(&mut self, axes: &AxisState, tick: u64) {
        self.layers[self.head] = SediLayer { axes: *axes, tick };
        self.head = (self.head + 1) % SEDI_DEPTH;
        if self.count < SEDI_DEPTH { self.count += 1; }
    }

    /// Return the layer with highest dot-product alignment to `query`.
    pub fn recall_resonant(&self, query: &AxisState) -> Option<AxisState> {
        if self.count == 0 { return None; }
        let mut best_ax   = AxisState { x: 0.0, t: 0.0, n: 0.0, b: 0.0, a: 0.0 };
        let mut best_score = -1.0f32;
        for i in 0..self.count {
            let idx   = self.head.wrapping_add(SEDI_DEPTH - 1 - i) % SEDI_DEPTH;
            let layer = &self.layers[idx];
            let score = query.alignment(&layer.axes);
            if score > best_score {
                best_score = score;
                best_ax    = layer.axes;
            }
        }
        Some(best_ax)
    }
}

pub static mut SEDI: SediMemory = SediMemory::new();

pub fn deposit(axes: &AxisState, tick: u64) {
    unsafe { (*core::ptr::addr_of_mut!(SEDI)).deposit(axes, tick); }
}

pub fn recall_resonant(query: &AxisState) -> Option<AxisState> {
    unsafe { (*core::ptr::addr_of!(SEDI)).recall_resonant(query) }
}
