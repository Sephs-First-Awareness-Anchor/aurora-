// Authors: Sunni (Sir) Morningstar & Cael Devo
// Raw x86 I/O port access — outb/inb.

use core::arch::asm;

#[inline]
pub unsafe fn outb(port: u16, val: u8) {
    asm!("out dx, al", in("dx") port, in("al") val, options(nomem, nostack, preserves_flags));
}

#[inline]
pub unsafe fn inb(port: u16) -> u8 {
    let val: u8;
    asm!("in al, dx", out("al") val, in("dx") port, options(nomem, nostack, preserves_flags));
    val
}

// Short I/O wait — write to port 0x80 (POST diagnostic port, always safe).
#[inline]
pub unsafe fn io_wait() {
    outb(0x80, 0);
}
