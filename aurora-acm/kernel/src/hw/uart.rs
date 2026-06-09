// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// COM1 UART driver (8250/16550A) — Aurora's body-to-mind channel.

use crate::hw::port::{inb, outb};

const COM1: u16 = 0x3F8;
const IER:  u16 = COM1 + 1;
const FCR:  u16 = COM1 + 2;
const LCR:  u16 = COM1 + 3;
const MCR:  u16 = COM1 + 4;
const LSR:  u16 = COM1 + 5;

const LSR_DATA_READY: u8 = 0x01;
const LSR_TX_EMPTY:   u8 = 0x20;

pub unsafe fn init() {
    outb(IER, 0x00);
    outb(LCR, 0x80);
    outb(COM1, 0x01);
    outb(IER,  0x00);
    outb(LCR, 0x03);
    outb(FCR, 0xC7);
    outb(MCR, 0x0B);
}

#[inline]
pub unsafe fn is_data_ready() -> bool {
    inb(LSR) & LSR_DATA_READY != 0
}

#[inline]
pub unsafe fn read_byte() -> u8 {
    inb(COM1)
}

#[allow(dead_code)]
pub unsafe fn write_byte(b: u8) {
    while inb(LSR) & LSR_TX_EMPTY == 0 {}
    outb(COM1, b);
}

#[allow(dead_code)]
pub unsafe fn write_bytes(data: &[u8]) {
    for &b in data { write_byte(b); }
}
