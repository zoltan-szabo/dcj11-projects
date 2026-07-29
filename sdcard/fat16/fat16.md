# fat16.mac — a FAT16 filesystem layer for the DCJ-11

`fat16.mac` is a small, self-contained FAT16 implementation in MACRO-11.
It sits on top of a raw 512-byte block driver (`../sddrv/sd.mac`) and
turns an SD/microSD card formatted as FAT16 into a readable and writable
filesystem: mount, walk directories, read files, and the full set of
write operations (create, delete, rename, overwrite, mkdir/rmdir) — in
the root or in any subdirectory, at any nesting depth.

It reads and writes only what it needs a sector at a time through a
single shared 512-byte buffer, so it runs comfortably in the DCJ-11
SBC's memory. It handles **8.3 short names only** (VFAT long-name
entries are recognised and skipped, never created).

This document is the reference for how it works and how to use it. The
source header in `fat16.mac` carries a condensed version of the API.

---

## 1. What FAT16 looks like on the card

A FAT16 volume is a chain of fixed regions laid out in this order,
starting at the partition's first sector (the **partition start LBA**):

```
  partition start
  ┌───────────────────────────────────────────────────────────────┐
  │ reserved (incl. the boot/BPB sector)   RESSEC sectors          │
  ├───────────────────────────────────────────────────────────────┤
  │ FAT copy 1                              SPFAT sectors           │
  │ FAT copy 2 (usually)                    SPFAT sectors           │
  ├───────────────────────────────────────────────────────────────┤
  │ root directory (fixed size)             RDSEC  sectors          │
  ├───────────────────────────────────────────────────────────────┤
  │ data region: clusters 2, 3, 4, …        rest of the volume      │
  └───────────────────────────────────────────────────────────────┘
```

Everything is addressed in 512-byte sectors by **LBA** (Logical Block
Address). On a modern (SDHC/SDXC) card the block driver is block-
addressed, so an LBA maps straight to a card block. LBAs are 32-bit; this
code carries them as **word pairs** (low word, high word) and passes them
to `sd.mac` in the `R0:R1` register pair.

### 1.1 The MBR (sector 0)

A card partitioned the normal way (as a Mac or PC does) begins with a
Master Boot Record at LBA 0. `fat16.mac` reads only two things from it:

| Offset | Size | Field                                 |
|-------:|-----:|---------------------------------------|
| 0x1BE  | 16 B | partition table entry 1               |
| 0x1C6  |  4 B | entry 1: first LBA of the partition   |
| 0x1FE  |  2 B | boot signature `55 AA`                |

The partition's first LBA (little-endian at 0x1C6) is where the FAT16
volume — and its BPB — begins. On a Mac-formatted card this is typically
LBA 2048.

### 1.2 The BPB (BIOS Parameter Block)

The first sector of the partition holds the boot sector, whose BPB
describes the geometry. The fields this code uses:

| Offset | Size | Field                | Symbol   |
|-------:|-----:|----------------------|----------|
| 0x0B   |  2 B | bytes per sector (512) | —      |
| 0x0D   |  1 B | sectors per cluster    | SPCLUS |
| 0x0E   |  2 B | reserved sectors       | RESSEC |
| 0x10   |  1 B | number of FATs         | NFATS  |
| 0x11   |  2 B | root entry count       | RENTC  |
| 0x13   |  2 B | total sectors (16-bit) | TOTSEC |
| 0x16   |  2 B | sectors per FAT        | SPFAT  |
| 0x20   |  4 B | total sectors (32-bit) | TOTSEC |
| 0x1FE  |  2 B | signature `55 AA`      | —      |

Total sectors lives in **two** places: the 16-bit field at 0x13 is used
if it is non-zero, otherwise the 32-bit field at 0x20. All multi-byte
fields are little-endian.

### 1.3 The FAT (File Allocation Table)

