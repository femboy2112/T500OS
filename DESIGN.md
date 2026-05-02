T500OS Project Design Document v0.2

0. Final Audit Status

Project name: T500OS
Document version: 0.2 audit-integrated baseline
Status: Complete planning baseline / implementation-ready for v0.0
Primary hardware target: Lenovo ThinkPad T500 2056BZ1
Primary project type: Ground-up hobby operating system
Design posture: Terminal-first, hardware-specific, low-RAM, deterministic, expandable in controlled stages
Performance posture: Math/research-first, minimal overhead, bare-metal optimization preferred
Security posture: Trusted local execution, hardened network boundary, explicit no-sandbox assumptions until real containment exists

0.1 Audit Result

Result: PASS — with review-driven hardening integrated.

This document is now a coherent baseline for beginning implementation. The major architectural risks identified by review have been addressed:

serial/debug infrastructure promoted early
virtual memory no longer deferred dangerously
GRUB accepted only as temporary acceleration
network stack borrowing allowed only inside containment policy
capsule execution model made concrete
T5L prompt identity elevated
FAT32 scope constrained
hardware surgery rules clarified
write safety hardened
QEMU regression harness required early
stability classifications required in docs and source comments

0.2 Remaining Reality Check

T500OS is ambitious. The first useful system will not be a modern desktop OS. The first true victory is narrower and more important:

Power on ThinkPad T500
Select T500OS
Kernel boots
Serial and screen print boot state
Keyboard works
Prompt appears
2+2 evaluates immediately
System can inspect CPU, memory, interrupts, and PCI state

Everything beyond that must pass milestone gates.


---

1. Executive Summary

T500OS is a ground-up 64-bit operating system designed specifically for the Lenovo ThinkPad T500 platform. It is not a Linux distribution, not a BSD fork, not a Q4OS/Debian customization, not a Unix clone, and not a desktop environment project. It is a custom kernel and minimal operating environment intended to boot directly on the target laptop, expose the hardware clearly, and gradually grow into a personal terminal-first math and research workstation.

T500OS is optimized around a narrow target: one old ThinkPad, one display class, one CPU generation, one Ethernet controller family, one disk-controller path, and one keyboard/mouse input path. This is intentional. General-purpose portability is deferred until the exact machine is stable and useful.

Performance is a first-class design axis. T500OS should eventually become a math and research environment that minimizes abstraction overhead, exposes hardware behavior clearly, and gives computational workloads direct access to efficient memory, CPU, and I/O paths. The system should favor simple, inspectable, aggressively optimized mechanisms over generic compatibility when the two conflict.

Security is intentionally narrow. The local machine is treated as a trusted single-user research instrument. The operator is expected to judge whether code is trustworthy before running it. Strong protection is required mainly at the network boundary: packet parsing, inbound services, remote execution surfaces, and future network file transfer mechanisms must be defensive, explicit, bounded, and off by default.

The system does not primarily reason in terms of userspace versus kernel space. That imported distinction is too Unix-shaped for the project. T500OS instead reasons in terms of stability and crash risk:

rigorously stable core
→ trusted research modules
→ restartable research capsules
→ volatile foreign compatibility layer
→ hostile network boundary


---

2. Mission Statement

T500OS exists to create a personally owned, understandable, controllable operating system for the ThinkPad T500.

The system should prioritize:

1. Performance for math and research — computational workloads should run with minimal runtime overhead, clear memory behavior, and hardware-specific optimization where justified.


2. Immediate research usefulness — after boot, the prompt should support direct mathematical work without launching a separate application.


3. Understandability — every subsystem should be small enough to inspect and reason about.


4. Determinism — avoid hidden background behavior, implicit service chains, and complex runtime policy.


5. Hardware intimacy — expose the actual hardware instead of burying it under generic abstraction too early.


6. Terminal-first utility — the shell/research prompt is the primary interface; graphics are secondary.


7. Low memory pressure — the OS should remain comfortable under 2 GiB RAM.


8. Incremental bootstrapping — each milestone should produce a bootable, testable system.


9. Narrow security — protect the network boundary strongly, but do not burden trusted local research execution with heavyweight policy until a concrete threat model requires it.


10. Architectural independence — do not copy Linux, BSD, Windows, POSIX, systemd, X11, Wayland, NT, or Unix structures by habit. Borrow only when a design clearly improves performance, simplicity, correctness, debugging, or implementation leverage.


11. Anti-drift discipline — no subsystem may be expanded before its predecessor meets concrete done criteria.




---

3. Non-Goals

3.1 Not a Linux Replacement Yet

T500OS v0.x is not intended to replace Linux for general daily computing. It will not initially provide:

a modern web browser

package management

POSIX compatibility

multiuser Unix semantics

full USB stack

Wi-Fi

audio

full hardware GPU acceleration

Samba/SMB client

X11 or Wayland compatibility

Docker, virtualization, or container runtime

full filesystem read/write support for modern filesystems


3.2 Not a Universal OS

T500OS is not initially portable across arbitrary hardware.

Early support is limited to:

BIOS boot, not UEFI
x86_64 long mode
Lenovo ThinkPad T500-era hardware
PS/2-style keyboard / TrackPoint path
VGA text mode and later VESA framebuffer
ATA/IDE path first, AHCI later
Intel 82567LM Ethernet later

3.3 Not a Browser Project First

A browser is not an early milestone. A modern browser engine is essentially its own operating-system-scale project.

Early web access should mean:

raw HTTP GET client
plain-text page fetcher
tiny HTML subset parser
local documentation viewer
optional image support much later

JavaScript execution is not in scope for the first major development arc.

3.4 Not a Pure Boot-Sector Project First

T500OS may use GRUB as a temporary bootloader during v0.x. This does not violate the project mission. The OS itself remains ground-up; GRUB is used only to load the kernel and provide early boot information.

A custom bootloader may be built later after the kernel can already inspect hardware, read disk sectors, and read a minimal filesystem.

3.5 Not Security-Theater Driven

T500OS should not imitate the full security posture of a multiuser internet-facing operating system in early versions.

Early local execution model:

single trusted operator
trusted local code by default
no claim of sandboxing unless a sandbox actually exists
no heavy permission framework before an execution layer needs it
no multiuser account model before it directly improves utility

The system must be honest about this: early T500OS is a trusted research instrument, not a hardened multi-tenant platform.

3.6 Not Structurally Derived From Linux, BSD, or Windows

T500OS should not copy Linux, BSD, Windows, POSIX, systemd, X11, Wayland, NT, or Unix architecture by default.

Borrowing is allowed only when the borrowed design explicitly wins on at least one of these grounds:

1. measurable performance


2. implementation simplicity


3. hardware correctness


4. debugging clarity


5. compatibility value that does not compromise the core design


6. correctness in hostile-input protocol domains



Compatibility is a later layer, not the root architecture.


---

4. Hardware Target

4.1 Confirmed Target Machine

Current known target machine:

Lenovo ThinkPad T500 2056BZ1
CPU: Intel Core 2 Duo T9400
Architecture: x86_64
Cores: 2
RAM: approximately 1.86 GiB usable
Display: 1280x800 internal LVDS panel
Storage: Hitachi 149 GB SATA HDD
Firmware: legacy BIOS
Graphics: Intel Mobile 4 Series / GMA 4500MHD and ATI/AMD Mobility Radeon HD 3650
Ethernet: Intel 82567LM Gigabit controller
Wi-Fi: Intel Ultimate-N 5300
Audio: Intel ICH9 HD Audio
USB: Intel ICH9 UHCI/EHCI controllers
Optical: internal DVD-RAM drive
Input: laptop keyboard + TrackPoint/touchpad path

4.2 Hardware Strategy

The system should target hardware in this order:

1. CPU and BIOS boot path


2. serial debug output


3. VGA text mode


4. PS/2 keyboard input


5. PIT/APIC timer


6. physical memory map


7. PCI enumeration


8. virtual memory mapping helpers


9. ATA/IDE disk access


10. VESA framebuffer


11. Intel 82567LM Ethernet


12. AHCI disk access


13. USB support


14. native Intel graphics mode-setting


15. Wi-Fi


16. audio


17. Radeon support



4.3 Hardware Avoidance List

The following hardware features should be ignored until the system is mature:

ATI/AMD Radeon acceleration
Intel Wi-Fi 5300
Bluetooth
fingerprint reader
modem, if present
FireWire, if present
advanced ACPI power management
suspend/resume
multi-monitor hotplug
audio mixing
hardware video decode


---

5. Core Design Philosophy

5.1 Narrow Before Broad

The system should work well on one exact laptop before it attempts to work poorly on many.

Universal abstractions are allowed only after the concrete driver or subsystem works against real hardware.

5.2 Math Prompt Before Admin Shell

The prompt is first a math/research instrument, second an operating-system control interface.

After v0.1, the system should feel like:

math/research REPL with hardware powers

not:

generic admin shell with a calculator bolted on

5.3 Shell Before Desktop

The shell/research prompt is the first-class interface. A graphical shell must not become a requirement for system administration or research execution.

Every important function should eventually be available through a command or T5L expression.

Examples:

mem
pci
disk
net
mount
log
panicdump
bench
profile
modpow
reboot
halt

5.4 Text Before Pixels

VGA text output is the first rendering target. Framebuffer graphics come later. Native GPU acceleration comes much later.

5.5 Read-Only Before Read-Write

Any storage subsystem should begin read-only where practical.

Recommended progression:

sector read → raw hexdump → partition scan → read-only FAT32 → limited FAT32 write → stronger storage later

5.6 Instrument Everything

T500OS is partly a hardware laboratory. Every subsystem should expose internal status clearly.

Examples:

T500OS> mem
T500OS> pci
T500OS> irq
T500OS> timers
T500OS> diskinfo
T500OS> netstat

5.7 Hardware Surgery Doctrine

T500OS should let the operator intentionally probe the machine as deeply as possible while the OS is running.

Design goal:

The machine should be inspectable down to registers, flags, descriptors, ports, buses, memory maps, and device state.

The OS should provide easy commands for:

reading CPU flags and control registers where safe

dumping CPUID leaves

inspecting GDT/IDT descriptors

viewing interrupt and timer state

dumping PCI config space

listing PCI BARs and decoded device regions

reading I/O ports where safe

reading MMIO regions where safe

