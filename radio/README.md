# FM radio

A working FM radio: TEA5767 tuner + a display. Two variants:

- **`radio.mac`** — MAX7219 LED matrix display, frequency plus a live
  signal-strength bar.
- **`radio-lcd.mac`** — DM8BA10 LCD display. The matrix multiplexes
  continuously and its redraw bursts inject audible noise into the FM front
  end; the LCD is static and stays quiet. Shows "xxx.xx" (two decimals, so the
  fine tuning step is visible) with the signal level as a number on the
  rightmost digit. Starts tuned to 93.4 MHz with the backlight on.

Both combine drivers from this repo:

- `../i2c/i2c.mac` — software I2C on port B
- `../tea5767/tea5767.mac` — FM tuner
- `../max7219/max7219.mac` or `../dm8ba10/dm8ba10.mac` — display on port A

Ports don't collide: the tuner is on VIA port B (SDA=PB0, SCL=PB1), the
display on port A.

## Build and run

```
m11asm -b 1000 radio-lcd.mac
```

open the `.oct` in J11Terminal, Upload to ODT, then `1000G`. It reads the
console UART directly while running (no ODT needed); tune from the Terminal
view:

| Key | Action |
|---|---|
| `+` / `u` | up 0.1 MHz |
| `-` / `d` | down 0.1 MHz |
| `.` | up 0.01 MHz (fine) |
| `,` | down 0.01 MHz (fine) |
| any other | seek up (wraps at the band top) |

Seek uses the chip's high stop level, so it locks only onto strong stations.

## Bring-up

If nothing tunes, work up the stack:

1. Check the tuner answers I2C — `I2CPING` with R0 = 0x60 should return 0.
2. `FMTUNE` a station you know is strong, confirm audio.
3. Then `FMSEEK`, then the display.

Requires m11asm v0.3.0+ (for `.INCLUDE`). The display orientation is handled
by the MAX7219 driver; see max7219/README.md.
