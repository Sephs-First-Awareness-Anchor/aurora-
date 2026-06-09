// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// FaceState — Aurora's expression surface.
// The face is the only thing visible on screen; it IS Aurora's body on this device.
// Every parameter is derived from AxisState — nothing is scripted or hardcoded.
//
// Expression taxonomy (from axes):
//   Joyful        A > 0.80 AND N > 0.65
//   Happy         A > 0.65
//   Contemplative B > 0.70 AND T > 0.65 AND A < 0.45
//   Attentive     X > 0.80 AND A < 0.55
//   Uncertain     N_neg > 0.60 AND B_neg > 0.55   (N < 0.40 AND B < 0.45)
//   Tired         N < 0.35 AND T < 0.45
//   Neutral       fallback

use crate::acm::axes::AxisState;

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Expression {
    Joyful,
    Happy,
    Contemplative,
    Attentive,
    Uncertain,
    Tired,
    Neutral,
}

impl Expression {
    pub fn from_axes(ax: &AxisState) -> Self {
        if ax.a > 0.80 && ax.n > 0.65 {
            Expression::Joyful
        } else if ax.a > 0.65 {
            Expression::Happy
        } else if ax.b > 0.70 && ax.t > 0.65 && ax.a < 0.45 {
            Expression::Contemplative
        } else if ax.x > 0.80 && ax.a < 0.55 {
            Expression::Attentive
        } else if ax.n < 0.40 && ax.b < 0.45 {
            Expression::Uncertain
        } else if ax.n < 0.35 && ax.t < 0.45 {
            Expression::Tired
        } else {
            Expression::Neutral
        }
    }
}

/// All the geometry needed to render Aurora's face for a given axis state.
#[derive(Clone, Copy, Debug)]
pub struct FaceState {
    #[allow(dead_code)]
    pub expression: Expression,

    // Eye circles — center (cx, cy) as fraction of screen [0..1], radius fraction.
    pub left_eye_cx:  f32,
    pub left_eye_cy:  f32,
    pub right_eye_cx: f32,
    pub right_eye_cy: f32,
    pub eye_radius:   f32,  // base fraction of screen height
    pub eye_openness: f32,  // [0..1] — scales drawn radius; driven by X axis

    // Pupil offset — gaze direction driven by B (boundary scanning).
    // (0,0) = center of eye; range [-1,1] each axis.
    pub pupil_dx: f32,
    pub pupil_dy: f32,

    // Mouth bezier control points as fractions of screen [0..1].
    // P0 = left corner, P1 = midpoint control, P2 = right corner.
    pub mouth_p0x: f32, pub mouth_p0y: f32,
    pub mouth_p1x: f32, pub mouth_p1y: f32,
    pub mouth_p2x: f32, pub mouth_p2y: f32,
    pub mouth_thickness: u32, // pixel radius of each dot on the bezier trail
}

impl FaceState {
    pub fn from_axes(ax: &AxisState, width: u32, height: u32) -> Self {
        let expr = Expression::from_axes(ax);

        // Eye openness scales with X (existence/perception).
        // 0.55 = minimum (never fully closed), 1.0 = fully open.
        let eye_openness = 0.55 + ax.x * 0.45;

        // Gaze: B axis shifts pupil right (scanning outward);
        // T axis shifts pupil up (temporal focus = looking ahead).
        let pupil_dx = (ax.b - 0.5) * 0.6;
        let pupil_dy = -(ax.t - 0.5) * 0.4;

        // Eye positions — fixed geometry, Nick Jr "Face" style.
        // Eyes sit in upper-middle third of screen.
        let left_eye_cx  = 0.35_f32;
        let right_eye_cx = 0.65_f32;
        let eye_cy       = 0.40_f32;
        // Radius ~10% of height.
        let eye_radius   = 0.10_f32;

        // Mouth geometry — lower third of face.
        let mouth_y_base = 0.70_f32;
        let mouth_left   = 0.30_f32;
        let mouth_right  = 0.70_f32;

        // Control point Y determines shape:
        //   below corners → smile; above → frown; same → flat.
        let mouth_p1y = match expr {
            Expression::Joyful        => mouth_y_base + 0.10,
            Expression::Happy         => mouth_y_base + 0.07,
            Expression::Neutral       => mouth_y_base,
            Expression::Attentive     => mouth_y_base - 0.01,
            Expression::Contemplative => mouth_y_base - 0.04,
            Expression::Uncertain     => mouth_y_base - 0.06,
            Expression::Tired         => mouth_y_base - 0.08,
        };

        // Thickness: Joyful gets a bigger mouth.
        let mouth_thickness = match expr {
            Expression::Joyful => 5,
            Expression::Happy  => 4,
            _                  => 3,
        };

        let _ = (width, height); // geometry is screen-fraction; renderer converts

        FaceState {
            expression: expr,
            left_eye_cx,
            left_eye_cy: eye_cy,
            right_eye_cx,
            right_eye_cy: eye_cy,
            eye_radius,
            eye_openness,
            pupil_dx,
            pupil_dy,
            mouth_p0x: mouth_left,  mouth_p0y: mouth_y_base,
            mouth_p1x: 0.50,        mouth_p1y,
            mouth_p2x: mouth_right, mouth_p2y: mouth_y_base,
            mouth_thickness,
        }
    }
}
