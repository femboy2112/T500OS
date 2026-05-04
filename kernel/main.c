/*
 * T500OS Component: kernel.main
 * Classification:   stable_core
 * Failure policy:   v0.0 has no recoverable failures here; kernel_main
 *                   is not expected to return. If it ever does, the
 *                   boot trampoline halts the CPU.
 * Owns:             v0.0 kernel entry point.
 * Mutates hardware: yes (clears IF and halts the CPU); also brings up
 *                   COM1 via serial_init (see kernel/serial.c).
 */

/*
 * v0.0 commit 2b scope: bring up COM1 and emit the literal first banner
 * line "T500OS v0.0\n" so the harness can assert CLAUDE.md §3's banner
 * contract. The full multi-line banner waits for printk in commit 3;
 * VGA mirroring waits for commit 4.
 */

#include "kernel/serial.h"

__attribute__((noreturn))
void kernel_main(void)
{
    serial_init();
    serial_puts("T500OS v0.0\n");

    for (;;) {
        __asm__ volatile ("cli; hlt");
    }
}
