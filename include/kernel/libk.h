/*
 * T500OS Component: kernel.libk (interface)
 * Classification:   stable_core
 * Failure policy:   freestanding string/memory primitives have no error
 *                   reporting path. Callers are responsible for valid
 *                   pointers and lengths; passing a bad pointer corrupts
 *                   memory silently in v0.0 (no MMU faults wired up yet).
 *                   No allocation, no recursion, no SSE/FPU.
 * Owns:             public declarations for memset/memcpy/memmove/memcmp
 *                   and strlen/strnlen/strcmp/strncmp.
 * Mutates hardware: no (this is a header).
 */

#ifndef T500OS_KERNEL_LIBK_H
#define T500OS_KERNEL_LIBK_H

typedef __SIZE_TYPE__ size_t;

void  *memset(void *dst, int c, size_t n);
void  *memcpy(void *dst, const void *src, size_t n);
void  *memmove(void *dst, const void *src, size_t n);
int    memcmp(const void *a, const void *b, size_t n);

size_t strlen(const char *s);
size_t strnlen(const char *s, size_t n);
int    strcmp(const char *a, const char *b);
int    strncmp(const char *a, const char *b, size_t n);

#endif /* T500OS_KERNEL_LIBK_H */
