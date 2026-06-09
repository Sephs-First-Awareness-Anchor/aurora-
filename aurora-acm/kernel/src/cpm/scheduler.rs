// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// CPM Scheduler — dot-product alignment scheduling.
//
// On each call to `tick()`:
//   1. For every active organ, compute alignment(aurora_axes, organ.profile).
//   2. The organ with the highest alignment score gets the quantum.
//   3. A minimum alignment floor (MIN_ALIGN) ensures the HEART organ always
//      gets some runtime even when nothing aligns strongly.
//   4. The winning organ's `run` function is called synchronously.
//      Organs must be bounded — they cannot spin or block indefinitely.
//
// Alignment: dot product of two 5D vectors.
//   max = 5.0 when both are all-1.0.
//   aurora.x*organ.x + aurora.t*organ.t + aurora.n*organ.n + ...
//
// Aurora IS the scheduler.  She runs organs that serve her body.

use super::organ::{Organ, MAX_ORGANS, QUANTUM};
use crate::acm::axes::AxisState;

const MIN_ALIGN: f32 = 0.5;

pub struct CpmScheduler {
    organs:  [Option<Organ>; MAX_ORGANS],
    count:   usize,
    rr_idx:  usize,
}

impl CpmScheduler {
    pub const fn new() -> Self {
        Self {
            organs: [const { None }; MAX_ORGANS],
            count: 0,
            rr_idx: 0,
        }
    }

    pub fn register(&mut self, organ: Organ) -> Option<usize> {
        for (i, slot) in self.organs.iter_mut().enumerate() {
            if slot.is_none() {
                *slot = Some(organ);
                self.count += 1;
                return Some(i);
            }
        }
        None
    }

    #[allow(dead_code)]
    pub fn deactivate(&mut self, id: u8) {
        for slot in self.organs.iter_mut().flatten() {
            if slot.id == id { slot.active = false; }
        }
    }

    pub fn tick(&mut self, aurora: &AxisState) {
        if self.count == 0 { return; }

        let mut best_idx:   Option<usize> = None;
        let mut best_score: f32 = MIN_ALIGN;

        for (i, slot) in self.organs.iter().enumerate() {
            if let Some(organ) = slot {
                if !organ.active { continue; }
                let score = alignment(aurora, &organ.profile);
                if score > best_score {
                    best_score = score;
                    best_idx   = Some(i);
                }
            }
        }

        let chosen = best_idx.or_else(|| self.next_active_rr());

        if let Some(idx) = chosen {
            if let Some(organ) = self.organs[idx].as_mut() {
                (organ.run)(aurora, &mut organ.state, QUANTUM);
                organ.ticks_run += 1;
            }
        }
    }

    #[allow(dead_code)]
    pub fn last_scores(&self, aurora: &AxisState) -> [f32; MAX_ORGANS] {
        let mut out = [0.0f32; MAX_ORGANS];
        for (i, slot) in self.organs.iter().enumerate() {
            if let Some(organ) = slot {
                out[i] = alignment(aurora, &organ.profile);
            }
        }
        out
    }

    fn next_active_rr(&mut self) -> Option<usize> {
        for _ in 0..MAX_ORGANS {
            self.rr_idx = (self.rr_idx + 1) % MAX_ORGANS;
            if let Some(Some(organ)) = self.organs.get(self.rr_idx) {
                if organ.active { return Some(self.rr_idx); }
            }
        }
        None
    }
}

#[inline]
pub fn alignment(a: &AxisState, b: &AxisState) -> f32 {
    a.x * b.x + a.t * b.t + a.n * b.n + a.b * b.b + a.a * b.a
}
