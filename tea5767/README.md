# TEA5767 FM radio driver

Driver for the TEA5767 (or GC-clone) FM stereo receiver over I2C, for the
DCJ-11. Talks only through `../i2c/i2c.mac`, so it touches no VIA hardware
itself. Include `i2c.mac` first.

## Frequency and PLL

Frequencies are in units of 10 kHz (100.00 MHz = 10000), which spans the FM
band in 16 bits. High-side injection, 32.768 kHz crystal, 50 us de-emphasis.
The PLL word is `(f_Hz + 225000) / 8192`, computed as
`(units * 10000 + 229096) >> 13` using the J-11 EIS `MUL`/`ASHC`/`DIV`.

## API

Routines clobber R0-R4; R5 preserved.

| Routine | Arguments |
|---|---|
| `FMINIT` | set up I2C and the default config |
| `FMTUNE` | R0 = frequency (10 kHz units) -> tune |
| `FMSEEK` | R0 = start frequency -> search up; returns R0 = found frequency |
| `FMRD` | refresh the 5 status bytes into TEARD |
| `FMFRQ` | R0 = tuned frequency from TEARD (call FMRD first) |
| `FMLEV` | R0 = signal level 0..15 from TEARD |
| `FMSTER` | R0 = 1 if stereo, else 0 |

The 5-byte control image is `TEABUF`; the 5-byte status read-back is `TEARD`.

## Note

The TEA5767 has no addressed registers — the driver streams all 5 control
bytes and reads all 5 status bytes each time. I2C address 0x60 (0xC0 write,
0xC1 read). `FMSEEK` stops on the chip's ready flag; at a band edge it stops
with no station (BLF set), so a fuller version would check that.
