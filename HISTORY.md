# History

Detailed notes per change. Commit messages stay short; the long story
lives here.

## sdcard: reorganised into a proper project (2026-07-29)

The directory had grown to ~45 files in one flat folder. Split it into
`sddrv/` (sd.mac), `fat16/` (fat16.mac + a new full reference fat16.md),
`sample/` (sdls — mount and list the root directory, the "hello world"
of the layer), and `discovery/` (all 15 dev-cycle programs, including
the divtest DIV probe). Confirmed m11asm resolves `.INCLUDE` relative to
the including file, so the discovery tests include the modules via
`../fat16/…` / `../sddrv/…` and still assemble in place; J11Terminal
handles the subfolder paths in the `.prj` file lists too. README rewritten
as an overview pointing at fat16.md; build artifacts (.oct/.lst/.sym,
never tracked) cleaned out. No code changed — pure reorganisation.

## sdcard: FAT16 free-cluster bound + a DIV gotcha (2026-07-29)

FATFREE was bounded only by the FAT's size in sectors, so on a full
volume it could hand back a cluster past the end of the data region (the
FAT is padded to whole sectors and has more entries than there are real
clusters). FATMNT now reads totalSectors (16-bit at 0x13, else 32-bit at
0x20), computes countOfClusters = (totalSectors - dataOffset) / spc, and
stores MAXCLUS = count + 1; FATFREE refuses any candidate above it. The
gotcha: the first cut used the EIS DIV and fatgtest printed a cluster
count of 0x3B for a 2 GB card - exactly the high word of the 0x003B9AD0
total. A hardware probe (divtest) isolated why: PDP-11/J-11 DIV is a
SIGNED divide, so a quotient over 32767 overflows and leaves the
dividend register pair UNCHANGED - and 0x003B9AD0/64 = 61019 is well
over 32767, so DIV left R4 = the high word 0x3B. Not an m11asm bug (the
encoding was textbook-correct). Fixed by replacing DIV with a shift:
sectorsPerCluster is always a power of two, so count = dataSectors >>
log2(spc), done with the same CLC/ROR 32-bit shift idiom already used
for rootDirSec. fatgtest then read totalSec 0x003B9AD0, spc 0x40, count
0xEE63 - a valid FAT16 count (~2 GB / 32 KB). The full-volume
refusal itself can't be exercised without filling the card, so it is
code-correct but not hardware-tested; the normal in-range path is.

## sdcard: FAT16 nested directories (2026-07-29)

FATMKD and FATRMD got the same wrapper/core split as the file ops, so a
subdirectory can be made or removed inside another subdirectory (not just
the root). FATMKDC's one wrinkle: the new directory's ".." must point at
its REAL parent, not always the root - so it takes the parent cluster
from the current directory (DSTART, or 0 when the parent is the root)
and writes that into the ".." entry, where FATMKD had hardcoded 0.
FATRMDC's wrinkle: its emptiness scan descends via FATCD, which clobbers
the current-directory pointer, so it saves DMODE/DSTART on entry and
restores them (RMREST) before deleting the entry in the parent via
FATDELC. Both root wrappers stay "FATDIR0 then the core", and FATMKD's
dir-full path now propagates FATSLOT's real code (3/4/6) like FATCRE.
`fat2test.mac` makes TOP, then NESTED inside it, and checks NESTED's ".."
cluster equals TOP's (a plain root subdir would read 0000 there), then
removes both - passed first run: TOP at cluster 3, NESTED ".." = 0003.
That completes the write ladder: every file and directory operation now
works at any depth.

## sdcard: FAT16 subdirectory writes (2026-07-29)

