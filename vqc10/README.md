# VQC10 LED matrix panel (pure driver)

Driver and clock demo for the **DisplayVQC10** panel — two Soviet/DDR **VQC10**
4-digit 5×7 LED matrix modules (WF Berlin) behind three chained 74HC595s.
"Pure" means the J-11 bit-bangs the panel's shift chain directly; the panel's
matching ATmega controller board is not used (a driver talking *through* that
controller may come later).

- `vqc10.mac` — the driver
- `clock.mac` — demo: DS3231 time as `HH:MM:SS` on the 8 digits

## Wiring (port A → panel J1)

| Signal | VIA | Panel J1 |
|---|---|---|
| DATA  | PA0 | 5 (MOSI) |
| CLK   | PA1 | 4 (SCLK) |
| LATCH | PA2 | 3 (RCLK) |
| OFF   | PA3 | 2 (LEDOFF = 595 /OE, 10k pull-up — panel blank until driven low) |
| +5V / GND | — | 1 / 6 |

The clock demo also needs the DS3231 on port B (SDA=PB0, SCL=PB1, SQW=PB2),
same as the `ds3231` project.

## How the panel works

24-bit chain: U4 (Y1–Y7 row select via P-FETs) ← U3 (C1–C8, one cp clock per
digit) ← U2 (D1–D5 column data). The row select is **active low** — Y drives a
P-FET gate against a 47k pull-up, so Y=0 turns the row on (all-off = 377).
Each VQC10 digit latches 5 column bits on its cp edge; the display is
row-multiplexed: per row, clock all 8 digits' column patterns in, then switch
that row on and dwell (~1:10 duty, which is what the datasheet's luminance
spec assumes).

## Driver API

Include order in a program: `../i2c/i2c.mac` (if used), `vqc10.mac`,
`../max7219/font5x7.mac` (the shared 5×7 font — the driver needs `FONT`).

| Routine | Does |
|---|---|
| `VQCINI` | init port A, defined chain state, clear, display on |
| `VQCPUT` | `R0` = ASCII, `R1` = digit 0..7 → render into the buffer |
| `VQCSTR` | `R0` → ASCIZ, `R1` = start digit (clips at 8) |
| `VQCCLR` | blank the buffer |
| `VQCSCN` | one full scan pass — call continuously; panel is dark when not scanned |
| `VQCON` / `VQCOFF` | display enable / blank via the OFF line |

Routines clobber R0–R3 and preserve R4/R5.

## Clock demo

```
m11asm -b 1000 clock.mac
```

Upload `clock.oct`, `1000G`. Same start-up as the `ds3231` demos: OSF check,
`Set date/time? (y/n)` on the console (forced if the clock lost power), RTC
kept on NZST, display in NZ local time (NZDT +1 h). The main loop alternates
panel scan passes with SQW polling; each 1 Hz falling edge re-reads the RTC.

## Hardware notes (verified on the real panel, 2026-07-15)

The datasheet ambiguities all resolved to the assumed defaults: **cp is
active-low** (data latched on release), **C1 = leftmost digit**, **Z1 = top
row**. Two lessons from bring-up, baked into the driver:

- **Row select is active low** (Y drives a P-FET gate) — with it inverted the
  whole panel lights solid, glyph columns smeared over every row.
- **cp timing is strict**: all 595 outputs move on one RCLK, so a word that
  raises a cp must not change D1–D5 (and vice versa) — violating that races
  the latch against chip skew and sprays ghost pixels from the neighbouring
  digit. `VQCSCN` therefore spends two words per digit (16 per row) with the
  last release merged into the row-on word.

Tunable: `DWELL` (brightness vs. refresh; ~60 Hz at the default). The clock
demo reads only 3 RTC bytes per tick (full block on hour change) to keep the
between-frames I2C pause short.

Runs on the DCJ-11 SBC + Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).
Panel: "DisplayVQC10" by Konstantin Repnikov (vk.com/retromodding).
VQC10 datasheet: Funkamateur-Bauelementeinformation FA 6/90.
Font: Pascal Stang font5x7 (avrlib, 2001).
