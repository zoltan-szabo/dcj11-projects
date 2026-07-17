# History

Detailed notes per change. Commit messages stay short; the long story
lives here.

## eeboot: boot-from-EEPROM experiment, shelved (2026-07-16..17)

The goal: power the machine on and have it run a program with no PC
attached — a ~250-word loader in the Multi IO card's boot ROM window
(173000) reads an image from the DS3231 board's AT24C32 over I2C, copies
it to RAM, verifies, jumps. The vqc10 clock (1404 words) was to be the
first payload. The loader, burner (`eeburn`), image format and test
payload all work; the mission failed anyway, for reasons worth recording.

What was built: a two-stage loader (stage 0 relocates stage 1 to RAM with
per-word verified writes; stage 1 masks interrupts, owns every vector,
disables the MMU, double-checksums the payload — I2C stream and RAM, the
RAM sum three consecutive times — settles, jumps; any later trap re-enters
the loader, so crashes self-heal), `eeburn.mac` (interactive AT24C32
burner with verify), `romburn.mac` (paced in-circuit AT28C64 burner with
data polling), `hitest.mac` (minimal payload), `mkrom.py` (ROM images for
external programmers and window .oct files for in-circuit parts).

What the campaign found, layer by layer: a verified AT28C64 burn lost to
a power cycle (unprotected EEPROMs catch stray writes as the rails move;
SDP would prevent it but exists only on the B parts — on plain AT28C64
the unlock writes are real writes and ruined the re-burn). W27C512
replacements needed their floating A13/A15 tied. ODT's `G` starts code at
priority 0, and one spurious interrupt through cold-garbage vectors makes
a trap storm: SP marches through RAM leaving PS/PC frames everywhere, the
console sprays kilobytes of garbage, and the wreck halts at a bias-stable
PC (045417 became an old friend). An FM1608 FRAM fits the socket
perfectly and burns by plain upload — and was shredded by the first wild
program, because a boot ROM that writes at bus speed is erased at bus
speed. And the one that cost days: **console ODT examine/deposit use the
address exactly as typed — `173000/` is physical 00173000, i.e. RAM;
only `G` completes 16-bit addresses into the I/O page** — so several
"burns" and "verifications" of the ROM windows had been reading and
writing RAM at 62K. Read the manual first.

Underneath it all: sporadically corrupted full-speed bus operations —
occasional lost stores and lying reads, seen even in a bare serial upload
(one word of a 1404-word image arrived wrong) — whenever the boot ROM
window was in play. Diagnosis: the Multi IO card's boot ROM handling does
not reliably coexist with the W65C22S-paced bus; the DCJ-11 and RAM are
sound (the 16 MHz clock is a VIA concession — the CPU is good for 18).
Conclusion: on this card revision, the W65C22S (with the software-I2C
EEPROM behind it) and the boot EPROM cannot be used together. Shelved;
`eeburn` and the image format remain useful, and the loader is ready
should the ROM path ever become trustworthy.

## VQC10 panel project (2026-07-15)

`vqc10/vqc10.mac` drives the "DisplayVQC10" panel (Konstantin Repnikov,
vk.com/retromodding) directly — two VQC10 4-digit 5x7 LED matrix modules
(WF Berlin) behind three chained 74HC595s. "Pure" = no ATmega controller;
the J-11 bit-bangs the chain on VIA port A (DATA=PA0, CLK=PA1, LATCH=PA2,
OFF=PA3 -> the 595s' /OE, which is pulled up so the panel is blank until
driven). API: VQCINI, VQCPUT/VQCSTR (glyphs transposed from the shared
column-major font into a row-major buffer), VQCSCN (one scan pass, call
continuously; ends dark so pausing is safe), VQCON/VQCOFF. `vqc10/clock.mac`
shows DS3231 time as HH:MM:SS on the 8 digits — same set-prompt/OSF/NZ-DST
behaviour as the ds3231 demos, ticked off the SQW edge, reading only 3 RTC
bytes per second (full block on hour change) to keep the between-frames
I2C pause invisible.

