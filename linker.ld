/*
 * T500OS linker script for v0.0.
 *
 * Loads the kernel at 1 MiB physical, ELF64. The Multiboot2 header must
 * sit in the first 32 KiB of the file so GRUB can find it; we keep it as
 * the very first PROGBITS section after the ELF header by giving its
 * input section the highest priority in the layout.
 *
 * No higher-half mapping yet. v0.0 runs identity-mapped.
 *
 * Map output is requested from the build driver (Makefile) via
 * --Map=build/kernel.map; debug sections are intentionally retained
 * (-g flows through; no strip step anywhere).
 */

ENTRY(_start)

OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)

KERNEL_LOAD_ADDR = 0x100000;

SECTIONS
{
    . = KERNEL_LOAD_ADDR;

    .multiboot2 ALIGN(8) :
    {
        KEEP(*(.multiboot2))
    }

    .text ALIGN(16) :
    {
        *(.text .text.*)
    }

    .rodata ALIGN(16) :
    {
        *(.rodata .rodata.*)
    }

    .data ALIGN(16) :
    {
        *(.data .data.*)
    }

    .bss ALIGN(16) :
    {
        *(COMMON)
        *(.bss .bss.*)
    }

    /DISCARD/ :
    {
        *(.note.gnu.build-id)
        *(.note.GNU-stack)
        *(.eh_frame)
        *(.eh_frame_hdr)
        *(.comment)
    }
}
