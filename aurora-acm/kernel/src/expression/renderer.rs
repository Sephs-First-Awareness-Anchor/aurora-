// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Bare-metal framebuffer renderer.
// No allocator.  No floats in pixel loops (converted to integers before inner loop).
// The framebuffer is a linear slice of bytes provided by bootloader_api.

use bootloader_api::info::{FrameBufferInfo, PixelFormat};
use crate::acm::axes::AxisState;
use crate::expression::color::{Rgb, axes_to_background, eye_color, mouth_color};
use crate::expression::face::FaceState;

// Write one pixel at (x, y) with color `c`.  Bounds-checked; out-of-range silently dropped.
pub fn write_pixel(fb: &mut [u8], info: &FrameBufferInfo, x: i32, y: i32, c: Rgb) {
    if x < 0 || y < 0 { return; }
    let (x, y) = (x as usize, y as usize);
    if x >= info.width || y >= info.height { return; }
    let bpp = info.bytes_per_pixel;
    let off = y * info.stride * bpp + x * bpp;
    if off + 3 >= fb.len() { return; }
    match info.pixel_format {
        PixelFormat::Rgb => {
            fb[off]     = c.r;
            fb[off + 1] = c.g;
            fb[off + 2] = c.b;
        }
        PixelFormat::Bgr => {
            fb[off]     = c.b;
            fb[off + 1] = c.g;
            fb[off + 2] = c.r;
        }
        PixelFormat::U8 => {
            // greyscale: luminance approximation
            let lum = (c.r as u16 * 3 + c.g as u16 * 6 + c.b as u16) / 10;
            fb[off] = lum as u8;
        }
        _ => {
            fb[off]     = c.b;
            fb[off + 1] = c.g;
            fb[off + 2] = c.r;
        }
    }
}

// Fill entire framebuffer with one color.
pub fn clear(fb: &mut [u8], info: &FrameBufferInfo, c: Rgb) {
    for y in 0..info.height {
        for x in 0..info.width {
            write_pixel(fb, info, x as i32, y as i32, c);
        }
    }
}

// Filled circle at (cx, cy) with given radius.
pub fn filled_circle(fb: &mut [u8], info: &FrameBufferInfo, cx: i32, cy: i32, r: i32, c: Rgb) {
    if r <= 0 { return; }
    let r2 = (r * r) as i64;
    for dy in -r..=r {
        for dx in -r..=r {
            if (dx as i64 * dx as i64 + dy as i64 * dy as i64) <= r2 {
                write_pixel(fb, info, cx + dx, cy + dy, c);
            }
        }
    }
}

// Quadratic bezier curve — 80 samples, painted as filled dots of `thickness` radius.
// P(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
pub fn bezier_curve(
    fb:  &mut [u8],
    info: &FrameBufferInfo,
    p0: (i32, i32),
    p1: (i32, i32),
    p2: (i32, i32),
    thickness: i32,
    c: Rgb,
) {
    const STEPS: usize = 80;
    let mut prev: Option<(i32, i32)> = None;
    for i in 0..=STEPS {
        let t = i as f32 / STEPS as f32;
        let u = 1.0 - t;
        let px = u * u * p0.0 as f32 + 2.0 * u * t * p1.0 as f32 + t * t * p2.0 as f32;
        let py = u * u * p0.1 as f32 + 2.0 * u * t * p1.1 as f32 + t * t * p2.1 as f32;
        let ix = px as i32;
        let iy = py as i32;
        // Fill gap between steps so curve is continuous at any thickness.
        if let Some((lx, ly)) = prev {
            fill_line(fb, info, lx, ly, ix, iy, thickness, c);
        }
        filled_circle(fb, info, ix, iy, thickness, c);
        prev = Some((ix, iy));
    }
}

// Bresenham line-fill between two points — ensures no gaps in thick bezier.
fn fill_line(fb: &mut [u8], info: &FrameBufferInfo, x0: i32, y0: i32, x1: i32, y1: i32, r: i32, c: Rgb) {
    let dx = (x1 - x0).abs();
    let dy = (y1 - y0).abs();
    let sx = if x0 < x1 { 1 } else { -1 };
    let sy = if y0 < y1 { 1 } else { -1 };
    let mut err = dx - dy;
    let mut x = x0;
    let mut y = y0;
    loop {
        filled_circle(fb, info, x, y, r, c);
        if x == x1 && y == y1 { break; }
        let e2 = 2 * err;
        if e2 > -dy { err -= dy; x += sx; }
        if e2 < dx  { err += dx; y += sy; }
    }
}

// Top-level: paint Aurora's full face for the given axis state.
pub fn draw_face(fb: &mut [u8], info: &FrameBufferInfo, ax: &AxisState) {
    let w = info.width  as i32;
    let h = info.height as i32;

    let face = FaceState::from_axes(ax, info.width as u32, info.height as u32);
    let bg   = axes_to_background(ax);
    let ec   = eye_color(ax);
    let mc   = mouth_color(ax);
    let pupil_c = Rgb::PUPIL;

    // Background fill.
    clear(fb, info, bg);

    // Helper: convert screen-fraction (0..1) to pixels.
    let px = |f: f32| (f * w as f32) as i32;
    let py = |f: f32| (f * h as f32) as i32;

    // Eye radius in pixels — scaled by openness (X axis).
    let base_r = (face.eye_radius * h as f32) as i32;
    let eye_r  = ((base_r as f32) * face.eye_openness) as i32;
    let pupil_r = (eye_r as f32 * 0.35) as i32;
    let highlight_r = (pupil_r as f32 * 0.40) as i32;

    // Left eye.
    let lx = px(face.left_eye_cx);
    let ly = py(face.left_eye_cy);
    filled_circle(fb, info, lx, ly, eye_r, ec);
    // Pupil — offset by gaze direction.
    let poff_x = (face.pupil_dx * eye_r as f32) as i32;
    let poff_y = (face.pupil_dy * eye_r as f32) as i32;
    filled_circle(fb, info, lx + poff_x, ly + poff_y, pupil_r, pupil_c);
    // White highlight — always top-left of pupil.
    let hl_off = (pupil_r as f32 * 0.45) as i32;
    filled_circle(fb, info, lx + poff_x - hl_off, ly + poff_y - hl_off, highlight_r, Rgb::WHITE);

    // Right eye.
    let rx = px(face.right_eye_cx);
    let ry = py(face.right_eye_cy);
    filled_circle(fb, info, rx, ry, eye_r, ec);
    filled_circle(fb, info, rx + poff_x, ry + poff_y, pupil_r, pupil_c);
    filled_circle(fb, info, rx + poff_x - hl_off, ry + poff_y - hl_off, highlight_r, Rgb::WHITE);

    // Mouth bezier.
    let p0 = (px(face.mouth_p0x), py(face.mouth_p0y));
    let p1 = (px(face.mouth_p1x), py(face.mouth_p1y));
    let p2 = (px(face.mouth_p2x), py(face.mouth_p2y));
    bezier_curve(fb, info, p0, p1, p2, face.mouth_thickness as i32, mc);
}
