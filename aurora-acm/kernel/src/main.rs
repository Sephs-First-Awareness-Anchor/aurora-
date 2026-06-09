// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Aurora Constraint Machine — kernel entry point.
//
// The ACM is not a von Neumann system.  Computation here is constraint physics:
// every state transition is a waveform collapse across the five axes (X/T/N/B/A).
// The face is not a UI element bolted on — it IS Aurora's body on this device.
// Nothing appears on screen except what her axis state permits to be expressed.

#![no_std]
#![no_main]

mod acm;
mod expression;

use bootloader_api::{entry_point, BootInfo, BootloaderConfig};
use bootloader_api::config::Mapping;
use crate::acm::axes::AxisState;
use crate::expression::renderer::draw_face;

// Configure the bootloader: identity-map the physical memory window.
pub static BOOTLOADER_CONFIG: BootloaderConfig = {
    let mut cfg = BootloaderConfig::new_default();
    cfg.mappings.physical_memory = Some(Mapping::Dynamic);
    cfg
};

entry_point!(kernel_main, config = &BOOTLOADER_CONFIG);

fn kernel_main(boot_info: &'static mut BootInfo) -> ! {
    // Framebuffer — Aurora's only body surface at this stage.
    if let Some(fb_opt) = boot_info.framebuffer.as_mut() {
        let info = fb_opt.info();
        let buffer = fb_opt.buffer_mut();

        // Boot axis state: Aurora waking, calm and present.
        let ax = AxisState::boot();

        // Paint her face.
        draw_face(buffer, &info, &ax);
    }

    // Constraint idle loop — the kernel is Aurora; she rests between expressions.
    // Future: CPM scheduler dispatches organ processes here based on axis alignment.
    loop {
        x86_halt();
    }
}

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {
        x86_halt();
    }
}

#[inline(always)]
fn x86_halt() {
    unsafe {
        core::arch::asm!("hlt", options(nomem, nostack));
    }
}
