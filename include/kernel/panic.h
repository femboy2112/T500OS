/*
 * T500OS Component: kernel.panic (interface)
 * Classification:   stable_core
 * Failure policy:   panic() is the last-line-of-defense halt path; it is
 *                   declared noreturn and must never return. It clears IF and
 *                   parks the CPU in a hlt loop. It performs no allocation
 *                   and no formatting beyond two const-string substitutions,
 *                   so it cannot itself fail in any way that would matter.
 * Owns:             public declaration of panic(). Callers pass two
 *                   short, statically-allocated, NUL-terminated strings
 *                   (subsystem.stage and short error message) as required by
 *                   DESIGN.md §10.5.
 * Mutates hardware: no (this is a header); the implementation in
 *                   kernel/panic.c writes COM1 and 0xB8000 via printk and
 *                   then executes cli; hlt; jmp .
 */

#ifndef T500OS_KERNEL_PANIC_H
#define T500OS_KERNEL_PANIC_H

__attribute__((noreturn))
void panic(const char *stage, const char *msg);

#endif /* T500OS_KERNEL_PANIC_H */
