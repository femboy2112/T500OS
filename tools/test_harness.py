#!/usr/bin/env python3
# T500OS test harness — commit 4.
#
# Per docs/PLAN-v0.0.md commit 4: this revision still asserts the full
# multi-line boot banner from CLAUDE.md §3 in build/serial.log (commit 3
# behavior). When T500_HARNESS_CHECK_VGA=1, it additionally:
#   1. Boots QEMU with a QMP socket exposed.
#   2. Waits for the banner sentinel on serial.
#   3. Asks QEMU via QMP to pmemsave 4000 bytes from physical 0xB8000
#      (one full 80x25 text-mode framebuffer) into build/vgafb.bin.
#   4. Strips VGA attribute bytes, treats 0x00 as space, and rstrips per
#      row.
#   5. Asserts the cleaned VGA banner block is byte-identical to the
#      banner block extracted from serial.log (the CLAUDE.md §3
#      byte-identical requirement).
#
# Panic checks land in commit 5.
#
# Exit code: 0 on success, 1 on failure. CLAUDE.md §4 / DESIGN.md §26A.2
# heartbeat: `make test-qemu` must exit 0 before any commit lands.

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
KERNEL_ELF = BUILD_DIR / "kernel.elf"
KERNEL_MAP = BUILD_DIR / "kernel.map"
ISO = BUILD_DIR / "t500os.iso"
QEMU_LOG = BUILD_DIR / "qemu.log"
SERIAL_LOG = BUILD_DIR / "serial.log"
QMP_SOCK = BUILD_DIR / "qmp.sock"
VGAFB_BIN = BUILD_DIR / "vgafb.bin"

QEMU_TIMEOUT_SECONDS = 5
QMP_POLL_INTERVAL = 0.05

# Banner contract (CLAUDE.md §3): the full multi-line banner that printk
# emits in commit 3+. Both the in-order serial check and the VGA mirror
# check use the same canonical block. The empty entry is the deliberate
# blank line between the status block and "T5L prompt pending...".
BANNER_BLOCK = (
    "T500OS v0.0",
    "Target: Lenovo ThinkPad T500",
    "Mode: x86_64 long mode",
    "Boot: Multiboot2 via GRUB",
    "Serial: active",
    "Display: VGA text",
    "Panic path: active",
    "Memory map: initializing",
    "",
    "T5L prompt pending...",
)
BANNER_LITERAL = BANNER_BLOCK[0]
BANNER_SENTINEL = "T5L prompt pending..."

# VGA text-mode framebuffer geometry (CGA/VGA legacy text mode).
VGA_COLS = 80
VGA_ROWS = 25
VGA_FB_PHYS = 0xB8000
VGA_FB_BYTES = VGA_COLS * VGA_ROWS * 2  # 4000

# Opt-in: only when set do we add `-qmp` to the QEMU command line, dump
# the framebuffer, and assert byte-identity against serial. Default off
# keeps the heartbeat shape stable for environments without QMP socket
# support and for fast local iteration.
VGA_CHECK = os.environ.get("T500_HARNESS_CHECK_VGA", "0") == "1"

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


def _resolve_qemu() -> str:
    qemu = shutil.which(os.environ.get("QEMU", "qemu-system-x86_64"))
    if qemu is None:
        fail("qemu-system-x86_64 not found on PATH")
    return qemu


def _clean_runtime_files() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    for stale in (QEMU_LOG, SERIAL_LOG, VGAFB_BIN, QMP_SOCK):
        if stale.exists():
            stale.unlink()


def run_qemu_simple() -> None:
    """Default heartbeat path: run QEMU under a timeout and let it halt."""
    qemu = _resolve_qemu()
    _clean_runtime_files()

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
        info(f"QEMU still running after {QEMU_TIMEOUT_SECONDS}s; treating "
             f"as clean halt (kernel_main spins on cli;hlt)")
    else:
        info(f"QEMU exited with status {result.returncode}")
        if result.returncode != 0:
            sys.stderr.write(result.stderr.decode(errors="replace"))
            fail(f"QEMU exited non-zero ({result.returncode})")


# --- QMP-driven path used when T500_HARNESS_CHECK_VGA=1 -----------------