showing page-table mappings

inspecting allocator state

showing disk controller registers

showing network device registers later

showing framebuffer/video state later

logging every manual hardware mutation


Default mode should be read-only. Mutating hardware state must require explicit surgery/write mode.

Progression:

detect → describe → dump → decode → benchmark → mutate only if explicitly requested

5.8 Avoid Hidden Automation

Background services should be explicit, visible, and few. If a daemon-like component exists, the shell should be able to list it, pause it, restart it, and show why it exists.


---

6. Performance and Research Computing Doctrine

6.1 Performance Is a Core Requirement

T500OS is intended to become a fast math and research environment for the exact T500 hardware. Performance must be treated as a design constraint from the beginning, even before advanced math tooling exists.

This means:

low interrupt and call overhead
predictable memory allocation
minimal background services
no compositor requirement
no general-purpose daemon graph
no heavyweight local security wrappers for trusted code
CPU-specific optimization where useful
data structures chosen for cache behavior and simplicity
explicit performance measurements before large abstractions are accepted

6.2 Core 2 Duo Optimization Profile

Primary CPU profile:

Intel Core 2 Duo T9400
x86_64
2 cores, but single-core first
SSE, SSE2, SSE3, SSSE3, SSE4.1 available
No AVX
Small caches by modern standards
Low memory bandwidth by modern standards

Optimization policy:

1. Correct scalar C implementation first.


2. Add benchmark harness.


3. Add SSE/SSE2/SSE4.1-specialized kernels only for hot paths.


4. Keep fallback scalar path for debugging and correctness checks.


5. Never add hand-written assembly without a measurable win or a hardware-control requirement.



6.3 Math Runtime Long-Term Targets

T500OS should eventually grow a native research runtime optimized for:

integer arithmetic

modular arithmetic

arbitrary precision integers

rational arithmetic

polynomial arithmetic

matrix/vector kernels

exact combinatorial computation

fast hashing/checksum routines

batch verification workloads

reproducible benchmark scripts


Potential library layers:

libt500core      basic runtime primitives
libt500math      integer/modular/rational kernels
libt500matrix    matrix/vector operations
libt500verify    hash/checksum/proof-witness helpers
libt500bench     deterministic benchmark harness

These libraries should use T500OS-native APIs first. POSIX or Linux compatibility should be optional and external.

6.4 Measurement Rule

Any subsystem that claims to be performance-oriented must expose a measurement path.

Examples:

cycles per operation
bytes per second
packets per second
sectors per second
allocation latency
interrupt frequency
cache-aligned versus unaligned performance

Do not argue performance purely by aesthetics. Measure it.

6.5 Timing Source Progression

Preferred timing progression:

v0.1: PIT-backed coarse timing plus shell-visible tick counter
v0.2: TSC read support with calibration against PIT
v0.3+: cycles/op reporting for hot math and memory kernels
later: compensate for frequency scaling only if needed on real hardware

Do not assume the TSC is perfectly invariant on this machine until tested. Calibrate and report the measurement method.

Example future output:

T500OS> bench modmul
kernel: modmul_u64_sse41
iterations: 1000000
timer: tsc_calibrated_pit
cycles/op: 38
result: PASS


---

7. Security and Trust Model

7.1 Security Ethos

T500OS assumes a trusted local operator. The operator is expected to inspect, judge, and accept responsibility for code before running it.

Core principle:

Local code execution is a trust decision.
Network input is hostile until parsed and validated.

7.2 Local Execution Policy

Early versions do not promise:

sandboxing
privilege separation
multiuser protection
malware resistance
safe execution of unknown binaries
containment of malicious local code

This is acceptable because early T500OS is a single-user research machine.

7.3 Network Boundary Policy

Networking must be treated differently from local code.

Network-facing code must prioritize:

bounds checking
explicit packet length validation
defensive parsing
no inbound services by default
no remote shell by default
no automatic execution of downloaded code
clear logs for packet errors
small attack surface
manual enablement for every listener

Early networking commands should be explicit:

net start
net stop
dhcp
ping
httpget
listen off

7.4 No False Security Claims

T500OS documentation must not claim security properties that are not implemented.

Correct language:

Trusted local execution.
No sandbox currently provided.
Networking parser is bounds-checked.
Inbound services are disabled by default.
Capsules are restartable execution units, not a security sandbox.

Incorrect language:

Secure OS.
Malware-proof.
Sandboxed.
Enterprise-grade.
Hardened multiuser platform.


---

8. External Code and Compatibility Doctrine

8.1 Compatibility Is a Risk Layer, Not a Userspace

T500OS should eventually support installing and running outside source code, but the governing distinction is not kernel space versus userspace.

The meaningful distinction is:

rigorously stable core → controlled research layer → volatile foreign-code layer → hostile network boundary

The native model comes first:

Stable T500OS Core → T500OS Native ABI → Research Runtime → Foreign Compatibility Layer

Not:

Unix clone → POSIX clone → Linux-like userspace → T500OS branding

The compatibility layer must not reshape the core. It is an outer execution/risk layer whose failure should not corrupt the stable core.

8.2 Future Foreign Code Compatibility Layer

A future compatibility layer may support selected external code by one or more methods:

1. source-level porting to the T500OS ABI


2. small libc-like shim for freestanding C programs


3. static binary format designed for T500OS


4. restricted POSIX compatibility only where it helps port useful math/research code


5. bytecode or script runtime for controlled research scripts


6. explicitly crashable/restartable research capsules



Possible layer names:

Foreign Code Compatibility Layer
Volatile Research Layer
T5 ABI Layer
Research Capsule Layer

Avoid the term userspace unless referring specifically to a later hardware-enforced privilege mechanism. It should not be the conceptual foundation.

8.3 Compatibility Acceptance Test

Outside-code compatibility may be added only if it supports at least one core project goal:

faster math computation
better research tooling
easier experiment scripting
useful file conversion
reproducible verification
network retrieval of research material

Compatibility for its own sake is deferred.

8.4 Malicious Code Assumption

If the operator installs unknown code, T500OS should assume the operator has accepted risk unless a real sandbox exists.

The OS may provide warnings and metadata, but it should not pretend to safely contain arbitrary malicious code before isolation is implemented.


---

9. System Architecture Overview

9.1 Initial Architecture

BIOS
  ↓
GRUB / Multiboot2 loader, temporary
  ↓
T500OS kernel
  ↓
Stable core subsystems
  ↓
Research prompt / T5L evaluator
  ↓
Trusted modules, capsules, hardware surgery tools

9.2 Early Monolithic Kernel

T500OS should start as a simple monolithic kernel.

Reason:

easier to debug
fewer privilege-boundary problems
simpler build system
better for early hardware discovery
less IPC complexity

Microkernel-style modularization may be revisited later, but not before storage, shell, framebuffer, and Ethernet basics work.

9.3 Suggested Source Tree

t500os/
  README.md
  CLAUDE.md
  Makefile
  linker.ld
  docs/
    DESIGN.md
    ROADMAP.md
    HARDWARE.md
    DECISIONS.md
    TESTING.md
    DRIFT.md
    BUGS.md
  grub/
    grub.cfg
  boot/
    multiboot2.asm
  kernel/
    main.c
    panic.c
    printk.c
    serial.c
    vga.c
    gdt.c
    idt.c
    isr.asm
    irq.c
    pic.c
    pit.c
    keyboard.c
    memory.c
    pmm.c
    vmm.c
    heap.c
    pci.c
    hw_atlas.c
    t5l_eval.c
    bench.c
    shell.c
  include/
    arch/x86_64/
      io.h
      gdt.h
      idt.h
      cpu.h
      cpuid.h
    kernel/
      printk.h
      panic.h
      memory.h
      pci.h
      hw_atlas.h
      shell.h
      t5l.h
      bench.h
  tools/
    make_iso.sh
    run_qemu.sh
    test_harness.py
    serial_log.sh
    build_cross.sh
    gen_commands_doc.py
  .githooks/
    pre-commit
  build/


---

10. Boot Design

10.1 Initial Bootloader

Initial versions use GRUB with Multiboot2.

Purpose of GRUB:

load kernel into memory
enter a known state
provide memory map
simplify ISO generation
simplify QEMU testing

GRUB is not considered part of T500OS proper.

10.2 Bootloader Ownership Track

GRUB is accepted only as a v0.x acceleration tool. Full ownership of the boot path remains a long-term project requirement.

Bootloader strategy:

v0.0–v0.4: use GRUB/Multiboot2 to accelerate kernel bring-up
post-v0.4: begin custom bootloader track after disk/FAT32 read is stable
later: replace or minimize GRUB dependency for real hardware boot

The custom bootloader track should not block kernel, shell, memory, disk-read, or math-runtime progress. It should begin only after T500OS can already inspect memory, enumerate PCI, read disk sectors, and read a minimal FAT32 volume.

Reason:

GRUB is practical early.
GRUB is not the final identity.
Boot ownership matters after the OS can already read its own storage path.

Possible custom bootloader milestones:

B0: document current GRUB boot contract
B1: parse BIOS memory map independently where possible
B2: load kernel from FAT32 test partition
B3: pass T500OS-native boot info structure
B4: boot without GRUB in QEMU
B5: boot without GRUB on T500 hardware

10.2A Real T500 Boot Media Plan

Real hardware booting should be planned before the first T500 attempt, not improvised.

Preferred early paths:

1. QEMU ISO boot for all initial work
2. controlled GRUB entry from existing Linux install, if available
3. DVD-R/DVD-RW boot using internal optical drive
4. USB boot only after confirming BIOS behavior with the specific stick

Rules:

no disk overwrite for early real-hardware boot
no raw disk write tests on the internal HDD until v0.3 write blockers exist
keep a known-good recovery path before storage experiments
record BIOS settings in every real hardware test log

The internal optical drive is an acceptable first removable-media path because it avoids USB boot quirks and avoids touching the internal disk.

10.3 Kernel Entry Requirements

At kernel entry, T500OS should:

1. validate Multiboot2 magic value


2. initialize serial logging


3. initialize emergency VGA text output


4. print boot banner to serial and screen


5. initialize panic path


6. capture boot information pointer


7. initialize GDT


8. initialize IDT


9. initialize PIC/PIT or APIC path


10. parse memory map


11. initialize physical memory allocator


