# Aurora AOOS — build orchestration
#
# Targets:
#   make rootfs     Build Docker image and export the root filesystem
#   make kernel     Download Alpine virt kernel + initramfs
#   make initramfs  Pack Aurora rootfs as gzipped cpio initramfs
#   make iso        Assemble bootable GRUB ISO (depends on rootfs + kernel)
#   make run        Boot in QEMU with serial console
#   make clean      Remove build/

REPO_ROOT := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))/../
BUILD     := $(REPO_ROOT)aurora_os/build
ALPINE_ISO_URL := https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/x86_64/alpine-virt-3.19.1-x86_64.iso
ALPINE_ISO := $(BUILD)/alpine-virt.iso

.PHONY: all rootfs kernel initramfs iso run clean

all: iso

# ── rootfs ─────────────────────────────────────────────────────────────────────
# Build the Docker image then export its filesystem.  The context is the
# repo root so COPY instructions in the Dockerfile can reach all source files.
rootfs: $(BUILD)/.rootfs_done

$(BUILD)/.rootfs_done:
	mkdir -p $(BUILD)/rootfs
	docker build \
		--no-cache \
		-f $(REPO_ROOT)aurora_os/Dockerfile.rootfs \
		-t aurora-aoos-rootfs:latest \
		$(REPO_ROOT)
	# Export the container filesystem as a flat tarball then untar it
	docker create --name aurora-aoos-export aurora-aoos-rootfs:latest /bin/true
	docker export aurora-aoos-export | tar -x -C $(BUILD)/rootfs
	docker rm aurora-aoos-export
	touch $(BUILD)/.rootfs_done

# ── kernel ─────────────────────────────────────────────────────────────────────
# Pull the Alpine virt ISO and extract the kernel + modloop with isoinfo/7z.
# We accept either tool to keep the host requirements loose.
kernel: $(BUILD)/vmlinuz

$(BUILD)/vmlinuz: $(ALPINE_ISO)
	mkdir -p $(BUILD)/iso_extract
	# Prefer isoinfo, then 7z; fall back to xorriso (always available)
	if command -v isoinfo >/dev/null 2>&1; then \
		isoinfo -i $(ALPINE_ISO) -x /boot/vmlinuz-virt > $(BUILD)/vmlinuz; \
	elif command -v 7z >/dev/null 2>&1; then \
		7z e -o$(BUILD)/iso_extract $(ALPINE_ISO) boot/vmlinuz-virt -y; \
		cp $(BUILD)/iso_extract/vmlinuz-virt $(BUILD)/vmlinuz; \
	else \
		xorriso -indev $(ALPINE_ISO) -osirrox on \
			-extract /boot/vmlinuz-virt $(BUILD)/vmlinuz 2>/dev/null; \
	fi
	@test -s $(BUILD)/vmlinuz || (echo "ERROR: vmlinuz extraction failed" >&2; exit 1)
	@echo "Kernel: $$(wc -c < $(BUILD)/vmlinuz) bytes"

$(ALPINE_ISO):
	mkdir -p $(BUILD)
	curl -L --progress-bar -o $(ALPINE_ISO) $(ALPINE_ISO_URL)

# ── initramfs ──────────────────────────────────────────────────────────────────
# Pack the exported rootfs as a newc cpio archive compressed with gzip -9.
initramfs: $(BUILD)/aurora.initramfs

$(BUILD)/aurora.initramfs: $(BUILD)/.rootfs_done
	# Exclude /proc and /sys (virtual, kernel-managed) but keep /dev
	# because Python needs /dev/urandom before it can even start.
	# Also exclude /dev/pts (mounted separately) and /dev/shm.
	cd $(BUILD)/rootfs && \
		find . \
			-path ./proc -prune -o \
			-path ./sys -prune -o \
			-path ./dev/pts -prune -o \
			-path ./dev/shm -prune -o \
			-print \
		| cpio -o -H newc | gzip -9 > $(BUILD)/aurora.initramfs
	@echo "Initramfs: $$(wc -c < $(BUILD)/aurora.initramfs) bytes"

# ── iso ────────────────────────────────────────────────────────────────────────
iso: $(BUILD)/aurora-aoos.iso

$(BUILD)/aurora-aoos.iso: $(BUILD)/aurora.initramfs $(BUILD)/vmlinuz
	bash $(REPO_ROOT)aurora_os/build_iso.sh \
		$(BUILD)/vmlinuz \
		$(BUILD)/aurora.initramfs \
		$(REPO_ROOT)aurora_os/grub.cfg \
		$(BUILD)/aurora-aoos.iso \
		$(BUILD)/iso_stage
	@echo "ISO ready: $(BUILD)/aurora-aoos.iso"
	@ls -lh $(BUILD)/aurora-aoos.iso

# ── run ────────────────────────────────────────────────────────────────────────
run: $(BUILD)/aurora.initramfs $(BUILD)/vmlinuz
	qemu-system-x86_64 \
		-m 2048 \
		-nographic \
		-cpu Cascadelake-Server-v1 \
		-kernel $(BUILD)/vmlinuz \
		-initrd $(BUILD)/aurora.initramfs \
		-append "console=ttyS0 root=/dev/ram0 rdinit=/aurora_init.py quiet"

# ── clean ──────────────────────────────────────────────────────────────────────
clean:
	rm -rf $(BUILD)
	-docker rmi aurora-aoos-rootfs:latest 2>/dev/null || true
