#!/usr/bin/env python3
"""mkrom.py -- pack the two-stage eeboot into ROM programmer images for the
Multi IO boot ROM sockets (U6 = DAL0-7 = low byte, U8 = DAL8-15 = high byte).

ROM layout (must match eeboot0.mac):
  chip 0x1500..0x153F  stage 0        (eeboot0.oct, org 173000, <= 64 words)
  chip 0x1540..0x15FF  loader part 1  (eeboot.oct words 0..191, org 70000)
  chip 0x0A00..0x0AFF  loader part 2  (eeboot.oct words 192..447)
(The 173000 window shows chip page 0x1500, the 165000 window page 0x0A00;
 one byte per chip per word.)

For W27C512 (64K) parts the 8 KB block is replicated 8x so the tied-off high
address pins never matter.

usage: mkrom.py [eeboot0.oct] [eeboot.oct] [--size 8k|16k|32k|64k]
writes eeboot-u6-low.bin and eeboot-u8-high.bin
"""
import sys, pathlib

args = [a for a in sys.argv[1:] if not a.startswith("-")]
s0_path = pathlib.Path(args[0] if len(args) > 0 else "eeboot0.oct")
ld_path = pathlib.Path(args[1] if len(args) > 1 else "eeboot.oct")
sizes = {"8k": 1, "16k": 2, "32k": 4, "64k": 8}
size = "64k"
if "--size" in sys.argv:
    size = sys.argv[sys.argv.index("--size")+1].lower()
    if size not in sizes:
        sys.exit(f"--size must be one of {list(sizes)}")

BLOCK = 8 * 1024
S0_OFF, S0_MAX = 0x1500, 64
P1_OFF, P1_MAX = 0x1540, 192
P2_OFF, P2_MAX = 0x0A00, 256

def read_oct(path, base):
    words, addr = [], None
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("@"):
            addr = int(ln[1:], 8)
            if addr != base:
                sys.exit(f"{path}: expected @{oct(base)[2:]}, got @{ln[1:]}")
        else:
            words.append(int(ln, 8))
    return words

s0 = read_oct(s0_path, 0o173000)
ld = read_oct(ld_path, 0o070000)
if len(s0) > S0_MAX:
    sys.exit(f"stage 0 is {len(s0)} words, limit {S0_MAX}")
if len(ld) > P1_MAX + P2_MAX:
    sys.exit(f"loader is {len(ld)} words, limit {P1_MAX + P2_MAX}")

lo = bytearray([0xFF] * BLOCK)
hi = bytearray([0xFF] * BLOCK)

def place(words, off):
    for i, w in enumerate(words):
        lo[off + i] = w & 0xFF
        hi[off + i] = (w >> 8) & 0xFF

place(s0, S0_OFF)
place(ld[:P1_MAX], P1_OFF)
place(ld[P1_MAX:], P2_OFF)

blo, bhi = bytes(lo) * sizes[size], bytes(hi) * sizes[size]

pathlib.Path("eeboot-u6-low.bin").write_bytes(blo)
pathlib.Path("eeboot-u8-high.bin").write_bytes(bhi)
print(f"stage0 {len(s0)}w + loader {len(ld)}w ({len(ld)-P1_MAX if len(ld)>P1_MAX else 0} in window 2) "
      f"-> eeboot-u6-low.bin / eeboot-u8-high.bin ({len(blo)} bytes each)")
