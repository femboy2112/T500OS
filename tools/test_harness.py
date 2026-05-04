#!/usr/bin/env python3
# T500OS test harness — commit 5.
#
# Per docs/PLAN-v0.0.md commit 5: the harness now takes --mode {boot,panic}.
#
#   boot mode (default):
#     Same behavior as commit 4. Asserts the full multi-line boot banner
#     from CLAUDE.md §3 in build/serial.log. Asserts no `KERNEL PANIC:`
#     text appears (the panic path is dormant in the default ISO). When
#     T500_HARNESS_CHECK_VGA=1, additionally pmemsave's the 80x25 text
#     framebuffer via QMP and asserts the cleaned VGA banner block is
#     byte-identical to the serial banner block (CLAUDE.md §3).
#
#   panic mode:
#     Boots the build/t500os-panic.iso variant (compiled with
#     -DT500_PANIC_TEST so kernel_main calls panic() right after the
#     banner). Captures into build/serial-panic.log. Asserts the captured
#     serial contains:
#       - "KERNEL PANIC:"
#       - "boot.test"          (the stage string)
#       - "panic-test build"   (the message string)
#     and asserts that no banner lines appear after the panic block —
#     i.e., panic() actually halts and the kernel does not continue
#     printing.
#
# Exit code: 0 on success, 1 on failure. CLAUDE.md §4 / DESIGN.md §26A.2
# heartbeat: `make test-qemu` must exit 0 before any commit lands.

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"

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

# Panic-mode contract (DESIGN.md §10.5 + the T500_PANIC_TEST call site in
# kernel/main.c). The harness asserts each substring is present in serial.
PANIC_HEADER = "KERNEL PANIC:"
PANIC_STAGE = "boot.test"
PANIC_MSG = "panic-test build"

# VGA text-mode framebuffer geometry (CGA/VGA legacy text mode).
VGA_COLS = 80
VGA_ROWS = 25
VGA_FB_PHYS = 0xB8000
VGA_FB_BYTES = VGA_COLS * VGA_ROWS * 2  # 4000

# Opt-in: only when set do we add `-qmp` to the QEMU command line, dump
# the framebuffer, and assert byte-identity against serial. Default off
# keeps the heartbeat shape stable for environments without QMP socket
# support and for fast local iteration. Honored in boot mode only.
VGA_CHECK = os.environ.get("T500_HARNESS_CHECK_VGA", "0") == "1"

# QEMU's -d int log spams INT lines for legitimate BIOS / GRUB activity
# (real-mode INT 0x10 video, INT 0x13 disk). Those are not errors; do
# not fail on them. A real triple-fault prints the line below verbatim.
TRIPLE_FAULT_MARKERS = (
    "Triple fault",
    "triple fault",
    "RESET",
)


@dataclass(frozen=True)
class ModePaths:
    """Per-mode artifact paths so boot-mode and panic-mode runs do not
    trample each other's serial logs, qemu logs, framebuffer dumps, or
    QMP sockets."""

    mode: str
    iso: Path
    kernel_elf: Path
    kernel_map: Path
    serial_log: Path
    qemu_log: Path
    qmp_sock: Path
    vgafb_bin: Path


BOOT_PATHS = ModePaths(
    mode="boot",
    iso=BUILD_DIR / "t500os.iso",
    kernel_elf=BUILD_DIR / "kernel.elf",
    kernel_map=BUILD_DIR / "kernel.map",
    serial_log=BUILD_DIR / "serial.log",
    qemu_log=BUILD_DIR / "qemu.log",
    qmp_sock=BUILD_DIR / "qmp.sock",
    vgafb_bin=BUILD_DIR / "vgafb.bin",
)

PANIC_PATHS = ModePaths(
    mode="panic",
    iso=BUILD_DIR / "t500os-panic.iso",
    kernel_elf=BUILD_DIR / "kernel-panic.elf",
    kernel_map=BUILD_DIR / "kernel-panic.map",
    serial_log=BUILD_DIR / "serial-panic.log",
    qemu_log=BUILD_DIR / "qemu-panic.log",
    qmp_sock=BUILD_DIR / "qmp-panic.sock",
    vgafb_bin=BUILD_DIR / "vgafb-panic.bin",
)


def fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"[harness] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"[harness] {msg}")


