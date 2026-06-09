// Authors: Sunni (Sir) Morningstar & Cael Devo
// 8253/8254 PIT — channel 0, mode 3, set to `hz` interrupts per second.

use super::port::outb;

const PIT_CH0:  u16 = 0x40;
const PIT_CMD:  u16 = 0x43;
const PIT_MODE: u8  = 0x36; // ch0 | lobyte/hibyte | mode3 | binary
const PIT_BASE: u32 = 1_193_182;

pub unsafe fn set_hz(hz: u32) {
    let divisor = ((PIT_BASE + hz / 2) / hz) as u16;
    outb(PIT_CMD, PIT_MODE);
    outb(PIT_CH0, (divisor & 0xFF) as u8);
    outb(PIT_CH0, (divisor >> 8) as u8);
}
