// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Background color is Aurora's emotional skin — driven entirely by axis state.
//
// Base color: Aurora's purple rgb(123, 94, 167) = #7B5EA7
// X shifts red component (perception intensity).
// A shifts blue component (agency depth).
// N shifts green component (energy saturation).
// The result always reads as purple; only the shade varies.

use crate::acm::axes::AxisState;

#[derive(Clone, Copy, Debug)]
pub struct Rgb {
    pub r: u8,
    pub g: u8,
    pub b: u8,
}

impl Rgb {
    pub const fn new(r: u8, g: u8, b: u8) -> Self { Self { r, g, b } }
    pub const WHITE: Rgb = Rgb::new(255, 255, 255);
    #[allow(dead_code)] pub const BLACK: Rgb = Rgb::new(10, 10, 10);
    #[allow(dead_code)] pub const AURORA_PURPLE: Rgb = Rgb::new(123, 94, 167);
    pub const PUPIL: Rgb = Rgb::new(30, 20, 50);
}

fn lerp_u8(a: u8, b: u8, t: f32) -> u8 {
    let a = a as f32;
    let b = b as f32;
    (a + (b - a) * t.clamp(0.0, 1.0)) as u8
}

pub fn axes_to_background(ax: &AxisState) -> Rgb {
    // X raises red toward vivid violet (147, 94, 167).
    let r = lerp_u8(100, 150, ax.x);
    // N raises green slightly — high energy makes her a bit warmer.
    let g = lerp_u8(70, 110, ax.n);
    // A deepens blue — high agency = rich indigo; low = paler lilac.
    let b = lerp_u8(130, 200, ax.a);
    Rgb::new(r, g, b)
}

pub fn eye_color(_ax: &AxisState) -> Rgb {
    Rgb::WHITE
}

pub fn mouth_color(_ax: &AxisState) -> Rgb {
    Rgb::new(255, 255, 255)
}
