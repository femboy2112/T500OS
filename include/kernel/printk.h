/*
 * T500OS Component: kernel.printk (interface)
 * Classification:   stable_core
 * Failure policy:   integer-only formatter, best-effort. Unsupported format
 *                   conversions emit the literal '%' followed by the
 *                   offending character so bugs are visible rather than
 *                   silent. Cannot fail; returns the number of characters
 *                   written. No allocation, no float, no SSE.
 * Owns:             public declarations for printk and vprintk. The
 *                   format-archetype attribute opts the call site into
 *                   GCC's printf-format diagnostics.
 * Mutates hardware: no (this is a header); the implementation calls
 *                   serial_putc which writes COM1.
 */

#ifndef T500OS_KERNEL_PRINTK_H
#define T500OS_KERNEL_PRINTK_H

typedef __builtin_va_list va_list;

int printk(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
int vprintk(const char *fmt, va_list ap);

#endif /* T500OS_KERNEL_PRINTK_H */
