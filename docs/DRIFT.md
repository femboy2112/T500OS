# DRIFT.md — Deferred Ideas

Anti-drift catch basin (CLAUDE.md §7 rule 2, DESIGN.md §27.3).

If a feature sounds exciting but is not in the current milestone's
in-scope list, it lands here instead of in code. This file is the
opposite of a TODO — it is the place ideas go to wait safely.

## Format

Each entry uses this shape:

```
Idea:           <one-line description>
Tempted at:     <milestone or commit>
Status:         deferred
Reason:         <why not now>
Revisit after:  <concrete prerequisite>
```

## Entries

```
Idea:           RWX LOAD segment from current linker.ld
Tempted at:     v0.0 commit 2a (initial Makefile + linker.ld)
Status:         deferred
Reason:         The single LOAD segment in v0.0 holds .multiboot2,
                .text, .rodata, .data, and .bss together with RWX
                permissions. ld emits a warning ("LOAD segment with
                RWX permissions"). Splitting into separate R-X / RW-
                / R-- segments is wasted effort until paging is owned
                by a real VMM that can apply per-page NX / write
                bits; v0.0 runs identity-mapped from the boot
                trampoline with no permission enforcement at all.
Revisit after:  v0.2 brings up the VMM with per-page permission
                bits. Section separation in linker.ld lands in the
                same change so the ELF segment layout matches the
                page-table permission policy.
```
