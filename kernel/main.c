/*
 * T500OS Component: kernel.main
 * Classification:   stable_core
 * Failure policy:   v0.0 has no recoverable failures here; kernel_main
 *                   is not expected to return. If it ever does, the
 *                   boot trampoline halts the CPU.
 * Owns:             v0.0 kernel entry point.
 * Mutates hardware: yes (clears IF and halts the CPU); no other state.
 */

/*
 * v0.0 commit 2a scope: prove the build, link, ISO, and QEMU loop work.
 * No serial driver, no banner, no harness assertions on output yet —
 * those land in commit 2b. kernel_main therefore does the absolute
 * minimum: disable interrupts and halt, looping on spurious NMIs.
 */
__attribute__((noreturn))
void kernel_main(void)
{
    for (;;) {
        __asm__ volatile ("cli; hlt");
    }
}