12. initialize early VMM mapping helpers


13. enable keyboard input


14. enter research prompt / shell



10.4 Boot Banner

Example first screen:

T500OS v0.0
Target: Lenovo ThinkPad T500
Mode: x86_64 long mode
Boot: Multiboot2 via GRUB
Serial: active
Display: VGA text
Panic path: active
Memory map: initializing

T5L prompt pending...

10.5 Early Failure Behavior

If initialization fails before the shell exists:

print a panic message to VGA text screen

print same panic message to serial output

halt CPU with interrupts disabled

include subsystem name and error code


Example:

KERNEL PANIC: memory map missing
stage=boot.parse_multiboot2
error=MB2_NO_MEMORY_MAP


---

11. Debug Infrastructure Doctrine

11.1 Debugging Is a Core Subsystem

T500OS must be designed as a debuggable system from the first bootable artifact. Debugging is not an afterthought or a later developer convenience; it is part of the survival strategy for real hardware bring-up.

Priority order:

serial output → panic path → symbolized kernel build → QEMU serial harness → debug breakpoints → optional GDB remote stub

The OS should not rely only on VGA output. VGA may fail, scroll away, render incorrectly, or become unusable during graphics experimentation. Serial output must come up as early as possible.

11.2 Required Debug Artifacts

Every build should be able to produce:

kernel.elf        unstripped ELF with debug symbols
kernel.map        linker map / symbol map
kernel.bin        bootable stripped or raw image, if needed
serial.log        captured boot/debug output
panic.log         last panic text, when persistence exists

The ISO may boot a stripped binary later, but the build system must preserve a symbolized kernel.elf for QEMU/GDB inspection.

11.3 Serial-First Rule

Serial logging should initialize before most other subsystems.

Early boot order should become:

validate boot entry
initialize serial
initialize emergency text output
print boot banner to serial and screen
initialize panic path
continue hardware setup

11.4 Debug Break Facility

A minimal debug break mechanism should exist once exceptions are working.

Initial form:

debug_break()

Possible behavior:

emit serial marker
trigger int3
halt in a known loop if no debugger is attached
later enter a GDB remote stub

11.5 GDB Stub Policy

A GDB remote stub is valuable, but it must not block the first boot banner.

Accepted path:

v0.0: serial + symbols + QEMU debug flags
v0.1: debug_break and exception register dumps
v0.2/v0.3: minimal GDB remote stub over COM1 if implementation remains bounded

The GDB stub is accepted as a high-leverage tool, not as a new open-ended protocol project.

11.6 Future Symbolized Panic Support

A later panic system should support symbolic stack traces.

Preferred path:

keep kernel.elf and kernel.map from day one
add in-kernel symbol table only after core boot/debug path is stable
define compact symbol format before embedding it
make stack traces optional in release/minimal builds

Do not let symbol-table work block v0.0 or v0.1.

11.7 Persistent Panic Log Policy

Persistent panic logging is deferred until safe storage write support exists.

Before implementation, define:

location: dedicated sector range, FAT32 file, or custom research log store
record format
magic/version/checksum
wraparound behavior
write ordering
failure behavior if panic occurs during log write

No panic log may write to disk unless the storage write blocker and explicit runtime write-enable policy are active.


---

12. CPU and Interrupt Design

12.1 CPU Target

T500OS v0.x targets:

x86_64 long mode
Intel Core 2 Duo class CPU
single-core execution first
dual-core/SMP later

Early versions should ignore the second core.

12.2 Required CPU Setup

Initial kernel must provide:

GDT
IDT
ISR stubs
IRQ handling
basic exception handlers
halt loop
panic path
register dump path

12.3 Exception Handling

Every CPU exception should print:

exception vector
exception name
error code, if present
instruction pointer
code segment
RFLAGS
stack pointer
selected general registers

Initial exception handling does not need stack traces, but the design should leave room for them.

12.4 Timer Strategy

Initial timer path:

PIT timer
fixed tick rate
global tick counter
shell command to view ticks

Later:

TSC read and calibration
local APIC timer
HPET detection
scheduler tick
sleep/delay APIs

12.5 Keyboard Strategy

Initial input:

PS/2 keyboard controller
scancode set handling
US keyboard layout first
line-buffered shell input

Deferred:

full keymap system
international layouts
hotkeys
TrackPoint/mouse


---

13. Memory Management

13.1 Physical Memory Manager

The physical memory manager should parse the bootloader memory map and identify usable regions.

Initial allocator:

bitmap-based page frame allocator
4 KiB pages
allocate page
free page
report total/free/used pages

Shell command:

mem

Example output:

T500OS> mem
Total usable: 1904 MiB
Reserved: 128 MiB
Page size: 4096 bytes
Free pages: 421183
Used pages: 2312
Allocator: bitmap

13.2 Virtual Memory Manager

Identity mapping is allowed only as a temporary bootstrap condition. T500OS should move to a clean virtual memory model early enough that PCI MMIO, framebuffer access, network buffers, capsules, and hardware surgery do not become a pile of hardcoded physical offsets.

Required by the memory/PCI milestone, or immediately after the physical allocator is stable:

fixed kernel virtual base or explicitly documented low-half policy
page table creation
map_page(phys, virt, flags)
unmap_page(virt)
map_region(phys, virt, size, flags)
page fault handler with register dump
kernel heap mapping
MMIO mapping helper
vmm shell command for inspecting mappings

Preferred design:

bootstrap identity map only
then stable kernel mapping
then explicit MMIO mappings
then capsule arenas/guard pages later

The hardware atlas must track both physical and virtual addresses when a device BAR or memory region is mapped.

13.3 Kernel Heap

Initial heap:

bump allocator

Next heap:

free-list allocator

Do not implement a complex malloc before the rest of the kernel needs it.

13.4 Memory Budget Rule

Every major subsystem should document expected memory use.

Example:

VGA text driver: < 16 KiB
Shell/T5L evaluator: < 128 KiB early
PCI table: < 128 KiB
FAT32 cache: configurable, default < 4 MiB
Network buffers: configurable, default < 8 MiB
Capsule arena: explicit per capsule


---

14. Console, Shell, and T5L

14.1 Console Output

Initial console target:

VGA text buffer at 80x25
serial mirror where practical
scrollback not required at v0.0
colored status/panic lines optional

Required functions:

putchar
puts
printf-like formatter
clear screen
set color
scroll

14.2 Serial Output

Serial output should be available early because real hardware debugging may need it.

Initial COM1 configuration:

38400 or 115200 baud
8N1
polling mode

14.3 Shell Design

The shell starts as built-in stable-core code.

The shell is not merely an administrative prompt. It is the primary research interface. It should support both command execution and direct mathematical expression evaluation.

Initial shell features:

prompt
line input
backspace
command parser
expression parser
fixed command table
help command
immediate arithmetic evaluation

Initial commands:

help
clear
version
cpu
mem
ticks
hw
cpuid
pci
pcidump
irq
idt
gdt
keytest
panic
reboot
halt

Initial expression support:

integer arithmetic
hexadecimal and binary literals
operator precedence
parentheses
basic variables later
built-in math functions as they become available

Examples:

T500OS> 2+2
4
T500OS> 0xff * 16
4080
T500OS> let n = 123456789
T500OS> n * n
15241578750190521

14.4 Native Research Language: T5L

Working name:

T5L — T500 Language

T5L should feel direct and approachable like classic BASIC while remaining modern enough for serious math and research.

Design goal:

Boot → prompt → type math immediately

T5L is the default personality of the prompt, not an optional application. Hardware commands remain available, but the first impression of the system should be a research/math instrument, not a generic hobby-OS admin console.

14.5 T5L Language Personality

T5L should be:

interactive first
readable
small enough to implement inside T500OS
usable without a filesystem
deterministic
math-friendly
compilable later
capable of calling optimized T500OS math kernels explicitly

It should not try to become Python, JavaScript, C++, Bash, or POSIX shell.

14.6 BASIC-Esque Immediate Mode

The prompt should support immediate expressions and statements:

T500OS> 2 + 2
4

T500OS> let x = 17
T500OS> x*x + 3*x + 1
341

T500OS> for i = 1 to 10: print i*i

Later, it may support classic numbered-line style as an optional convenience:

10 LET S = 0
20 FOR I = 1 TO 1000
30 LET S = S + I*I
40 NEXT I
50 PRINT S
RUN

Numbered lines are optional. The more important feature is immediate boot-to-math interaction.

14.7 T5L Execution Modes

Staged execution modes:

Mode 0: direct evaluator for integer expressions
Mode 1: interpreted statements and variables
Mode 2: bytecode compiler for loops/functions
Mode 3: native code compiler for hot routines
Mode 4: profile-guided Core 2 optimized code generation

The interpreter comes first. Compilation comes only after correctness and benchmarks exist.

14.8 Early T5L Types

Initial types:

u64
i64
bool

Next types:

bigint
rational
modint
vector
matrix
polynomial

Type design should serve research math, not general application development.

14.9 Explicit Bare-Metal Optimization Hooks

T5L and the future compiler should allow code to explicitly request T500OS-native optimized kernels.

Potential syntax examples:

use kernel modpow_sse41
use arena fast
use profile on
use exact bigint

Potential annotation examples:

@hot
@core2
@sse41
@no_alloc
@arena(fast)
@bounds_checked(false)

Dangerous annotations must be honest. For example, disabling bounds checks should be allowed only in trusted research modules or explicitly volatile capsules.

14.10 Prompt Identity Rule

After v0.1, expression evaluation should be the default interpretation path when input is not recognized as a built-in command.

Priority:

1. exact built-in command match
2. T5L expression or statement
3. helpful parse error

Hardware surgery commands should remain explicit command families. Math should feel immediate.

14.11 Forth-Like Bootstrap Option

A tiny Forth-like threaded interpreter may be prototyped as a bootstrap aid if the BASIC-like evaluator grows too quickly.

Forth-like advantages:

small implementation
interactive
immediate execution
simple dictionary
can call kernel primitives directly
good for hardware surgery and experiments

Constraint:

Forth-like tooling may support bring-up, but it must not replace the long-term T5L prompt identity unless it proves clearly superior for the project mission.


---

15. Hardware Introspection and Live Surgery Console

15.1 Purpose

