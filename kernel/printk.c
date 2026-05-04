/*
 * T500OS Component: kernel.printk
 * Classification:   stable_core
 * Failure policy:   tiny integer-only formatter; cannot fail. Unsupported
 *                   conversion specifiers emit the literal '%' followed by
 *                   the offending character so bugs are visible. Field
 *                   widths beyond the buffer for a single integer are
 *                   honored, but no truncation is applied to %s — callers
 *                   own their string lifetimes. Returns the count of
 *                   characters emitted.
 * Owns:             format-string interpretation and output routing for
 *                   v0.0. Routes only to serial; VGA mirroring lands in
 *                   commit 4 (CLAUDE.md §3 byte-identical rule).
 * Mutates hardware: indirectly — every emitted byte goes to COM1 via
 *                   serial_putc.
 */

#include "kernel/printk.h"
#include "kernel/serial.h"
#include "kernel/libk.h"

typedef __UINT64_TYPE__  uint64_t;
typedef __INT64_TYPE__   int64_t;
typedef __UINTPTR_TYPE__ uintptr_t;

#define va_start(ap, last) __builtin_va_start(ap, last)
#define va_arg(ap, type)   __builtin_va_arg(ap, type)
#define va_end(ap)         __builtin_va_end(ap)

/* Maximum digits for a 64-bit unsigned value in base 10 is 20; +1 for NUL. */
#define NUMBUF_LEN 21

static void emit_char(char c, int *count)
{
    serial_putc(c);
    (*count)++;
}

static void emit_run(const char *s, int n, int *count)
{
    for (int i = 0; i < n; i++) {
        emit_char(s[i], count);
    }
}

/* Render `v` in radix `base` (lowercase) into `buf`. Returns the number of
 * digits written (without NUL). `buf` must be at least NUMBUF_LEN bytes. */
static int u64_to_str(uint64_t v, unsigned base, char *buf)
{
    static const char digits[] = "0123456789abcdef";
    char tmp[NUMBUF_LEN];
    int  n = 0;

    if (v == 0) {
        tmp[n++] = '0';
    } else {
        while (v != 0 && n < (int)sizeof(tmp)) {
            tmp[n++] = digits[v % base];
            v /= base;
        }
    }
    for (int i = 0; i < n; i++) {
        buf[i] = tmp[n - 1 - i];
    }
    buf[n] = '\0';
    return n;
}

/* Emit `s` (length `slen`) right-justified in a field of `width`. If
 * `zero_pad` is set, pad with '0'; otherwise pad with ' '. No left-justify
 * support — v0.0 has no need. */
static void emit_padded(const char *s, int slen, int width, int zero_pad,
                        int *count)
{
    int pad = (width > slen) ? (width - slen) : 0;
    char pc = zero_pad ? '0' : ' ';
    for (int i = 0; i < pad; i++) {
        emit_char(pc, count);
    }
    emit_run(s, slen, count);
}

int vprintk(const char *fmt, va_list ap)
{
    int  count = 0;
    char numbuf[NUMBUF_LEN];

    for (const char *p = fmt; *p != '\0'; p++) {
        if (*p != '%') {
            emit_char(*p, &count);
            continue;
        }

        p++;
        if (*p == '\0') {
            break;
        }

        int zero_pad = 0;
        int width    = 0;

        if (*p == '0') {
            zero_pad = 1;
            p++;
        }
        while (*p >= '0' && *p <= '9') {
            width = width * 10 + (*p - '0');
            p++;
        }

        switch (*p) {
        case 'c': {
            char c = (char)va_arg(ap, int);
            emit_padded(&c, 1, width, 0, &count);
            break;
        }
        case 's': {
            const char *s = va_arg(ap, const char *);
            if (s == (const char *)0) {
                s = "(null)";
            }
            int slen = (int)strlen(s);
            emit_padded(s, slen, width, 0, &count);
            break;
        }
        case 'd': {
            int      v = va_arg(ap, int);
            int      neg = 0;
            uint64_t u;
            if (v < 0) {
                neg = 1;
                u = (uint64_t)(-(int64_t)v);
            } else {
                u = (uint64_t)v;
            }
            int n = u64_to_str(u, 10, numbuf);
            int total = n + (neg ? 1 : 0);
            int pad = (width > total) ? (width - total) : 0;
            if (zero_pad) {
                if (neg) {
                    emit_char('-', &count);
                }
                for (int i = 0; i < pad; i++) {
                    emit_char('0', &count);
                }
            } else {
                for (int i = 0; i < pad; i++) {
                    emit_char(' ', &count);
                }
                if (neg) {
                    emit_char('-', &count);
                }
            }
            emit_run(numbuf, n, &count);
            break;
        }
        case 'u': {
            uint64_t u = (uint64_t)va_arg(ap, unsigned int);
            int n = u64_to_str(u, 10, numbuf);
            emit_padded(numbuf, n, width, zero_pad, &count);
            break;
        }
        case 'x': {
            uint64_t u = (uint64_t)va_arg(ap, unsigned int);
            int n = u64_to_str(u, 16, numbuf);
            emit_padded(numbuf, n, width, zero_pad, &count);
            break;
        }
        case 'p': {
            uintptr_t addr = (uintptr_t)va_arg(ap, void *);
            int n = u64_to_str((uint64_t)addr, 16, numbuf);
            emit_char('0', &count);
            emit_char('x', &count);
            int inner = (width > 2) ? (width - 2) : 0;
            emit_padded(numbuf, n, inner, 1, &count);
            break;
        }
        case '%':
            emit_char('%', &count);
            break;
        default:
            emit_char('%', &count);
            emit_char(*p, &count);
            break;
        }
    }
    return count;
}

int printk(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    int n = vprintk(fmt, ap);
    va_end(ap);
    return n;
}
