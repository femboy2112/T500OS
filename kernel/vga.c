/*
 * T500OS Component: kernel.vga
 * Classification:   stable_core
 * Failure policy:   pure memory-mapped output, no failure path. A control
 *                   character other than '\n' is printed as its literal
 *                   glyph so bugs are visible rather than swallowed.
 *                   Cursor wrap and scroll are unconditional and silent.
 * Owns:             physical 0xB8000..0xB8FA0 (80*25*2 bytes — the legacy
 *                   VGA text framebuffer) and the v0.0 cursor row/column
 *                   counters. No other subsystem touches this region.
 *                   The hardware text cursor (CRTC ports 0x3D4/0x3D5) is
 *                   intentionally NOT touched in v0.0; only character
 *                   cells are written, which keeps the IO surface zero.
 * Mutates hardware: yes (writes the legacy text-mode framebuffer at
 *                   physical 0xB8000). No port I/O.
 */

#include "kernel/vga.h"

typedef __UINT8_TYPE__  uint8_t;
typedef __UINT16_TYPE__ uint16_t;

#define VGA_FB_PHYS  0xB8000
#define VGA_COLS     80
#define VGA_ROWS     25
#define VGA_ATTR     0x07  /* light gray foreground on black background */

/* Pre-composed blank cell: space character with the default attribute. */
#define VGA_BLANK_CELL ((uint16_t)((VGA_ATTR << 8) | (uint8_t)' '))

static volatile uint16_t *const fb = (volatile uint16_t *)VGA_FB_PHYS;

static int cursor_row;
static int cursor_col;

static void vga_clear(void)
{
    for (int i = 0; i < VGA_ROWS * VGA_COLS; i++) {
        fb[i] = VGA_BLANK_CELL;
    }
}

static void vga_scroll(void)
{
    /* Move rows 1..VGA_ROWS-1 up by one row. Iterative copy, no memmove
     * dependency — keeps the file standalone and obvious. */
    for (int r = 1; r < VGA_ROWS; r++) {
        for (int c = 0; c < VGA_COLS; c++) {
            fb[(r - 1) * VGA_COLS + c] = fb[r * VGA_COLS + c];
        }
    }
    /* Blank the final row. */
    for (int c = 0; c < VGA_COLS; c++) {
        fb[(VGA_ROWS - 1) * VGA_COLS + c] = VGA_BLANK_CELL;
    }
}

static void vga_newline(void)
{
    cursor_col = 0;
    cursor_row++;
    if (cursor_row >= VGA_ROWS) {
        vga_scroll();
        cursor_row = VGA_ROWS - 1;
    }
}

void vga_init(void)
{
    cursor_row = 0;
    cursor_col = 0;
    vga_clear();
}

void vga_putc(char c)
{
    if (c == '\n') {
        vga_newline();
        return;
    }
    fb[cursor_row * VGA_COLS + cursor_col] =
        (uint16_t)((VGA_ATTR << 8) | (uint8_t)c);
    cursor_col++;
    if (cursor_col >= VGA_COLS) {
        vga_newline();
    }
}

void vga_puts(const char *s)
{
    while (*s) {
        vga_putc(*s++);
    }
}
