/*
 * T500OS Component: kernel.vga (interface)
 * Classification:   stable_core
 * Failure policy:   text-mode framebuffer writes are best-effort and never
 *                   block; control characters other than '\n' are rendered
 *                   as their literal glyph rather than dropped, so bugs are
 *                   visible. No error reporting path.
 * Owns:             public declarations for the 80x25 legacy VGA text-mode
 *                   driver. The implementation in kernel/vga.c owns the
 *                   physical framebuffer at 0xB8000 and the cursor counters.
 * Mutates hardware: no (this is a header).
 */

#ifndef T500OS_KERNEL_VGA_H
#define T500OS_KERNEL_VGA_H

void vga_init(void);
void vga_putc(char c);
void vga_puts(const char *s);

#endif /* T500OS_KERNEL_VGA_H */
