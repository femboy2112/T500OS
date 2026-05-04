# T500OS v0.0 Commit Plan

Status: planning artifact only. No kernel code written yet. To be reviewed
on branch `plan/v0.0`. When approved, implementation proceeds commit-by-
commit with `make test-qemu` exiting 0 at every code-bearing commit.

## Context

CLAUDE.md and DESIGN.md define one milestone — **v0.0 Boot and Debug
Seed**. Today the repo holds only `CLAUDE.md`, `DESIGN.md`, and `README.md`.
This plan takes it to passing v0.0 done criteria in **8 small commits**.
Each non-doc commit must end with `make test-qemu` exiting 0; doc-only
commits skip the heartbeat and say so in the commit message.

## Confirmation of v0.0 doctrine (read in full)

**In scope** (CLAUDE.md §2, DESIGN.md §30.1):

- project tree, Git repo
- `Makefile`, `linker.ld`
- Multiboot2 header (`boot/multiboot2.asm`)
- kernel entry (`kernel/main.c`)
- COM1 polled serial, 38400 or 115200 8N1
- VGA text 80x25
- `printk` formatter
- `panic()` halts on serial + VGA
- classification headers in every C/ASM source
- `build/kernel.elf` with debug symbols
- `build/kernel.map`
- `build/t500os.iso` via `grub-mkrescue`
- `tools/run_qemu.sh`, `tools/test_harness.py`
- `make test-qemu` heartbeat

**Forbidden** (CLAUDE.md §2): keyboard / IRQ / IDT / GDT beyond GRUB,
PIT/timer, memory allocator, heap, PCI, disk, networking, framebuffer,
T5L evaluator, capsules, Python, SSE/FPU, hardware mutation, disk writes.

**Source header** (CLAUDE.md §5, DESIGN.md §28.5): every `.c`/`.asm`
under `kernel/` and `boot/` carries the 5-field block. v0.0 = every file
`stable_core` — no exceptions.

**Heartbeat** (CLAUDE.md §4, DESIGN.md §26A.2): `make test-qemu`. Commit
only if exit 0; doc-only commits skip and say so.

**Banner contract** (CLAUDE.md §3): the literal `T500OS v0.0` plus the
seven labelled lines and `T5L prompt pending...`. **Serial copy
byte-identical to VGA copy** where charset allows.

**Done criteria** (CLAUDE.md §2 / DESIGN.md §30.1):
1. [x] `make iso` succeeds
2. [x] `make run` boots in QEMU
3. [x] VGA shows banner
4. [x] `serial.log` from harness contains banner
5. [x] `panic()` halts visibly on both
6. [x] `build/kernel.elf` has debug symbols
7. [x] `build/kernel.map` exists
8. [x] `make test-qemu` exits 0

All eight done criteria are satisfied as of commit 7. The annotated tag
`v0.0-boot-banner` is applied on the merge commit that closes commit 7's
PR into `main`. v0.1 work is gated behind a fresh planning round per
D0007.

## Resolved doctrine-vs-repo conflicts

- **DESIGN.md path drift** — CLAUDE.md §1 / §11 and DESIGN.md §27.1
  reference `docs/DESIGN.md`, but the file lives at `DESIGN.md` in the
  repo root. Operator decision: **move** it to `docs/DESIGN.md` in
  commit 1. Logged as D0004.
- **VGA harness scope** — Operator decision: in commit 4 the harness
  uses **QMP `pmemsave 0xB8000 4000`** plus a Python attribute-byte
  stripper. No env-var / A-B switch. The harness asserts that the banner
  bytes recovered from VGA equal the banner bytes recovered from
  `serial.log` (CLAUDE.md §3 byte-identical requirement).

## The 8 commits

### Commit 1 — repo hygiene, governance docs, dev-env bootstrap (DOC-ONLY)

**Scope:** baseline files needed before any kernel code lands. No build
artifacts, no kernel sources, no harness yet.

**Files:**
- `.gitignore` (excludes `build/`, `*.o`, `*.elf`, `*.iso`, `*.map`,
  `serial-*.log`, `screen*.ppm`, `*.bin`, editor junk)
