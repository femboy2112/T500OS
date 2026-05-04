# DECISIONS.md — Architectural Decision Ledger

Format from DESIGN.md §27.2. Decisions are append-only; revisits add a
new entry that supersedes the prior one.

---

## D0001 — Bootloader: GRUB / Multiboot2 for v0.x

- **Topic:** Bootloader
- **Decision:** Use GRUB with a Multiboot2 header for v0.0 through v0.4.
- **Reason:** Avoids bootloader complexity until the kernel itself is
  useful. GRUB hands us a known long-mode-capable entry environment, a
  memory map, and an ISO build path (via `grub-mkrescue`). Building a
  custom bootloader before the kernel can read disk sectors and a
  filesystem would block all higher-priority bring-up work.
- **Rejected alternatives:**
  - Custom MBR bootloader from day one — too much yak-shaving for v0.0.
  - UEFI-only boot — the target hardware (ThinkPad T500 2056BZ1) is
    legacy BIOS; UEFI is out of scope for this machine.
- **Revisit condition:** After shell, disk read, FAT32 read-only, and
  hardware atlas milestones (DESIGN.md §10.2 "post-v0.4").
- **Status:** Accepted

## D0002 — Toolchain: host gcc for v0.0 only; cross-compiler before v0.2

- **Topic:** Toolchain
- **Decision:** v0.0 may be built with the host `gcc`, provided strict
  freestanding flags are used (`-ffreestanding -fno-stack-protector
  -fno-pic -mno-red-zone -nostdlib`). A reproducible
  `x86_64-elf-gcc` cross-toolchain (`tools/build_cross.sh`) must exist
  before v0.2 grows complex.
- **Reason:** Eliminates a pre-requisite before the first kernel boots.
  A cross-toolchain detour at v0.0 buys nothing measurable: the host
  `gcc` produces correct ELF64 output under the freestanding flag set,
  and `-Wno-builtin-*` plus our own `kernel/libk` covers the
  compiler-emitted memcpy/memset references called out in DESIGN.md
  §25.5.
- **Rejected alternatives:**
  - Cross-compiler now — delays v0.0 with no proportional safety win.
  - Host gcc forever — reproducibility risk grows once the kernel
    surface widens (DESIGN.md §25.2).
- **Revisit condition:** Before v0.2 (memory / VMM / PCI work) lands.
- **Status:** Accepted

## D0003 — License: MIT

- **Topic:** License
- **Decision:** Adopt the MIT license for the repository.
- **Reason:** DESIGN.md §25.9 names MIT or BSD-style as the
  recommended personal-project default. MIT keeps reuse flexibility and
  avoids GPL-import accounting until external code is actually
  imported.
- **Rejected alternatives:**
  - BSD-2/BSD-3 — equivalent intent, slightly less recognized.
  - GPL — adds compliance bookkeeping the project does not yet need;
    DESIGN.md §25.9 requires a decision-ledger entry before any GPL
    component is imported.
  - Unlicensed — leaves downstream reuse ambiguous.
- **Revisit condition:** Before importing any non-MIT/BSD-compatible
  external source.
- **Status:** Accepted

## D0004 — DESIGN.md location: moved to docs/DESIGN.md

- **Topic:** Documentation layout
- **Decision:** Move `DESIGN.md` from the repository root to
  `docs/DESIGN.md` to match CLAUDE.md §1 / §11 references and the
  `docs/` inventory listed in DESIGN.md §27.1. No content edits to
  DESIGN.md itself.
- **Reason:** CLAUDE.md §11.11 (Agent governance rule) requires that
  stale references be reported and resolved rather than silently fixed.
  Two clean resolutions existed: move the file, or amend CLAUDE.md and
  DESIGN.md §27.1. The operator chose to move the file because it
  matches DESIGN.md's own layout claim and avoids touching either
  governance document's text.
- **Rejected alternatives:**
  - Leave at root and patch CLAUDE.md / DESIGN.md §27.1.
  - Symlink `docs/DESIGN.md → ../DESIGN.md`. Symlinks behave
    inconsistently across Git on Windows checkouts and would surprise
    a future contributor.
- **Revisit condition:** None expected.
- **Status:** Accepted

## D0005 — Build flag: -Werror is v0.0-only

- **Topic:** Build flags
- **Decision:** Compile v0.0 kernel objects with `-Werror`. The flag
  will be revisited (and likely relaxed for specific files) when v0.1
  introduces IRQ stubs and exception handlers.
- **Reason:** v0.0 has zero IRQ paths and zero hand-written register
  shuffling. Under those conditions `-Werror` is cheap insurance
  against silent regressions in a tiny C surface. v0.1 will introduce
  ISR shims and inline-asm clobber lists that historically trip
  `-Wunused-parameter`, `-Wunused-but-set-variable`, and structure-
  layout warnings in ways that genuinely should not block boot
  bring-up. Promoting these to errors at that point would push the
  project toward suppressing real warnings to ship.
- **Rejected alternatives:**
  - Skip `-Werror` from the start. Loses cheap regression protection
    in the period when it costs nothing.
  - Keep `-Werror` forever. Will eventually conflict with low-level
    code that legitimately needs warning-tolerant builds; better to
    revisit explicitly than to bypass with `-Wno-*` flags later.
- **Revisit condition:** First v0.1 commit that introduces an IRQ stub
  or exception handler.
- **Status:** Accepted (v0.0 only)

## D0006 — Host gcc version used for v0.0

- **Topic:** Toolchain (record)
- **Decision:** v0.0 was built and tested with the following host
  toolchain on the development sandbox:

  ```
  gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
  ```

  This is the version observed at commit 6 (artifact hardening) — the
  first commit at which the harness gates the debug-symbol contract
  in code via `check_artifacts()`. The freestanding flag set from D0002
  (`-ffreestanding -fno-stack-protector -fno-pic -mno-red-zone -nostdlib`,
  plus `-mno-mmx -mno-sse -mno-sse2 -mno-80387 -nostdinc -fno-builtin
  -fno-asynchronous-unwind-tables` in the actual Makefile) is what makes
  this host compiler acceptable for v0.0 per D0002 / DESIGN.md §25.2.
- **Reason:** CLAUDE.md §6 requires that the host gcc version used for
  v0.0 be documented in `docs/DECISIONS.md`. Recording the exact
  version string lets a future contributor reproduce the v0.0 boot
  artifact bit-for-similarly even before `tools/build_cross.sh` lands,
  and gives D0002's revisit condition ("before v0.2") a concrete
  baseline to compare against.
- **Rejected alternatives:**
  - Record only the major version ("gcc 13"). Loses the patch-level
    information that matters when chasing a miscompile.
  - Pin via Docker image now. The cross-compiler (D0002 revisit) is the
    correct place to add reproducibility infrastructure; doing it here
    would conflate "record what was used" with "guarantee what will be
    used."
- **Revisit condition:** Re-record at every milestone tag (v0.0,
  v0.1, ...) until `tools/build_cross.sh` (D0002) replaces the host
  gcc as the supported build toolchain.
- **Status:** Accepted (v0.0 record)

---

_Future entries: D0007 (v0.0 closure note, commit 7)._