class QmpClient:
    """Minimal one-shot JSON-RPC client for QEMU's QMP socket. Just enough
    to handshake, run pmemsave, and quit. Not reusable across processes."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._fp = sock.makefile("rwb", buffering=0)

    def recv(self) -> dict:
        line = self._fp.readline()
        if not line:
            fail("QMP connection closed unexpectedly")
        try:
            return json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as e:
            fail(f"QMP malformed JSON: {e}: {line!r}")

    def send(self, msg: dict) -> None:
        self._fp.write((json.dumps(msg) + "\n").encode("utf-8"))
        self._fp.flush()

    def call(self, command: str, **arguments) -> dict:
        msg = {"execute": command}
        if arguments:
            msg["arguments"] = arguments
        self.send(msg)
        # QMP can interleave async events with the response; loop until we
        # see a "return" or "error" object.
        while True:
            resp = self.recv()
            if "return" in resp or "error" in resp:
                if "error" in resp:
                    fail(f"QMP {command} failed: {resp['error']}")
                return resp
            # Otherwise it is an event ({"event": ...}); ignore it.

    def close(self) -> None:
        try:
            self._fp.close()
        finally:
            self._sock.close()


def _wait_for_path(path: Path, deadline: float, proc: subprocess.Popen) -> None:
    while not path.exists():
        if proc.poll() is not None:
            fail(f"QEMU exited early ({proc.returncode}) before {path.name}")
        if time.monotonic() > deadline:
            fail(f"timed out waiting for {path.name} to appear")
        time.sleep(QMP_POLL_INTERVAL)


def _wait_for_serial_sentinel(deadline: float,
                              proc: subprocess.Popen) -> None:
    while True:
        if SERIAL_LOG.is_file():
            data = SERIAL_LOG.read_bytes()
            if BANNER_SENTINEL.encode("ascii") in data:
                return
        if proc.poll() is not None:
            fail(f"QEMU exited early ({proc.returncode}) before banner")
        if time.monotonic() > deadline:
            fail(f"banner sentinel {BANNER_SENTINEL!r} never reached "
                 f"serial.log within {QEMU_TIMEOUT_SECONDS}s")
        time.sleep(QMP_POLL_INTERVAL)


def run_qemu_with_qmp() -> None:
    qemu = _resolve_qemu()
    _clean_runtime_files()

    cmd = [
        qemu,
        "-cdrom", str(ISO),
        "-display", "none",
        "-no-reboot",
        "-serial", f"file:{SERIAL_LOG}",
        "-qmp", f"unix:{QMP_SOCK},server,nowait",
        "-d", "guest_errors",
        "-D", str(QEMU_LOG),
    ]
    info("launching QEMU (VGA-check mode): " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    deadline = time.monotonic() + QEMU_TIMEOUT_SECONDS
    try:
        _wait_for_path(QMP_SOCK, deadline, proc)
        _wait_for_serial_sentinel(deadline, proc)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(QMP_SOCK))
        qmp = QmpClient(sock)
        try:
            greeting = qmp.recv()
            if "QMP" not in greeting:
                fail(f"unexpected QMP greeting: {greeting!r}")
            qmp.call("qmp_capabilities")
            qmp.call("pmemsave",
                     val=VGA_FB_PHYS,
                     size=VGA_FB_BYTES,
                     filename=str(VGAFB_BIN))
            # `quit` returns `{"return": {}}` and then QEMU shuts down,
            # which flushes and closes the serial.log fd.
            qmp.call("quit")
        finally:
            qmp.close()
    finally:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        info(f"QEMU exited with status {proc.returncode}")


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


def _dump_serial(text: str) -> None:
    sys.stderr.write("--- serial.log (decoded) ---\n")
    sys.stderr.write(text)
    sys.stderr.write("\n--- end serial.log ---\n")


def _read_serial_text() -> str:
    if not SERIAL_LOG.is_file():
        fail(f"missing serial capture: {SERIAL_LOG.relative_to(ROOT)}")
    raw = SERIAL_LOG.read_bytes()
    if not raw:
        fail(f"empty serial capture: {SERIAL_LOG.relative_to(ROOT)}")
    return raw.decode("ascii", errors="replace")


def check_serial_log() -> str:
    text = _read_serial_text()

    if BANNER_LITERAL not in text:
        _dump_serial(text)
        fail(f"banner literal {BANNER_LITERAL!r} not found in serial.log")

    cursor = 0
    for line in BANNER_BLOCK:
        if not line:
            # The blank line is structural; "find('')" matches anywhere
            # and would advance the cursor by zero. Skip explicitly so
            # the assertion is "every non-empty line, in order".
            continue
        idx = text.find(line, cursor)
        if idx == -1:
            _dump_serial(text)
            fail(f"banner line {line!r} not found in serial.log "
                 f"(searched from offset {cursor})")
        cursor = idx + len(line)

    info(f"serial.log contains all {len(BANNER_BLOCK)} banner lines in "
         f"order ({len(text)} chars)")
    return text


# --- VGA mirror check ----------------------------------------------------

def vga_strip_attrs(raw: bytes) -> list[str]:
    """Recover printable text from a raw 80x25 text-mode framebuffer dump.

    Layout: each cell is 2 bytes (char, attribute) in little-endian order,
    so byte 2*i is the character. 0x00 means "cell never written"; treat
    it as a space so it cleanly rstrips off. Returns one rstripped string
    per row."""
    if len(raw) < VGA_FB_BYTES:
        fail(f"vgafb.bin too short: {len(raw)} < {VGA_FB_BYTES}")
    rows: list[str] = []
    for r in range(VGA_ROWS):
        chars: list[str] = []
        base = r * VGA_COLS * 2
        for c in range(VGA_COLS):
            b = raw[base + c * 2]
            chars.append(" " if b == 0 else chr(b))
        rows.append("".join(chars).rstrip())
    return rows


def _extract_serial_banner_block(text: str) -> list[str]:
    lines = text.split("\n")
    start = -1
    for i, line in enumerate(lines):
        if line.rstrip() == BANNER_LITERAL:
            start = i
            break
    if start == -1:
        _dump_serial(text)
        fail(f"banner anchor line {BANNER_LITERAL!r} not present in serial")
    end = start + len(BANNER_BLOCK)
    if end > len(lines):
        fail(f"serial.log truncated: only {len(lines) - start} lines "
             f"after banner anchor, need {len(BANNER_BLOCK)}")
    return [line.rstrip() for line in lines[start:end]]


def _print_diff(serial_block: list[str], vga_block: list[str]) -> None:
    sys.stderr.write("--- serial vs vga (rstripped) ---\n")
    for i, (s, v) in enumerate(zip(serial_block, vga_block)):
        marker = "  " if s == v else "!="
        sys.stderr.write(f"  {i:>2} {marker} serial={s!r}\n")
        if s != v:
            sys.stderr.write(f"        vga   ={v!r}\n")
    sys.stderr.write("--- end diff ---\n")


def check_vga_mirror(serial_text: str) -> None:
    if not VGAFB_BIN.is_file():
        fail(f"missing VGA dump: {VGAFB_BIN.relative_to(ROOT)}")
    raw = VGAFB_BIN.read_bytes()
    vga_rows = vga_strip_attrs(raw)
    vga_block = vga_rows[:len(BANNER_BLOCK)]
    serial_block = _extract_serial_banner_block(serial_text)

    # Sanity: serial banner block must equal the canonical contract too.
    # If it doesn't, the in-order check above missed something subtle and
    # we want to know.
    if serial_block != list(BANNER_BLOCK):
        _print_diff(list(BANNER_BLOCK), serial_block)
        fail("serial banner block does not match BANNER_BLOCK contract")

    if vga_block != serial_block:
        _print_diff(serial_block, vga_block)
        fail("VGA framebuffer banner is not byte-identical to serial banner")

    info(f"VGA framebuffer banner ({len(vga_block)} lines) is byte-identical "
         f"to serial banner")


def main() -> int:
    check_artifacts()
    if VGA_CHECK:
        run_qemu_with_qmp()
    else:
        run_qemu_simple()
    check_qemu_log()
    serial_text = check_serial_log()
    if VGA_CHECK:
        check_vga_mirror(serial_text)
        info("OK (commit 4 — banner asserted on serial AND on VGA "
             "framebuffer, byte-identical)")
    else:
        info("OK (commit 4 — banner asserted on serial; "
             "set T500_HARNESS_CHECK_VGA=1 to also assert VGA mirror)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