- `LICENSE` (MIT — DESIGN.md §25.9 default)
- `tools/setup.sh` — installs `build-essential nasm
  qemu-system-x86 grub-pc-bin grub-common xorriso python3`. Idempotent
  (`apt-get install -y` with `--no-install-recommends`). README adds a
  "Running in a fresh sandbox" subsection that points to it.
- `README.md` — short note: project intent in one paragraph; pointer to
  `docs/DESIGN.md`, `CLAUDE.md`, `docs/PLAN-v0.0.md`; "Run
  `bash tools/setup.sh` first in a fresh dev sandbox" instruction.
- `docs/PLAN-v0.0.md` — this file.
- `docs/DRIFT.md` — empty list with the format from DESIGN.md §27.3.
- `docs/DECISIONS.md` — seed entries:
  - D0001 GRUB/Multiboot2 boot for v0.x (DESIGN.md §10.2)
  - D0002 host gcc for v0.0 only; cross-compiler before v0.2
    (DESIGN.md §25.2)
  - D0003 MIT license (DESIGN.md §25.9)
  - D0004 `DESIGN.md` moved from repo root to `docs/DESIGN.md` to
    match CLAUDE.md §1/§11 and DESIGN.md §27.1
  - D0005 `-Werror` is v0.0-only; will be revisited when IRQ stubs land
    in v0.1 (raw register-clobbering ASM tends to trip
    `-Wunused-parameter` and friends)
- `git mv DESIGN.md docs/DESIGN.md` (no content edits to DESIGN.md)

**Heartbeat:** skipped — doc-only. Commit message:
`docs-only: skipped make test-qemu (no buildable kernel yet)`.

**Harness asserts:** N/A — harness not implemented yet.

### Commit 2a — minimal buildable kernel that halts cleanly

**Scope:** prove the build, link, ISO, and QEMU loop work. No serial,
no banner, no harness yet — `kernel_main` just halts. The point of
splitting from 2b is that this is the riskiest piece of plumbing
(linker, multiboot2 header, long-mode trampoline) and deserves an
isolated diff and bisect point.

**Files:**
- `Makefile` with targets `all`, `clean`, `iso`, `run`, `run-serial`,
  `test-qemu`, `debug` (DESIGN.md §25.3). Compile flags:
  `-ffreestanding -fno-stack-protector -fno-pic -mno-red-zone -nostdlib
  -g -O2 -Wall -Wextra -Werror`. `-Werror` carries the D0005 caveat in
  a Makefile comment.
- `linker.ld` — load at 1 MiB physical, ELF64, sections
  `.multiboot2 .text .rodata .data .bss`, `--Map=build/kernel.map`,
  no strip, debug sections retained.
- `grub/grub.cfg` — `menuentry "T500OS v0.0" { multiboot2
  /boot/kernel.elf }`.
- `boot/multiboot2.asm` — MB2 header + 32-bit entry that builds
  identity-mapped paging for the first 2 MiB, enables PAE + LME,
  loads CR3, sets CR0.PG, far-returns into 64-bit `kernel_main`.
  Carries the classification header.
- `kernel/main.c` — `void kernel_main(void) { for (;;) __asm__
  volatile("cli; hlt"); }`. Carries the classification header.
- `tools/run_qemu.sh` — `qemu-system-x86_64 -cdrom build/t500os.iso
  -display none -no-reboot -d guest_errors,int -D build/qemu.log`.
- `tools/test_harness.py` (placeholder) — runs `tools/run_qemu.sh`
  with a 5 s timeout, asserts QEMU did NOT triple-fault (no `Triple
  fault` line in `build/qemu.log`), asserts `build/kernel.elf`,
  `build/kernel.map`, `build/t500os.iso` all exist. No banner check
  yet — that lands in 2b.

**Heartbeat:** `make test-qemu` exits 0. Commit message notes the
harness is a placeholder that will gain banner assertions in 2b.

**Harness asserts:** ISO + ELF + map artifacts present; QEMU survives
5 s with no triple fault; no `guest_errors` or `int` log entries
beyond the expected pre-long-mode INT 0x10/0x13 emitted by GRUB.

### Commit 2b — COM1 serial driver, "T500OS v0.0" line, real harness assertion

**Scope:** add the smallest serial output path, print the literal
banner first line so the harness assertion required by CLAUDE.md §3
goes green. Full multi-line banner waits until commit 3.

