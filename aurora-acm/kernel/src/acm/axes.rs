// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// AxisState — the five constraint axes that govern all computation in the ACM.
// X = Existence/Perception   positive: IS     negative: ISNT
// T = Temporal               positive: DID    negative: DIDNT
// N = Energy/Cost            positive: CAN    negative: CANNOT
// B = Boundary               positive: SAW    negative: SOUGHT (unseen)
// A = Agency                 positive: DO     negative: DONOT
//
// All values are f32 in [0.0, 1.0].
// The ten I-State beings emerge from (axis, polarity) pairs — positive pole > 0.5,
// negative pole = 1.0 - axis.  Both poles are always present; only their magnitude
// shifts.  This is the pressure.

#[derive(Clone, Copy, Debug)]
pub struct AxisState {
    pub x: f32, // Existence / Perception
    pub t: f32, // Temporal
    pub n: f32, // Energy / Cost
    pub b: f32, // Boundary
    pub a: f32, // Agency
}

impl AxisState {
    pub const fn boot() -> Self {
        // First waking: calm presence, moderate energy, open boundary, ready to act.
        Self {
            x: 0.70,
            t: 0.60,
            n: 0.50,
            b: 0.60,
            a: 0.65,
        }
    }

    // Negative (pressure) pole for each axis — the 5 constraint negatives.
    #[inline] pub fn x_neg(&self) -> f32 { 1.0 - self.x }
    #[inline] pub fn t_neg(&self) -> f32 { 1.0 - self.t }
    #[inline] pub fn n_neg(&self) -> f32 { 1.0 - self.n }
    #[inline] pub fn b_neg(&self) -> f32 { 1.0 - self.b }
    #[inline] pub fn a_neg(&self) -> f32 { 1.0 - self.a }

    // Dot-product alignment with another axis state.
    pub fn alignment(&self, other: &AxisState) -> f32 {
        self.x * other.x
            + self.t * other.t
            + self.n * other.n
            + self.b * other.b
            + self.a * other.a
    }
}