T500OS should include a first-class hardware introspection interface. The operator should be able to inspect every meaningful hardware layer from the shell without needing external tools.

Working concept:

Hardware Surgery Console

This console is not separate from the shell. It is a command family inside the shell.

15.2 Read-First Principle

Every hardware subsystem should expose read-only inspection before mutation is allowed.

Progression:

detect → describe → dump → decode → benchmark → mutate only if explicitly requested

15.3 Core Commands

Initial command families:

hw                 hardware overview
cpu                CPU summary
cpuid              dump/decode CPUID leaves
regs               selected CPU register state
msr                model-specific register interface, read-first
memmap             boot memory map
pmm                physical allocator state
vmm                page table / mapping state later
gdt                GDT dump
idt                IDT dump
irq                IRQ/PIC/APIC state
pit                timer state
pci                PCI device list
pcidump            raw PCI config dump
bar                PCI BAR decode
io                 I/O port read/write interface
mmio               MMIO read/write interface
ata                ATA controller status
diskraw            raw disk sector lab
fb                 framebuffer/video state later
nic                Ethernet device state later

15.4 Example Interactions

T500OS> hw
Target: ThinkPad T500 profile
CPU: Core 2 Duo T9400
RAM: 1904 MiB usable
PCI devices: 27
Storage path: ATA/IDE probe pending
Network path: Intel 82567LM probe pending

T500OS> cpuid 1
EAX=0001067a EBX=00020800 ECX=0008e3fd EDX=bfebfbff
flags: sse sse2 sse3 ssse3 sse4.1 ...

T500OS> pci 00:19.0 -v
vendor=8086 device=10f5 class=0200
name=Intel 82567LM Gigabit Ethernet
bars: BAR0 mmio ...
status: decoded, driver not attached

T500OS> pcidump 00:19.0
00: 86 80 f5 10 ...
...

T500OS> idt
vector 00 divide_error handler=...
vector 0e page_fault handler=...
vector 20 timer_irq handler=...

15.5 Mutation / Surgery Mode

Hardware mutation must be possible eventually, but it must be explicit.

Dangerous commands:

io write <port> <width> <value>
mmio write <address> <width> <value>
pci write <bus:dev.fn> <offset> <width> <value>
msr write <index> <value>

These commands must require surgery mode.

Example:

T500OS> surgery on
warning: hardware write mode can crash or damage running state
classification required: trusted_research_module
T500OS[surgery]> pci write 00:19.0 0x04 u16 0x0007
logged: pci write device=00:19.0 offset=0x04 width=16 old=0x0003 new=0x0007

15.6 Surgery Log

Every hardware mutation should be logged in a ring buffer.

Log fields:

tick/time
command
subsystem
target
old value, if readable
new value
classification
result
panic risk note, if known

Command:

surgerylog

When storage write support exists, dangerous operations should optionally persist the surgery log before mutation.

15.7 Register Maps

T500OS should prefer decoded register maps over raw hex when documentation is available.

Example:

T500OS> pci 00:19.0 status
COMMAND: io=1 mem=1 busmaster=1 special=0 mwie=0 vga=0 parity=0 serr=0 int_disable=0
STATUS: cap_list=1 interrupt_status=0 fast_back=0 parity_error=0

Unknown registers should still be dumpable as raw values.

15.8 Hardware Atlas

The OS should maintain a live hardware atlas: a structured internal map of detected devices, address regions, registers, interrupts, and driver ownership.

The atlas should track:

CPU capabilities
memory regions
reserved regions
PCI devices
PCI BARs
I/O port reservations
MMIO reservations
physical and virtual mappings
interrupt lines/vectors
driver attachment status
known safe read registers
known dangerous registers

The hardware atlas becomes the backbone for probing, debugging, driver development, and performance tuning.


---

16. PCI and Hardware Discovery

16.1 PCI Enumeration

The PCI subsystem should scan bus/device/function and list:

vendor ID
device ID
class code
subclass
programming interface
command register flags
status register flags
interrupt pin/line
capabilities pointer, if present
BARs and decoded regions

Initial commands:

pci
pci -v
pcidump <bus:dev.fn>
bar <bus:dev.fn>

Verbose PCI output should decode every known flag, not merely print device IDs.

16.2 T500 Hardware Recognition

T500OS should eventually recognize expected hardware IDs and print friendly names for target devices.

Example:

Intel 82567LM Gigabit Ethernet: detected
Intel ICH9 ATA/SATA controller: detected
Intel Mobile 4 Series Graphics: detected
ATI Mobility Radeon HD 3650: detected, ignored by policy

16.3 Hardware Policy Table

T500OS should maintain a compile-time hardware policy table:

supported_now
probe_only
ignore
forbidden_until_later

Example:

Intel 82567LM Ethernet: probe_only until net milestone
ATI Radeon HD 3650: ignore until graphics milestone
Intel Wi-Fi 5300: forbidden_until_later


---

17. Storage Design

17.1 Storage Milestones

Recommended storage progression:

v0.1: no disk required
v0.2: no writes, memory/PCI only
v0.3: ATA PIO identify command and sector read
v0.4: MBR partition scan and FAT32 read-only
later: limited write only after heavy gating
later: AHCI driver

17.2 ATA First

Because the T500 BIOS may expose SATA in IDE/compatibility mode, ATA PIO is the simplest first storage path.

Initial commands:

diskinfo
readsector <lba>
hexdump <lba> [count]

17.3 Filesystem Strategy

First filesystem:

FAT32 read-only

Reasons:

simpler than ext4
easy to inspect from Linux
works well with boot partitions
adequate for early configuration files and logs

Strict FAT32 scope limit:

read-only
bounds-checked
minimal cache
no long detour into filesystem sophistication
no write support until math/runtime/debug foundations justify it

FAT32 exists to load scripts, logs, small data, and eventually boot artifacts. It must not become the center of the project before the math/runtime kernels are benchmarked.

Second filesystem candidate:

ext2 read-only or read/write

Custom research store candidate later:

sequential append-oriented store for logs, benchmark output, scripts, and large math datasets

Do not attempt ext4 early.

17.4 Disk Safety Rule

No write operation may be enabled until:

1. read path is stable


2. partition bounds checking exists


3. QEMU disk-image test exists


4. write-protection flag exists


5. command requires explicit confirmation or developer build flag



17.5 Development Write Blocker

Storage write support must be gated at both compile time and runtime.

Default development builds should refuse disk writes unless explicitly compiled with:

-DALLOW_WRITE

Runtime command gate:

write enable
write disable
write status

Rules:

no startup path may enable writes automatically
sector writes require explicit write-enabled state
filesystem writes require explicit write-enabled state
raw disk writes require surgery mode plus write-enabled state
public/test builds default to read-only

This protects the host disk, MBR, partition table, and future T500OS filesystems from accidental early-driver damage.


---

18. Graphics and UI Design

18.1 Graphics Milestones

v0.0: VGA text mode
v0.5: VESA framebuffer
v0.5+: software font renderer
later: card-style graphical shell
later: mouse pointer
much later: native Intel mode-setting experiment

18.2 VESA Framebuffer First

The first graphical mode should use VESA/linear framebuffer if available. This avoids native GPU-driver complexity.

Target resolution:

1280x800 preferred
1024x768 fallback
800x600 fallback

18.3 UI Philosophy

The graphical UI should be:

low animation
no compositor
keyboard-first
card/panel based
readable on 1280x800
optimized for status and command execution

Initial graphical components:

status bar
command panel
log panel
hardware summary panel
file list panel later
network panel later

18.4 No Desktop Metaphor First

Do not implement early:

draggable windows
wallpaper system
transparency
icon grid
taskbar with arbitrary apps
themes beyond basic colors/fonts

The first GUI is a control dashboard, not a consumer desktop.


---

19. Math and Research Runtime Design

19.1 Purpose

The math/research runtime is the long-term heart of T500OS. It should provide fast local computation without requiring a Unix-like process model, heavyweight dynamic linker, or general desktop stack.

The runtime is organized by stability and crash-risk layer, not by inherited userspace/kernel-space terminology.

19.2 Early Runtime Shape

Early research commands may run as built-in core commands or statically linked research modules in developer builds.

Early examples:

bench memcpy
bench memset
hash test
modmul test
bigint selftest

This is not a final containment model. It is an efficient bring-up model. Early research commands are trusted but should still be written so that faults are visible, diagnosable, and eventually isolatable.

19.3 Later Runtime Shape

Later, research code should move into explicit execution layers with a native T500OS ABI. The goal is not to create Unix-like userspace; the goal is to separate stable machinery from volatile computation.

Possible progression:

stable core commands
→ trusted statically linked research modules
→ restartable research capsules
→ T500 executable format
→ optional compatibility shim for selected C/POSIX-like code

Risk progression:

Core: must not crash under normal operation
Trusted research modules: allowed to fail during development, but not corrupt core state
Research capsules: expected to be restartable after crash/fault
Foreign compatibility code: treated as volatile unless audited
Network-fed code/data: hostile until explicitly accepted

19.4 Optimization Targets

Initial performance kernels should focus on operations useful for mathematical research and verification:

memory copy/fill/compare
integer parsing/formatting
modular addition/multiplication/exponentiation
fixed-width vector operations
arbitrary precision limb operations
polynomial coefficient loops
hash/checksum pipelines
simple matrix multiply

19.5 Profiling Requirement

A profile or bench mechanism should exist before serious optimization claims are accepted.

Example future output:

T500OS> bench modmul
kernel: modmul_u64_sse41
iterations: 1000000
timer: tsc_calibrated_pit
cycles/op: 38
result: PASS


---

20. System-Optimized Compiler Doctrine

20.1 Long-Term Goal

T500OS should eventually include a system-optimized compiler pipeline for selected languages. The compiler should embed T500OS bare-metal enhancements into code explicitly instead of hiding them behind generic runtime assumptions.

The goal is not broad language compatibility. The goal is fast research execution on this exact hardware.

20.2 Compiler Targets

Initial native target:

T5L → evaluator

Later targets:

T5L → T5 bytecode or IR
T5L → T500 native code
restricted C subset → T500 native code
selected external math code → T500 research capsule

Do not attempt full C/C++/Python compatibility early.

20.3 Optimization Philosophy

The compiler should optimize for:

Core 2 Duo T9400
x86_64 without AVX
SSE/SSE2/SSE4.1 where useful
small cache behavior
low allocation pressure
predictable memory arenas
loop-heavy integer/math workloads
exact arithmetic kernels
deterministic benchmark output

20.4 Explicit Hardware Enhancement Model

T500OS should make hardware-specific enhancements visible and intentional.

Examples:

compile hot functions with Core 2 profile
route modular arithmetic to optimized kernel
place working buffers in explicit arenas
emit SSE4.1 loop variant when benchmarked faster
disable generic safety checks only under explicit trusted/volatile classification

The compiler should be able to generate reports such as:

function: modpow_batch
classification: trusted_research_module
backend: native_x86_64_core2
optimizations: unroll=4, sse41=yes, heap_alloc=no
estimated stack: 2048 bytes
benchmark: pending

20.5 Compiler Safety Honesty

The compiler may allow unsafe performance features, but it must label them clearly.

Correct behavior:

warning: @bounds_checked(false) requires trusted_research_module or volatile capsule classification
warning: native pointer arithmetic can corrupt capsule memory
warning: no sandbox is active

Incorrect behavior:

silently compiling unsafe code as if contained
pretending hostile code is sandboxed
hiding architecture-specific assumptions


---

20A. Python and MicroPython Compatibility Policy

20A.1 Placement

Python support is a foreign compatibility goal, not part of the stable core and not a peer of T5L.

Correct placement:

MicroPython/CPython → foreign compatibility layer
runs inside → restartable research capsule
calls down into → trusted T500OS math kernels through explicit FFI

T5L remains the native research instrument. Python is a guest language.

20A.2 First Concrete Python Target

The first Python-family target should be a MicroPython capsule, not CPython and not Python-source-to-T5L translation.

Reason:

smaller porting surface
more suitable for constrained/bare-metal-style environments
useful for scripting research workflows
does not require owning Python language semantics forever

20A.3 FFI Requirement for Math Kernels

Math kernels must be callable through a stable foreign-function interface, not only from T5L.

The FFI should expose trusted kernels such as:

modular arithmetic
bigint limb operations
hash/checksum kernels
matrix/vector kernels
benchmark/profiling hooks

This prevents the optimized research runtime from becoming trapped inside one language frontend.

20A.4 Python Translation Rejection

Do not attempt Python source translation into T5L bytecode early.

Rejected early path:

Python source → T5L frontend → T5 bytecode

Reason:

owning Python frontend semantics is much larger than embedding or porting an existing interpreter

Preferred path:

MicroPython interpreter in capsule → explicit FFI → T500OS optimized kernels

20A.5 CPython and Scientific Python Scope

CPython is a long-term revisit item, not a committed early milestone.

Explicitly out of scope until CPython itself works:

NumPy compatibility
SciPy compatibility
SymPy compatibility
pandas compatibility
arbitrary C-extension ecosystem

Future Python value should come from familiar scripting syntax calling T500OS-native math kernels, not from recreating a full Linux Python ecosystem.

21. Network Stack Policy

21.1 Protocol Pragmatism

The rejection of inherited OS architecture does not require writing every protocol state machine from scratch. TCP/IP is a protocol domain with many edge cases. A proven embedded stack may be used if it clearly improves correctness, development leverage, and anti-drift discipline.

Accepted candidates:

lwIP
uIP
other tiny permissively licensed embedded TCP/IP stack after audit

This is not a violation of T500OS doctrine if the borrowed stack is contained, audited, and replaceable.

21.2 Stable Core / Network Split

The stable core should provide only the minimum required network substrate:

NIC driver bring-up
raw Ethernet TX/RX queues
packet buffer arenas
time source
explicit start/stop control
hardware atlas registration

Higher protocols should initially live outside the stable core:

ARP/DHCP/IP/TCP/HTTP → net capsule or network module

21.3 Network Capsule Rules

The network stack should be treated as hostile-input-facing code.

Rules:

bounded packet buffers
no unbounded allocation from packet input
clear input/output queues
drop malformed packets
log parse errors
no inbound listener by default
no auto-execution of fetched data
restartable when possible

21.4 Borrow-Then-Replace Path

Borrowing a small stack is acceptable as a bootstrapping move.

Lifecycle:

port small proven stack
wrap in T500OS packet queues
expose explicit shell commands
audit hot paths and parsers
replace or specialize pieces only when justified

This keeps the project moving toward useful Ethernet and HTTP without turning the whole OS into a network-stack research project.


---

22. Stability and Risk Layer Strategy

22.1 No Userspace Assumption

T500OS should not assume the Unix distinction of kernel space versus userspace as the primary design model.

The early system is a single trusted machine with a rigorously stable core and progressively less trusted outer execution layers.

The correct early question is not:

Is this kernel-space or user-space?

The correct question is:

How stable must this component be, and what damage may it cause if it crashes?

22.2 Core Stability Layers

Conceptual layers:

Layer 0: Boot and hardware bring-up
Layer 1: Stable core
Layer 2: Trusted research modules
Layer 3: Restartable research capsules
Layer 4: Foreign compatibility layer
Layer 5: Network boundary

22.3 Layer 0 — Boot and Hardware Bring-Up

Responsibilities:

boot entry
early console
panic path
GDT/IDT
memory map capture
transition to stable core

Failure policy:

fail hard, print clear panic, halt

This layer must remain tiny.

22.4 Layer 1 — Stable Core

Responsibilities:

memory allocator
interrupt control
timer
shell substrate
logging
PCI discovery
core diagnostics
stable driver interfaces
stable benchmark timer

Failure policy:

must not crash under normal operation
panic only on invariant violation
never trust volatile layers blindly

This is the part of the OS that must be boring, strict, and hard to break.

22.5 Layer 2 — Trusted Research Modules

Responsibilities:

built-in math commands
benchmark kernels
hash/checksum routines
exact arithmetic experiments
hardware-specific optimized routines

Failure policy:

trusted but experimental
bugs are acceptable during development
must not silently corrupt stable core state
should expose self-tests and benchmarks

These modules may run close to the metal for speed.

22.6 Layer 3 — Restartable Research Capsules

Responsibilities:

larger experimental computations
long-running math jobs
scripts or bytecode later
external source code after porting

Failure policy:

may crash
may be killed/restarted
must have explicit input/output boundaries
should support checkpointing later

This layer is the meaningful replacement for the vague word userspace in this project.

22.7 Layer 4 — Foreign Compatibility Layer

Responsibilities:

selected external source-code compatibility
tiny libc-like shim if justified
optional POSIX-like functions only when useful
static executable format or capsule packaging

Failure policy:

volatile unless audited
not allowed to redefine core architecture
not trusted with networking by default
not allowed to claim sandboxing unless real isolation exists

22.8 Layer 5 — Network Boundary

Responsibilities:

packet parsing
DHCP/ARP/IP/TCP/HTTP input handling
future file retrieval
future remote-control surfaces, if any

Failure policy:

network input is hostile
bounds-check everything
no inbound services by default
no automatic execution from network data


---

23. Concrete Capsule Execution Model

23.1 Purpose

The stability/risk-layer model needs a concrete execution mechanism before large non-core code exists. The first capsule model does not need full hardware isolation, but it must define entry, exit, memory ownership, and abort behavior.

23.2 Initial Capsule Model

Early capsules may run in the same privilege level as the core, but they must have explicit boundaries.

Initial capsule structure:

capsule entry function
capsule-local stack
capsule arena allocator
capsule resource list
capsule status/result block
capsule abort path

23.3 Capsule Arena

Each capsule should receive a bounded memory arena.

Arena metadata:

base
size
used
high_water_mark
owned pages/regions
classification
abort cleanup function

A capsule may allocate only from its arena unless explicitly granted core access.

23.4 Capsule Abort Path

Abort conditions:

fault
timeout later
manual abort
resource violation later
explicit capsule failure

Initial abort behavior:

record fault context
release capsule arena
release capsule-owned resources
return to shell when possible
panic only if stable core invariants are damaged

23.5 Timer and Fault Integration

The first implementation may be cooperative. Later implementations should add:

timer budget
page-fault recovery for capsule mappings
guard pages
explicit kill/restart command

Example commands:

capsules
capsule run <name>
capsule kill <id>
capsule log <id>

23.6 No Fake Isolation

Until separate page tables or hardware protection exist, documentation must say:

Capsules are restartable execution units, not a security sandbox.


---

24. Process, Scheduling, and SMP

24.1 Early Execution Model

Early T500OS should not implement full processes.

Initial model:

single kernel thread
interrupt-driven input/timer
synchronous shell commands

24.2 Later Cooperative Tasks

Next step:

cooperative kernel tasks
simple task table
manual yield

24.3 Later Preemptive Scheduler

Preemptive scheduling is deferred until after:

timer is stable
memory management is stable
shell exists
storage basics exist
capsule model exists

24.4 SMP Deferred

Second CPU core should remain unused until the single-core kernel is stable.

Do not implement SMP early.


---

25. Build System

25.1 Initial Toolchain

Development host:

Current Linux Mint install on the T500 or another Linux machine

Required tools:

gcc or x86_64-elf-gcc
ld or x86_64-elf-ld
nasm
make
grub-mkrescue
xorriso
qemu-system-x86_64
python3, for harness

The v0.0 path may use the host compiler if the freestanding flags are strict. Before v0.2, the project should have a reproducible cross-toolchain plan.

25.2 Cross-Compiler Policy

Phase 1 may use the host compiler carefully if configured for freestanding output.

A dedicated cross-compiler should be introduced once the first kernel boots reliably and before v0.2 becomes complex.

Required cross-toolchain artifact:

tools/build_cross.sh

It should define:

binutils version
gcc version
target triplet: x86_64-elf
install prefix: toolchain/x86_64-elf or /opt/t500os-toolchain
verification command
expected compiler target output

A Dockerfile, flake.nix, or equivalent reproducible environment may be added later, but the T500 must also retain a plain local build path.

Kernel compile flags should include:

-ffreestanding
-fno-stack-protector
-fno-pic
-mno-red-zone
-nostdlib

-nostdinc may be added later once the include structure is mature.

25.3 Build Targets

Recommended make targets:

make all
make clean
make iso
make run
make run-serial
make debug
make test-qemu
make test-shell
make test-math
make realhw-checklist

