# sdcard — microSD driver + read-only FAT16 for the DCJ-11

Bit-banged SPI-mode SD/microSD access from the PDP-11 — the card init
ladder and 512-byte sector read/write over the W65C22S VIA — plus a
read-only FAT16 layer on top (mount, walk the directory tree including
subdirectories, read files by following the cluster chain).

<img width="60%" height="60%" alt="image" src="https://github.com/user-attachments/assets/5d9f19f4-d323-410b-b69a-fd54c3a67a28" />


**Status:** the raw block layer (init + sector **read**/**write**) and
FAT16 (mount, walk root *and* subdirectories, read files, and
**overwrite a file in place**) are all hardware-verified — the PDP-11
mounts a formatted card, walks the tree, dumps a file, round-trips a
scratch-sector write, and overwrites `TEST.TXT` (verified on a PC
afterward). FAT can overwrite existing data in place, the allocation
primitives (free-cluster search + FAT-entry write to both copies) are
verified reversibly, and it can **create, delete, and rename** files in the root — including
**multi-cluster** files, allocating and linking the FAT chain as it
writes — and **create subdirectories** (`FATMKD`, with the `.` and `..`
entries). It does not yet write files *inside* a subdirectory. 8.3
names only.

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
- `sdwtest.mac` — write test: pattern → scratch LBA 100 (in the MBR gap,
  outside the FAT volume) → read back → verify; saves and restores the
  original sector.
- `fat16.mac` — read-only FAT16 on top of `sd.mac`: `FATMNT` (read MBR +
  BPB, compute geometry), a directory iterator (`FATNXT`) that walks the
  root or any subdirectory (`FATDIR0` / `FATCD` / `FATREW`), and file
  reading (`FATOPN` + `FATRD`) via the cluster chain. 32-bit LBAs as
  word pairs, EIS `MUL` for cluster arithmetic.
- `fattest.mac` — FAT bring-up: mount, print geometry, recursively walk
  the directory tree (indented, with sizes; depth/entry capped), then
  open and dump the first regular file as text.
- `fatwtest.mac` — FAT overwrite test: rewrite `TEST.TXT` in place with
  a same-length pattern via `FATWR`, read back, verify (leaves the file
  changed so it can be confirmed on a PC).
- `fatatest.mac` — FAT allocation test: `FATFREE` a cluster, confirm
  it's free, `FATWEN` an EOC marker into both FAT copies, verify, then
  restore it — reversibly, so the FAT ends unchanged.
- `sdtest.prj` / `sdwtest.prj` / `fattest.prj` / `fatwtest.prj` /
  `fatatest.prj` — J11Terminal projects (origin 1000).

## Projects (which `.prj` does what)

Each `.prj` is a self-contained J11Terminal project (origin 1000) that
builds one test program on top of `sd.mac` / `fat16.mac`.

| Project | What it exercises |
|---------|-------------------|
| `sdtest.prj`  | Raw SD bring-up: CMD0 wiring probe, init, capacity class, sector-0 hex dump (the MBR) |
| `sdwtest.prj` | Raw sector **write**: pattern → scratch LBA 100 → read back → verify; saves/restores the sector |
| `fattest.prj` | FAT16 mount + geometry, recursive **directory-tree** walk, dump the first file |
| `fatwtest.prj`| FAT16 **overwrite** `TEST.TXT` in place (same length), read back, verify |
| `fatatest.prj`| FAT16 **allocation** primitives: `FATFREE` + `FATWEN` a cluster to EOC in both FAT copies, verify, restore (reversible) |
| `fatctest.prj`| FAT16 file **create**: make `PDPFILE.TXT` (allocate cluster + write directory entry + data), read back, verify (re-runnable; leaves the file on the card) |
| `fatdtest.prj`| FAT16 file **delete**: create `DELME.TXT`, confirm present, `FATDEL` it, confirm gone (frees the chain + marks the entry 0xE5; self-cleaning) |
| `fatxtest.prj`| FAT16 **multi-cluster** create/extend: make a 33 KB `XBIG.TXT` (> one 32 KB cluster), check the chain spans two clusters, verify the data, then delete it (self-cleaning) |
| `fatntest.prj`| FAT16 **rename**: create `RENFROM.TXT`, `FATREN` it to `RENTO.TXT`, verify the new name has the data and the old is gone, delete (self-cleaning) |
| `fatmtest.prj`| FAT16 **make directory**: `FATMKD` `NEWDIR`, verify it's a directory, descend and check the `.` / `..` entries, then remove it (self-cleaning) |

## Using it

Open `sdtest.prj` in J11Terminal, Assemble, Upload, `P`. On a formatted
card you should see the init succeed, `SDHC BLOCK-ADDRESSED`, and the
MBR in the sector-0 dump — the partition entry at offset 0x1BE and
`55 AA` at 0x1FE.

`fattest.prj` is the FAT layer: it mounts, prints the geometry, walks
the directory tree, and dumps the first file. (A card formatted on a Mac
carries a `.Spotlight-V100` tree — real macOS index data, listed
correctly but noisy; a card you populate yourself is cleaner.)

`SDINI` error codes (also in the source header): 1 no card, 2 CMD0 never
idle, 3 CMD8 rejected, 4 ACMD41 timeout, 5 CMD58/OCR. The `PROBE` line
distinguishes hardware faults: all `FF` = card silent (power/level/MISO),
all `00` = MISO stuck low, a byte with bit 7 clear (e.g. `01`) = the card
is answering.

## Card format

Small FAT16 (≤ 2 GB, MBR) is what the FAT layer here reads; the volume
starts at LBA 2048 on a Mac-formatted card. For PDP-11-only storage a
filesystem is optional — the raw sector layer alone backs a disk image
or program library.

Runs on the DCJ-11 SBC + Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).
