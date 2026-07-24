# DM8BA10 driver

Driver for the eletechsup DM8BA10 10-digit 16-segment LCD panel
(TM1622 controller, HT1622 compatible) for the DCJ-11 SBC with the
Multi IO card, in MACRO-11.

## Wiring

| Panel | VIA (Multi IO, port A) |
|---|---|
| CS | PA0 |
| WR | PA1 |
| DATA | PA2 |
| LED (backlight) | PA3 — optional, active high |
| VDD / GND | 5 V / GND |

## API

All routines clobber R0-R3 unless noted.

| Routine | Arguments |
|---|---|
| `LCDINI` | none — call once; sets DDRA=7, oscillator on, clears, LCD on |
| `LCDCLR` | none — blank display |
| `LCDSTR` | R0 -> ASCIZ string, R1 = start position 0..9 (also clobbers R4) |
| `LCDCHR` | R0 = ASCII character, R1 = position (preserved) |
| `LCDWRD` | R0 = raw 16-bit segment word, R1 = nibble address |
| `LCDCMD` | R0 = HT1622 command byte |
| `LCDLED` | R0 = `ON` or `OFF` (backlight) |

Positions run 0 (leftmost) to 9 (rightmost). Include the driver at the
end of your program:

```
	.INCLUDE /dm8ba10.mac/
```

(paths containing `/` need another delimiter: `.INCLUDE "sub/file.mac"`)

## Example

`hello.mac` writes "Hello" starting at position 2:

```
m11asm -b 1000 hello.mac
```

open `hello.oct` in J11Terminal, Upload to ODT, then `1000G`.

## Notes

- Requires m11asm v0.3.0 or later (for `.INCLUDE`).
- The driver owns port A direction (writes DDRA = 17; PA4-PA7 inputs).
- The backlight bit shares port A with the serial lines. Every port write
  in the driver ORs in `LEDSTA`, the shadow of the current backlight
  state, so serial traffic cannot flicker the LED. Do not write `VIAORA`
  directly from application code.
- `LCDINI` starts with the backlight off; call `LCDLED` to switch it:

```
	MOV	#ON, R0
	JSR	PC, LCDLED
```

  The driver defines `ON = 1` and `OFF = 0`. They are ordinary equates:
  a program that defines its own `ON` would silently override them
  (see [m11asm#4](https://github.com/zoltan-szabo/m11asm/issues/4)).
- Decimal points between digits are not driven yet.
- Protocol, addressing and font from the MIT-licensed Arduino library
  by Ilya 'road-t' Annikov: https://github.com/road-t/DM8BA10