The shared 5x7 font moved out of max7219.mac into `max7219/font5x7.mac`
(both drivers .INCLUDE it); hello.oct proved byte-identical after the
refactor, so no re-test was needed.

Hardware bring-up found two real lessons, both now in the driver and its
README: the panel's row select is ACTIVE LOW (595 -> P-FET gate, so an
inverted row byte lights the whole panel with glyph columns smeared over
every row), and cp timing is strict — all 595 outputs move on one RCLK, so
the word that raises a cp must not change the data lines, or chip skew
races the module's latch and sprays ghost pixels from the neighbouring
digit (seen as stray pixels on digits 5/7 before the fix). VQCSCN therefore
costs two latch words per digit; the refresh (~60 Hz) was won back by
tightening VQSEND instead: port address and idle state held in registers
and the DATA bit set straight from the carry (ADC — DATA is PA0).
Datasheet assumptions verified: cp active-low latching on release,
C1 = leftmost digit, Z1 = top row. Hardware-tested: the clock runs.

Next: a second driver talking to the panel's own ATmega328 controller
board instead of driving the latches directly.

## AT24C32 EEPROM project (2026-07-12)

`at24c32/at24c32.mac` drives the AT24C32 (32 Kbit / 4 KB) I2C EEPROM on the
`i2c/` master — pure I2C, no VIA. API: `EEPING`, `EEWRB`/`EEWR` (byte / block
write), `EERDB`/`EERD` (byte / block read). 12-bit address sent as two bytes;
writes go byte-by-byte, each a ~5 ms cycle ended by ACK polling (simple and
page-safe; page writes are a future optimisation); reads are one sequential
transfer. The chip is the same standalone or on a ZS-042 DS3231 module — only
`EEADDR` differs (A0–A2 → 0x50..0x57; 0x57 on ZS-042). `at24c32/demo.mac` writes
a string to address 0, reads it back, prints it, and verifies (PASS/FAIL).
`at24c32/readonly.mac` reads address 0 only (no writing) — run it after a
power-cycle to prove the EEPROM kept what demo.mac wrote. Closes #1.

## DS3231 RTC project (2026-07-12)

`ds3231/ds3231.mac` drives the DS3231 I2C real-time clock on top of the
`i2c/` master — register blocks are read/written through the I2C layer, and the
VIA is touched directly only to read the SQW pin (PB2, a DS3231 output). API:
`RTCINI` (SQW = 1 Hz, oscillator on, flags cleared), `RTCSET`/`RTCGET` (7-byte
BCD time), `RTCA1` (Alarm 1), `RTCAF`/`RTCACL` (alarm flags), `RTCSQ` (SQW
level). The DS3231 address is fixed at 0x68; A0–A2 on ZS-042 modules belong to
the AT24C32 EEPROM, not the clock.

Two demos share the driver. `ds3231/demo.mac` is the plain console clock —
reads the RTC and prints `20YY-MM-DD HH:MM:SS NZxT` in place once a second.
`ds3231/clock.mac` is the graphical version: a big centre `HH:MM:SS` in 5x5
block digits (VT cursor addressing, so it needs the general Terminal, not the
ODT console) with a small date/zone line and `*ALARM*` flashing at :10 — the
base to grow alerts and timers on. Both prompt to set the time (declining reads
the running clock, unless OSF reports it lost power, where it insists on a set),
keep the RTC on NZST and convert to NZ local time (+1 h in NZDT, last Sun Sep ..
first Sun Apr, weekday by Sakamoto, date rolls at midnight), and tick off the
1 Hz SQW falling edge on PB2 (A1F polled over I2C, so tick and alarm coexist).

## MMU project (2026-07-11)

`mmu/mmu.mac` brings up the J-11 on-chip memory management to reach RAM above
the 16-bit 64 KB limit. `MMUON` installs an identity map (page 7 → 22-bit I/O
page) and turns on 22-bit relocation so running code is unaffected; `WINDOW`
re-points page 6 (virtual 140000) at any physical block, giving a sliding 8 KB
view of the 512 kW (1 MB, 128 banks) physical space. `mmu/demo.mac` writes a
distinct signature into four high banks (8, 32, 64, 96) and reads them back
through the window, printing PASS/FAIL on the console — a mismatch would mean
the high addresses aliased instead of being real distinct RAM.

