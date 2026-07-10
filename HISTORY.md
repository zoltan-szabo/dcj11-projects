# History

Detailed notes per change. Commit messages stay short; the long story
lives here.

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
