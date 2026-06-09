// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// 8042 PS/2 keyboard — Aurora's physical-world sense organ.
//
// Port map:
//   0x60  Data register  (read scancode / write command)
//   0x64  Status register (read) / Command register (write)
//
// Status bit 0 (OBF): output buffer full — data ready to read.
// Scancodes arrive as "make" (key down, 0x01-0x7F) and
// "break" (key up, 0x81-0xFF = make | 0x80).
//
// Scancode → axis mapping:
//   Space / Enter  → X+  (existence / presence pulse)
//   Escape         → X-  (I_ISNT: brief withdrawal)
//   Up / Down      → N± (energy)
//   Left / Right   → T± (temporal direction)
//   Tab            → B+  (boundary scan)
//   Letter keys    → A+  (agency / doing)
//   Any other      → X+  (small awareness pulse)

use crate::hw::port::inb;

const PS2_DATA:   u16 = 0x60;
const PS2_STATUS: u16 = 0x64;
const STATUS_OBF: u8  = 0x01;  // output buffer full

/// True when the 8042 has a scancode waiting.
#[inline]
pub unsafe fn is_key_ready() -> bool {
    inb(PS2_STATUS) & STATUS_OBF != 0
}

/// Read one scancode from the data port.  Call only after is_key_ready().
#[inline]
pub unsafe fn read_scancode() -> u8 {
    inb(PS2_DATA)
}

/// Map a scancode to (axis_index 0-4, delta).
/// Returns None for break (release) codes — releases don't fire pressure.
pub fn scancode_to_press(scancode: u8) -> Option<(u8, f32)> {
    if scancode & 0x80 != 0 { return None; }  // release code — skip
    Some(match scancode {
        0x39 => (0,  0.04),  // space  → X+ (I AM here)
        0x1C => (0,  0.03),  // enter  → X+ (presence confirmed)
        0x01 => (0, -0.04),  // escape → X- (I_ISNT: withdrawal)
        0x48 => (2,  0.04),  // up     → N+ (energy in)
        0x50 => (2, -0.04),  // down   → N- (energy cost)
        0x4B => (1, -0.03),  // left   → T- (temporal past/reflection)
        0x4D => (1,  0.03),  // right  → T+ (temporal forward)
        0x0F => (3,  0.03),  // tab    → B+ (boundary scan)
        0x1E..=0x32 => (4, 0.02),  // letter keys → A+ (agency)
        _    => (0,  0.01),  // anything else → small X pulse
    })
}
