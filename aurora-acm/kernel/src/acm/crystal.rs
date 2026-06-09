// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// ConceptCrystalStore — axis-pattern memory.
//
// A crystal is a remembered AxisState pattern that has been observed
// repeatedly.  When the current axis state resonates strongly with an
// existing crystal (alignment > OBS_THRESHOLD), that crystal strengthens
// and its pattern is nudged toward the observed state.  If no crystal
// resonates, a new weak crystal is seeded.
//
// Crystals decay slowly each tick.  Patterns that are visited often
// persist; patterns that are only visited once dissolve.
//
// Xaurora CRYSTAL.OBS feeds the current state into observe().
// Xaurora CRYSTAL.SEED force-seeds a crystal at the current state.
//
// Up to MAX_CRYSTALS crystals.  When full the weakest is replaced.
// Total storage: 16 × (5 f32 + 1 f32) = 384 bytes.

use crate::acm::axes::AxisState;

pub const MAX_CRYSTALS: usize = 16;

const OBS_THRESHOLD:   f32 = 2.5;   // min alignment to resonate with existing crystal
const STRENGTHEN_RATE: f32 = 0.08;  // crystal grows this much per resonant observation
const DECAY_RATE:      f32 = 0.001; // crystal loses this much strength per tick

pub struct Crystal {
    pub pattern:  AxisState,
    pub strength: f32,   // [0, 1]
}

pub struct CrystalStore {
    crystals: [Option<Crystal>; MAX_CRYSTALS],
    pub count: usize,
}

impl CrystalStore {
    pub const fn new() -> Self {
        Self {
            crystals: [const { None }; MAX_CRYSTALS],
            count: 0,
        }
    }

    /// Observe `axes`: strengthen the best-matching crystal or seed a new one.
    pub fn observe(&mut self, axes: &AxisState) {
        let mut best_idx:   Option<usize> = None;
        let mut best_score: f32           = OBS_THRESHOLD;
        for (i, slot) in self.crystals.iter().enumerate() {
            if let Some(c) = slot {
                let score = axes.alignment(&c.pattern);
                if score > best_score {
                    best_score = score;
                    best_idx   = Some(i);
                }
            }
        }
        if let Some(idx) = best_idx {
            if let Some(c) = self.crystals[idx].as_mut() {
                c.strength = (c.strength + STRENGTHEN_RATE).clamp(0.0, 1.0);
                // Pull pattern toward observed state at STRENGTHEN_RATE.
                c.pattern.x += (axes.x - c.pattern.x) * STRENGTHEN_RATE;
                c.pattern.t += (axes.t - c.pattern.t) * STRENGTHEN_RATE;
                c.pattern.n += (axes.n - c.pattern.n) * STRENGTHEN_RATE;
                c.pattern.b += (axes.b - c.pattern.b) * STRENGTHEN_RATE;
                c.pattern.a += (axes.a - c.pattern.a) * STRENGTHEN_RATE;
            }
        } else {
            self.seed(axes, 0.10);
        }
    }

    /// Force-seed a crystal with initial `strength` (clamped to [0, 1]).
    /// Replaces the weakest existing crystal if the store is full.
    pub fn seed(&mut self, axes: &AxisState, strength: f32) {
        let mut target: Option<usize> = None;
        let mut weakest: f32 = 2.0;
        for (i, slot) in self.crystals.iter().enumerate() {
            match slot {
                None => { target = Some(i); break; }
                Some(c) if c.strength < weakest => {
                    weakest = c.strength;
                    target  = Some(i);
                }
                _ => {}
            }
        }
        if let Some(idx) = target {
            if self.crystals[idx].is_none() { self.count += 1; }
            self.crystals[idx] = Some(Crystal {
                pattern:  *axes,
                strength: strength.clamp(0.0, 1.0),
            });
        }
    }

    /// Decay all crystals by DECAY_RATE; dissolve those that reach 0.
    pub fn tick_decay(&mut self) {
        for slot in self.crystals.iter_mut() {
            if let Some(c) = slot {
                c.strength -= DECAY_RATE;
                if c.strength <= 0.0 {
                    *slot = None;
                    if self.count > 0 { self.count -= 1; }
                }
            }
        }
    }

    /// Return the strongest crystal's pattern, if any.
    #[allow(dead_code)]
    pub fn strongest_pattern(&self) -> Option<AxisState> {
        self.crystals.iter()
            .filter_map(|s| s.as_ref())
            .max_by(|a, b| a.strength.partial_cmp(&b.strength)
                .unwrap_or(core::cmp::Ordering::Equal))
            .map(|c| c.pattern)
    }
}

pub static mut CRYSTAL_STORE: CrystalStore = CrystalStore::new();

pub fn observe(axes: &AxisState) {
    unsafe { (*core::ptr::addr_of_mut!(CRYSTAL_STORE)).observe(axes); }
}

pub fn seed(axes: &AxisState, strength: f32) {
    unsafe { (*core::ptr::addr_of_mut!(CRYSTAL_STORE)).seed(axes, strength); }
}

pub fn tick_decay() {
    unsafe { (*core::ptr::addr_of_mut!(CRYSTAL_STORE)).tick_decay(); }
}

#[allow(dead_code)]
pub fn strongest_pattern() -> Option<AxisState> {
    unsafe { (*core::ptr::addr_of!(CRYSTAL_STORE)).strongest_pattern() }
}
