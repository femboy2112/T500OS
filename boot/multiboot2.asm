; T500OS Component: boot.multiboot2
; Classification:   stable_core
; Failure policy:   if any of these checks would fail, the CPU triple-faults
;                   before kernel_main runs; there is no recovery in v0.0.
; Owns:             Multiboot2 header, 32-bit -> 64-bit long-mode trampoline,
;                   boot stack, identity-mapped page tables for 0..2 MiB,
;                   the v0.0 64-bit GDT.
; Mutates hardware: yes (CR0/CR3/CR4, EFER, GDTR) — only on the boot path,
;                   no surgery-mode call path exists in v0.0.

; ---------------------------------------------------------------------------
; Multiboot2 header. GRUB scans the first 32 KiB of the ELF for this magic.
; The linker script puts .multiboot2 first so we land well within that
; window. Format: see Multiboot2 spec, "OS image format".
; ---------------------------------------------------------------------------

MB2_MAGIC          equ 0xE85250D6
MB2_ARCH_I386      equ 0           ; 32-bit protected mode entry
MB2_HEADER_LENGTH  equ mb2_header_end - mb2_header_start
MB2_CHECKSUM       equ -(MB2_MAGIC + MB2_ARCH_I386 + MB2_HEADER_LENGTH)

section .multiboot2
align 8
mb2_header_start:
    dd MB2_MAGIC
    dd MB2_ARCH_I386
    dd MB2_HEADER_LENGTH
    dd MB2_CHECKSUM

    ; End tag (type=0, flags=0, size=8). Required.
    align 8
    dw 0
    dw 0
    dd 8
mb2_header_end:

; ---------------------------------------------------------------------------
; Boot stack and page tables. .bss is zero-initialized by GRUB when it
; loads the ELF (memsz > filesz of the LOAD segment), so we can rely on
; the unused PML4/PDPT/PD entries being non-present (P=0).
; ---------------------------------------------------------------------------

section .bss
align 16
boot_stack_bottom:
    resb 16384
boot_stack_top:

align 4096
boot_pml4:
    resb 4096
boot_pdpt:
    resb 4096
boot_pd:
    resb 4096

; ---------------------------------------------------------------------------
; 64-bit GDT used to leave 32-bit compatibility mode and enter long mode.
; Two entries: null + 64-bit code segment. No data segment is needed in
; long mode for code that only touches DS/ES/SS as flat zero selectors.
; ---------------------------------------------------------------------------

section .rodata
align 8
gdt64:
    dq 0                                                ; null descriptor
.code_offset equ $ - gdt64
    ; P=1 (47), S=1 (44), E=1 (43), RW=1 (41), L=1 (53)
    dq (1 << 41) | (1 << 43) | (1 << 44) | (1 << 47) | (1 << 53)
.pointer:
    dw $ - gdt64 - 1
    dd gdt64                                            ; 32-bit base; loaded
                                                        ; while still in
                                                        ; protected mode

; ---------------------------------------------------------------------------
; 32-bit entry from GRUB. We are in protected mode, paging off, EAX has
; the Multiboot2 magic 0x36D76289, EBX points at the boot information
; structure. v0.0 ignores both — no consumer for them yet.
; ---------------------------------------------------------------------------

section .text
bits 32
global _start
extern kernel_main

_start:
    cli
    mov     esp, boot_stack_top

    ; PML4[0] -> PDPT
    mov     eax, boot_pdpt
    or      eax, 0x3                ; present + writable
    mov     [boot_pml4], eax

    ; PDPT[0] -> PD
    mov     eax, boot_pd
    or      eax, 0x3
    mov     [boot_pdpt], eax

    ; PD[0] -> 0x00000000 as a single 2 MiB page (PS=1, P=1, RW=1)
    mov     dword [boot_pd], 0x00000083

    ; CR3 <- PML4 physical address
    mov     eax, boot_pml4
    mov     cr3, eax

    ; Enable PAE (CR4.PAE = bit 5)
    mov     eax, cr4
    or      eax, 1 << 5
    mov     cr4, eax

    ; Set IA32_EFER.LME (bit 8) via WRMSR(0xC0000080)
    mov     ecx, 0xC0000080
    rdmsr
    or      eax, 1 << 8
    wrmsr

    ; Enable paging (CR0.PG = bit 31). After this we are in IA-32e
    ; compatibility mode; the far jump below switches to true 64-bit.
    mov     eax, cr0
    or      eax, 1 << 31
    mov     cr0, eax

    ; Load 64-bit GDT and far-jump into the 64-bit code segment.
    lgdt    [gdt64.pointer]
    jmp     gdt64.code_offset:long_mode_start

bits 64
long_mode_start:
    ; Flatten the data/stack segment selectors. In long mode their bases
    ; are forced to zero anyway, but the selector value still needs to be
    ; sane so future segment-reloading code does not trip.
    xor     ax, ax
    mov     ds, ax
    mov     es, ax
    mov     fs, ax
    mov     gs, ax
    mov     ss, ax

    call    kernel_main

    ; kernel_main is not expected to return in v0.0, but if it ever does
    ; we halt cleanly rather than fall off the end of the text section.
.hang:
    cli
    hlt
    jmp     .hang