The FAT is an array of 16-bit little-endian entries, one per cluster.
Entry *N* is the word at byte `N*2` of the FAT region. It records what
follows cluster *N* in a file's chain:

| Entry value        | Meaning                          |
|--------------------|----------------------------------|
| `0x0000`           | free cluster                     |
| `0x0002`–`0xFFEF`  | next cluster in the chain        |
| `0xFFF8`–`0xFFFF`  | end of chain (EOC)               |
| `0x0001`, `0xFFF0`–`0xFFF6` | reserved / bad         |

Clusters are numbered from **2** (0 and 1 are reserved), so the first
data cluster is cluster 2. There are usually two identical FAT copies;
writes must update **all** of them (see `FATWEN`).

### 1.4 The root directory and directory entries

The root directory is a **fixed-size** region (unlike subdirectories,
which are cluster chains in the data region). It holds `RENTC` 32-byte
entries across `RDSEC` sectors. A subdirectory has the identical entry
format but lives in data clusters and grows by extending its chain.

Each 32-byte directory entry:

| Offset | Size | Field                                        |
|-------:|-----:|----------------------------------------------|
| 0x00   | 11 B | 8.3 name: 8 name + 3 ext, space-padded       |
| 0x0B   |  1 B | attributes                                   |
| 0x0C   | 14 B | reserved / timestamps (unused here)          |
| 0x1A   |  2 B | first cluster (low word)                     |
| 0x1C   |  4 B | file size in bytes (32-bit)                  |

Attribute bits (byte 0x0B):

| Bit    | Meaning                                            |
|--------|----------------------------------------------------|
| `0x10` | directory                                           |
| `0x08` | volume label                                        |
| `0x0F` | (all four low bits) a VFAT long-name fragment       |
| `0x20` | archive (an ordinary file)                          |

First-name-byte special values:

| First byte | Meaning                                            |
|------------|----------------------------------------------------|
| `0x00`     | end of directory — no entries beyond this          |
| `0xE5`     | deleted / free slot                                |
| `0x2E`     | `.` or `..` (only inside a subdirectory)           |

The iterator skips `0xE5` (deleted), `0x0F` (long-name) and `0x08`
(volume label) entries, and stops at the first `0x00`.

---

## 2. Geometry: turning the BPB into LBAs

`FATMNT` reads the MBR and BPB and computes the region LBAs once, so the
rest of the code is just arithmetic:

```
  fatStart   = partStart + reservedSectors
  rootStart  = fatStart  + numFATs * sectorsPerFAT
  rootDirSec = ceil(rootEntryCount * 32 / 512)      ; root region size
  dataStart  = rootStart + rootDirSec               ; LBA of cluster 2
```

A cluster maps to its first LBA with:

```
  clusterLBA(N) = dataStart + (N - 2) * sectorsPerCluster
```

The `(N-2)*sectorsPerCluster` and `numFATs*sectorsPerFAT` products use
the J-11 **EIS `MUL`** (a 16×16→32-bit multiply into a register pair).
The `rootDirSec` round-up (`*32`, `+511`, `>>9`) is done with a shift
loop, since `>>9` is just nine right shifts of a 32-bit value.

### 2.1 The real cluster count

The FAT is padded up to whole sectors, so it has room for **more** entries
than the volume has real clusters. To avoid ever allocating a cluster
past the end of the data region, `FATMNT` also computes the true count:

```
  dataSectors     = totalSectors - (dataStart - partStart)
  countOfClusters = dataSectors / sectorsPerCluster
  MAXCLUS         = countOfClusters + 1     ; highest valid cluster number
```

`FATFREE` never returns a cluster above `MAXCLUS`.

