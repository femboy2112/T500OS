#!/usr/bin/env bash
# T500OS dev-environment bootstrap.
#
# Installs the host packages required to build and test v0.0 in QEMU:
#   - build-essential : gcc, make, ld, binutils
#   - nasm            : Multiboot2 assembly entry
#   - qemu-system-x86 : QEMU target for make run / make test-qemu
#   - grub-pc-bin     : i386-pc BIOS modules used by grub-mkrescue
#   - grub-common     : grub-mkrescue itself
#   - xorriso         : ISO 9660 image generator used by grub-mkrescue
#   - python3         : test harness (tools/test_harness.py)
#
# Idempotent: re-running is safe; apt-get will skip already-installed
# packages.
#
# Run this once on a fresh dev sandbox before the first `make iso`.
# It is NOT auto-invoked by any Makefile target — running it requires
# sudo and would surprise an operator on a long-lived machine.

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    SUDO="sudo"
else
    SUDO=""
fi

PACKAGES=(
    build-essential
    nasm
    qemu-system-x86
    grub-pc-bin
    grub-common
    xorriso
    python3
)

echo "[setup] installing host packages: ${PACKAGES[*]}"
${SUDO} apt-get update
${SUDO} apt-get install -y --no-install-recommends "${PACKAGES[@]}"

echo "[setup] done."