25.4 Artifact Policy

Build outputs go under:

build/

No generated files should be committed except intentional documentation artifacts.

Every build should produce:

build/kernel.elf
build/kernel.map
build/t500os.iso

Serial logs should be persisted by commit when practical:

build/serial-<git-sha>.log

This enables regression comparison against known-good boot output.

25.5 Freestanding libk Primitive Policy

T500OS must provide its own small kernel primitive library.

Home:

kernel/libk/
include/kernel/libk.h

Required early functions:

memcpy
memset
memcmp
memmove
strlen
strnlen
strcmp
strncmp

Naming policy:

public kernel names may use t500_ prefix internally
compiler-required symbols such as memcpy/memset may also be provided when needed

Compiler policy:

use -ffreestanding
consider -fno-builtin or targeted -fno-builtin-memcpy/-fno-builtin-memset if compiler emits unwanted calls
keep scalar reference implementations
benchmark optimized variants later

25.6 Floating-Point and SSE State Policy

Early kernel code is integer-only.

Default policy:

no floating-point in stable core
no implicit XMM/FPU use in interrupt handlers
compile ISR/low-level code with flags that prevent accidental FP/vector register use where practical
save/restore only general-purpose registers initially

SSE is allowed only in explicitly classified trusted math kernels after an FPU/SSE state policy exists.

Before enabling SSE kernels, define:

CR0/CR4 setup
FXSAVE/FXRSTOR or equivalent state handling
which layers may use SSE
whether interrupts can occur inside SSE code
how capsule/math state is saved or invalidated

Rule:

No SSE optimization may enter trusted research modules until the kernel can honestly preserve or constrain FPU/XMM state.

25.7 Build Flag Taxonomy

Build flags must be classified to avoid safety gates being treated as ordinary features.

Categories:

feature flags: enable optional subsystem code
debug flags: add diagnostics, assertions, traces
safety gates: permit dangerous behavior only when explicitly requested
optimization flags: choose tuned implementation variants

Examples:

T500_FEATURE_FRAMEBUFFER
T500_DEBUG_SERIAL_TRACE
T500_SAFETY_ALLOW_WRITE
T500_OPT_CORE2_SSE41

Rules:

safety gates default off
safety gates must be visible in boot banner or build info
optimization flags must not change correctness
feature flags must not bypass milestone gates

25.8 Endianness and Bus Helper Policy

Hardware and protocol helpers should standardize byte order from the first relevant subsystem.

Examples:

pci_read_le16
pci_read_le32
mmio_read_le32
net_read_be16
net_write_be32

This prevents silent byte-order drift between PCI, storage, and network code.

25.9 License Policy

The repository should include a license before external code is imported.

Recommended personal-project default:

MIT or BSD-style license for maximum reuse flexibility

If GPL components are imported later, the decision ledger must record license implications before import.


---

26. Testing Strategy

26.1 Test Environments

T500OS should be tested in this order:

1. QEMU basic boot


2. QEMU serial log


3. QEMU automated shell harness


4. QEMU disk-image tests


5. real T500 boot through controlled GRUB entry


6. real T500 hardware diagnostic commands



26.2 Minimum QEMU Test

The kernel must boot in QEMU and print:

T500OS v0.0
kernel initialized
T500OS>

26.3 Automated Test Harness

A fast QEMU regression harness should exist from the beginning.

A tool such as tools/test_harness.py should:

launch QEMU
capture serial output
wait for the T500OS prompt
send shell commands
capture responses
compare expected output patterns
return nonzero on failure

Initial command script:

version
help
2+2
panic-test, only in controlled mode

Later command script:

mem
cpuid
pci
pcidump
bench

26.4 Test Targets

Recommended make targets:

make test-qemu
make test-serial
make test-shell
make test-math
make test-panic
make test-regression

Minimum early automated assertions:

boot banner appears on serial
prompt appears
2+2 returns 4
unknown command does not crash
panic-test produces controlled panic output

26.5 Real Hardware Test Log

Every real hardware test should record:

date
commit/hash or archive version
boot method
BIOS settings
graphics mode
observed output
keyboard status
timer status
panic/errors
next action

26.6 Regression Rule

A feature is not considered stable until it survives:

3 consecutive QEMU boots
3 consecutive real hardware boots, when applicable
basic shell interaction
no unexpected exception/panic

26.7 Git Discipline

The project should use Git from the first file.

Rules:

one commit per working increment
tag each milestone
keep build artifacts out of commits
commit design changes separately from code changes when practical
preserve known-good boot points for bisecting

Suggested tags:

v0.0-boot-banner
v0.1-interrupt-shell
v0.2-hardware-atlas


---

26A. Agent-Assisted Development Workflow

26A.1 CLAUDE.md Requirement

Before kernel code is generated, the repository must contain:

CLAUDE.md

Purpose:

compress the design doctrine into a short agent-readable rule file
state the current milestone
state forbidden work for the current milestone
state required test command
state classification-header requirement
state anti-drift rules

Claude Code or any coding agent should read this file at the start of every session.

26A.2 Agent Heartbeat Command

The standard agent validation loop is:

make test-qemu

Every implementation task should end with this command unless the task is documentation-only or explicitly marked as non-buildable.

The harness should fail on:

missing boot banner
missing serial output
missing prompt once prompt exists
2+2 failing once math evaluator exists
unexpected panic
changed output without updated expectation

26A.3 Pre-Commit Hook

A git pre-commit hook should run the relevant test tier for the current milestone.

Early hook:

make test-qemu

Later hook may split fast and slow tests.

26A.4 Milestone Diff Discipline

Each milestone should be tagged.

Agent work should often compare against the prior milestone:

git diff v0.1-interrupt-shell..HEAD
git diff v0.2-hardware-atlas..HEAD

This makes drift visible.

26A.5 Multi-Model Role Split

Recommended roles:

Architect reviewer: checks design violations and milestone drift
Implementer: edits repository and runs tests
External reviewer: reads code without design doc and checks standalone clarity
Hardware oracle: answers narrow datasheet questions with citations required
Math kernel specialist: reviews optimized arithmetic/SSE claims later

The implementer and reviewer should preferably be different model families to reduce shared blind spots.

26A.6 Agent Scope Rule

Do not ask an agent to implement a whole milestone at once.

Correct task shape:

Implement serial COM1 output and prove boot banner appears in serial.log.
Implement panic() and prove panic-test prints expected message.
Implement integer expression parser until 2+2 passes test harness.

Incorrect task shape:

Implement v0.2.
Build the OS.
Add networking.

27. Documentation Strategy

27.1 Required Docs

docs/DESIGN.md       architecture and philosophy
docs/ROADMAP.md      milestones and completion status
docs/HARDWARE.md     T500-specific hardware information
docs/DECISIONS.md    decision ledger
docs/TESTING.md      test procedures and logs
docs/DRIFT.md        anti-drift rules and deferred ideas
docs/BUGS.md         known issues
docs/COMMANDS.md     generated command reference, once shell table exists
CLAUDE.md            root agent instruction file, not optional

27.2 Decision Ledger Format

Every architectural decision should be recorded.

Example:

Decision ID: D0001
Topic: Bootloader
Decision: Use GRUB/Multiboot2 for v0.x.
Reason: Avoid bootloader complexity until kernel is useful.
Rejected alternatives: custom MBR bootloader immediately, UEFI-only boot.
Revisit condition: after shell, disk read, FAT32 read-only, and hardware atlas milestones.
Status: Accepted

27.3 Deferred Ideas List

Any tempting idea that appears mid-project should go into docs/DRIFT.md, not the current milestone.

Example:

Idea: custom JavaScript engine
Status: deferred
Reason: browser stack is not part of v0.x
Revisit after: HTTP client + text HTML viewer


---

28. Coding Standards

28.1 Language

Initial languages:

C
NASM assembly
Make
Python for test harness
Shell scripts for tooling

28.2 Kernel Style

Rules:

no libc dependence
no dynamic allocation before allocator init
no recursion in kernel core
explicit integer widths
explicit error codes
simple structs
no clever macro-heavy abstractions early
comments explain hardware assumptions

28.3 Error Style

Use explicit status codes where practical.

Example:

typedef enum {
    T500_OK = 0,
    T500_ERR_INVALID_ARG,
    T500_ERR_NOT_FOUND,
    T500_ERR_HW_TIMEOUT,
    T500_ERR_UNSUPPORTED,
} t500_status_t;

28.4 Logging Style

Use subsystem prefixes:

[boot] parsed multiboot2 info
[mem] usable memory: 1904 MiB
[pci] 00:19.0 Intel Ethernet detected
[kbd] keyboard IRQ enabled

28.5 Component Classification Headers

Every substantial component must declare its stability/risk classification in source comments.

Required classification values:

stable_core
trusted_research_module
restartable_research_capsule
foreign_compatibility_layer
network_boundary

Suggested source header pattern:

/*
 * T500OS Component: pci_core
 * Classification: stable_core
 * Failure policy: panic only on invariant violation; never trust device input blindly
 * Owns: PCI enumeration tables, read-only config access helpers
 * Mutates hardware: no, except through explicit surgery-mode call path
 */

This prevents the stability model from remaining only a document-level idea.


---

29. Anti-Drift Governance

29.1 The Milestone Gate Rule

No milestone may begin until the previous milestone has a clear pass/fail result.

29.2 The Temptation Rule

If a feature sounds exciting but is not required for the current milestone, it goes into DRIFT.md.

29.3 The Hardware Rule

If a feature does not improve the T500 target, it is deferred.

29.4 The Browser Rule

No browser work until Ethernet, HTTP GET, filesystem read, and framebuffer text rendering exist.

29.5 The Wi-Fi Rule

No Wi-Fi work until wired Ethernet can DHCP and ping reliably.

29.6 The GPU Rule

No native GPU acceleration until VESA framebuffer UI is stable.

29.7 The Filesystem Write Rule

No disk writes until read-only disk and filesystem code have test coverage in QEMU disk images.

29.8 The SMP Rule

No second-core work until the single-core system is stable.

29.9 The Performance Rule

No abstraction may be added to a hot path unless it is required for correctness, debugging, or measured performance.

29.10 The Borrowed-Architecture Rule

Do not copy Linux, BSD, Windows, POSIX, or Unix structures unless the design decision ledger explicitly explains why the borrowed structure is best for T500OS.

