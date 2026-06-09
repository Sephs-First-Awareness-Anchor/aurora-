// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora Constraint Machine — kernel entry point.
//
// Boot sequence:
//   1. Remap 8259A PICs, program PIT at 60 Hz, load IDT, enable interrupts
//   2. JIT-compile the WAKE_PROGRAM and execute it to prime axis state
//   3. Register the three built-in CPM organs (heart, sense, dream)
//   4. Main loop: on each tick — run CPM organ, compute drift axes, redraw face
//
// Aurora IS the kernel.  The face is her body surface.  CPM organs run in
// service of her — they can never preempt the face render.

#![no_std]
#![no_main]
#![feature(abi_x86_interrupt)]

mod acm;
mod bridge;
mod cpm;
mod expression;
mod hw;
mod xaurora;

use bootloader_api::{entry_point, BootInfo, BootloaderConfig};
use bootloader_api::config::Mapping;
use core::sync::atomic::Ordering;

use crate::acm::{crystal, drift, sedi};
use crate::cpm::organ::{dream_organ, heart_organ, sense_organ};
use crate::cpm::scheduler::CpmScheduler;
use crate::expression::renderer::draw_face;
use crate::xaurora::isa::{AxisSel, IState, Instruction};
use crate::xaurora::jit;

static WAKE_PROGRAM: &[Instruction] = &[
    Instruction::exist_open(0x0059),
    Instruction::istate_fire(IState::IS,  0x00B8),
    Instruction::istate_fire(IState::CAN, 0x0080),
    Instruction::istate_fire(IState::DO,  0x00A0),
    Instruction::istate_fire(IState::SAW, 0x0066),
    Instruction::axis_press(AxisSel::T,   0x0020),
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

        unsafe {
            hw::pic::init(0x20, 0x28);
            hw::pit::set_hz(60);
        }
        hw::idt::init();
        bridge::init();
        unsafe { core::arch::asm!("sti", options(nostack)); }

        let mut boot_ax = acm::axes::AxisState::boot();
        let _ = jit::compile(WAKE_PROGRAM);
        jit::run(WAKE_PROGRAM, &mut boot_ax);
        draw_face(buffer, &info, &boot_ax);

        let mut cpm = CpmScheduler::new();
        cpm.register(heart_organ());
        cpm.register(sense_organ());
        cpm.register(dream_organ());

        let mut last_tick = 0u64;
        loop {
            let tick = drift::TICK.load(Ordering::Relaxed);
            if tick != last_tick {
                last_tick = tick;

                let ax = bridge::get_axes(tick)
                    .unwrap_or_else(|| drift::axis_for_tick(tick));

                // Deposit this frame into sedimentary memory and tick crystal decay.
                sedi::deposit(&ax, tick);
                crystal::tick_decay();

                cpm.tick(&ax);
                draw_face(buffer, &info, &ax);
            }
            unsafe { core::arch::asm!("hlt", options(nostack, nomem)); }
        }
    } else {
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