Gotcha found and documented: MACRO-11 (and m11asm) evaluate expressions left to
right with no operator precedence, so `KIPAR0 + WINPAG*2` computed
`(KIPAR0 + WINPAG)*2`. Written as `WINPAG*2 + KIPAR0` instead.

## I2C, TEA5767 and radio project (2026-07-11)

Three layered projects. `i2c/i2c.mac` is a bit-banged I2C master on VIA
port B (SDA=PB0, SCL=PB1), open-drain via DDR toggling. `tea5767/tea5767.mac`
is an FM radio driver over that I2C layer (no direct VIA access): tune, seek,
and status. Frequencies are in 10 kHz units; the PLL word
(f_Hz + 225000) / 8192 is computed with the J-11 EIS MUL/ASHC/DIV
(PLL math and the "xxx.x" display formatting both verified numerically).
`radio/radio.mac` combines i2c + tea5767 + max7219 into an FM radio: seek to
the first station, then tune from the console (+/- coarse 0.1 MHz, ./, fine
0.01 MHz, any other key seeks up), with a live signal bar on the matrix.

The MAX7219 matrix turned out to inject audible noise into the FM front end —
it multiplexes continuously and the redraw bursts land in the audio band.
`radio/radio-lcd.mac` is a fork onto the static DM8BA10 LCD (port A), which
stays quiet: "xxx.xx" frequency (two decimals so the fine step shows) with the
signal level as a number on the rightmost digit. It starts tuned to 93.4 MHz
with the backlight on. Hardware-tested and working.

Note: m11asm parses EIS operands register-first (MUL Rn, src), reversed from
MACRO-11 — see m11asm#6. The tea5767 driver is written to that convention.

## max7219 driver and Hello example (2026-07-11)

Driver for chained 1088AS 8x8 LED matrix panels on a MAX7219 / GC7219C,
bit-banged over VIA port A (DIN=PA0, CS=PA1, CLK=PA2). 1..MAXMOD modules;
MXINIT takes the count in R0. Column-major framebuffer (one byte per
column, bit 0 top) with MXFLSH shifting the whole chain and latching on
CS. Text via the classic Pascal Stang font5x7 (avrlib 2001), verified in
ASCII-art to render "Hello" before emission. Bring-up routines MXDTST
(all-on) and MXWALK (single dot through every pixel) verify wiring and
orientation, since generic modules vary in digit-to-matrix mapping. The
Hello example centers "Hello" on a 6-module chain. Not yet hardware-tested.

## dm8ba10 backlight support (2026-07-10)

The panel's LED backlight is wired to VIA PA3. Because the backlight bit
shares port A with CS/WR/DATA, every port write in the driver now ORs in
`LEDSTA`, a shadow word holding the current backlight state — otherwise
each transmitted bit would blank the LED. `LCDINI` widens DDRA to 17
(PA0-3 outputs) and starts with the backlight off; `LCDLED` (R0 = 0 off,
`ON`/`OFF`) switches it and rewrites the idle bus state. `BIS` does not
affect the carry flag, so the shadow OR is safe inside `SENDB`'s
carry-driven bit loop. The Hello example switches the backlight on.

Hardware-verified 2026-07-10: "Hello" displays on the panel.

## dm8ba10 driver and Hello example (2026-07-10)

Driver for the eletechsup DM8BA10 panel (TM1622, HT1622-compatible
3-wire serial) on the Multi IO card's VIA port A (CS=PA0, WR=PA1,
DATA=PA2). Protocol, digit addressing (leftmost digit at nibble address
0x24, step -4) and the 96-glyph 16-segment font follow Ilya Annikov's
MIT-licensed Arduino library (github.com/road-t/DM8BA10), credited in
the source header.

Design notes: bit-banging needs no delay loops — each VIA access is
already microseconds, an order of magnitude above the TM1622 minimum
pulse widths. The driver owns port A direction (DDRA = 7). Decimal
points (RAM addresses 0x29/0x2B/0x2D) are not driven yet. The example
includes the driver via m11asm's new .INCLUDE directive.
