# netmon — the network monitor for the DCJ-11

The living continuation of the `../net-discovery` campaign: an
ODT-style monitor served over a TCP/SLU mirrored console. Connect with
`telnet 10.1.0.199` (character mode, remote echo — negotiated) or
`nc 10.1.0.199 23` (raw line mode); the physical console shares the
same session.

- `netmon.mac` — the monitor (origin 40000, payloads keep 1000):
  `NNNNNN/` examine, value+CR deposit, LF close-and-next, `Rn/`/`RS/`
  read the trap frame, `G` launch at PRI 7. CATCH owns every vector:
  a crashed payload prints !PC and returns the prompt with its
  registers laid out. Prompt is `>` (deliberately not `@` — see
  HISTORY: J11Terminal's register auto-refresh types at ODT prompts).
- `netcon.mac` — the console layer: NCPUTC/NCPOLC/NCFLSH, output to
  SLU + line-buffered socket, input from either, self-tending
  connection (accept, FIN, re-listen), telnet IAC state machine with
  a character-mode offer to callers that speak telnet. Network
  identity (MAC/IP/mask/gw) lives here.
- `w5500.mac` — W5500 register access over `../spi/spi.mac`.

Addressing is 16-bit software addressing: `173000/` here reads the
boot ROM window (physical 17773000) — the top-8KB I/O-page relocation,
the inverse of console ODT's treatment of the same digits.

Notes: 000007 is MFPT on the J-11, not an illegal instruction — for a
deterministic crash test deposit TRAP (104400). A payload HALT still
drops to microcode ODT on the physical console.
