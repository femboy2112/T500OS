/*
 * T500OS Component: kernel.serial
 * Classification:   stable_core
 * Failure policy:   serial output is best-effort polling I/O. If the UART
 *                   never asserts LSR.THRE, serial_putc spins forever. v0.0
 *                   accepts that; a stuck UART is treated as a hung machine.
 *                   No interrupts, no FIFO management beyond a one-shot
 *                   reset, no error reporting path.
 * Owns:             COM1 (I/O ports 0x3F8..0x3FF) for the duration of the
 *                   boot. No other subsystem touches these ports in v0.0.
 * Mutates hardware: yes (UART configuration registers, TX FIFO).
 */

/*
 * v0.0 commit 2b scope: produce the smallest possible serial output path
 * so the harness can assert on the literal "T500OS v0.0" line. printk and
 * the multi-line banner come in commit 3; VGA mirroring in commit 4.
 *
 * COM1 is configured for 115200 baud, 8 data bits, no parity, 1 stop bit
 * (8N1) using polled transmit. This matches CLAUDE.md §2 (38400 or 115200
 * 8N1) and DESIGN.md §11 (serial-first debug). The reference clock for
 * the legacy 16550 UART is 1.8432 MHz; the divisor for 115200 baud is 1.
 */

#include "kernel/serial.h"

typedef __UINT8_TYPE__  uint8_t;
typedef __UINT16_TYPE__ uint16_t;

#define COM1_BASE 0x3F8

/* Register offsets from COM1_BASE. The data register and divisor-low
 * register share the same port; the divisor latch is selected by LCR.DLAB. */
#define COM1_DATA (COM1_BASE + 0)  /* DLAB=0: TX/RX data */
#define COM1_IER  (COM1_BASE + 1)  /* DLAB=0: interrupt enable */
#define COM1_DLL  (COM1_BASE + 0)  /* DLAB=1: divisor latch low  */
#define COM1_DLH  (COM1_BASE + 1)  /* DLAB=1: divisor latch high */
#define COM1_FCR  (COM1_BASE + 2)  /* FIFO control (write) */
#define COM1_LCR  (COM1_BASE + 3)  /* line control */
#define COM1_MCR  (COM1_BASE + 4)  /* modem control */
#define COM1_LSR  (COM1_BASE + 5)  /* line status (read) */

#define LCR_8N1   0x03  /* 8 data bits, no parity, 1 stop bit, DLAB=0 */
#define LCR_DLAB  0x80  /* divisor latch access bit */

#define FCR_ENABLE_CLEAR  0xC7  /* enable FIFO, clear RX+TX, 14-byte trigger */

#define MCR_DTR_RTS_OUT2  0x0B  /* DTR + RTS + OUT2 (OUT2 gates IRQs; we
                                 * keep it set to match real-hardware
                                 * conventions even though IER is 0) */

#define LSR_THRE  0x20  /* transmitter holding register empty */

/* Divisor for 115200 baud at the standard 1.8432 MHz UART clock. */
#define DIVISOR_115200_LO  0x01
#define DIVISOR_115200_HI  0x00

static inline void outb(uint16_t port, uint8_t val)
{
    __asm__ volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline uint8_t inb(uint16_t port)
{
    uint8_t v;
    __asm__ volatile ("inb %1, %0" : "=a"(v) : "Nd"(port));
    return v;
}

void serial_init(void)
{
    outb(COM1_IER, 0x00);              /* disable all UART interrupts */
    outb(COM1_LCR, LCR_DLAB);          /* select divisor latch */
    outb(COM1_DLL, DIVISOR_115200_LO);
    outb(COM1_DLH, DIVISOR_115200_HI);
    outb(COM1_LCR, LCR_8N1);           /* 8N1, DLAB=0 */
    outb(COM1_FCR, FCR_ENABLE_CLEAR);  /* enable FIFO and clear it */
    outb(COM1_MCR, MCR_DTR_RTS_OUT2);
}

static void serial_wait_tx(void)
{
    while ((inb(COM1_LSR) & LSR_THRE) == 0) {
        /* spin: see failure policy in the file header */
    }
}

void serial_putc(char c)
{
    serial_wait_tx();
    outb(COM1_DATA, (uint8_t)c);
}

void serial_puts(const char *s)
{
    while (*s) {
        serial_putc(*s++);
    }
}