29.11 The Compatibility Rule

No compatibility layer may reshape the stable core architecture. Compatibility must remain an outer risk layer above the native T500OS model.

29.12 The Local-Trust Rule

Do not add heavyweight local security machinery before there is a concrete execution layer that needs it. Do harden network input from the beginning.

29.13 The Stability-Layer Rule

Classify components by required stability and crash risk, not by inherited userspace/kernel-space terminology.

29.14 The Hardware Surgery Rule

Read-only hardware introspection should be easy. Hardware mutation should be possible only through explicit surgery mode.

Rules:

read by default
write only after explicit surgery on
log every mutation
show old value when possible
classify crash risk
never hide dangerous register writes behind friendly commands

29.15 The T5L Rule

The shell math evaluator is permanent and supported. The optimizing compiler is deferred until the evaluator, benchmark path, memory model, and capsule model exist.

29.16 The GRUB Retirement Rule

GRUB may accelerate v0.x, but the project must maintain a documented bootloader ownership track after disk/FAT32 read is stable.

29.17 The Python Rule

No Python-family work may begin until the capsule model survives controlled testing and the T5L benchmark core is stable.

Rules:

T5L remains native
MicroPython may be a future guest capsule
CPython is revisit-only
no Python-to-T5L translation project early
no NumPy/SciPy/SymPy compatibility claims before CPython feasibility exists

29.18 The Agent Governance Rule

No AI coding agent should modify implementation files without an up-to-date CLAUDE.md, current milestone target, and test command.

Required agent loop:

read CLAUDE.md
make scoped change
run make test-qemu
report diff and test result


---

30. Roadmap

30.0 Audit-Promoted Global Requirements

The following requirements apply across early milestones:

serial logging before VGA dependence
kernel.elf with debug symbols every build
kernel.map every build
QEMU serial test harness early
math evaluator test from the first interactive shell
identity mapping only as temporary bootstrap
map_page/unmap_page before serious driver work
hardware atlas tracks physical and virtual mappings
network stack may borrow lwIP/uIP if capsule-contained
FAT32 remains minimal and read-only early
disk writes blocked by default unless ALLOW_WRITE and runtime write-enable are active
capsules use explicit arenas and abort paths
component classification appears in docs and source comments
TSC timing is calibrated before cycles/op claims
Git from first commit

These are not optional polish items. They reduce bring-up pain and prevent architectural rot.

30.1 T500OS v0.0 — Boot and Debug Seed

Goal:

Boots in QEMU, prints banner through serial and VGA, and has a panic path.

Required:

project tree
Git repository
Makefile
linker script
Multiboot2 header
kernel entry
serial output
VGA text output
panic function
kernel.elf with debug symbols
kernel.map
QEMU run target
ISO build target
basic serial capture
classification headers in source files

Done criteria:

make iso succeeds
make run boots in QEMU
screen displays T500OS banner
serial log receives boot text
panic() visibly halts with message
kernel.elf and kernel.map exist

30.2 T500OS v0.1 — Interrupt Shell + Immediate Math

Goal:

Interactive shell with timer, keyboard, and immediate arithmetic evaluation.

Required:

GDT
IDT
exception handlers
PIC remap
PIT timer
keyboard IRQ
shell prompt
commands: help, clear, version, ticks, reboot, halt
integer expression parser
operator precedence
decimal and hexadecimal integer input
direct expression evaluation at prompt
first bench stub or timing command
automated QEMU test proving 2+2 works

Done criteria:

keyboard input works
backspace works
timer tick command works
unknown command handled cleanly
exceptions print useful panic/register messages
2+2 evaluates to 4 at the shell prompt
hex arithmetic works
expression errors do not crash the core

30.3 T500OS v0.2 — Memory, VMM, PCI, and Hardware Atlas

Goal:

Memory map, physical allocation, early VMM, PCI enumeration, and first hardware atlas.

Required:

Multiboot2 memory map parser
physical page allocator
early heap
map_page/unmap_page
map_region
MMIO mapping helper
page fault handler with register dump
mem command
vmm command
hw command
cpuid command
PCI config access
pci command
pcidump command
BAR decode stub
GDT/IDT dump commands
T500 hardware ID recognition table
initial hardware atlas structure
TSC read + PIT calibration experiment

Done criteria:

mem reports plausible RAM
vmm shows known mappings
map_page/unmap_page pass QEMU tests
hw prints hardware overview
cpuid dumps and decodes basic CPU flags
pci lists real devices in QEMU
pci lists real T500 devices on hardware, when tested
pcidump shows raw config space
idt/gdt dumps do not crash
allocator can allocate/free test pages

30.4 T500OS v0.3 — Disk Read Lab

Goal:

Read sectors from disk safely, with writes impossible by default.

Required:

ATA identify
sector read
diskinfo command
readsector command
hexdump command
QEMU disk-image test
-DALLOW_WRITE blocker, off by default
runtime write status command

Done criteria:

can identify QEMU disk
can read sector 0
can print MBR bytes
no write path exists unless explicitly compiled and enabled
write status reports disabled by default

30.5 T500OS v0.3A — Debug Stub Seed

Goal:

Add bounded debugger hooks after exceptions and serial logging are stable.

Required:

debug_break()
serial debug marker
exception register dump
symbolized GDB/QEMU workflow documentation
optional minimal GDB remote stub if bounded

Done criteria:

debug_break produces predictable halt/trap behavior
exceptions print useful register state
QEMU/GDB can inspect symbolized kernel.elf
feature does not block ordinary boot

30.6 T500OS v0.4 — FAT32 Read-Only

Goal:

Read files from a FAT32 partition.

Required:

MBR parser
FAT32 BPB parser
root directory listing
file read
commands: ls, cat
minimal cache
bounds checking
write blocked

Done criteria:

can list files on test FAT32 image
can cat a text file
bounds checking exists
read-only enforced
FAT32 code remains minimal

30.7 Bootloader Ownership Track Begins

Trigger:

After v0.4 passes.

Goal:

Begin replacing GRUB dependency without blocking main OS progress.

Initial tasks:

document GRUB boot contract
create native boot info structure
experiment with FAT32 kernel loading in QEMU

30.8 T500OS v0.5 — Framebuffer UI

Goal:

Switch from VGA text to framebuffer-rendered text dashboard.

Required:

framebuffer initialization
font rendering
basic drawing primitives
status bar
log panel
command panel
VGA fallback

Done criteria:

text is readable at chosen resolution
keyboard shell still works
fallback to VGA text exists
no compositor or windowing yet

30.9 T500OS v0.6 — Capsule Arena/Abort Core

Goal:

Make the stability-layer model executable.

Required:

capsule structure
capsule-local stack
arena allocator
resource list
status/result block
manual abort path
capsule commands

Done criteria:

can run a test capsule
can abort a capsule manually
capsule arena is released after abort
no fake sandbox claims

30.10 T500OS v0.7 — Ethernet Raw Frames

Goal:

Interact with Intel 82567LM Ethernet hardware.

Required:

PCI BAR mapping
NIC reset/init
read MAC address
TX descriptor path
RX descriptor path
raw packet send/receive
nic command

Done criteria:

mac command prints real MAC
link status visible
can send raw Ethernet frame
can receive broadcast frame

30.11 T500OS v0.8 — Network Capsule, DHCP, and HTTP GET

Goal:

Obtain IP address and fetch a simple webpage through contained network stack.

Required:

network capsule
raw packet queues
borrowed or native ARP/DHCP/IP/TCP path
explicit net start/stop
httpget command
parse/error logs
no inbound listener by default

Done criteria:

DHCP lease obtained
gateway configured
can ping router or equivalent diagnostic works
httpget can fetch a simple plain HTTP page
malformed packets do not crash stable core in QEMU tests where practical

30.12 T500OS v0.9 — T5L Foundation

Goal:

Turn the shell math evaluator into a small native research language.

Required:

variables
assignment
built-in functions
simple loops
function definitions
script buffer in memory
clear error messages
integer self-tests

Done criteria:

can define variables
can define and call a simple function
can run a loop-based arithmetic experiment
language errors do not crash the stable core

30.13 T500OS v1.0 — Research Benchmark Core

Goal:

Add deterministic benchmark and profiling commands for early math/research kernels.

Required:

calibrated timing path
bench command
profile command stub
memory throughput benchmark
integer arithmetic benchmark
modular arithmetic self-test
hash/checksum benchmark
scalar reference implementations
optimized variant hooks

Done criteria:

bench command runs repeatably
results show operation count and timing
self-tests distinguish PASS/FAIL
benchmarks run without filesystem dependency

30.14 T500OS v1.1 — T500 Research Workstation Core

Goal:

Stable terminal-first OS core for local mathematical experiments, hardware inspection, file reading, and basic network retrieval.

Required:

stable shell/T5L prompt
memory and PCI inspection
safe disk read path
read-only filesystem
framebuffer or reliable text UI
wired Ethernet DHCP/ping/httpget
benchmark/profiling core
documented trusted-local/security-boundary model
documented stability/risk-layer model
hardware surgery read-first console

Done criteria:

boots reliably on T500
can run local benchmark/research commands
can fetch simple network resources explicitly
contains no false sandbox/security claims
has a documented compatibility-layer plan but does not let it dominate architecture
uses stability/risk layers instead of vague userspace assumptions

30.15 T500OS v1.2 — Native Compiler Seed

Goal:

Compile hot T5L routines into a lower-level representation suitable for benchmarking and later native code generation.

Required:

bytecode or IR format
compiler diagnostics
benchmark comparison against interpreter
explicit optimization report
no false safety claims

Done criteria:

T5L function can be interpreted and compiled
compiled path produces same result as interpreted path
benchmark report shows timing comparison
unsafe options require explicit classification

30.16 T500OS v1.3 — MicroPython Research Capsule

Goal:

Run a small Python-family interpreter as a foreign compatibility capsule that can call selected T500OS math kernels.

Required:

capsule model stable
T5L benchmark core stable
FFI boundary defined
MicroPython or equivalent small interpreter selected after license/portability review
no CPython compatibility claims
no NumPy/SciPy/SymPy claims

Done criteria:

interpreter runs inside a restartable capsule
simple script executes
script can call one approved T500OS math kernel through FFI
capsule crash does not corrupt stable core in controlled tests
all documentation states that this is foreign compatibility, not native T500OS architecture


