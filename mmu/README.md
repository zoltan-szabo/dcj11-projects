# MMU — using memory above 64 KB

The J-11's program counter is 16 bits, so at any instant it can only name
64 KB. The on-chip MMU maps that 16-bit **virtual** address onto a 22-bit
**physical** address (up to 4 MB), so reaching more memory means keeping a
64 KB window and sliding it around physical RAM — classic PDP-11 banking.

The 64 KB space is eight 8 KB pages. Each page *n* has a **PAR** (physical
base, in 64-byte blocks) and a **PDR** (access + length):
`physical = PAF*0100 + offset-in-page`.

## Driver (`mmu.mac`)

| Routine | Does | Clobbers |
|---|---|---|
| `MMUON` | Identity-map the low 64 KB (page 7 → 22-bit I/O page) and enable 22-bit relocation. Existing code keeps running. | R0-R2 |
| `MMUOFF` | Turn relocation off (back to plain 16-bit). | — |
| `WINDOW` | Point the window page at physical block `R0` (PAF). For an 8 KB bank *k*, `R0 = k*0200`. | — |

The window is page 6 (`WINVA = 140000`). After `WINDOW`, the range
`140000..157777` is an 8 KB view of the physical memory you selected.
**Never re-point the page your code or stack lives in** — keep those in the
low, identity-mapped pages.

## Demo (`demo.mac`)

```
m11asm -b 1000 demo.mac
```

Upload `demo.oct`, then `1000G`. It enables the MMU, writes a distinct
signature into four high banks (8, 32, 64, 96 → physical 0200000, 1000000,
2000000, 3000000), reads each back through the window, and prints to the
console:

```
MMU on - testing RAM above 64K
PASS - high memory reads back correctly
```

`PASS` proves the banks are real, distinct physical memory: if the high
addresses aliased (no RAM there), the later writes would overwrite the
earlier ones and the read-back would mismatch (`FAIL`).

## This board: 512 kW

512 kW = 1 MB = **128 banks** of 8 KB, physical `0`..`3777777`. The low 64 KB
is banks 0..7, so banks 8..127 are all usable high RAM. Mapping a window onto
an address with no RAM behind it gives a bus timeout (trap), so keep bank
indices ≤ 127 on this board.

## Placing code to run high

Load and run addresses differ. Assemble a high routine with its **virtual**
run address as the origin (e.g. `m11asm -b 120000`), then edit the `.oct`'s
`@120000` line to the **physical** deposit address (J11Terminal keeps the
octal editable for exactly this). A resident setup routine in low memory then
`WINDOW`s that bank in and `JSR`s to the virtual address.

## Note on MACRO-11 expressions

MACRO-11 evaluates left to right with **no operator precedence**, so
`A + B*2` means `(A + B)*2`. `mmu.mac` writes `WINPAG*2 + KIPAR0` for that
reason — put the multiply first.

Runs on the DCJ-11 SBC + Multi IO card by Peter Schranz
(https://www.5volts.ch/pages/dcj11sbc/).