> **Gotcha — do not divide this with EIS `DIV`.** PDP-11 `DIV` is a
> *signed* divide: the quotient must fit in −32768…32767. A FAT16 cluster
> count is routinely 40 000–65 000, which overflows — and on overflow the
> J-11 leaves the dividend registers *unchanged* (and sets `V`). An early
> version used `DIV` and got a cluster count equal to the dividend's high
> word (the untouched register). Because `sectorsPerCluster` is always a
> power of two, the divide is done as a right shift instead:
> `count = dataSectors >> log2(sectorsPerCluster)`.

---

## 3. Using the code

Assemble your program together with `fat16.mac` and `sd.mac` (see the
`sdls` sample). Call `SDINI` (from `sd.mac`) first to bring up the card,
then `FATMNT`, then the calls below. Everything returns a status in `R0`
(`0` = success unless noted).

### 3.1 Mount and navigation

| Call     | In / Out | Description |
|----------|----------|-------------|
| `FATMNT` | → `R0` = 0 / 1 bad MBR sig / 2 bad BPB sig / 3 read error | Read MBR + BPB, compute geometry. |
| `FATDIR0`| — | Make the root directory current, rewound. |
| `FATCD`  | `R0` = first cluster (0 = root) | Make that subdirectory current, rewound. Use a `DECLUS` from a listing, or a `..` entry's cluster. |
| `FATREW` | — | Rewind the current directory. |

### 3.2 The directory iterator

`FATNXT` returns the next valid 8.3 entry of the current directory, or
`R0 = 1` at the end. After a successful call the entry's fields are in:

| Symbol   | Contents                                   |
|----------|--------------------------------------------|
| `DENAME` | 11 bytes, the space-padded 8.3 name        |
| `DEATTR` | attribute byte (test `0x10` for directory) |
| `DECLUS` | first cluster                              |
| `DESIZE` | 32-bit size (low word, high word)          |

Descend into a subdirectory by calling `FATCD` with its `DECLUS`.

### 3.3 Reading a file

| Call     | In / Out | Description |
|----------|----------|-------------|
| `FATOPN` | `R1` → 11-byte name; → `R0` = 0 found / 1 not found | Find a name in the current directory and open it. |
| `FATRD`  | `R2` → 512-byte buffer; → `R0` = bytes read (0 = EOF) | Read the next sector of the open file. |

### 3.4 Writing

Overwrite in place, never extending:

| Call     | In / Out | Description |
|----------|----------|-------------|
| `FATWR`  | `R2` → buffer; → `R0` = bytes written (0 = done) | Overwrite the open file's next sector in place. Re-`FATOPN` before switching between reading and writing. |

Whole-file and directory operations. The `…C` variants act on the
**current** directory (set with `FATCD`), so they work in subdirectories
and nest; the plain names are thin wrappers that just select the root
first (`FATDIR0` then the core):

| Call (root / current) | In | Out (`R0`) |
|-----------------------|----|-----------|
| `FATCRE` / `FATCREC`  | `R1` → name, `R2` → data buffer, `R3` = length | 0 ok / 2 exists / 3 no cluster / 4 dir full / 6 write / 7 out of space |
| `FATDEL` / `FATDELC`  | `R1` → name | 0 ok / 1 not found / 2 write |
| `FATREN` / `FATRENC`  | `R1` → old name, `R2` → new name | 0 ok / 1 not found / 2 new name exists / 3 write |
| `FATMKD` / `FATMKDC`  | `R1` → name | 0 ok / 2 exists / 3 no cluster / 4 dir full / 6 write |
| `FATRMD` / `FATRMDC`  | `R1` → name | 0 ok / 1 not found / 2 write / 3 not empty / 4 not a directory |

`FATCRE` allocates and links a multi-cluster chain as needed; the data
buffer must hold `ceil(length/512)` whole sectors. `FATMKD` writes the
mandatory `.` (→ itself) and `..` (→ the parent) entries and zeroes the
new cluster so no stale data appears as phantom entries. `FATRMD`
refuses a non-empty directory.

### 3.5 Allocation primitives (used internally, usable directly)

