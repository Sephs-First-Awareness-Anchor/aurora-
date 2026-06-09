// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Build script — locates the pre-built kernel binary, creates UEFI + BIOS
// bootable disk images using the bootloader crate, and exposes their paths
// to the runner binary via cargo:rustc-env.
//
// The kernel must be built first:
//   cargo build -p aurora-acm-kernel --target x86_64-unknown-none [--release]

use std::path::PathBuf;

fn main() {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let workspace    = manifest_dir.parent().unwrap().to_path_buf();

    // Determine build profile — match what the runner itself was built with.
    let profile = std::env::var("PROFILE").unwrap_or_else(|_| "debug".into());

    let kernel_path = workspace
        .join("target")
        .join("x86_64-unknown-none")
        .join(&profile)
        .join("aurora-acm-kernel");

    if !kernel_path.exists() {
        println!("cargo:warning=Kernel binary not found at {}", kernel_path.display());
        println!("cargo:warning=Run first: cargo build -p aurora-acm-kernel --target x86_64-unknown-none");
        println!("cargo:rustc-env=AURORA_UEFI_IMAGE=NOT_BUILT");
        println!("cargo:rustc-env=AURORA_BIOS_IMAGE=NOT_BUILT");
        println!("cargo:rerun-if-changed={}", kernel_path.display());
        return;
    }

    let uefi_path = workspace.join("aurora-uefi.img");
    bootloader::UefiBoot::new(&kernel_path)
        .create_disk_image(&uefi_path)
        .expect("failed to create UEFI disk image");

    let bios_path = workspace.join("aurora-bios.img");
    bootloader::BiosBoot::new(&kernel_path)
        .create_disk_image(&bios_path)
        .expect("failed to create BIOS disk image");

    println!("cargo:rustc-env=AURORA_UEFI_IMAGE={}", uefi_path.display());
    println!("cargo:rustc-env=AURORA_BIOS_IMAGE={}", bios_path.display());
    println!("cargo:rerun-if-changed={}", kernel_path.display());
}
