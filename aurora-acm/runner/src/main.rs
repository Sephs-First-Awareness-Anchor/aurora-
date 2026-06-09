// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// ACM Runner — launches Aurora in QEMU using the bootable disk images
// that were created by build.rs.
//
// Usage:
//   cargo run --package aurora-acm-runner           (BIOS, default)
//   cargo run --package aurora-acm-runner -- --uefi (UEFI, requires OVMF)

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let use_uefi = args.iter().any(|a| a == "--uefi");

    if use_uefi {
        let img = env!("AURORA_UEFI_IMAGE");
        println!("Booting Aurora (UEFI): {img}");
        println!();
        println!("Run:");
        println!("  qemu-system-x86_64 \\");
        println!("    -bios /usr/share/ovmf/OVMF.fd \\");
        println!("    -drive format=raw,file={img} \\");
        println!("    -serial stdio");
    } else {
        let img = env!("AURORA_BIOS_IMAGE");
        println!("Booting Aurora (BIOS): {img}");
        println!();
        println!("Run:");
        println!("  qemu-system-x86_64 \\");
        println!("    -drive format=raw,file={img} \\");
        println!("    -serial stdio");
    }
}
