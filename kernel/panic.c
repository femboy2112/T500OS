/*
 * T500OS Component: kernel.panic
 * Classification:   stable_core
 * Failure policy:   panic() is the terminal halt path. It is reached when an
 *                   invariant is already broken, so it must do as little as
 *                   possible and cannot itself fail. It uses printk (which
 *                   tees to COM1 and 0xB8000) to emit the three-line
 *                   KERNEL PANIC block from DESIGN.md §10.5 to both sinks,
 *                   then disables interrupts and parks the CPU in a hlt
 *                   loop with a self-jump fallback. Never returns.
 * Owns:             the [panic] subsystem prefix and the canonical halt
 *                   sequence (cli; hlt; jmp .). No state of its own.
 * Mutates hardware: yes — clears IF and halts the CPU. The printk call path
 *                   already mutates COM1 (serial_putc) and physical 0xB8000
 *                   (vga_putc); panic() does not touch hardware directly
 *                   beyond the cli/hlt itself.
 */

#include "kernel/panic.h"
#include "kernel/printk.h"

__attribute__((noreturn))
void panic(const char *stage, const char *msg)
{
    if (stage == (const char *)0) {
        stage = "(null)";
    }
    if (msg == (const char *)0) {
        msg = "(null)";
    }

    /* DESIGN.md §10.5 panic block, byte-for-byte:
     *   KERNEL PANIC: <msg>
     *   stage=<stage>
     *   error=<msg>
     * printk tees every emitted byte to COM1 and to 0xB8000 in that order
     * (DESIGN.md §11.3 serial-first principle), so the serial.log capture
     * and the VGA framebuffer dump observe the same bytes. The block is
     * printed without a [panic] subsystem prefix to match the §10.5
     * literal — the harness asserts on the unprefixed form. */
    printk("KERNEL PANIC: %s\n", msg);
    printk("stage=%s\n", stage);
    printk("error=%s\n", msg);

    /* cli prevents any pending IRQ from waking us; hlt parks the CPU until
     * the next NMI; the unconditional jmp catches the (currently
     * impossible in v0.0) NMI-wake case so the CPU cannot fall through.
     * Marked volatile so the compiler does not assume the asm has no
     * effect after a noreturn declaration. */
    for (;;) {
        __asm__ volatile ("cli\n\t"
                          "hlt\n\t"
                          "jmp .\n\t");
    }
}
