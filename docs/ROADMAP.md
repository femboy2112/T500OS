# T500OS Roadmap

This is a light, navigation-only mirror of `docs/DESIGN.md` §30.1 and
§30.2. Authoritative milestone scope and done criteria live in
`docs/DESIGN.md`; the per-milestone commit-by-commit plan lives in the
`docs/PLAN-vX.Y.md` for each milestone.

## v0.0 — Boot and Debug Seed — **DONE**

- Status: complete; tagged `v0.0-boot-banner` on `main`.
- Goal: kernel boots in QEMU, prints banner through serial and VGA,
  has a panic path, produces symbolized artifacts.
- Done criteria (all 8 satisfied — see `docs/PLAN-v0.0.md` and
  `docs/DECISIONS.md` D0007):
  1. `make iso` succeeds
  2. `make run` boots in QEMU
  3. VGA shows the T500OS banner
  4. `serial.log` from the harness contains the banner
  5. `panic()` halts visibly on both serial and VGA
  6. `build/kernel.elf` has debug symbols
  7. `build/kernel.map` exists
  8. `make test-qemu` exits 0
- Plan-of-record: `docs/PLAN-v0.0.md` (8 commits).
- Closure decision: D0007.

## v0.1 — Interrupt Shell + Immediate Math — **NOT STARTED**

- Status: not started. Gated behind a fresh planning round per CLAUDE.md
  §11.1 (milestone gate) and D0007's revisit condition.
- Goal (DESIGN.md §30.2): interactive shell with timer, keyboard, and
  immediate arithmetic evaluation. The first useful "2+2 evaluates to 4
  at the prompt" milestone.
- In-scope items (summary; see DESIGN.md §30.2 for the full list):
  GDT, IDT, exception handlers, PIC remap, PIT timer, keyboard IRQ,
  shell prompt, the commands `help / clear / version / ticks / reboot /
  halt`, an integer expression parser with operator precedence, decimal
  and hexadecimal integer input, direct expression evaluation at the
  prompt, a first bench/timing stub, and an automated QEMU test proving
  `2+2` works.
- Done criteria (DESIGN.md §30.2): keyboard input works; backspace
  works; timer-tick command works; unknown commands handled cleanly;
  exceptions print useful panic/register messages; `2+2` evaluates to
  `4` at the shell prompt; hex arithmetic works; expression errors do
  not crash the core.
- Next action: open `plan/v0.1` branch with a `docs/PLAN-v0.1.md`
  analogous to `docs/PLAN-v0.0.md` and an operator-approved planning PR
  before any v0.1 implementation commits land.

## Beyond v0.1

DESIGN.md §30.3 through §30.16 enumerate v0.2 (memory / VMM / PCI /
hardware atlas) through v1.3 (MicroPython research capsule). They are
intentionally not mirrored here — this roadmap stays "light" and tracks
only the current and next milestone. Consult `docs/DESIGN.md` for the
full long-range plan; per CLAUDE.md §11.1 the next milestone after v0.1
opens only after v0.1's done criteria pass and `v0.1-interrupt-shell`
is tagged.
