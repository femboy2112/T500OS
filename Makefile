# T500OS v0.0 build driver.
#
# Targets (per docs/PLAN-v0.0.md commit 2a and DESIGN.md §25.3):
#   all         — link build/kernel.elf
#   clean       — remove build/
#   iso         — produce build/t500os.iso via grub-mkrescue
#   run         — boot the ISO in QEMU, headless
#   run-serial  — boot with serial captured to build/serial.log
#   test-qemu   — run tools/test_harness.py (the heartbeat)
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

C_SOURCES   := kernel/main.c kernel/serial.c
ASM_SOURCES := boot/multiboot2.asm

C_OBJECTS   := $(patsubst %.c,$(BUILD_DIR)/%.c.o,$(C_SOURCES))
ASM_OBJECTS := $(patsubst %.asm,$(BUILD_DIR)/%.asm.o,$(ASM_SOURCES))
OBJECTS     := $(ASM_OBJECTS) $(C_OBJECTS)

.PHONY: all clean iso run run-serial test-qemu debug
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
	python3 tools/test_harness.py

debug: $(ISO)
	$(QEMU) -cdrom $(ISO) -display none -no-reboot \
	        -serial file:$(BUILD_DIR)/serial.log \
	        -s -S

clean:
	rm -rf $(BUILD_DIR)
