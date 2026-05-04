#!/usr/bin/env bash
# T500OS QEMU launcher used by tools/test_harness.py and `make run`-ish
# targets that want a single canonical command line.
#
# Commit 4 scope: in addition to the headless / serial-log / no-reboot
# baseline, we expose a QMP control socket at build/qmp.sock so the
# harness can ask QEMU to dump the VGA text framebuffer (pmemsave on
# 0xB8000) for the byte-identical serial-vs-VGA check (CLAUDE.md §3).
# The socket uses `nowait`, so leaving it unconnected is harmless when
# `make run`-style invocations don't care about QMP.
#
# `make run` and `make run-serial` invoke QEMU directly with their own
# flags; this script exists for the harness and for ad-hoc reruns.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
ISO="${BUILD_DIR}/t500os.iso"
QMP_SOCK="${BUILD_DIR}/qmp.sock"

if [[ ! -f "${ISO}" ]]; then
    echo "[run_qemu] missing ${ISO}; run 'make iso' first" >&2
    exit 1
fi

# Stale unix-socket files block QEMU from re-binding the path.
rm -f "${QMP_SOCK}"

QEMU="${QEMU:-qemu-system-x86_64}"

exec "${QEMU}" \
    -cdrom "${ISO}" \
    -display none \
    -no-reboot \
    -serial "file:${BUILD_DIR}/serial.log" \
    -qmp "unix:${QMP_SOCK},server,nowait" \
    -d guest_errors,int \
    -D "${BUILD_DIR}/qemu.log" \
    "$@"
