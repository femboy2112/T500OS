# T500OS

Hardware-targeted, optimized, math- and research-based hobby OS for the
Lenovo ThinkPad T500 2056BZ1.

T500OS is a ground-up 64-bit kernel — not a Linux/BSD/Unix derivative.
Long-term identity: a terminal-first math/research workstation built
around a native research language (T5L). Current milestone: **v0.0
Boot and Debug Seed**.

## Project documents

- [`CLAUDE.md`](CLAUDE.md) — root agent instruction file. Read first.
- [`docs/DESIGN.md`](docs/DESIGN.md) — full design doctrine
  (T500OS Project Design Document v0.2).
- [`docs/PLAN-v0.0.md`](docs/PLAN-v0.0.md) — eight-commit plan from
  empty repo to passing v0.0 done criteria.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — architectural decision
  ledger (D0001+).
- [`docs/DRIFT.md`](docs/DRIFT.md) — deferred ideas; the anti-drift
  catch basin.

## Running in a fresh sandbox

Before the first `make iso`, install the host build/test packages:

```sh
bash tools/setup.sh
```

This installs `build-essential`, `nasm`, `qemu-system-x86`,
`grub-pc-bin`, `grub-common`, `xorriso`, and `python3`. The script is
idempotent and is **not** invoked from any Makefile target — running
it requires sudo and would surprise an operator on a long-lived
machine.
