#!/usr/bin/env bash
# build_iso.sh — assemble the Aurora AOOS bootable ISO
#
# Usage: build_iso.sh <vmlinuz> <initramfs> <grub.cfg> <out.iso> <stage_dir>
#
# grub-mkrescue expects an input directory tree laid out as:
#   stage/boot/grub/grub.cfg
#   stage/boot/vmlinuz
#   stage/boot/aurora.initramfs

set -euo pipefail

VMLINUZ="$1"
INITRAMFS="$2"
GRUB_CFG="$3"
OUT_ISO="$4"
STAGE="$5"

echo "[build_iso] Creating ISO stage at ${STAGE}"
rm -rf "${STAGE}"
mkdir -p "${STAGE}/boot/grub"

cp "${VMLINUZ}"   "${STAGE}/boot/vmlinuz"
cp "${INITRAMFS}" "${STAGE}/boot/aurora.initramfs"
cp "${GRUB_CFG}"  "${STAGE}/boot/grub/grub.cfg"

echo "[build_iso] Running grub-mkrescue..."
grub-mkrescue -o "${OUT_ISO}" "${STAGE}" -- -volid AURORA_AOOS 2>&1

echo "[build_iso] ISO assembled: ${OUT_ISO}"
ls -lh "${OUT_ISO}"
