# sdcard — raw microSD driver for the DCJ-11

Bit-banged SPI-mode SD/microSD access from the PDP-11: the card
initialisation ladder and 512-byte sector read/write, over the W65C22S
VIA on the Multi IO card. No filesystem yet — this is the block layer a
FAT (or a raw disk image) would sit on.

**Status:** init + sector **read** are hardware-verified — the PDP-11
reads a formatted card's MBR (partition table + `55 AA` signature). The
sector **write** path is coded but not yet exercised on hardware.

## Wiring (VIA port B)

| Signal | VIA | Card |
|--------|-----|------|
| CS   | PB3 | chip select (active low) |
| SCK  | PB4 | clock |
| MOSI | PB5 | DI / CMD |
| MISO | PB6 | DO / DAT0 |

Only PB3–PB6 are touched; PB0/1 (I2C), PB2 (SQW) and PB7 stay free. The
card is 3.3 V-only. Verified on a **Catalex-style breakout** (AMS1117-3.3
regulator + SN74HC125 quad buffer) powered from 5 V — it accepts the 5 V
VIA lines directly and returns a MISO level the 5 V VIA reads reliably.
A bare passive adapter would need external 3.3 V + level shifting.

## Files

- `sd.mac` — the driver. `SDINI` (CMD0/CMD8/ACMD41/CMD58 init, returns a
  numbered error code), `SDRD`/`SDWR` (single-block read/write; LBA in
  the R0:R1 register pair, buffer in R2). Block-addressed SDHC/SDXC
  (every modern microSD); carries its own SPI mode-0 primitives because
  the SD pin map differs from `../spi/spi.mac`.
- `sdtest.mac` — bring-up: a raw-CMD0 `PROBE` (dumps the MISO reply for
  wiring diagnosis), then init, capacity class, and a full hex-dump of
  sector 0.
- `sdtest.prj` — J11Terminal project (origin 1000).

## Using it

Open `sdtest.prj` in J11Terminal, Assemble, Upload, `P`. On a formatted
card you should see the init succeed, `SDHC BLOCK-ADDRESSED`, and the
MBR in the sector-0 dump — the partition entry at offset 0x1BE and
`55 AA` at 0x1FE.

`SDINI` error codes (also in the source header): 1 no card, 2 CMD0 never
idle, 3 CMD8 rejected, 4 ACMD41 timeout, 5 CMD58/OCR. The `PROBE` line
distinguishes hardware faults: all `FF` = card silent (power/level/MISO),
all `00` = MISO stuck low, a byte with bit 7 clear (e.g. `01`) = the card
is answering.

## Card format

Small FAT16 (≤ 2 GB, MBR) is the least code for a future filesystem
layer; the MBR read here already reports the FAT16 volume starting at
LBA 2048. For PDP-11-only storage a filesystem is optional — the sector
layer alone backs a raw disk image or program library.

Runs on the DCJ-11 SBC + Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).
