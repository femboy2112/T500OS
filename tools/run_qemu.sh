#!/usr/bin/env bash
# T500OS QEMU launcher used by tools/test_harness.py and `make run`-ish
# targets that want a single canonical command line.
#
# Commit 2a scope: no banner yet, no serial assertion. We boot the ISO
# headless, log guest_errors and interrupt activity to build/qemu.log,
# and rely on -no-reboot so a triple-fault leaves QEMU exited (rather
# than rebooting forever) and the harness can detect it.
#
# `make run` and `make run-serial` invoke QEMU directly with their own
# flags; this script exists for the harness and for ad-hoc reruns.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
ISO="${BUILD_DIR}/t500os.iso"

if [[ ! -f "${ISO}" ]]; then
    echo "[run_qemu] missing ${ISO}; run 'make iso' first" >&2
    exit 1
fi

QEMU="${QEMU:-qemu-system-x86_64}"

exec "${QEMU}" \
    -cdrom "${ISO}" \
    -display none \
    -no-reboot \
    -serial "file:${BUILD_DIR}/serial.log" \
    -d guest_errors,int \
    -D "${BUILD_DIR}/qemu.log" \
    "$@"
