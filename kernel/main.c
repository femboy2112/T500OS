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
 * v0.0 commit 5 scope: same boot path as commit 4 (serial up, VGA up,
 * banner emitted via printk), plus a build-time gate T500_PANIC_TEST that
 * triggers a deterministic panic right after the banner so the harness
 * can verify the halt block on both sinks. The default (non-panic-test)
 * ISO behavior is unchanged.
 */

#include "kernel/serial.h"
#include "kernel/vga.h"
#include "kernel/printk.h"
#include "kernel/panic.h"

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

#ifdef T500_PANIC_TEST
    /* Build-time gate per docs/PLAN-v0.0.md commit 5. The panic-test ISO
     * fires panic() immediately after the banner so the harness can prove
     * the halt path on both serial and VGA without altering normal-boot
     * behavior. The default ISO never defines T500_PANIC_TEST. */
    panic("boot.test", "panic-test build");
#endif

    for (;;) {
        __asm__ volatile ("cli; hlt");
    }
}