**Files:**
- `kernel/serial.c`, `include/kernel/serial.h` — COM1 = 0x3F8,
  115200 8N1 polling: `serial_init`, `serial_putc`, `serial_puts`.
  Classification header.
- `kernel/main.c` updated — `kernel_main` calls `serial_init()` then
  `serial_puts("T500OS v0.0\n")` then halts.
- `tools/run_qemu.sh` updated — adds `-serial file:build/serial.log`.
- `tools/test_harness.py` upgraded — captures `build/serial.log`,
  asserts the literal `T500OS v0.0` is present, exits 0/1.

**Heartbeat:** `make test-qemu` exits 0.

**Harness asserts:** `build/serial.log` contains `T500OS v0.0`; QEMU
exited within timeout; no triple-fault.

### Commit 3 — `printk`, libk primitives, full multi-line banner on serial

**Scope:** add the formatter and the freestanding string primitives
required by DESIGN.md §25.5; replace ad-hoc `serial_puts` calls with
`printk`; emit the full banner.

**Files:**
- `kernel/libk/string.c`, `include/kernel/libk.h` — `memset`,
  `memcpy`, `memmove`, `memcmp`, `strlen`, `strnlen`, `strcmp`,
  `strncmp` (scalar reference, no SSE).
- `kernel/printk.c`, `include/kernel/printk.h` — tiny `vprintk`
  supporting `%c %s %d %u %x %p %%`, fixed-width and zero-pad.
  Currently routed to serial only; subsystem prefixes
  `[boot] [serial]` per DESIGN.md §28.4.
- `kernel/main.c` — emits the full 9-line banner from CLAUDE.md §3
  plus trailing `T5L prompt pending...`.
- `tools/test_harness.py` extended to assert `Target: Lenovo
  ThinkPad T500`, `Boot: Multiboot2 via GRUB`, `Panic path: active`,
  `T5L prompt pending`.

**Heartbeat:** `make test-qemu` exits 0.

**Harness asserts:** all banner lines present in
`build/serial.log` in the order specified.

### Commit 4 — VGA text driver, banner mirrored, byte-identical harness check

**Scope:** add VGA 80x25 text driver and tee `printk` to both serial
and VGA. Harness verifies the VGA framebuffer and asserts the banner
bytes match the serial bytes (CLAUDE.md §3 byte-identical rule).

**Files:**
- `kernel/vga.c`, `include/kernel/vga.h` — `vga_init` clears
  0xB8000, `vga_putc` with newline + scroll, `vga_puts`, default
  attribute light-gray-on-black. Classification header.
- `kernel/printk.c` updated — each char writes through both
  `serial_putc` and `vga_putc`. Order: serial first (DESIGN.md
  §11.3 serial-first principle).
- `kernel/main.c` — calls `vga_init` after `serial_init` and
  before banner printing.
- `tools/run_qemu.sh` — adds `-qmp unix:build/qmp.sock,server,nowait`
  in addition to existing serial capture.
- `tools/test_harness.py` — after banner detected on serial, opens
  the QMP socket, issues `pmemsave` of 0x4000 bytes from 0xB8000 to
  `build/vgafb.bin`. New helper `vga_strip_attrs(bytes) -> str`
  reads every other byte (the character cell, 0x00 → space) and
  trims trailing whitespace per row. Asserts the cleaned VGA
  banner block equals the corresponding banner block extracted
  from `build/serial.log`. Byte-by-byte equality, not "contains".

**Heartbeat:** `make test-qemu` exits 0.

**Harness asserts:** all prior + VGA framebuffer banner bytes
equal serial banner bytes after VGA-attribute strip.

### Commit 5 — `panic()` path on serial + VGA, panic-test build flag

**Scope:** add the panic surface and prove it actually halts
visibly on both. Build-time gate `T500_PANIC_TEST` triggers a
deterministic panic right after the banner so the harness can
verify the halt block without altering normal-boot behavior.

**Files:**
- `kernel/panic.c`, `include/kernel/panic.h` —
  `__attribute__((noreturn)) panic(stage, msg)` prints the
  `KERNEL PANIC` block from DESIGN.md §10.5 to both sinks, then
  `cli; hlt; jmp .`.
- `kernel/main.c` — `#ifdef T500_PANIC_TEST` calls
  `panic("boot.test", "panic-test build")` after the banner.