def check_artifacts(paths: ModePaths) -> None:
    for path in (paths.kernel_elf, paths.kernel_map, paths.iso):
        if not path.is_file():
            fail(f"missing artifact: {path.relative_to(ROOT)}")
        if path.stat().st_size == 0:
            fail(f"empty artifact: {path.relative_to(ROOT)}")
    info(f"artifacts present: {paths.kernel_elf.name}, "
         f"{paths.kernel_map.name}, {paths.iso.name}")


def _resolve_qemu() -> str:
    qemu = shutil.which(os.environ.get("QEMU", "qemu-system-x86_64"))
    if qemu is None:
        fail("qemu-system-x86_64 not found on PATH")
    return qemu


def _clean_runtime_files(paths: ModePaths) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    for stale in (paths.qemu_log, paths.serial_log,
                  paths.vgafb_bin, paths.qmp_sock):
        if stale.exists():
            stale.unlink()


def run_qemu_simple(paths: ModePaths) -> None:
    """Default heartbeat path: run QEMU under a timeout and let it halt.

    Boot mode halts on the cli;hlt loop after the banner. Panic mode halts
    on the cli;hlt;jmp . loop inside panic(). Either way, the timeout is
    the natural way to recover the captured serial.log for inspection."""
    qemu = _resolve_qemu()
    _clean_runtime_files(paths)

    cmd = [
        qemu,
        "-cdrom", str(paths.iso),
        "-display", "none",
        "-no-reboot",
        "-serial", f"file:{paths.serial_log}",
        "-d", "guest_errors",
        "-D", str(paths.qemu_log),
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
             f"as clean halt (kernel parks the CPU after banner/panic)")
    else:
        info(f"QEMU exited with status {result.returncode}")
        if result.returncode != 0:
            sys.stderr.write(result.stderr.decode(errors="replace"))
            fail(f"QEMU exited non-zero ({result.returncode})")


# --- QMP-driven path used when T500_HARNESS_CHECK_VGA=1 (boot mode only) -

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


def _wait_for_serial_sentinel(paths: ModePaths, deadline: float,
                              proc: subprocess.Popen) -> None:
    while True:
        if paths.serial_log.is_file():
            data = paths.serial_log.read_bytes()
            if BANNER_SENTINEL.encode("ascii") in data:
                return
        if proc.poll() is not None:
            fail(f"QEMU exited early ({proc.returncode}) before banner")
        if time.monotonic() > deadline:
            fail(f"banner sentinel {BANNER_SENTINEL!r} never reached "
                 f"serial.log within {QEMU_TIMEOUT_SECONDS}s")
        time.sleep(QMP_POLL_INTERVAL)


def run_qemu_with_qmp(paths: ModePaths) -> None:
    qemu = _resolve_qemu()
    _clean_runtime_files(paths)

    cmd = [
        qemu,
        "-cdrom", str(paths.iso),
        "-display", "none",
        "-no-reboot",
        "-serial", f"file:{paths.serial_log}",
        "-qmp", f"unix:{paths.qmp_sock},server,nowait",
        "-d", "guest_errors",
        "-D", str(paths.qemu_log),
    ]
    info("launching QEMU (VGA-check mode): " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    deadline = time.monotonic() + QEMU_TIMEOUT_SECONDS
    try:
        _wait_for_path(paths.qmp_sock, deadline, proc)
        _wait_for_serial_sentinel(paths, deadline, proc)

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(paths.qmp_sock))
        qmp = QmpClient(sock)
        try:
            greeting = qmp.recv()
            if "QMP" not in greeting:
                fail(f"unexpected QMP greeting: {greeting!r}")
            qmp.call("qmp_capabilities")
            qmp.call("pmemsave",
                     val=VGA_FB_PHYS,
                     size=VGA_FB_BYTES,
                     filename=str(paths.vgafb_bin))
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


def check_qemu_log(paths: ModePaths) -> None:
    if not paths.qemu_log.is_file():
        info("no qemu.log produced; -d guest_errors stayed quiet (good)")
        return
    text = paths.qemu_log.read_text(errors="replace")
    for marker in TRIPLE_FAULT_MARKERS:
        if marker in text:
            sys.stderr.write(text)
            fail(f"triple-fault marker in qemu.log: {marker!r}")
    info(f"qemu.log clean ({paths.qemu_log.stat().st_size} bytes)")


