/*
 * T500OS Component: kernel.serial (interface)
 * Classification:   stable_core
 * Failure policy:   serial output is best-effort polling I/O; a stuck UART
 *                   means serial_putc spins on LSR.THRE forever. v0.0 has
 *                   no watchdog and no timeout — that is acceptable because
 *                   serial is the boot-time debug sink and a stuck UART is
 *                   indistinguishable from a hung CPU.
 * Owns:             public declarations for the COM1 polled UART driver.
 * Mutates hardware: no (this is a header); the implementation in
 *                   kernel/serial.c writes COM1 (0x3F8..0x3FF).
 */

#ifndef T500OS_KERNEL_SERIAL_H
#define T500OS_KERNEL_SERIAL_H

void serial_init(void);
void serial_putc(char c);
void serial_puts(const char *s);

#endif /* T500OS_KERNEL_SERIAL_H */