Files can now be created, renamed, and deleted INSIDE a subdirectory,
not just the root. The refactor: FATCRE/FATDEL/FATREN each became a thin
root wrapper ("FATDIR0 then the core") plus a current-directory core
FATCREC/FATDELC/FATRENC that acts on whatever FATCD last selected. The
cores already used the DELBA/DEOFF/FCLUS the iterator records for any
directory, so the only thing that had forced root was the leading
FATDIR0 - and FATDIR0 leaves R1/R2/R3 untouched, so the wrapper falls
straight through into the core. FATSLOT was generalized: root still
scans the fixed region (can't grow -> "dir full"), a subdirectory walks
its cluster chain and, if no free/deleted slot is found, extends the
chain by one freshly-zeroed cluster (link previous->new, new->EOC). Two
small tidy-ups fell out: FATSLOT now returns a uniform "dir full" = 4
(both callers already remapped its old 1 to 4, so no observable change),
and FATCRE propagates FATSLOT's real code (3/4/6) instead of always
reporting 4. `fatstest.mac` drives the whole lifecycle in SUBDIR -
create INSIDE.TXT, verify the data AND that it never appears in the
root, rename, delete, then RMDIR the empty dir - and passed first run.
It exercises both FATSLOT paths at once (root via FATMKD's parent entry,
subdir via FATCREC). Directory-chain extension is code-correct but not
hardware-exercised: a fresh subdir cluster holds ~1024 entries, too many
to fill in a test.

## sdcard: FAT16 subdirectory removal (2026-07-29)

FATRMD (R1 -> 11-byte name): the honest counterpart to the FATDEL
shortcut the MKDIR test used. Confirm it's a directory (attr 0x10),
descend, scan for any entry past "." and ".."; if the directory is empty
hand the removal to FATDEL (free the one-cluster chain + mark the parent
entry), otherwise return "not empty" without touching anything. Codes
0/1 not found/2 write/3 not empty/4 not a directory. `fatrtest.mac`
tests both halves honestly: after MKDIR it injects a directory entry
straight into the new cluster (raw SDRD/SDWR via CLBA) so the dir is
genuinely non-empty, checks FATRMD refuses, clears the entry, then checks
FATRMD removes it. First run surfaced a state leak - the emptiness scan
uses FATCD, and the code-3 path returned without restoring the root as
current dir, so the test's follow-up FATOPN searched inside the subdir
and misread "vanished". Fixed by a FATDIR0 before the code-3 return (the
success path already ends at root via FATDEL). The directory was never
actually deleted - the guard worked; only the current-dir state leaked.

## sdcard: FAT16 subdirectory creation (2026-07-29)

FATMKD (R1 -> 11-byte name): the first structural write. Allocate a
cluster, mark it EOC, zero the whole cluster (all 64 sectors - so no
stale data from a previously-deleted file shows up as a phantom entry),
write the mandatory "." (first cluster = itself) and ".." (first cluster
= 0, the root) entries with attr 0x10 in the first sector, then add a
directory entry (attr 0x10, size 0) in the root via FATSLOT. Root parent
only. `fatmtest.mac` makes NEWDIR, confirms the directory bit, descends
and checks the iterator returns "." then "..", then removes it - an
empty directory is just a one-cluster chain, so FATDEL frees it (no
emptiness guard yet; that's the job of a proper RMDIR). Hardware: clean
first run, NEWDIR landed at cluster 3.

## sdcard: FAT16 rename (2026-07-29)

FATREN (R1 old name, R2 new name): the smallest write op - FATOPN the
old name (the iterator records the entry's DELBA/DEHI/DEOFF), confirm the
new name doesn't already exist, then re-read the entry's sector,
overwrite just the 11 name bytes in place, write it back. No FAT touch,
no data move. Root only. `fatntest.mac` creates RENFROM.TXT, renames to
RENTO.TXT, verifies the new name carries the same data and the old is
gone, then deletes. Hardware: clean first run. Reuses exactly the
entry-location tracking added for delete - which is turning into the
general "edit a directory entry" primitive.

## sdcard: FAT16 multi-cluster create + a latent chain-walk bug (2026-07-29)

FATCRE generalised: the data-write half now allocates and links a
cluster chain as the data flows - when a cluster fills and bytes remain,
FATFREE the next, FATWEN cur->next, mark next EOC, continue. The <=512
cap is gone (16-bit length). `fatxtest.mac` creates a 33280-byte (65
sector) file - one cluster is 64 sectors here, so it spans two - checks
the directory's first cluster FATNX'es to a real second cluster, verifies
the position pattern across the boundary, then deletes it (multi-cluster
free too). Self-cleaning.

Two bugs found, both instructive:
- Inverted branch: FATFREE returns the cluster (nonzero) on success, but
  the extend used `TST R0 / BNE out-of-space`, so a SUCCESSFUL alloc took
  the error path. Create failed exactly when extend worked.
- THE latent one: FATRD and FATWR hold the byte count in R3 and, on a
  cluster-boundary sector, call FATNX to follow the chain - but FATNX
  clobbers R3, so those routines returned a GARBAGE count on boundary
  sectors. Never caught before because every earlier test used files <= 1
  cluster, so the boundary path never ran. The disk data was always
  correct; only the readback count was wrong (a verify loop ran 3412
  bytes into garbage). Fix: save/restore R3 across FATNX in both. Third
  instance this project of "a subroutine clobbering a register holding a
  live value" (after SDCMD's R0 and a test harness's R0) - the recurring
  PDP-11 hazard.

Also relearned: test buffers must stay BELOW the I/O page (160000) or
reads/writes hit device registers, not RAM (a 33 KB buffer at 60000 ran
into it). And m11asm fills even a trailing .BLKB with zeros in its
contiguous emission, so a big buffer bloats the .oct - define it as a
fixed RAM address (=) instead.

## sdcard: FAT16 file delete (2026-07-29)

FATDEL (R1 name): FATOPN the file, walk its cluster chain freeing each
entry to 0x0000 (read the next link with FATNX BEFORE writing 0 to the
current, or the chain is lost), then mark the directory entry 0xE5.
Enabler: FATNXT now records each matched entry's location - the sector
LBA (DELBA/DEHI, saved at load) and byte offset in FATBUF (DEOFF, saved
at the valid-entry return) - so FATDEL knows which directory byte to
overwrite. That also unblocks any future in-place entry edit. `fatdtest`
is self-cleaning: create DELME.TXT, confirm present, delete, confirm
gone. Hardware: clean round trip, card unchanged. That completes the
core FAT16 write set - create, overwrite-in-place, delete - all
hardware-verified. Remaining: extend past one cluster (multi-cluster
chains) and subdirectory writes.

## sdcard: FAT16 file create (2026-07-29)

First creation of a file from the J-11. FATCRE (R1 name, R2 512-byte
data buffer, R3 length) builds a small single-cluster file in the root:
reject if the name already exists (FATOPN), FATFREE a cluster and
FATWEN it to EOC, FATSLOT a free 32-byte directory slot (first byte 0x00
never-used or 0xE5 deleted), zero the entry and fill name / attr 0x20 /
first-cluster-low (0x1A) / size (0x1C), write the directory sector back,
then write the one data sector. One cluster / one sector for now
(length <= 512); no extend, no delete, root only. FATSLOT is the genuinely
new primitive. `fatctest.mac` creates PDPFILE.TXT, reads it back, and
verifies; re-runnable (2nd run reports "exists" and verifies the
persisted copy). Hardware: "CREATED / VERIFIED", contents correct, and
the file appears on the card when read on a PC.

## sdcard: FAT16 allocation primitives (2026-07-29)

The shared foundation for file create/extend and delete: FATWEN (write
a FAT entry into every FAT copy, read-modify-write; entry N at FAT byte
N*2) and FATFREE (scan the FAT a sector at a time for a 0x0000 entry;
bounded by the FAT size for now, not the true cluster count). FATNX is
the entry reader. `fatatest.mac` tests them reversibly: FATFREE a
cluster, confirm FATNX reads it as 0 (abort if not — never write a used
cluster), FATWEN 0xFFFF, verify from BOTH copies (FAT2 read directly at
FATLBA+SPFAT), then FATWEN 0 to restore. Hardware: on the card cluster 2
was free; a pre/post raw dump of the FAT sector showed bytes 4-5 flip
00 00 -> FF FF, both copies held FFFF, and restore returned 0000 — FAT
unchanged.

Debug note: the primitives worked first try; the failure was in the
test — it called PMSG (which leaves R0 = the string's NUL) before saving
FATNX's result, so it compared 0 instead of 0xFFFF. Same trap as the
SDCMD R0-clobber earlier: a helper overwriting the register holding your
result. The raw FAT-sector dump is what proved the write had persisted
and pointed at the harness, not the driver.

## sdcard: FAT16 overwrite-in-place (2026-07-29)

`fat16.mac` gained FATWR — the write twin of FATRD: it walks the open
file's existing cluster chain and writes each sector with SDWR instead
of reading. Overwrite ONLY: it never extends or allocates, so it stops
at the file's current byte count and touches neither the FAT nor the
directory (the size and cluster chain are unchanged, so no metadata
update is needed). Re-open a file to switch between reading and writing
it. `fatwtest.mac` opens TEST.TXT, overwrites it in place with a
repeating same-length pattern, reads it back and verifies, and leaves
the file changed. Hardware: "VERIFIED - readback matches", and TEST.TXT
reads the PDP-11's text when the card is remounted on a PC. First real
modification of a FAT volume from the J-11. Next up the write ladder:
create/extend (free-cluster search + FAT/dir updates), then delete.

## sdcard: sector write verified (2026-07-29)

`sdwtest.mac` exercises sd.mac's SDWR (untested until now) safely:
writes a position-dependent pattern (byte[i] = (i+0x11) & 0xFF) to
scratch LBA 100 — in the MBR gap, before the partition at LBA 2048, so
it can't touch the FAT volume — reads it back into a 0xEE-poisoned
buffer (so a no-op read can't fake success), and compares. It saves the
original sector first and writes it back at the end. Hardware result:
"WRITE VERIFIED - 512 BYTES MATCH" on the first run. The block layer
(init + read + write) is now fully verified; the FAT16 write ladder is
unblocked (overwrite-in-place, then create/extend with cluster
allocation + FAT/dir updates, then delete).

## sdcard: FAT16 subdirectory descent (2026-07-28)

Generalised the directory iterator to walk any directory, not just the
fixed root region. A subdirectory is stored exactly like a file — a
cluster chain of 32-byte entries — so FATNXT now runs in one of two
modes: root (the fixed ROOTLBA region) or subdir (follow the FAT chain
from a start cluster). New calls: FATDIR0 (root), FATCD R0=cluster
(descend; 0 = root), FATREW (rewind current). Descend from a listing by
FATCD'ing an entry's DECLUS when DEATTR has 0x10; ascend via the ".."
entry's cluster. Replaced the single DCACHE with DMODE/DSTART/DCLUS/
DLOADED state.

fattest gained a recursive tree walk (WALK): indented by depth, dirs
marked "/", sizes shown, "." and ".." skipped, saving/restoring the
global iterator state around each descent, with depth (6) and entry
(200) caps so a big tree can't run away. Verified on the card: it walked
the full macOS `.Spotlight-V100` tree several levels deep (STORE-V2 ->
AA1BA5~2 -> journal subdirs) and back, then dumped TEST.TXT. The
"rubbish" was just macOS's Spotlight index that the format left on the
card, traversed correctly.

## sdcard: read-only FAT16 (2026-07-28)

`sdcard/fat16.mac` — a read-only FAT16 layer on the raw sector driver.
FATMNT reads the MBR (partition-1 start LBA), reads the BPB there, and
computes the region geometry: fatStart = partStart + reserved;
rootStart = fatStart + nFATs*secPerFAT; rootDirSec = ceil(rootEnt*32 /
512); dataStart = rootStart + rootDirSec. FATNXT iterates the fixed
root-directory region (skips 0xE5 deleted, 0x0F long-name, 0x08 volume
label). FATOPN/FATRD open by 8.3 name and stream the file, following
the 16-bit FAT chain (entry N at FAT byte N*2; >=0xFFF8 = end). All
LBAs are 32-bit word pairs; cluster->LBA uses EIS MUL and the ADC/SBC
idioms. Root directory + 8.3 only; no subdirectory descent, no writes.

`fattest.mac` mounts, prints geometry, lists the root dir, and dumps
the first regular file. Hardware-verified on the 2 GB FAT16 card: the
computed geometry was exact (64 sec/cluster, 1 reserved, two 239-sector
FATs, 32-sector root dir), the listing showed the real entries
(SPOTLI~1/TMP dirs, TEST.TXT, README.MD), and a file read back byte-for-
byte.

Gotchas: m11asm has no `N.` decimal literal (use `^D`) — a bulk convert
then wrongly decimalised three offsets that were meant as OCTAL (dir
entry fields 0x1A/0x1C/0x1E = octal 32/34/36, not `^D32/34/36`) and the
>>9 shift count; caught by re-reading the constants before the run. And
a label collision: the test's dump-loop `DSEC` clashed with fat16's
dir-sector variable `DSEC` (renamed to DUMPS). Text files show a
staircase unless bare LF is expanded to CR+LF (Unix line endings) — the
dumper now does that; the file data itself was always correct.

## sdcard: raw microSD block driver (2026-07-28)

`sdcard/sd.mac` — SD/microSD over SPI on VIA port B (CS=PB3, SCK=PB4,
MOSI=PB5, MISO=PB6; own SPI mode-0 primitives, since the SD pin map
differs from spi.mac). The init ladder (CMD0 GO_IDLE, CMD8 SEND_IF_COND,
ACMD41 with HCS, CMD58 READ_OCR) plus single-block read/write
(CMD17/CMD24) of 512-byte sectors. Block-addressed SDHC/SDXC only; the
32-bit LBA is passed as an R0:R1 register pair and staged big-endian by
SDLBA. CRC is hardcoded only where it's checked (CMD0=0x95, CMD8=0x87);
after init SPI mode ignores it. `sdtest.mac` inits, prints the capacity
class, and hex-dumps sector 0.

Hardware-verified on an 8 GB card (Catalex-style breakout: AMS1117-3.3 +
SN74HC125 buffer, fed 5 V): init OK, SDHC block-addressed, and sector 0
read back as a byte-perfect MBR — partition entry at 0x1BE with type
0x06 (FAT16), start LBA 2048, ~1.86 GB, and 55 AA at 0x1FE, exactly the
2 GB FAT16 volume the card was formatted with. The write path is coded
but not yet exercised.

Two bugs found during bring-up, both classic bit-bang traps:
- SDCMD built the command byte with `BIS #100,R0` AFTER a priming
  SDIDLE — but SDIDLE returns its received byte in R0, so the command
  index was clobbered and every command went out corrupt. The tell was
  that a hand-coded CMD0 (which set R0 fresh) got a clean 0x01 idle
  reply while SDINI failed. Fix: stash the command byte before the
  prime. Lesson: a helper that returns a value in the register you're
  using to hold state will eat it.
- Several early arg-setup lines used `MOV #^D1AA,...` (not valid
  decimal) and word CLRs at odd addresses (`CLR CMDARG+1/+3`, which
  would trap). Replaced with the SDLBA register-pair path and byte ops.

sdtest keeps a raw-CMD0 PROBE that dumps the MISO reply before the
ladder, so a wiring/power fault is legible even when init can't start
(all FF = silent, all 00 = MISO stuck low, a bit-7-clear byte = the
card is answering). It is what pinpointed the R0-clobber in one run.

Next: exercise SDWR against a scratch sector outside the FAT volume
(e.g. LBA 100), then a read-only FAT16 layer starting at LBA 2048.

## net: W5500 — the PDP-11 answers ping; ENC28J60 convicted (2026-07-24)

Plot twist resolved by a second witness. A W5500 module went onto the
SAME five wires and dividers-less MISO as the ENC28J60 (PB3 CS, PB4
RSTn, PB5 MOSI, PB6 SCLK, PB7 MISO — VIA→chip lines through 3.3 V
dividers, W5500 is not 5 V tolerant) and read clean on the first try:
VER 000004, no rotate. The ROL1 gremlin is therefore NOT the wiring —
it is the ENC28J60 module itself (input stage or clone silicon counting
an extra edge). The scope experiment is now optional curiosity, not a
blocker; the ENC28J60 goes back in the drawer with its chapter below.

`w5500.mac` (frame = addr-hi, addr-lo, control, data over SPIXFR;
W5RD/W5WR + burst W5RDN/W5WRN, hardware reset) and `w5test.mac`
(ladder: VERSIONR — with a built-in 000010-means-rotated detector —
link wait on PHYCFGR, then MAC/IP/mask/gw config with readback verify)
ran the whole ladder first attempt:

	VER 000004 / LINK UP / IP SET - PING 10.1.0.199

and from the Mac: 4/4 replies, ~2 ms RTT, ARP shows 02:dc:11:0:1:99.
The silicon answers ARP and ICMP itself — zero protocol code on the
J-11. Config: 10.1.0.199/24 gw 10.1.0.1, spi.mac still in ~5 kHz
diagnostic slow mode (remove SPIDLY for speed; W5500 has no minimum).

Next rungs: UDP echo (socket 0, nc -u), then TCP LISTEN port 23 — a
telnet-able PDP-11 with the chip doing the TCP state machine.

2026-07-24 evening: `netcon.mac` + `netmon.mac` — the network console
and the monitor on top of it. netcon mirrors a TCP caller (port 23)
with the SLU: NCPUTC hits both, NCPOLC reads whichever has a byte,
output is line-buffered toward the socket, and the pump tends the
connection (accept, FIN, re-listen; SLU-only if no W5500). netmon is
an ODT-grammar monitor at 40000 (payloads keep 1000): NNNNNN/ examine,
value CR deposit, LF close-and-next, Rn//RS/ read the trap frame, G
launches at PRI 7 — and CATCH owns every vector, so a crashed payload
prints !PC and hands the prompt back with its registers laid out for
inspection. Verified over nc: deposit/verify, LF-walk, crash-examine-
patch-relaunch. Note netmon's 16-bit addressing: 173000/ there IS the
boot ROM window (I/O-page top-8KB relocation) — inverse of console ODT.

2026-07-25: netcon learned telnet. A no-port `telnet` invocation (unlike
`telnet host 23` - BSD telnet only auto-negotiates on the default port,
which is why the first test looked clean) opened with an option burst
whose OPTION bytes are small - they sailed through the naive >177
filter, one "?" per option. netcon now runs a real IAC state machine:
swallows verb+option triplets and SB..SE blocks, refuses every request
(DO->WONT, WILL->DONT), and - only once a caller reveals itself by
sending IAC - offers WILL SGA + WILL ECHO, flipping telnet into
character mode with remote echo: examine answers at the '/', no Enter
needed. nc never sends IAC, so raw sessions never see a protocol byte
(verified both ways over the wire).

Three live findings during bring-up, each worth remembering:
- A tight poll loop catches TCP transients (SYN_RECV mid-handshake);
  treating them as dead and reopening RSTs the caller. Only SOCK_CLOSED
  warrants a reopen. w5tcp never saw this - its 20 ms VQCSCN pass made
  transients invisible. Latency hid the bug; speed exposed it.
- J11Terminal's register auto-refresh types R0/..RS/ at anything that
  prompts "@" and goes idle - with netmon on the SLU it was a third
  participant silently wrecking open locations. netmon prompts ">" now;
  a software monitor must not impersonate microcode ODT to the tools.
- 000007 is not an illegal instruction on a DCJ-11 - it is MFPT. For a
  deterministic crash test, deposit TRAP (104400): !PC = site + 2.

Rung 5 same day: `w5tcp.mac` — TCP listener on port 23. The greeting
line reads the DS3231 over I2C at connect time ("DCJ-11 SBC READY -
HH:MM:SS", live: a reconnect two seconds later showed the clock two
seconds on) — port B carries I2C (PB0/1), SQW (PB2) and SPI (PB3-7)
at once, with I2CINI re-run before each RTC read because SPI's port
RMWs set the I2C ORB bits (the gotcha called out below, now load-
bearing). Echo loop with the byte count on the VQC10; FIN answered
with DISCON and the socket re-armed - serial reconnects work. Verified:
banner + 20/20 lines byte-correct, a 1500-byte burst (three 512-byte
laps) exact, reconnect clean. Four drivers, one VIA, no collisions.

Same day, rung 4 verified on hardware: `w5udp.mac` echoes UDP on port
7 with the packet count live on the VQC10 panel ("UDP nnnnn") — 50/50
packets byte-correct at ~40 ms RTT (latency = the VQCSCN scan pass per
poll, ~20 ms each: the display sets the pace), a 400-byte payload
byte-exact, 600-byte correctly dropped. Full-speed spi.mac (SPIDLY
removed) reconfirmed by w5test first. The reply aiming is free: the
chip's 8-byte RX header (peer IP, port) has exactly DIPR/DPORT's
layout, so one 6-byte burst write points the echo home.

## net: ENC28J60 Ethernet, SPI bring-up — the rotate mystery (2026-07-22, RESOLVED: module fault — see the W5500 chapter above)

The plan: bit-banged SPI on VIA port B (CS=PB3, RESET=PB4, MOSI=PB5,
SCK=PB6, MISO=PB7 — coexists with I2C on PB0/1 and SQW on PB2), an
ENC28J60 driver, then a from-scratch TCP/IP stack. Static 10.1.0.199/24,
gw 10.1.0.1, MAC 02:DC:11:00:01:99. First milestone: answer a ping.
Deliberately the hard road — a W5500 would do TCP in silicon; the point
is to own the stack ("have it in the software stack").

Built so far: `spi/spi.mac` (mode 0, MSB first, ~150 lines in the
i2c.mac mold), `net/enc.mac` (banked register access with cached bank
select, MAC/MII dummy-byte handling, PHY via MII, errata-aware init:
hardware reset instead of SRC, RX buffer at 0, ERXRDPT kept odd,
HDLDIS), `net/nettest.mac` (bring-up ladder: EREVID → PHY ID → link,
with an SPI loopback echo and, on failure, ESTAT dump + write/readback
diagnostics through ERDPTL).

What the hardware says (module: HR911105A-jack board, chip alive, link
LEDs up): every SPI READ comes back **rotated left by one bit** —
WR 125 RD 252, WR 63 RD 146, and the tell-tale WR 377 RD 377 (a plain
shift would give 376; the MSB wraps around to bit 0). ESTAT reads 002 =
ROL1(001 = CLKRDY): the chip was ready all along. Writes land correctly
(the readback correlation proves it); only the read path rotates.

Ruled out, with evidence:
- MISO level margin (3.3 V into 5 V VIA): chip-driven 1-bits read fine.
- Sampling phase: sample-during-high and sample-before-rise give
  IDENTICAL results (fix verified in RAM by fingerprint word — 3742/
  032737 — after a stale-tab detour, see below). So SO is stable across
  the clock phases; the misalignment is a whole clock, not a phase.
- Settle time: a ~5 kHz slow build (SPIDLY on every edge) changes
  nothing. NOTE the trap I fell into: this does NOT acquit signal
  integrity — each edge is still a full-speed 5 V CMOS transition, so
  edge-local ringing/crosstalk survives any slowdown.

Current best theory: ONE extra perceived rising edge per transaction,
byte-consistently placed — the signature of a crosstalk blip on SCK
fired by the CS falling edge (adjacent jumper wires), or ring-back on
the SCK edge itself. The wrap bit (last sample = b7 again) suggests the
chip repeats the data byte when clocked past 16, consistent with it
running one clock ahead of us.

NEXT, when the bench reopens (two experiments, in order):
1. Scope SCK at the module pin: trigger on CS falling (look for a blip
   on SCK), then on SCK rising (look for a double-crossing ring-back).
   Cure if seen: ~100 ohm series in SCK (and CS) at the VIA end, SCK
   twisted with its own ground return, wires separated/shortened.
2. The definitive logic-level test: a HAND-CLOCKED RCR-ESTAT transaction
   from ODT (DDRB=170, ORB deposits: 030 idle, 020 CS-low, per bit
   020/120/020 for 0 and 060/160/060 for 1, opcode 0,0,0,1,1,1,0,1;
   then 8x read-ORB-then-120/020, CS back to 030). Correct chip: bit 7
   of the reads = 0 seven times then 1 (ESTAT=001). Rotate at hand
   speed = the chip/protocol; correct at hand speed = electrical.

Workflow lesson (cost three test cycles): editing sources outside a
running J11Terminal is treacherous — open tabs win over disk at
assemble AND at upload (the popup sends tab text; even "Open .oct
File..." returns an already-open stale tab). Remedy used: stage builds
under a fresh filename (nettest2/3.oct) and verify a fingerprint word
in RAM via ODT before trusting a run. App-side fix worth doing: watch
for external file changes and offer reload.

Also latent, found by inspection while debugging: BIS/BIC on ORB are
read-modify-write — they read the PINS and write back the latch, so
SPI traffic silently sets the ORB bits of the idle-high I2C lines
(PB0/1). Harmless for SPI, but i2c.mac depends on ORB bits 0/1 staying
0 ("output means drive low") — the first I2C transaction after SPI use
would drive SDA/SCL HIGH instead of low. Fix before mixing the two on
one boot: re-BIC the I2C bits in I2CINI (already done there — I2CINI
clears them — so calling I2CINI after SPI use suffices; note it in the
app code that mixes them).

Status: nothing committed yet; spi/ + net/ exist as files only.

## eeboot: boot-from-EEPROM experiment, shelved (2026-07-16..17)

The goal: power the machine on and have it run a program with no PC
attached — a ~250-word loader in the Multi IO card's boot ROM window
(173000) reads an image from the DS3231 board's AT24C32 over I2C, copies
it to RAM, verifies, jumps. The vqc10 clock (1404 words) was to be the
first payload. The loader, burner (`eeburn`), image format and test
payload all work; the mission failed anyway, for reasons worth recording.

What was built: a two-stage loader (stage 0 relocates stage 1 to RAM with
per-word verified writes; stage 1 masks interrupts, owns every vector,
disables the MMU, double-checksums the payload — I2C stream and RAM, the
RAM sum three consecutive times — settles, jumps; any later trap re-enters
the loader, so crashes self-heal), `eeburn.mac` (interactive AT24C32
burner with verify), `romburn.mac` (paced in-circuit AT28C64 burner with
data polling), `hitest.mac` (minimal payload), `mkrom.py` (ROM images for
external programmers and window .oct files for in-circuit parts).

What the campaign found, layer by layer: a verified AT28C64 burn lost to
a power cycle (unprotected EEPROMs catch stray writes as the rails move;
SDP would prevent it but exists only on the B parts — on plain AT28C64
the unlock writes are real writes and ruined the re-burn). W27C512
replacements needed their floating A13/A15 tied. ODT's `G` starts code at
priority 0, and one spurious interrupt through cold-garbage vectors makes
a trap storm: SP marches through RAM leaving PS/PC frames everywhere, the
console sprays kilobytes of garbage, and the wreck halts at a bias-stable
PC (045417 became an old friend). An FM1608 FRAM fits the socket
perfectly and burns by plain upload — and was shredded by the first wild
program, because a boot ROM that writes at bus speed is erased at bus
speed. And the one that cost days: **console ODT examine/deposit use the
address exactly as typed — `173000/` is physical 00173000, i.e. RAM;
only `G` completes 16-bit addresses into the I/O page** — so several
"burns" and "verifications" of the ROM windows had been reading and
writing RAM at 62K. Read the manual first.

Underneath it all: sporadically corrupted full-speed bus operations —
occasional lost stores and lying reads, seen even in a bare serial upload
(one word of a 1404-word image arrived wrong) — whenever the boot ROM
window was in play. Diagnosis: the Multi IO card's boot ROM handling does
not reliably coexist with the W65C22S-paced bus; the DCJ-11 and RAM are
sound (the 16 MHz clock is a VIA concession — the CPU is good for 18).
Conclusion: on this card revision, the W65C22S (with the software-I2C
EEPROM behind it) and the boot EPROM cannot be used together. Shelved;
`eeburn` and the image format remain useful, and the loader is ready
should the ROM path ever become trustworthy.

Closing exhibit (`hellorom.mac`, a 34-word print-and-halt with no writes
to the window): uploaded to an FM1608 FRAM and disassembled back perfect,
it froze on G — and afterwards the ROM content had changed, scattered
words replaced by garbage, including the first fetch. FRAM reads are
destructive with an internal restore; the card's marginal ROM-select
timing interrupts restores at full fetch speed, so **executing from FRAM
on this card destroys the code being executed** (ODT-paced reads restore
fine, which is why every verify passed). One root cause, ranked by chip
sensitivity: EPROM immune to read and write disturb, EEPROM vulnerable to
write glitches (the original power-cycle loss), a 45 ns W27C512 fast
enough to answer decode ghosts, FRAM fatally read-fragile.

Final chapter (2026-07-18), with a standard SRAM (LH5268A) in the
sockets: `hellorom` runs perfectly — the window executes code fine — and
the full eeboot flow loads and verifies the whole clock over I2C from the
window-resident loader ("EEBOOT .....OK"). The payload then dies on its
FIRST VIA port A access: CATCH (taught to print the trapped PC) reports
004446 = mid `MOV #17, @#VIADRA` in VQCINI — a bus timeout. And the state
is a LATCH: once armed, ODT-paced VIA access still works, but full-speed
VIA access traps from any launch — `P`, even a plain `1000G` that had
always worked — and neither the software RESET instruction nor G's bus
init clears it; only a power cycle does. The loader's own I2C (port B,
via DDRB/ORB) ran flawlessly moments earlier, so the arming happens
somewhere between the boot flow and the first port A (DDRA) touch.
Separation in time is already maximal (stage 0 only copies and jumps;
everything else runs from RAM) — a latch cannot be architected around.

Context that matters for the sequel: this Multi IO is NOT stock — the
GAL timing equations were already modified, and the PCB carries three
added latched-address lines (LAI00-03). The next campaign starts there:
the boot ROM area and the GAL timing, equations in hand. The SRAM stays
in the sockets as the playground. Until then: shelved, mechanisms mapped,
loader ready, and the machine still tells the time via 1000G.

## VQC10 panel project (2026-07-15)

`vqc10/vqc10.mac` drives the "DisplayVQC10" panel (Konstantin Repnikov,
vk.com/retromodding) directly — two VQC10 4-digit 5x7 LED matrix modules
(WF Berlin) behind three chained 74HC595s. "Pure" = no ATmega controller;
the J-11 bit-bangs the chain on VIA port A (DATA=PA0, CLK=PA1, LATCH=PA2,
OFF=PA3 -> the 595s' /OE, which is pulled up so the panel is blank until
driven). API: VQCINI, VQCPUT/VQCSTR (glyphs transposed from the shared
column-major font into a row-major buffer), VQCSCN (one scan pass, call
continuously; ends dark so pausing is safe), VQCON/VQCOFF. `vqc10/clock.mac`
shows DS3231 time as HH:MM:SS on the 8 digits — same set-prompt/OSF/NZ-DST
behaviour as the ds3231 demos, ticked off the SQW edge, reading only 3 RTC
bytes per second (full block on hour change) to keep the between-frames
I2C pause invisible.

The shared 5x7 font moved out of max7219.mac into `max7219/font5x7.mac`
(both drivers .INCLUDE it); hello.oct proved byte-identical after the
refactor, so no re-test was needed.

Hardware bring-up found two real lessons, both now in the driver and its
README: the panel's row select is ACTIVE LOW (595 -> P-FET gate, so an
inverted row byte lights the whole panel with glyph columns smeared over
every row), and cp timing is strict — all 595 outputs move on one RCLK, so
the word that raises a cp must not change the data lines, or chip skew
races the module's latch and sprays ghost pixels from the neighbouring
digit (seen as stray pixels on digits 5/7 before the fix). VQCSCN therefore
costs two latch words per digit; the refresh (~60 Hz) was won back by
tightening VQSEND instead: port address and idle state held in registers
and the DATA bit set straight from the carry (ADC — DATA is PA0).
Datasheet assumptions verified: cp active-low latching on release,
C1 = leftmost digit, Z1 = top row. Hardware-tested: the clock runs.

Next: a second driver talking to the panel's own ATmega328 controller
board instead of driving the latches directly.

## AT24C32 EEPROM project (2026-07-12)

`at24c32/at24c32.mac` drives the AT24C32 (32 Kbit / 4 KB) I2C EEPROM on the
`i2c/` master — pure I2C, no VIA. API: `EEPING`, `EEWRB`/`EEWR` (byte / block
write), `EERDB`/`EERD` (byte / block read). 12-bit address sent as two bytes;
writes go byte-by-byte, each a ~5 ms cycle ended by ACK polling (simple and
page-safe; page writes are a future optimisation); reads are one sequential
transfer. The chip is the same standalone or on a ZS-042 DS3231 module — only
`EEADDR` differs (A0–A2 → 0x50..0x57; 0x57 on ZS-042). `at24c32/demo.mac` writes
a string to address 0, reads it back, prints it, and verifies (PASS/FAIL).
`at24c32/readonly.mac` reads address 0 only (no writing) — run it after a
power-cycle to prove the EEPROM kept what demo.mac wrote. Closes #1.

## DS3231 RTC project (2026-07-12)

`ds3231/ds3231.mac` drives the DS3231 I2C real-time clock on top of the
`i2c/` master — register blocks are read/written through the I2C layer, and the
VIA is touched directly only to read the SQW pin (PB2, a DS3231 output). API:
`RTCINI` (SQW = 1 Hz, oscillator on, flags cleared), `RTCSET`/`RTCGET` (7-byte
BCD time), `RTCA1` (Alarm 1), `RTCAF`/`RTCACL` (alarm flags), `RTCSQ` (SQW
level). The DS3231 address is fixed at 0x68; A0–A2 on ZS-042 modules belong to
the AT24C32 EEPROM, not the clock.

Two demos share the driver. `ds3231/demo.mac` is the plain console clock —
reads the RTC and prints `20YY-MM-DD HH:MM:SS NZxT` in place once a second.
`ds3231/clock.mac` is the graphical version: a big centre `HH:MM:SS` in 5x5
block digits (VT cursor addressing, so it needs the general Terminal, not the
ODT console) with a small date/zone line and `*ALARM*` flashing at :10 — the
base to grow alerts and timers on. Both prompt to set the time (declining reads
the running clock, unless OSF reports it lost power, where it insists on a set),
keep the RTC on NZST and convert to NZ local time (+1 h in NZDT, last Sun Sep ..
first Sun Apr, weekday by Sakamoto, date rolls at midnight), and tick off the
1 Hz SQW falling edge on PB2 (A1F polled over I2C, so tick and alarm coexist).

## MMU project (2026-07-11)

`mmu/mmu.mac` brings up the J-11 on-chip memory management to reach RAM above
the 16-bit 64 KB limit. `MMUON` installs an identity map (page 7 → 22-bit I/O
page) and turns on 22-bit relocation so running code is unaffected; `WINDOW`
re-points page 6 (virtual 140000) at any physical block, giving a sliding 8 KB
view of the 512 kW (1 MB, 128 banks) physical space. `mmu/demo.mac` writes a
distinct signature into four high banks (8, 32, 64, 96) and reads them back
through the window, printing PASS/FAIL on the console — a mismatch would mean
the high addresses aliased instead of being real distinct RAM.

Gotcha found and documented: MACRO-11 (and m11asm) evaluate expressions left to
right with no operator precedence, so `KIPAR0 + WINPAG*2` computed
`(KIPAR0 + WINPAG)*2`. Written as `WINPAG*2 + KIPAR0` instead.

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
