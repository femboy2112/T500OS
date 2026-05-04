# T500OS v0.0 build driver.
#
# Targets (per docs/PLAN-v0.0.md commit 2a/5 and DESIGN.md §25.3):
#   all         — link build/kernel.elf
#   clean       — remove build/
#   iso         — produce build/t500os.iso via grub-mkrescue
#   run         — boot the ISO in QEMU, headless
#   run-serial  — boot with serial captured to build/serial.log
#   test-qemu   — run tools/test_harness.py in boot mode (the heartbeat)
#   test-panic  — build a -DT500_PANIC_TEST variant ISO and run the
#                 harness in panic mode to verify the halt path
#   debug       — boot with QEMU paused for gdb on tcp::1234
#
# v0.0 may use the host gcc per D0002 / DESIGN.md §25.2 provided strict
# freestanding flags are used. -Werror is v0.0-only per D0005; v0.1 will
# revisit it once IRQ stubs land. None of the targets here write to disk
# images, host disks, or block devices (CLAUDE.md §7 disk-write rule).

CC      ?= gcc
LD      ?= ld
NASM    ?= nasm
QEMU    ?= qemu-system-x86_64

BUILD_DIR := build
ISO_DIR   := $(BUILD_DIR)/iso

KERNEL_ELF := $(BUILD_DIR)/kernel.elf
KERNEL_MAP := $(BUILD_DIR)/kernel.map
ISO        := $(BUILD_DIR)/t500os.iso

# Panic-test variant (docs/PLAN-v0.0.md commit 5): identical sources, but
# compiled with -DT500_PANIC_TEST so kernel_main fires panic() immediately
# after the banner. Built into a separate object tree and separate ISO so
# `make test-qemu` and `make test-panic` cannot trample each other.
PANIC_BUILD_DIR  := $(BUILD_DIR)/panic
PANIC_ISO_DIR    := $(PANIC_BUILD_DIR)/iso
PANIC_KERNEL_ELF := $(BUILD_DIR)/kernel-panic.elf
PANIC_KERNEL_MAP := $(BUILD_DIR)/kernel-panic.map
PANIC_ISO        := $(BUILD_DIR)/t500os-panic.iso

CFLAGS  := -ffreestanding -fno-stack-protector -fno-pic -mno-red-zone \
           -mno-mmx -mno-sse -mno-sse2 -mno-80387 \
           -nostdlib -nostdinc \
           -fno-builtin -fno-asynchronous-unwind-tables \
           -g -O2 -Wall -Wextra -Werror \
           -std=gnu11 \
           -Iinclude
LDFLAGS := -nostdlib -static -z noexecstack -z max-page-size=0x1000 \
           -T linker.ld -Map=$(KERNEL_MAP)
ASFLAGS := -f elf64 -g -F dwarf

C_SOURCES   := kernel/main.c kernel/serial.c kernel/vga.c kernel/printk.c \
               kernel/panic.c kernel/libk/string.c
ASM_SOURCES := boot/multiboot2.asm

C_OBJECTS   := $(patsubst %.c,$(BUILD_DIR)/%.c.o,$(C_SOURCES))
ASM_OBJECTS := $(patsubst %.asm,$(BUILD_DIR)/%.asm.o,$(ASM_SOURCES))
OBJECTS     := $(ASM_OBJECTS) $(C_OBJECTS)

PANIC_C_OBJECTS   := $(patsubst %.c,$(PANIC_BUILD_DIR)/%.c.o,$(C_SOURCES))
PANIC_ASM_OBJECTS := $(patsubst %.asm,$(PANIC_BUILD_DIR)/%.asm.o,$(ASM_SOURCES))
PANIC_OBJECTS     := $(PANIC_ASM_OBJECTS) $(PANIC_C_OBJECTS)

PANIC_CFLAGS  := $(CFLAGS) -DT500_PANIC_TEST
PANIC_LDFLAGS := -nostdlib -static -z noexecstack -z max-page-size=0x1000 \
                 -T linker.ld -Map=$(PANIC_KERNEL_MAP)

.PHONY: all clean iso run run-serial test-qemu test-panic debug
.DEFAULT_GOAL := all

all: $(KERNEL_ELF)

$(BUILD_DIR)/%.c.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/%.asm.o: %.asm
	@mkdir -p $(dir $@)
	$(NASM) $(ASFLAGS) $< -o $@

$(KERNEL_ELF): $(OBJECTS) linker.ld
	@mkdir -p $(BUILD_DIR)
	$(LD) $(LDFLAGS) -o $@ $(OBJECTS)

iso: $(ISO)

$(ISO): $(KERNEL_ELF) grub/grub.cfg
	@rm -rf $(ISO_DIR)
	@mkdir -p $(ISO_DIR)/boot/grub
	cp $(KERNEL_ELF) $(ISO_DIR)/boot/kernel.elf
	cp grub/grub.cfg $(ISO_DIR)/boot/grub/grub.cfg
	grub-mkrescue -o $@ $(ISO_DIR) 2>/dev/null

run: $(ISO)
	$(QEMU) -cdrom $(ISO) -display none -no-reboot \
	        -d guest_errors -D $(BUILD_DIR)/qemu.log

run-serial: $(ISO)
	$(QEMU) -cdrom $(ISO) -display none -no-reboot \
	        -serial file:$(BUILD_DIR)/serial.log \
	        -d guest_errors -D $(BUILD_DIR)/qemu.log

test-qemu: $(ISO)
	python3 tools/test_harness.py --mode boot

# Panic-test variant rules. Object files live under $(PANIC_BUILD_DIR) so
# `make test-qemu` and `make test-panic` do not invalidate each other.
$(PANIC_BUILD_DIR)/%.c.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(PANIC_CFLAGS) -c $< -o $@

$(PANIC_BUILD_DIR)/%.asm.o: %.asm
	@mkdir -p $(dir $@)
	$(NASM) $(ASFLAGS) $< -o $@

$(PANIC_KERNEL_ELF): $(PANIC_OBJECTS) linker.ld
	@mkdir -p $(BUILD_DIR)
	$(LD) $(PANIC_LDFLAGS) -o $@ $(PANIC_OBJECTS)

$(PANIC_ISO): $(PANIC_KERNEL_ELF) grub/grub.cfg
	@rm -rf $(PANIC_ISO_DIR)
	@mkdir -p $(PANIC_ISO_DIR)/boot/grub
	cp $(PANIC_KERNEL_ELF) $(PANIC_ISO_DIR)/boot/kernel.elf
	cp grub/grub.cfg $(PANIC_ISO_DIR)/boot/grub/grub.cfg
	grub-mkrescue -o $@ $(PANIC_ISO_DIR) 2>/dev/null

test-panic: $(PANIC_ISO)
	python3 tools/test_harness.py --mode panic

debug: $(ISO)
	$(QEMU) -cdrom $(ISO) -display none -no-reboot \
	        -serial file:$(BUILD_DIR)/serial.log \
	        -s -S

clean:
	rm -rf $(BUILD_DIR)
