# AT24C32 I2C EEPROM

Driver and demo for the AT24C32 (32 Kbit / 4 KB) I2C EEPROM, built on the
software I2C master in [`../i2c/`](../i2c). Pure I2C — no VIA access of its own.

- `at24c32.mac` — the driver
- `demo.mac` — writes a string, reads it back, and verifies
- `readonly.mac` — reads address 0 only (no writing); proves persistence

## Where it is doesn't matter

The AT24C32 is the same chip standalone or on a **ZS-042 DS3231 module** — same
I2C bus, one driver. Only the address differs: A0–A2 select **0x50–0x57**, and on
the ZS-042 board it's **0x57** (pads pulled high). The DS3231 (0x68) is a
separate device, so the two coexist on the bus. Change `EEADDR` for a different
strap.

## Wiring (port B)

Same two wires as everything else: **SDA = PB0**, **SCL = PB1** (bus pull-ups
required; most modules have them). No other pins.

## Driver API

Include `../i2c/i2c.mac` **before** `at24c32.mac`. Addresses are 12-bit (0–4095).

| Routine | Does |
|---|---|
| `EEPING` | returns `R0` = 0 if the EEPROM answers |
| `EEWRB`  | `R0` = address, `R1` = byte → write one byte (waits the cycle) |
| `EEWR`   | `R0` = address, `R1` = buffer, `R2` = count → write a block |
| `EERDB`  | `R0` = address → returns `R0` = byte |
| `EERD`   | `R0` = address, `R1` = buffer, `R2` = count → read a block |

Writes go **byte-by-byte** — each is a full ~5 ms write cycle ended by ACK
polling, which is simple and page-boundary-safe (a future optimisation is
32-byte page writes). Reads are one sequential transfer, any length.

## Demo

```
m11asm -b 1000 demo.mac
```

Upload `demo.oct`, `1000G`. It pings the EEPROM (`No AT24C32 at 0x57` + halt if
absent), writes `Hello from the AT24C32!` to address 0, reads it back, prints it,
and reports `PASS`/`FAIL`:

```
Read back: Hello from the AT24C32!
PASS - EEPROM verifies
```

## Persistence proof (`readonly.mac`)

`readonly.mac` reads address 0 and prints it — **no writing at all**. Run
`demo.mac` once to store the string, **power-cycle the board**, then run
`readonly.mac`: the same string comes back though nothing wrote it this run, so
the EEPROM genuinely kept it across power.

```
Stored: Hello from the AT24C32!
PASS - EEPROM retained the data
```

Runs on the DCJ-11 SBC + Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).
