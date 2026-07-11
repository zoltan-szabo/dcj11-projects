# dcj11-projects

MACRO-11 projects for the DCJ-11 SBC and Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).

| Project | Description |
|---|---|
| `dm8ba10/` | Driver for the DM8BA10 10-digit 16-segment LCD panel (TM1622), plus a "Hello" example |
| `max7219/` | Driver for chained 1088AS 8x8 LED matrix modules (MAX7219 / GC7219C), plus a "Hello" example |
| `i2c/` | Software (bit-banged) I2C master on VIA port B |
| `tea5767/` | TEA5767 FM radio driver (over i2c), plus a tune example |
| `radio/` | FM radio project: TEA5767 tuner + display (MAX7219 matrix, or DM8BA10 LCD variant) |

## Toolchain

- [m11asm](https://github.com/zoltan-szabo/m11asm) — MACRO-11 assembler,
  **v0.3.0 or later** (the examples use `.INCLUDE`; check with
  `m11asm --version`)
- [J11Terminal](https://github.com/zoltan-szabo/j11-terminal) — serial
  terminal with ODT upload

Build an example:

```
m11asm -b 1000 hello.mac
```

then paste the `.oct` into J11Terminal's Octal Upload and start it with
`1000G` from the ODT prompt.

## Project files

`*.prj` files are J11Terminal projects: a small JSON bundle of the sources,
origin address, and build settings for a directory (e.g. `radio/radio-lcd.prj`).
Paths inside are relative to the `.prj`, so the files are committed here.
Generated output (`*.oct` `*.bin` `*.lst` `*.sym`) stays gitignored.

## License

MIT — see LICENSE. Individual projects credit their upstream references
in the source headers.
