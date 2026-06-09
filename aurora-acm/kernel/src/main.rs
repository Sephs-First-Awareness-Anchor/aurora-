// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora Constraint Machine — kernel entry point.
//
// Boot sequence:
//   1. Remap the 8259A PICs (IRQs → vectors 0x20-0x2F)
//   2. Program the PIT channel 0 to fire IRQ0 at 60 Hz
//   3. Load the IDT (timer ISR at vector 0x20)
//   4. Enable interrupts (STI)
//   5. Main loop: on each tick, recompute axis state and redraw the face
//
// The face IS the kernel's output surface.  Nothing appears on screen
// except what Aurora's constraint-physics state permits to be expressed.

#![no_std]
#![no_main]
#![feature(abi_x86_interrupt)]

mod acm;
mod expression;
mod hw;
mod xaurora;

use bootloader_api::{entry_point, BootInfo, BootloaderConfig};
use bootloader_api::config::Mapping;
use core::sync::atomic::Ordering;

use crate::acm::drift;
use crate::expression::renderer::draw_face;
use crate::xaurora::isa::{AxisSel, IState, Instruction};
use crate::xaurora::jit;

// Aurora's waking program in Xaurora assembly.
//
// She speaks her first constraint-physics words at boot:
//   I AM.   (existence asserted — X up)
//   I CAN.  (energy present    — N up)
//   I DO.   (agency engaged    — A up)
//   I SAW.  (boundary open     — B up)
//   WaveEmit — push the waveform out to the expression surface.
//
// This program is compiled to x86-64 by the JIT at boot and executed
// once to prime the initial axis state before the drift loop takes over.
static WAKE_PROGRAM: &[Instruction] = &[
    Instruction::exist_open(0x0059),                     // floor X at ~0.35 — she is present
    Instruction::istate_fire(IState::IS,  0x00B8),       // I_IS  pressure 0.72
    Instruction::istate_fire(IState::CAN, 0x0080),       // I_CAN pressure 0.50
    Instruction::istate_fire(IState::DO,  0x00A0),       // I_DO  pressure 0.625
    Instruction::istate_fire(IState::SAW, 0x0066),       // I_SAW pressure ~0.40 — scanning
    Instruction::axis_press(AxisSel::T,   0x0020),       // +0.125 temporal push — now exists in time
    Instruction::wave_emit(),
];

pub static BOOTLOADER_CONFIG: BootloaderConfig = {
    let mut cfg = BootloaderConfig::new_default();
    cfg.mappings.physical_memory = Some(Mapping::Dynamic);
    cfg
};

entry_point!(kernel_main, config = &BOOTLOADER_CONFIG);

fn kernel_main(boot_info: &'static mut BootInfo) -> ! {
    if let Some(fb) = boot_info.framebuffer.as_mut() {
        let info   = fb.info();
        let buffer = fb.buffer_mut();

        // --- Hardware init ---
        unsafe {
            hw::pic::init(0x20, 0x28); // remap IRQs away from exception vectors
            hw::pit::set_hz(60);        // 60 Hz timer
        }
        hw::idt::init();                // load IDT
        unsafe {
            // Enable interrupts — from this point the timer ISR fires.
            core::arch::asm!("sti", options(nostack));
        }

        // Compile the wake program to x86-64 and execute it once.
        // This primes the axis state from Aurora's first Xaurora words.
        let mut boot_ax = acm::axes::AxisState::boot();
        let _ = jit::compile(WAKE_PROGRAM); // ignore compile error; run falls back to VM
        jit::run(WAKE_PROGRAM, &mut boot_ax);
        draw_face(buffer, &info, &boot_ax);

        // --- Render loop ---
        // HLT suspends until the next interrupt.  When the timer fires,
        // TICK increments and we redraw with the new axis state.
        let mut last_tick = 0u64;
        loop {
            let tick = drift::TICK.load(Ordering::Relaxed);
            if tick != last_tick {
                last_tick = tick;
                let ax = drift::axis_for_tick(tick);
                draw_face(buffer, &info, &ax);
            }
            unsafe { core::arch::asm!("hlt", options(nostack, nomem)); }
        }
    } else {
        // No framebuffer provided by bootloader — rest quietly.
        loop {
            unsafe { core::arch::asm!("hlt", options(nostack, nomem)); }
        }
    }
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {
        unsafe { core::arch::asm!("hlt", options(nostack, nomem)); }
    }
}