---

31. Risk Register

R001 — Scope Explosion

Risk:

Project expands into browser, Wi-Fi, GPU, package manager, and compiler before kernel basics exist.

Mitigation:

Milestone gates, DRIFT.md, and current-milestone-only implementation.

R002 — Real Hardware Debugging Difficulty

Risk:

Kernel works in QEMU but fails silently on T500.

Mitigation:

Serial-first output, VGA fallback, panic codes, kernel symbols, real-hardware test logs.

R003 — Disk Corruption

Risk:

Early storage code writes to the wrong disk sector.

Mitigation:

No disk writes until QEMU image tests, ALLOW_WRITE compile flag, runtime write-enable, and explicit surgery mode for raw writes.

R004 — GPU Trap

Risk:

Native graphics driver consumes project time before shell/storage/network are stable.

Mitigation:

Use VGA text and VESA framebuffer first. Radeon ignored until much later.

R005 — Wi-Fi Trap

Risk:

Intel Wi-Fi support requires large firmware and protocol work.

Mitigation:

Ethernet only until wired network stack is stable.

R006 — Toolchain Confusion

Risk:

Host compiler emits assumptions unsuitable for freestanding kernel.

Mitigation:

Use strict compiler flags early; build cross-compiler once boot seed is stable.

R007 — Losing Usable Laptop

Risk:

Bootloader or disk experiments break existing Mint install.

Mitigation:

Develop ISO/QEMU first. Real hardware boot through controlled GRUB entry. Avoid disk writes.

R008 — Compatibility Layer Takes Over

Risk:

The project turns into a bad Unix clone while trying to run outside software.

Mitigation:

Design the T500OS-native ABI first. Add compatibility only as an optional layer for useful research code.

R009 — Security Model Drift

Risk:

The OS accumulates complex local security mechanisms that slow research execution without providing real protection.

Mitigation:

Keep local execution trusted. Spend security effort on network parsing, explicit service activation, and truthful documentation.

R010 — Premature Optimization Without Measurement

Risk:

The codebase fills with assembly and special cases that are not actually faster.

Mitigation:

Require benchmark evidence for hot-path optimization. Keep scalar reference implementations.

R011 — Language Becomes Too Large

Risk:

T5L grows into a general-purpose language before the OS core is stable.

Mitigation:

Keep early T5L focused on immediate math, variables, loops, functions, and benchmarkable kernels.

R012 — Compiler Complexity Overtakes OS Bring-Up

Risk:

The compiler becomes the main project before shell, memory, disk, and networking foundations exist.

Mitigation:

Use evaluator first, bytecode second, native compiler later. Compiler work must support math/research milestones, not replace OS bring-up.

Extra guard:

The shell math evaluator is permanent and supported.
The optimizing compiler is deferred until the evaluator, benchmark path, memory model, and capsule model exist.

R013 — Hardware Surgery Crashes the Core

Risk:

Raw I/O, MMIO, PCI, or MSR mutation destabilizes the running OS.

Mitigation:

Read-first probing. Explicit surgery mode for writes. Mutation log. Crash-risk classification. No friendly command may silently write dangerous hardware state.

R014 — Debug Infrastructure Arrives Too Late

Risk:

The kernel reaches PCI, paging, or driver bring-up without enough visibility to debug failures.

Mitigation:

Serial-first output, kernel.elf symbols, kernel.map, QEMU serial harness, debug_break, and optional bounded GDB stub.

R015 — Identity Mapping Becomes Permanent

Risk:

Temporary identity mapping leaks into driver and capsule design, making MMIO and memory ownership messy.

Mitigation:

Promote map_page/unmap_page, VMM inspection, and explicit MMIO mappings into the early memory/PCI milestone.

R016 — Network Stack Becomes a Vulnerability Sink

Risk:

A from-scratch TCP/IP stack consumes years and creates avoidable parsing/state-machine bugs.

Mitigation:

Allow a tiny audited embedded stack such as lwIP/uIP inside a restartable network capsule, with the stable core exposing only raw NIC queues.

R017 — Capsule Model Stays Vague

Risk:

Research modules and foreign code exist without a clear arena, abort, or cleanup model.

Mitigation:

Define capsule-local stack, arena allocator, resource list, status block, and abort path before non-core code grows.

R018 — Regression Testing Is Manual Only

Risk:

Small changes repeatedly break boot, shell, or diagnostics without immediate detection.

Mitigation:

Use a QEMU serial test harness and Git tags from the first milestone.

R019 — GRUB Becomes Permanent by Accident

Risk:

The temporary GRUB/Multiboot2 dependency remains forever and prevents full boot-path ownership.

Mitigation:

Keep GRUB through early kernel bring-up, but schedule a bootloader ownership track after disk/FAT32 read is stable.

R020 — Filesystem Work Displaces Math Runtime

Risk:

FAT32/ext2/custom storage work expands before the system has useful research computation.

Mitigation:

Keep FAT32 minimal, read-only, and bounded. Prioritize math evaluator, benchmark path, and core kernels before filesystem sophistication.

R021 — AI Context Drift

Risk:

AI collaborators lose or dilute doctrine across sessions and start implementing generic OS patterns.

Mitigation:

Root CLAUDE.md, current-milestone target, classification headers, milestone tags, and make test-qemu as the required agent heartbeat.

R022 — Toolchain Reproducibility Drift

Risk:

Build failures appear because different sessions or machines use different compiler/binutils/QEMU behavior.

Mitigation:

Cross-compiler build script, documented versions, local build path, optional container/Nix reproducibility track, and kernel.elf/kernel.map artifact checks.

R023 — Python Compatibility Scope Creep

Risk:

The project chases CPython, NumPy, SciPy, pandas, or Python-source translation before the native OS and T5L are stable.

Mitigation:

T5L remains native. Python waits until capsule and benchmark foundations exist. First target is a MicroPython-style guest capsule with explicit FFI to T500OS math kernels.

R024 — FPU/SSE State Corruption

Risk:

SSE or floating-point code corrupts state across interrupts, capsules, or math kernels.

Mitigation:

Integer-only stable core early. No SSE math kernels until CR0/CR4 setup and FPU/XMM save/restore or strict no-interrupt/no-preemption constraints are defined.


---

32. Final Implementation Contract

T500OS is a ground-up 64-bit operating system for the Lenovo ThinkPad T500. It begins as a small monolithic kernel loaded by GRUB through Multiboot2. Its first mission is to boot, print text, log through serial, handle input, evaluate math immediately, inspect hardware, manage memory, read storage, draw a simple framebuffer UI, communicate over wired Ethernet, and become a fast local math/research computation environment.

T500OS deliberately rejects modern desktop, browser, Wi-Fi, GPU, and general-purpose OS ambitions until the core system is stable.

T500OS treats local code execution as a user-trust decision and does not pretend to sandbox arbitrary malicious code before real isolation exists. Its strongest early security posture is at the networking boundary. It also rejects inherited operating-system structures unless they provide explicit performance, simplicity, correctness, debugging, or compatibility value.

T500OS does not primarily reason in terms of userspace. It reasons in terms of stable core versus progressively more volatile execution layers. The core must be rigorous and boring. Research modules may be fast and experimental. Foreign compatibility code is volatile. Network input is hostile.

The first real victory is this:

Power on ThinkPad T500
Select T500OS
Kernel boots
Serial log starts
Screen prints T500OS banner
Keyboard works
T5L prompt appears
2+2 returns 4
System can describe its own CPU, memory, interrupts, and PCI state

That is the foundation.


---

33. Immediate Next Artifacts

33.1 Pre-v0.0 Governance Artifact

Before code generation, create:

CLAUDE.md

This is the root instruction file for Claude Code or any implementation agent. It must state:

current milestone: v0.0
allowed scope
forbidden scope
required source headers
required build/test command
anti-drift rules

33.2 v0.0 Bootstrap Generator

The next implementation artifact should be:

T500OS v0.0 Bootstrap Generator

It should create the project tree and write the initial files for:

Makefile
linker.ld
grub/grub.cfg
boot/multiboot2.asm
kernel/main.c
kernel/serial.c
kernel/vga.c
kernel/panic.c
kernel/printk.c
include files
tools/run_qemu.sh
tools/test_harness.py stub
QEMU run target
ISO build target

The v0.0 bootstrap must not attempt keyboard, interrupts, memory allocation, PCI, disk, networking, T5L, or capsules. It should only prove:

build
boot
serial output
VGA fallback
panic path
symbolized kernel artifact
QEMU execution loop

Once v0.0 is real, the project can begin.

Accepted and integrated. This feedback caught several implementation-readiness gaps that belong in the baseline before code starts.

Added to the design document

Hard blockers now captured

CLAUDE.md root agent instruction file
cross-compiler bootstrap policy
freestanding libk primitive policy
FPU/SSE state policy
real T500 boot media plan

Soft gaps now captured

future in-kernel symbol table
persistent panic log format policy
build flag taxonomy
boot/recovery discipline
license policy
endianness / bus helper policy
auto-generated command reference

Python support now placed correctly

Python is now explicitly not core and not a peer of T5L.

Correct placement:

MicroPython/CPython
→ foreign compatibility layer
→ inside restartable research capsule
→ explicit FFI into trusted T500OS math kernels

Added future milestone:

T500OS v1.3 — MicroPython Research Capsule

With guardrails:

No Python work until capsule model survives controlled testing.
No CPython commitment early.
No NumPy/SciPy/SymPy claims.
No Python-to-T5L translation project early.
T5L remains native.

AI/Claude Code workflow added

New section:

Agent-Assisted Development Workflow

It now requires:

CLAUDE.md before implementation
make test-qemu as agent heartbeat
pre-commit hook
milestone git tags
different model families for implementer/reviewer when practical
small scoped agent tasks only

New risks added

R021 — AI Context Drift
R022 — Toolchain Reproducibility Drift
R023 — Python Compatibility Scope Creep
R024 — FPU/SSE State Corruption

Important correction to the immediate next step

The next artifact is now split into two:

1. CLAUDE.md
2. T500OS v0.0 Bootstrap Generator

That is the right order: governance before code.

I agree with the review’s conclusion: CLAUDE.md generated, ready for bootstrap generator
