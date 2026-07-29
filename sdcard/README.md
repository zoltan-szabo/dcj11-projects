# sdcard — microSD driver + FAT16 filesystem for the DCJ-11

Bit-banged SPI-mode SD/microSD access from the PDP-11 — the card init
ladder and 512-byte sector read/write over the W65C22S VIA — plus a
FAT16 filesystem layer on top: mount, walk the directory tree, read
files, and the full set of write operations (create, delete, rename,
overwrite, mkdir/rmdir) in the root or any subdirectory, at any depth.

<img width="60%" height="60%" alt="image" src="https://github.com/user-attachments/assets/5d9f19f4-d323-410b-b69a-fd54c3a67a28" />

All of it is hardware-verified on the DCJ-11 SBC + Multi IO card by Peter
Schranz (<https://www.5volts.ch/pages/dcj11sbc/>) on a Catalex-style
microSD breakout. 8.3 names only.

## Layout

```
sdcard/
├── sddrv/       the SD/SPI block driver
│   └── sd.mac       SDINI · SDRD · SDWR   (LBA in R0:R1, buffer in R2)
├── fat16/       the FAT16 filesystem layer
│   ├── fat16.mac    mount, iterate, read, and all write operations
│   └── fat16.md     full reference: on-disk format, API, design notes
├── sample/      a working demo built on the two modules above
│   ├── sdls.mac     mount the card and list the root directory
│   └── sdls.prj
└── discovery/   every program from the development cycle (see below)
```

**Start here:** open `sample/sdls.prj` in J11Terminal, Assemble, Upload,
`P` — it prints the root directory of a formatted card. For the full
filesystem API and how FAT16 works on disk, read **`fat16/fat16.md`**.

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

`SDINI` error codes: 1 no card, 2 CMD0 never idle, 3 CMD8 rejected,
4 ACMD41 timeout, 5 CMD58/OCR. Block-addressed SDHC/SDXC (every modern
microSD). `sd.mac` carries its own SPI mode-0 primitives because the SD
pin map differs from `../spi/spi.mac`.

## discovery/ — the development cycle

Each program under `discovery/` exercises one step of the build-up and
doubles as its regression test. They include the two modules by relative
path (`../fat16/fat16.mac`, `../sddrv/sd.mac`), so they still assemble in
place. All are self-cleaning (they leave the card as they found it)
unless noted.

| Project | What it exercises |
|---------|-------------------|
| `sdtest.prj`  | Raw SD bring-up: CMD0 wiring probe, init, capacity class, sector-0 hex dump (the MBR) |
| `sdwtest.prj` | Raw sector **write**: pattern → scratch LBA 100 → read back → verify; saves/restores the sector |
| `fattest.prj` | FAT16 mount + geometry, recursive **directory-tree** walk, dump the first file |
| `fatwtest.prj`| FAT16 **overwrite** `TEST.TXT` in place (same length), read back, verify |
| `fatatest.prj`| FAT16 **allocation** primitives: `FATFREE` + `FATWEN` a cluster to EOC in both FAT copies, verify, restore |
| `fatctest.prj`| FAT16 file **create**: `PDPFILE.TXT` (allocate + entry + data), read back, verify (leaves the file) |
| `fatdtest.prj`| FAT16 file **delete**: create `DELME.TXT`, confirm present, `FATDEL`, confirm gone |
| `fatxtest.prj`| FAT16 **multi-cluster** create/extend: a 33 KB `XBIG.TXT` spanning two clusters, verify, delete |
| `fatntest.prj`| FAT16 **rename**: `RENFROM.TXT` → `RENTO.TXT`, verify data moved and old name gone, delete |
| `fatmtest.prj`| FAT16 **make directory**: `FATMKD NEWDIR`, verify the `.`/`..` entries, remove |
| `fatrtest.prj`| FAT16 **remove directory**: confirm `FATRMD` refuses a non-empty dir (code 3), then removes the empty one |
| `fatstest.prj`| FAT16 **subdirectory writes**: create/rename/delete a file *inside* `SUBDIR`, verify it never appears in root |
| `fat2test.prj`| FAT16 **nested directories**: `NESTED` inside `TOP`, check `NESTED`'s `..` points at `TOP`'s cluster |
| `fatgtest.prj`| FAT16 **geometry + free-cluster bound**: print total sectors, sectors/cluster, cluster count; check `FATFREE` is in range |
| `divtest.prj` | EIS **`DIV` probe**: shows PDP-11 `DIV` is signed (quotient > 32767 overflows) — the reason `fat16` divides by shifting |

## Card format

Small FAT16 (≤ 2 GB, MBR) is what the FAT layer reads; on a Mac-formatted
card the volume starts at LBA 2048 and carries a `.Spotlight-V100` index
tree (real data, listed correctly, but noisy). A card you populate
yourself is cleaner. For PDP-11-only storage a filesystem is optional —
the raw block layer alone backs a disk image or program library.

Runs on the DCJ-11 SBC + Multi IO card by Peter Schranz
(<https://www.5volts.ch/pages/dcj11sbc/>).
