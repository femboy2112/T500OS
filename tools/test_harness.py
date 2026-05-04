#!/usr/bin/env python3
# T500OS test harness — commit 2b.
#
# Per docs/PLAN-v0.0.md commit 2b: this revision boots the ISO under QEMU
# with COM1 captured to build/serial.log and asserts that the literal
# string "T500OS v0.0" is present in the captured serial output. Build
# artifacts are still verified to exist; full multi-line banner / VGA /
# panic checks are added in commits 3, 4, and 5 respectively.
#
# Exit code: 0 on success, 1 on failure. CLAUDE.md §4 / DESIGN.md §26A.2
# heartbeat: `make test-qemu` must exit 0 before any commit lands.

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
KERNEL_ELF = BUILD_DIR / "kernel.elf"
KERNEL_MAP = BUILD_DIR / "kernel.map"
ISO = BUILD_DIR / "t500os.iso"
QEMU_LOG = BUILD_DIR / "qemu.log"
SERIAL_LOG = BUILD_DIR / "serial.log"

QEMU_TIMEOUT_SECONDS = 5

# Banner contract (CLAUDE.md §3): the literal first line of the boot
# banner. Commit 2b only checks for this prefix; commit 3 will assert the
# full multi-line banner once printk lands.
BANNER_LITERAL = "T500OS v0.0"

# QEMU's -d int log spams INT lines for legitimate BIOS / GRUB activity
# (real-mode INT 0x10 video, INT 0x13 disk). Those are not errors; do
# not fail on them. A real triple-fault prints the line below verbatim.
TRIPLE_FAULT_MARKERS = (
    "Triple fault",
    "triple fault",
    "RESET",
)


def fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"[harness] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"[harness] {msg}")


def check_artifacts() -> None:
    for path in (KERNEL_ELF, KERNEL_MAP, ISO):
        if not path.is_file():
            fail(f"missing artifact: {path.relative_to(ROOT)}")
        if path.stat().st_size == 0:
            fail(f"empty artifact: {path.relative_to(ROOT)}")
    info(f"artifacts present: {KERNEL_ELF.name}, {KERNEL_MAP.name}, {ISO.name}")


def run_qemu() -> None:
    qemu = shutil.which(os.environ.get("QEMU", "qemu-system-x86_64"))
    if qemu is None:
        fail("qemu-system-x86_64 not found on PATH")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    for stale in (QEMU_LOG, SERIAL_LOG):
        if stale.exists():
            stale.unlink()

    cmd = [
        qemu,
        "-cdrom", str(ISO),
        "-display", "none",
        "-no-reboot",
        "-serial", f"file:{SERIAL_LOG}",
        "-d", "guest_errors",
        "-D", str(QEMU_LOG),
    ]
    info("launching QEMU: " + " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            timeout=QEMU_TIMEOUT_SECONDS,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.TimeoutExpired:
        # Expected: kernel halts in `cli; hlt; jmp .` and never exits on
        # its own. The timeout means we got far enough to halt cleanly;
        # subprocess.run kills the child and waits, which closes QEMU's
        # serial.log fd so the banner bytes are flushed.
        info(f"QEMU still running after {QEMU_TIMEOUT_SECONDS}s; treating "
             f"as clean halt (kernel_main spins on cli;hlt)")
    else:
        info(f"QEMU exited with status {result.returncode}")
        if result.returncode != 0:
            sys.stderr.write(result.stderr.decode(errors="replace"))
            fail(f"QEMU exited non-zero ({result.returncode})")


def check_qemu_log() -> None:
    if not QEMU_LOG.is_file():
        info("no qemu.log produced; -d guest_errors stayed quiet (good)")
        return
    text = QEMU_LOG.read_text(errors="replace")
    for marker in TRIPLE_FAULT_MARKERS:
        if marker in text:
            sys.stderr.write(text)
            fail(f"triple-fault marker in qemu.log: {marker!r}")
    info(f"qemu.log clean ({QEMU_LOG.stat().st_size} bytes)")


def check_serial_log() -> None:
    if not SERIAL_LOG.is_file():
        fail(f"missing serial capture: {SERIAL_LOG.relative_to(ROOT)}")
    raw = SERIAL_LOG.read_bytes()
    if not raw:
        fail(f"empty serial capture: {SERIAL_LOG.relative_to(ROOT)}")
    text = raw.decode("ascii", errors="replace")
    if BANNER_LITERAL not in text:
        sys.stderr.write("--- serial.log (decoded) ---\n")
        sys.stderr.write(text)
        sys.stderr.write("\n--- end serial.log ---\n")
        fail(f"banner literal {BANNER_LITERAL!r} not found in serial.log")
    info(f"serial.log contains banner literal {BANNER_LITERAL!r} "
         f"({len(raw)} bytes captured)")


def main() -> int:
    check_artifacts()
    run_qemu()
    check_qemu_log()
    check_serial_log()
    info("OK (commit 2b — banner first line asserted on serial)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
