# dcj11-projects

MACRO-11 projects for the DCJ-11 SBC and Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).

| Project | Description |
|---|---|
| `dm8ba10/` | Driver for the DM8BA10 10-digit 16-segment LCD panel (TM1622), plus a "Hello" example |
| `max7219/` | Driver for chained 1088AS 8x8 LED matrix modules (MAX7219 / GC7219C), plus a "Hello" example |

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

## License

MIT — see LICENSE. Individual projects credit their upstream references
in the source headers.