| Call      | In / Out | Description |
|-----------|----------|-------------|
| `FATFREE` | → `R0` = a free cluster, or 0 if none (bounded by `MAXCLUS`) | Scan the FAT for a `0x0000` entry. |
| `FATWEN`  | `R0` = cluster, `R1` = value; → `R0` = 0 / 1 error | Write a FAT entry into **every** FAT copy. |
| `FATSLOT` | → `R0` = 0 / 3 / 4 / 6, and `DSLBA`/`DSHI`/`DSOFF` | Find a free directory slot in the current directory, extending a subdirectory's chain if it is full. |

Names must be pre-formatted as 11 bytes: 8-char name + 3-char extension,
upper-case, space-padded — e.g. `"README  TXT"`, `"SUBDIR     "`.

### 3.6 A minimal listing

```
	JSR	PC, SDINI	; from sd.mac
	JSR	PC, FATMNT
	JSR	PC, FATDIR0
1$:	JSR	PC, FATNXT
	TST	R0
	BNE	2$		; end of directory
	; DENAME / DEATTR / DECLUS / DESIZE now hold this entry
	BR	1$
2$:	...
```

See `../sample/sdls.mac` for the complete, working version.

---

## 4. Design notes and constraints

- **One shared sector buffer.** `FATBUF` (512 bytes) is reused for the
  MBR, BPB, FAT sectors and directory sectors. Any call that touches the
  FAT (`FATNX`, `FATFREE`, `FATWEN`) invalidates the directory cache
  (`DLOADED`), so the iterator reloads its sector as needed. Keep this in
  mind if you interleave operations.

- **32-bit LBAs as word pairs.** Sector numbers are `(low, high)` word
  pairs. 32-bit add/subtract uses the `ADD`/`ADC` and `SUB`/`SBC`
  idioms; cluster arithmetic uses EIS `MUL`.

- **8.3 names only.** VFAT long-name entries (attribute `0x0F`) are
  skipped on read and never written. A file created here shows its short
  name; the OS that reads the card afterwards may add a long name.

- **Current-directory model.** Read and write operations act on whatever
  directory `FATDIR0`/`FATCD` last selected. The `…C` write cores rely
  on the same `DELBA`/`DEHI`/`DEOFF` entry-location that the iterator
  records for *any* directory, which is why root and subdirectory writes
  share one code path.

- **I/O page.** On the DCJ-11 the top 8 KB (0o160000–0o177777) is the
  device I/O page. Any data buffer you pass to `FATRD`/`FATWR`/`FATCRE`
  must live **below** 0o160000, or reads and writes will hit device
  registers instead of RAM.

- **`FATWR` never extends.** It overwrites within the file's existing
  size and stops; it never allocates or touches the FAT/directory. Use
  `FATCRE` to (re)create a file at a new length.

- **Directory-chain growth.** A fresh subdirectory cluster holds ~1024
  entries, so `FATSLOT`'s chain-extension path only triggers with very
  large directories; it is exercised by construction rather than by the
  test suite.

---

## 5. Formatting a card

Small FAT16 (≤ 2 GB, MBR-partitioned) is what this layer reads. On a Mac
the volume typically starts at LBA 2048. A card populated by this code is
cleaner to inspect than a Mac-formatted one, which carries a
`.Spotlight-V100` index tree (real data, listed correctly, but noisy).

For PDP-11-only storage a filesystem is optional — the raw block layer
in `../sddrv/sd.mac` alone backs a disk image or program library.

---

## 6. Where this came from

This layer was built and hardware-verified incrementally on the DCJ-11
SBC + Multi IO card (Peter Schranz, <https://www.5volts.ch/pages/dcj11sbc/>),
one operation at a time — block driver, read-only mount and tree walk,
overwrite, allocation primitives, create/delete/rename, mkdir/rmdir, then
the generalisation to subdirectories and nesting. Every step has a
corresponding program under `../discovery/`, which doubles as a test
suite and a record of the development path.