def _dump_serial(text: str) -> None:
    sys.stderr.write("--- serial.log (decoded) ---\n")
    sys.stderr.write(text)
    sys.stderr.write("\n--- end serial.log ---\n")


def _read_serial_text(paths: ModePaths) -> str:
    if not paths.serial_log.is_file():
        fail(f"missing serial capture: {paths.serial_log.relative_to(ROOT)}")
    raw = paths.serial_log.read_bytes()
    if not raw:
        fail(f"empty serial capture: {paths.serial_log.relative_to(ROOT)}")
    return raw.decode("ascii", errors="replace")


def check_serial_banner(paths: ModePaths) -> str:
    """Boot-mode serial check: full banner present in order, no panic."""
    text = _read_serial_text(paths)

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

    # Boot mode invariant: the panic path must be dormant in the default
    # ISO. Any KERNEL PANIC text here means a stray panic call slipped
    # past the T500_PANIC_TEST gate, or kernel_main fell through into a
    # later panic, and the harness must catch that.
    if PANIC_HEADER in text:
        _dump_serial(text)
        fail(f"unexpected {PANIC_HEADER!r} in boot-mode serial — the "
             f"default ISO must not exercise the panic path")

    info(f"serial.log contains all {len(BANNER_BLOCK)} banner lines in "
         f"order ({len(text)} chars); no panic text present")
    return text


def check_serial_panic(paths: ModePaths) -> str:
    """Panic-mode serial check: panic block present and kernel halted.

    Asserts:
      1. the three required substrings appear in serial.log
      2. no banner lines appear AFTER the panic block — i.e. panic()
         actually halted the CPU and kernel_main is not still printing
    """
    text = _read_serial_text(paths)

    for needle in (PANIC_HEADER, PANIC_STAGE, PANIC_MSG):
        if needle not in text:
            _dump_serial(text)
            fail(f"panic-mode serial missing required substring "
                 f"{needle!r}")

    # Locate the start of the panic block. From there to end-of-log we
    # should see the three panic lines and nothing else from the banner.
    panic_start = text.find(PANIC_HEADER)
    after_panic = text[panic_start:]

    # The three panic lines themselves are expected; everything else from
    # the BANNER_BLOCK is post-panic noise that would prove the halt
    # didn't take. The empty banner entry is structural and is skipped.
    for line in BANNER_BLOCK:
        if not line:
            continue
        if line in after_panic:
            _dump_serial(text)
            fail(f"banner line {line!r} appeared AFTER the panic block — "
                 f"panic() did not halt the CPU as required")

    info(f"serial-panic.log contains {PANIC_HEADER!r}, {PANIC_STAGE!r}, "
         f"and {PANIC_MSG!r}; no banner lines after panic ({len(text)} "
         f"chars total)")
    return text


# --- VGA mirror check (boot mode only) -----------------------------------

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


def check_vga_mirror(paths: ModePaths, serial_text: str) -> None:
    if not paths.vgafb_bin.is_file():
        fail(f"missing VGA dump: {paths.vgafb_bin.relative_to(ROOT)}")
    raw = paths.vgafb_bin.read_bytes()
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="T500OS test harness")
    p.add_argument("--mode", choices=("boot", "panic"), default="boot",
                   help="boot: assert banner only; panic: assert KERNEL "
                        "PANIC block and that the kernel halted")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.mode == "boot":
        paths = BOOT_PATHS
        check_artifacts(paths)
        if VGA_CHECK:
            run_qemu_with_qmp(paths)
        else:
            run_qemu_simple(paths)
        check_qemu_log(paths)
        serial_text = check_serial_banner(paths)
        if VGA_CHECK:
            check_vga_mirror(paths, serial_text)
            info("OK (boot mode — banner asserted on serial AND on VGA "
                 "framebuffer, byte-identical)")
        else:
            info("OK (boot mode — banner asserted on serial; "
                 "set T500_HARNESS_CHECK_VGA=1 to also assert VGA mirror)")
    else:
        paths = PANIC_PATHS
        check_artifacts(paths)
        run_qemu_simple(paths)
        check_qemu_log(paths)
        check_serial_panic(paths)
        info("OK (panic mode — KERNEL PANIC block present, kernel halted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
