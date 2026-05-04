/*
 * T500OS Component: kernel.libk.string
 * Classification:   stable_core
 * Failure policy:   scalar reference implementations with no bounds checks
 *                   beyond the count argument. A bad pointer corrupts memory
 *                   silently in v0.0 (no MMU faults wired up yet); callers
 *                   are responsible. No SSE, no allocation, no recursion.
 * Owns:             freestanding implementations of memset/memcpy/memmove/
 *                   memcmp and strlen/strnlen/strcmp/strncmp. GCC may lower
 *                   small string-literal copies to inline calls of these,
 *                   so the link unit must provide them.
 * Mutates hardware: no.
 */

#include "kernel/libk.h"

typedef __UINT8_TYPE__ uint8_t;

void *memset(void *dst, int c, size_t n)
{
    uint8_t *d = (uint8_t *)dst;
    uint8_t  v = (uint8_t)c;
    for (size_t i = 0; i < n; i++) {
        d[i] = v;
    }
    return dst;
}

void *memcpy(void *dst, const void *src, size_t n)
{
    uint8_t       *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    for (size_t i = 0; i < n; i++) {
        d[i] = s[i];
    }
    return dst;
}

void *memmove(void *dst, const void *src, size_t n)
{
    uint8_t       *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;

    if (d == s || n == 0) {
        return dst;
    }
    if (d < s) {
        for (size_t i = 0; i < n; i++) {
            d[i] = s[i];
        }
    } else {
        for (size_t i = n; i != 0; i--) {
            d[i - 1] = s[i - 1];
        }
    }
    return dst;
}

int memcmp(const void *a, const void *b, size_t n)
{
    const uint8_t *x = (const uint8_t *)a;
    const uint8_t *y = (const uint8_t *)b;
    for (size_t i = 0; i < n; i++) {
        if (x[i] != y[i]) {
            return (int)x[i] - (int)y[i];
        }
    }
    return 0;
}

size_t strlen(const char *s)
{
    size_t n = 0;
    while (s[n] != '\0') {
        n++;
    }
    return n;
}

size_t strnlen(const char *s, size_t n)
{
    size_t i = 0;
    while (i < n && s[i] != '\0') {
        i++;
    }
    return i;
}

int strcmp(const char *a, const char *b)
{
    const uint8_t *x = (const uint8_t *)a;
    const uint8_t *y = (const uint8_t *)b;
    while (*x != 0 && *x == *y) {
        x++;
        y++;
    }
    return (int)*x - (int)*y;
}

int strncmp(const char *a, const char *b, size_t n)
{
    const uint8_t *x = (const uint8_t *)a;
    const uint8_t *y = (const uint8_t *)b;
    for (size_t i = 0; i < n; i++) {
        if (x[i] != y[i]) {
            return (int)x[i] - (int)y[i];
        }
        if (x[i] == 0) {
            return 0;
        }
    }
    return 0;
}
