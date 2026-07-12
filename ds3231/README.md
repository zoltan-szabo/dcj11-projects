# DS3231 real-time clock

Driver and demo for the DS3231 I2C RTC (the TCXO one) on the Multi IO card,
built on the software I2C master in [`../i2c/`](../i2c).

- `ds3231.mac` — the driver (register access via i2c; SQW read directly)
- `demo.mac` — sets the clock + an alarm and prints a live clock over serial

## Wiring (port B)

| Signal | Pin | |
|---|---|---|
| SDA | PB0 | I2C data |
| SCL | PB1 | I2C clock |
| SQW | PB2 | DS3231 square-wave output → VIA input |

The **DS3231 address is fixed at 0x68** — it has no A0–A2 pins. On ZS-042-style
modules the A0–A2 pads belong to the separate AT24C32 EEPROM (0x57), not the
clock, so they don't affect this driver.

## Driver API

Times are **BCD, 24-hour**. Buffers: time = 7 bytes `sec min hour dow date
month year`; alarm = 4 bytes `sec min hour day/date` (bit 7 of each is its
alarm-mask bit).

| Routine | Does |
|---|---|
| `RTCINI` | Bus up, SQW = 1 Hz, oscillator on, PB2 set as input. Leaves the status flags alone so the caller can test OSF (lost-power) first. |
| `RTCSET` | `R1` → 7-byte time buffer, written to the clock |
| `RTCGET` | `R1` → 7-byte buffer, filled from the clock |
| `RTCA1`  | `R1` → 4-byte Alarm 1 buffer, written to the clock |
| `RTCAF`  | returns `R0` = status register (bit 0 = A1F, bit 1 = A2F) |
| `RTCACL` | clear the alarm flags |
| `RTCSQ`  | returns `R0` = SQW pin level (0 low, non-zero high) |

Include `../i2c/i2c.mac` **before** `ds3231.mac`.

## Demo

```
m11asm -b 1000 demo.mac
```

Upload `demo.oct`, then `1000G` **in the general Terminal** (it uses VT cursor
addressing, so the ODT console won't render it). It pings the clock (prints
`No DS3231 at 0x68` and halts if absent), then:

**Set or read.** It asks `Set date/time? (y/n):`. Answer **y** to set the clock;
decline and it reads the running (battery-backed) clock — **unless the DS3231
reports it lost power (OSF set)**, in which case it insists on a fresh entry.

**Interactive entry.** On a set it prompts `Enter DD/MM/YYYY HH:MM:SS:` and
parses exactly 14 digits (any separators you type are ignored, so type it as
shown). It also computes and stores the correct weekday. Enter the time in
**NZST** (standard time) — see DST below.

**Big centre clock.** It clears the screen and draws `HH:MM:SS` in the middle
with 5x5 block digits, plus a small `20YY-MM-DD  NZxT` line below:

```
             DS3231 CLOCK

  ##  ##  ## ## ##   ## #####
 #  # # #  #  # # #   #     #
  ##   #  ##  #  ##  ##  ####   ...(HH:MM:SS in block digits)

           2026-07-12  NZST
```

**NZ local time.** The RTC is kept on NZST; the display adds one hour during
**NZDT** (last Sunday of September … first Sunday of April), rolling the date
across midnight, and tags the line NZST/NZDT.

The one-second tick is the DS3231's **1 Hz SQW** on PB2 — the loop waits for its
falling edge rather than polling the seconds register. Alarm 1 matches
`seconds = 10`, so `*ALARM*` flashes below the clock once a minute at `:10`;
with SQW on the pin the alarm doesn't drive it, but **A1F still sets** and the
demo polls it over I2C, so tick and alarm coexist.

The weekday and DST boundaries use Sakamoto's algorithm; the 2000s form is exact
for 2001–2099. Want the alarm to drive the pin (INT mode) or the AT24C32 EEPROM
on the same module? Both are small additions — ask.

Runs on the DCJ-11 SBC + Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).
