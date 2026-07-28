# dcj11-projects

These are only my little test projects for different hardware, modules,
electronic parts. Even though all of them working no garantee that they do
what promised in the docs :-)

MACRO-11 projects for the DCJ-11 SBC and Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).

| Project | Description |
|---|---|
| `at24c32/` | AT24C32 I2C EEPROM driver (over i2c), plus a write/read-back demo |
| `dm8ba10/` | Driver for the DM8BA10 10-digit 16-segment LCD panel (TM1622), plus a "Hello" example |
| `ds3231/` | DS3231 I2C real-time clock driver (over i2c), plus a live serial-clock demo with alarm |
| `eeboot/` | Boot-from-EEPROM experiment: AT24C32 image format + burner work; standalone boot shelved (Multi IO boot ROM issue, see HISTORY) |
| `i2c/` | Software (bit-banged) I2C master on VIA port B |
| `max7219/` | Driver for chained 1088AS 8x8 LED matrix modules (MAX7219 / GC7219C), plus a "Hello" example |
| `mmu/` | Memory management: enable 22-bit mapping and window physical RAM above 64 KB, plus a self-checking demo |
| `net-discovery/` | The Ethernet bring-up campaign (archived): ENC28J60 (shelved — rotates SPI reads) and W5500, up to a ping-answering, telnet-able PDP-11. See HISTORY |
| `netmon/` | The living network project: an ODT-style monitor served over a TCP/SLU mirrored console (`telnet 10.1.0.199` / `nc`) — examine/deposit/go, trap CATCH, W5500 |
| `radio/` | FM radio project: TEA5767 tuner + display (MAX7219 matrix, or DM8BA10 LCD variant) |
| `sdcard/` | microSD over SPI (VIA port B): init ladder + 512-byte sector read/write, plus a read-only FAT16 layer (mount, walk the directory tree, read files) |
| `spi/` | Software (bit-banged) SPI master on VIA port B (mode 0, MSB first) |
| `tea5767/` | TEA5767 FM radio driver (over i2c), plus a tune example |
| `vqc10/` | Pure driver for the DisplayVQC10 panel (two VQC10 5x7 LED matrix modules behind 74HC595s), plus a DS3231 clock demo |

## Toolchain

- [m11asm](https://github.com/zoltan-szabo/m11asm) — MACRO-11 assembler,
  **v0.3.0 or later** (the examples use `.INCLUDE`; check with
  `m11asm --version`)
- [J11Terminal](https://github.com/zoltan-szabo/j11-terminal) — serial
  terminal with ODT upload

<img width="1431" height="1324" alt="j11-terminal" src="https://github.com/user-attachments/assets/d2249248-9562-47a6-92b7-f22efd38aa05" />

Build an example:

```
m11asm -b 1000 hello.mac
```

then open the `.oct` (or the project's `.prj`) in J11Terminal, **Upload to
ODT**, and start it with `1000G` from the ODT prompt (or `P`, since Upload
sets the PC).

## Project files

`*.prj` files are J11Terminal projects: a small JSON bundle of the sources,
origin address, and build settings for a directory (e.g. `radio/radio-lcd.prj`).
Paths inside are relative to the `.prj`, so the files are committed here.
Generated output (`*.oct` `*.bin` `*.lst` `*.sym`) stays gitignored.

## License

MIT — see LICENSE. Individual projects credit their upstream references
in the source headers.
