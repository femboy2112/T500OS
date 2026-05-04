# CLAUDE.md — T500OS Agent Instruction File

This is the root agent instruction file for Claude Code (and any other coding
agent) working on T500OS. Read this in full at the start of every session.
It compresses the doctrine in `docs/DESIGN.md` into rules that govern what
you may and may not do right now.

If `docs/DESIGN.md` and this file conflict, this file wins for execution
decisions; raise the conflict to the operator before changing either.

---

## 1. What T500OS is

A ground-up 64-bit hobby operating system for one specific machine: a Lenovo
ThinkPad T500 2056BZ1 (Core 2 Duo T9400, ~1.86 GiB RAM, BIOS boot, Intel
82567LM Ethernet, ICH9 ATA). It is not a Linux/BSD/Unix clone. Its long-term
identity is a terminal-first math/research workstation with a native research
language called T5L.

Stability/risk layers (replaces the userspace/kernelspace distinction):

```
Layer 0  Boot and hardware bring-up
Layer 1  Stable core            <- must be boring and hard to break
Layer 2  Trusted research modules
Layer 3  Restartable research capsules
Layer 4  Foreign compatibility layer (future MicroPython lives here)
Layer 5  Network boundary       <- hostile input
```

---

## 2. Current milestone

**Milestone: v0.0 — Boot and Debug Seed**

Goal: kernel boots in QEMU, prints banner to serial and VGA, has a panic path,
and produces symbolized artifacts.

### In scope for v0.0

- project tree and Git repo
- `Makefile`, `linker.ld`
- Multiboot2 header (`boot/multiboot2.asm`)
- kernel entry (`kernel/main.c`)
- serial output (COM1, polling, 38400 or 115200 baud, 8N1)
- VGA text output (80x25)
- `printk` formatter
- `panic()` that halts with message on both serial and VGA
- classification headers in every source file
- `build/kernel.elf` with debug symbols
- `build/kernel.map` linker map
- `build/t500os.iso` via `grub-mkrescue`
- `tools/run_qemu.sh` and a `tools/test_harness.py` stub
- `make test-qemu` target that boots in QEMU, captures serial, asserts banner

### Forbidden in v0.0 (goes in `docs/DRIFT.md` if tempting)

- keyboard / IRQ / IDT / GDT beyond what GRUB leaves behind
- PIT, timer, ticks
- physical or virtual memory allocator
- heap
- PCI
- disk / ATA / FAT32
- networking
- framebuffer / VESA
- T5L evaluator (math eval)
- capsules
- Python anything
- SSE / FPU code

These belong to v0.1+ and must not appear in v0.0 commits.

### Done criteria for v0.0

- `make iso` succeeds
- `make run` boots in QEMU
- VGA shows the T500OS banner
- `serial.log` captured by harness contains the banner
- `panic()` halts visibly with a message on serial + VGA
- `build/kernel.elf` exists with debug symbols
- `build/kernel.map` exists
- `make test-qemu` exits 0

When all done criteria pass, tag `v0.0-boot-banner` and stop. Do not
volunteer to start v0.1 in the same session.

---

## 3. Required boot banner format

```
T500OS v0.0
Target: Lenovo ThinkPad T500
Mode: x86_64 long mode
Boot: Multiboot2 via GRUB
Serial: active
Display: VGA text
Panic path: active
Memory map: initializing

T5L prompt pending...
```

The serial copy must be byte-identical to the VGA copy where the character
set allows. The harness asserts on the literal string `T500OS v0.0`.

---

## 4. Agent heartbeat (mandatory)

Every implementation task ends with:

```
make test-qemu
```

Commit only if it exits 0. If it fails, fix or revert before the session
ends. Do not leave the tree in a state where `make test-qemu` fails.

The harness must fail on:

- missing boot banner on serial
- missing serial output entirely
- unexpected panic during boot
- changed output without updated expectation

Documentation-only changes may skip the heartbeat but must say so in the
commit message.

---

## 5. Required source header

Every C and ASM file in `kernel/` and `boot/` must begin with:

```c
/*
 * T500OS Component: <name>
 * Classification:   <stable_core | trusted_research_module |
 *                    restartable_research_capsule |
 *                    foreign_compatibility_layer | network_boundary>
 * Failure policy:   <one line — what happens on bug or invariant violation>
 * Owns:             <data structures or hardware regions this file owns>
 * Mutates hardware: <no | yes via surgery-mode call path>
 */
```

For v0.0, every file is `stable_core`. No exceptions. If you feel a file
should not be `stable_core`, that means it doesn't belong in v0.0.

---

## 6. Build and toolchain rules

- Host compiler is acceptable for v0.0 only, with strict freestanding flags.
- A cross-compiler (`x86_64-elf-gcc`) plan must exist before v0.2; for v0.0
  document the host gcc version used in `docs/DECISIONS.md`.
- Required compile flags for kernel objects:
  `-ffreestanding -fno-stack-protector -fno-pic -mno-red-zone -nostdlib`
  plus `-mgeneral-regs-only` for any code reachable from interrupts (not
  applicable yet in v0.0 since there are no IRQs, but set the precedent).
