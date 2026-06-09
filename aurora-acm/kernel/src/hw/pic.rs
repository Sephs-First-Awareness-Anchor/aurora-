// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// 8259A Programmable Interrupt Controller — dual-PIC cascade init.
// Remaps IRQ0-7  → vectors 0x20-0x27
//        IRQ8-15 → vectors 0x28-0x2F
// so they don't collide with CPU exception vectors 0x00-0x1F.

use super::port::{inb, io_wait, outb};

const PIC1_CMD:  u16 = 0x20;
const PIC1_DATA: u16 = 0x21;
const PIC2_CMD:  u16 = 0xA0;
const PIC2_DATA: u16 = 0xA1;

const ICW1_INIT: u8 = 0x10;
const ICW1_ICW4: u8 = 0x01;
const ICW4_8086: u8 = 0x01;

/// Initialise both PICs with the given vector offsets and unmask IRQ0 (timer).
pub unsafe fn init(offset1: u8, offset2: u8) {
    let m1 = inb(PIC1_DATA);
    let m2 = inb(PIC2_DATA);

    outb(PIC1_CMD, ICW1_INIT | ICW1_ICW4); io_wait();
    outb(PIC2_CMD, ICW1_INIT | ICW1_ICW4); io_wait();
    outb(PIC1_DATA, offset1); io_wait();
    outb(PIC2_DATA, offset2); io_wait();
    outb(PIC1_DATA, 0x04); io_wait();
    outb(PIC2_DATA, 0x02); io_wait();
    outb(PIC1_DATA, ICW4_8086); io_wait();
    outb(PIC2_DATA, ICW4_8086); io_wait();

    outb(PIC1_DATA, m1 & 0xFE); // unmask IRQ0 (timer)
    outb(PIC2_DATA, m2);
}

/// Send End-Of-Interrupt.
pub unsafe fn eoi(irq: u8) {
    if irq >= 8 { outb(PIC2_CMD, 0x20); }
    outb(PIC1_CMD, 0x20);
}
