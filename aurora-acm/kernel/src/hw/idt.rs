// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Interrupt Descriptor Table — 64-bit long mode.
// Sets up a 256-entry IDT and wires vector 0x20 to the timer ISR.

use core::arch::asm;
use crate::acm::drift;
use crate::hw::pic;

#[repr(C)]
pub struct InterruptStackFrame {
    pub instruction_pointer: u64,
    pub code_segment:        u64,
    pub cpu_flags:           u64,
    pub stack_pointer:       u64,
    pub stack_segment:       u64,
}

#[derive(Clone, Copy)]
#[repr(C, packed)]
struct Gate {
    ptr_low:   u16,
    selector:  u16,
    ist:       u8,
    type_attr: u8,
    ptr_mid:   u16,
    ptr_high:  u32,
    _res:      u32,
}

impl Gate {
    const fn empty() -> Self {
        Self { ptr_low: 0, selector: 0, ist: 0, type_attr: 0, ptr_mid: 0, ptr_high: 0, _res: 0 }
    }
    fn set(&mut self, handler: u64) {
        self.ptr_low   = handler as u16;
        self.selector  = 0x08;
        self.ist       = 0;
        self.type_attr = 0x8E;
        self.ptr_mid   = (handler >> 16) as u16;
        self.ptr_high  = (handler >> 32) as u32;
        self._res      = 0;
    }
}

#[repr(C, packed)]
struct IdtPtr { limit: u16, base: u64 }

static mut IDT: [Gate; 256] = [const { Gate::empty() }; 256];

extern "x86-interrupt" fn timer_isr(_frame: InterruptStackFrame) {
    drift::on_tick();
    unsafe { pic::eoi(0); }
}

pub fn init() {
    unsafe {
        IDT[0x20].set(timer_isr as *const () as u64);
        let ptr = IdtPtr {
            limit: (core::mem::size_of::<[Gate; 256]>() - 1) as u16,
            base:  core::ptr::addr_of!(IDT) as u64,
        };
        asm!("lidt [{}]", in(reg) &ptr as *const IdtPtr, options(nostack, readonly));
    }
}