- No libc. If GCC emits a call to `memcpy` or `memset`, provide them in
  `kernel/libk/` rather than linking libc, or add `-fno-builtin-memcpy` etc.
- No floating point or SSE/XMM in any code path. v0.0 is integer-only.
- No dynamic allocation. There is no allocator yet.
- No recursion in kernel code.
- Explicit integer widths (`uint32_t`, `uint64_t`); avoid `int` and `long`
  for hardware-facing values.
- Build outputs go under `build/`. Nothing in `build/` is committed.

---

## 6A. Sandbox bootstrap

Run `bash tools/setup.sh` before the first `make` in any fresh session.
Do not `apt-get` individual packages — `tools/setup.sh` is the single
canonical list of host build/test dependencies (build-essential, nasm,
qemu-system-x86, grub-pc-bin, grub-common, xorriso, python3). Installing
ad hoc subsets bit-rots the dependency list and produces sessions that
silently differ from the documented one. If a needed package is missing
from `tools/setup.sh`, add it there in the same commit that needs it.

---

## 7. Anti-drift rules (hard)

1. **Milestone gate:** do not begin v0.1 work until v0.0 done criteria pass
   and a `v0.0-boot-banner` tag exists.
2. **Temptation rule:** if you want to add something not in section 2's
   "in scope" list, write it into `docs/DRIFT.md` and stop.
3. **Hardware rule:** features that don't help the T500 target are deferred.
4. **Borrowed-architecture rule:** do not copy Linux/BSD/Windows/POSIX/Unix
   structures by habit. Borrowing requires a `docs/DECISIONS.md` entry
   citing performance, simplicity, correctness, debugging, or hostile-input
   handling as the reason.
5. **No-userspace rule:** do not introduce user/kernel terminology. Use the
   stability/risk-layer vocabulary.
6. **No false security claims:** never describe T500OS as sandboxed,
   secure, hardened, or malware-resistant. Local code is trusted; network
   input is hostile. That's it.
7. **Disk write rule:** there is no disk write code in v0.0 and none until
   v0.3 with `-DALLOW_WRITE` plus a runtime write-enable command. Do not
   write to any disk image, host disk, or block device.
8. **Python rule:** no Python interpreter, no Python translation, no
   NumPy/SciPy claims. Python-family work is gated behind a stable capsule
   model and stable T5L benchmark core (v1.3 at earliest).
9. **Compiler rule:** no T5L bytecode or native compiler in v0.x. The
   evaluator is permanent; the compiler is deferred.
10. **Surgery rule:** no hardware mutation paths in v0.0. Read-only only,
    and there isn't even a shell to read from yet.
11. **Agent governance rule:** if `CLAUDE.md`, the milestone target, or
    `make test-qemu` are missing or stale, stop and report rather than
    making implementation edits.

---

## 8. Task shape (how to receive work)

**Correct task shape:**

- "Implement serial COM1 init and `serial_putc`. Prove the banner appears
  in the harness's captured `serial.log`."
- "Implement `panic(msg)` that halts on both serial and VGA. Add a
  panic-test mode and prove the harness sees the panic string."
- "Add `make test-qemu` target and Python harness stub that asserts the
  banner string is in the captured serial."

**Incorrect task shape:**

- "Implement v0.0." (too broad — break it into the items above)
- "Build the OS." (no)
- "Add networking / a shell / interrupts." (forbidden in v0.0)

If the operator gives you a task that crosses the v0.0 boundary, push back
and propose a smaller task that fits the milestone.

---

## 9. Repository conventions

- Git from the first commit. One commit per working increment.
- Tag milestones: `v0.0-boot-banner`, `v0.1-interrupt-shell`, ...
- Commit design changes (this file, `docs/DESIGN.md`) separately from code.
- `.githooks/pre-commit` runs `make test-qemu`.
- New architectural decisions go in `docs/DECISIONS.md` with ID, topic,
  decision, reason, rejected alternatives, revisit condition, status.
- New deferred ideas go in `docs/DRIFT.md`.
- Subsystem log lines use bracketed prefixes: `[boot]`, `[serial]`, `[vga]`,
  `[panic]`.

---

## 10. Out-of-band signals to the operator

When you encounter any of the following, stop editing and report:

- a task that requires crossing the v0.0 boundary
- a tool or library you'd like to import (license, scope, capsule placement)
- a build flag that would change correctness, not just performance
- any case where the design doc and this file conflict
- any temptation to silence a failing test rather than fix the cause
- any case where you would otherwise add user/kernel terminology, sandbox
  claims, or hidden background services

Reporting is cheap. Drift is expensive.

---

## 11. Reference

Full doctrine: `docs/DESIGN.md` (T500OS Project Design Document v0.2).
Sections most relevant to v0.0: 9 (architecture), 10 (boot), 11 (debug),
14 (console), 25 (build), 26 (testing), 26A (agent workflow), 28 (coding
standards), 29 (anti-drift), 30.1 (v0.0 milestone), 33 (next artifacts).

End of CLAUDE.md.
