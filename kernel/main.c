/*
 * T500OS Component: kernel.main
 * Classification:   stable_core
 * Failure policy:   v0.0 has no recoverable failures here; kernel_main
 *                   is not expected to return. If it ever does, the
 *                   boot trampoline halts the CPU.
 * Owns:             v0.0 kernel entry point and the boot-banner emit
 *                   sequence (CLAUDE.md §3).
 * Mutates hardware: yes (clears IF and halts the CPU); also brings up
 *                   COM1 via serial_init (see kernel/serial.c) and the
 *                   80x25 VGA text framebuffer via vga_init (see
 *                   kernel/vga.c). Every printk byte is delivered to COM1
 *                   by serial_putc and to physical 0xB8000 by vga_putc.
 */

/*
 * v0.0 commit 4 scope: bring up COM1 and the legacy VGA text framebuffer,
 * then emit the full multi-line boot banner via printk. printk tees every
 * byte to both sinks (serial first), so the serial.log capture and the
 * VGA pmemsave dump must be byte-identical (CLAUDE.md §3).
 */

#include "kernel/serial.h"
#include "kernel/vga.h"
#include "kernel/printk.h"

__attribute__((noreturn))
void kernel_main(void)
{
    serial_init();
    vga_init();

    printk("T500OS v0.0\n");
    printk("Target: Lenovo ThinkPad T500\n");
    printk("Mode: x86_64 long mode\n");
    printk("Boot: Multiboot2 via GRUB\n");
    printk("Serial: active\n");
    printk("Display: VGA text\n");
    printk("Panic path: active\n");
    printk("Memory map: initializing\n");
    printk("\n");
    printk("T5L prompt pending...\n");

    for (;;) {
        __asm__ volatile ("cli; hlt");
    }
}
