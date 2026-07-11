# History

Detailed notes per change. Commit messages stay short; the long story
lives here.

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
