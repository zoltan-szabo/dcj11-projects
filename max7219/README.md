# MAX7219 LED matrix driver

Driver for chained **1088AS 8x8 LED matrix** modules driven by a **MAX7219**
(or **GC7219C** clone) for the DCJ-11 SBC with the Multi IO card, in MACRO-11.
Any number of modules from 1 to `MAXMOD` (default 8) can be chained.

## Wiring

| Module | VIA (Multi IO, port A) |
|---|---|
| DIN | PA0 |
| CS | PA1 (LOAD) |
| CLK | PA2 |
| VCC / GND | 5 V / GND |

## API

Routines clobber R0-R3 unless noted; R4/R5 are preserved.

| Routine | Arguments |
|---|---|
| `MXINIT` | R0 = number of modules (1..MAXMOD); inits all, clears, display on |
| `MXCLR` | blank the framebuffer and display |
| `MXFLSH` | shift the framebuffer to the chain |
| `MXBRT` | R0 = intensity 0..17 octal (0 dim .. 17 bright) |
| `MXCH` | R0 = ASCII, R1 = start column; renders, advances R1 by 6 |
| `MXSTR` | R0 -> ASCIZ string, R1 = start column (also uses R4) |

Include the driver at the end of your program:

```
	.INCLUDE /max7219.mac/
```

## Framebuffer and font

The framebuffer is column-major: one byte per column across the whole chain,
bit 0 = top row. The font is the classic **5x7 dot-matrix set** (Pascal
Stang's `font5x7`, avrlib 2001), column-major with bit 0 top — so rendering
text is a straight copy into the buffer.

## Bring-up and orientation

Generic 1088AS + MAX7219 modules differ in how the MAX7219 "digit" registers
map to the physical matrix (rows vs columns, mirrored, rotated). `MXFLSH`
assumes digit register D(n) drives column n, module 0 nearest DIN. **Verify
first** with the bring-up routines:

| Routine | Arguments |
|---|---|
| `MXDTST` | R0 = 1 all LEDs on, 0 off (display-test register, ignores RAM) |
| `MXWALK` | step one lit pixel through every pixel of every module |

`MXWALK` should walk a single dot left-to-right, top-to-bottom, module 0
first. If it walks differently, that reveals the true mapping — adjust
`MXFLSH` to match. `hello.mac` has these calls commented at the top.

## Example

`hello.mac` displays "Hello" centered on a 6-module chain:

```
m11asm -b 1000 hello.mac
```

open `hello.oct` in J11Terminal, Upload to ODT, then `1000G`.

## Notes

- Requires m11asm v0.3.0 or later (for `.INCLUDE`).
- The driver owns port A direction (writes DDRA = 7; PA3-PA7 inputs).
- Font: Pascal Stang font5x7, a public 5x7 dot-matrix character set.
