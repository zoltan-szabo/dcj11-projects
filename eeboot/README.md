# eeboot — boot a program from the DS3231 board's EEPROM (SHELVED)

**Status: shelved.** The loader architecture is sound and was verified piece
by piece on hardware — with an SRAM in the boot sockets the window executes
code cleanly and the full load (I2C read + double verification) succeeds.
What blocks the mission is a hardware LATCH on the (already-modified) Multi
IO card: after the boot flow runs, the payload's first VIA port A access
bus-times-out, and from then on ALL full-speed VIA access traps (ODT-paced
access still works) from any launch, `G` included — only a power cycle
clears it. The DCJ-11 and RAM are fine (16 MHz is a VIA concession; the CPU
is good for 18). Next campaign: the card's boot ROM area and GAL timing,
equations in hand. Full war story: see HISTORY.md — it is instructive.

What remains useful and works:

- `eeburn.mac` — store a program image in the AT24C32 (console prompts,
  octal with a trailing `.` for decimal; writes, then re-reads and verifies).
  Proven on hardware.
- The image format (below) and `hitest.mac`, a minimal test payload.
- `eeboot0.mac` + `eeboot.mac` — the two-stage loader: stage 0 relocates
  stage 1 to RAM with per-word verified writes; stage 1 masks interrupts,
  owns all vectors (traps restart the boot instead of storming), disables
  the MMU, loads the payload, checksums it twice (I2C stream and RAM, the
  RAM sum three consecutive times), settles, then jumps. Any crash of the
  payload re-enters the loader via the vectors: self-healing by design.
- `mkrom.py` — packs the two stages into ROM programmer images
  (`--size 8k|16k|32k|64k` for 2764/27128-class EPROMs up to W27C512) and
  window `.oct` files for in-circuit-writable parts.
- `romburn.mac` — in-circuit burner for AT28C64-class EEPROMs in the
  173000 window (data polling, verify; commented-out SDP unlock for
  AT28C64B parts).

## Image format in the AT24C32

All words little-endian, starting at EEPROM address 0:

| Offset | Content |
|---|---|
| 0 | payload word count (1..2044) |
| 2 | load address (even, ≥ 1000) |
| 4 | start address |
| 6 | payload words |
| 6 + 2·count | checksum — the sum of every word above including itself is 0 |

## Hard-won lessons (details in HISTORY.md)

- **Console ODT addressing:** examine/deposit take the address exactly as
  typed — `173000/` is physical 00173000 (RAM!). Only `G` completes a 16-bit
  address into the I/O page. Serial-upload "burns" and "verifies" of the ROM
  windows must use 8-digit physical addresses (17773000 / 17765000).
- A boot ROM must **mask interrupts and own the vectors before anything
  else** — ODT's `G` starts at priority 0, and one spurious interrupt
  through cold-garbage vectors is a stack storm that shreds RAM.
- The two ROM windows map ROM pages 1500 (at 173000) and 0A00 (at 165000)
  of one chip pair; ROM A8..A12 = CPU A10,A11,A12,A11,A10.
- SDP exists only on AT28C64**B**; on plain AT28C64 the unlock writes are
  real writes and ruin the burn. Unprotected EEPROMs can be corrupted by
  stray writes during power transitions.
- 27C512-class EPROMs leave A13/A15 floating in these sockets (tie them);
  a bus-speed-writable FRAM (FM1608) fits perfectly but is shredded by the
  first wild program — write-slowness is a feature in a boot ROM.

Runs on (or rather, was fought on) the DCJ-11 SBC + Multi IO card by Peter
Schranz (https://www.5volts.ch/pages/dcj11sbc/).