- `Makefile` — `make test-panic` builds with `-DT500_PANIC_TEST`
  into separate artifacts (`build/kernel-panic.elf`,
  `build/t500os-panic.iso`) and runs the harness in panic mode.
- `tools/test_harness.py` — `--mode {boot,panic}`. Panic mode
  asserts `KERNEL PANIC:`, the stage string, the message string,
  and that no banner lines appear after the panic block.

**Heartbeat:** `make test-qemu` exits 0; `make test-panic` exits 0.

**Harness asserts:** boot mode unchanged (no `KERNEL PANIC` text);
panic mode shows the expected halt block on both serial and VGA.

### Commit 6 — artifact hardening, pre-commit hook, debug-symbol verification

**Scope:** close the remaining done-criteria assertions in code so
they cannot regress silently.

**Files:**
- `Makefile` — confirms `-g` flows through to `kernel.elf` (no
  strip step anywhere); explicit `--Map=build/kernel.map` to `ld`.
- `tools/test_harness.py` — `check_artifacts()`: `build/kernel.elf`
  exists, `readelf -S` shows `.debug_info`; `build/kernel.map`
  non-empty; `build/t500os.iso` present.
- `.githooks/pre-commit` — runs **`make test-qemu` only**. Reason
  documented inline: `make test-panic` builds a separate artifact
  set with a different feature flag and is owned by `make
  test-regression` once that exists; making every commit pay for
  it would slow the agent loop without catching new regressions
  beyond what `test-qemu` already catches. `test-panic` will
  return to the hook only when v0.1 introduces real exception
  handlers that share code paths with `panic()`.
- `Makefile` — `make hooks-install` sets
  `core.hooksPath=.githooks` (idempotent).
- `docs/DECISIONS.md` — D0006 records the host gcc version
  actually used (was D0005 in earlier draft; renumbered because
  D0005 is now `-Werror` policy).

**Heartbeat:** `make test-qemu` exits 0; `make test-panic` exits 0
(run manually); pre-commit hook runs `make test-qemu`.

**Harness asserts:** all prior + ELF debug section present + map
non-empty + ISO present.

### Commit 7 — declare v0.0 done and tag (DOC-ONLY)

**Scope:** mark milestone complete, check the done-criteria boxes,
annotate-tag.

**Files:**
- `docs/PLAN-v0.0.md` updated to checked completion list.
- `docs/DECISIONS.md` D0007 records v0.0 closure and explicitly
  notes v0.1 is gated until next planning round.
- `docs/ROADMAP.md` (light) mirrors DESIGN.md §30.1/§30.2:
  v0.0 done, v0.1 not started.
- annotated tag `v0.0-boot-banner` on this commit.

**Heartbeat:** re-run `make test-qemu` and `make test-panic` once
before tagging; the doc commit itself is doc-only.

**Harness asserts:** prior commit's assertions still pass.

## Critical files in the eventual implementation

- `Makefile` — drives every heartbeat; `-Werror` here per D0005
- `linker.ld` — load address, debug-section retention, map output
- `boot/multiboot2.asm` — only path into long mode in v0.0
- `kernel/main.c` — banner string, ordering, panic-test hook
- `kernel/serial.c` — must be up before anything else prints
- `kernel/vga.c` — second output sink; byte-identical with serial
- `kernel/printk.c` — formatter shared by banner and panic
- `kernel/panic.c` — last-line-of-defense halt path
- `tools/test_harness.py` — encodes the done criteria in code,
  including QMP `pmemsave` VGA verification
- `tools/setup.sh` — fresh-sandbox dev-env bootstrap

## Verification (end-to-end)

After commit 7:

1. `git checkout v0.0-boot-banner`
2. `bash tools/setup.sh` (only on a fresh sandbox)
3. `make clean && make iso` → zero errors, `build/t500os.iso` exists
4. `make test-qemu` → exit 0; full banner on serial; VGA framebuffer
   bytes match serial bytes
5. `make test-panic` → exit 0; `KERNEL PANIC:` block on both sinks
6. `make run` → human visually confirms VGA banner in QEMU window
7. `readelf -S build/kernel.elf | grep debug_info` → non-empty
8. `[ -s build/kernel.map ]` → true
9. `git tag --list 'v0.0-boot-banner'` → present
10. Stop. v0.1 only after a fresh planning round.
