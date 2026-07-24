# net — Ethernet for the DCJ-11

Bit-banged SPI on the VIA + a WIZnet W5500 (TCP/IP in silicon). The
machine answers ping as 10.1.0.199/24 (gw 10.1.0.1, MAC
02:DC:11:00:01:99) — verified 2026-07-24, 4/4 replies at ~2 ms.

**Status: ping works (w5test.mac, rungs 1-3). Next: UDP echo, then a
TCP listener on port 23 — a telnet-able PDP-11.** The original
ENC28J60 attempt is on hold: that module rotates every SPI read left
by one bit on wiring the W5500 reads cleanly — full war story in
../HISTORY.md.

## Wiring (Multi IO card, VIA port B)

| VIA | Module | Note |
|-----|--------|------|
| PB3 | CS     | active low |
| PB4 | RESET  | active low; driver hard-resets instead of SRC (errata) |
| PB5 | SI (MOSI) | |
| PB6 | SCK    | suspect line — see HISTORY |
| PB7 | SO (MISO) | 3.3 V into 5 V VIA: reads fine on this board |

PB0/PB1 (I2C) and PB2 (SQW) are untouched; clock and network can share
the port. WOL and INT on the module stay unconnected (everything is
polled). Module powering: mind that many of these boards are 3.3 V-only
(no regulator).

## Files

- `../spi/spi.mac` — SPI mode 0 master, MSB first: SPIINI / SPICSL/H /
  SPIRSL/H / SPIXFR (R0 in/out). Currently carries diagnostic SPIDLY
  settle delays (~5 kHz); remove for full speed once the rotate is fixed.
- `enc.mac` — register-level ENC28J60 driver: banked access (cached),
  MAC/MII dummy-byte reads, PHY via MII, errata-aware ENCINI (RX buffer
  at 0, ERXRDPT odd, HDLDIS, half duplex), MAC address in ENCMAC.
- `nettest.mac` — bring-up ladder: SPI echo, EREVID, PHY ID (expect
  000203), link wait; on failure: ESTAT dump + write/readback probes.
- `nettest.prj` — J11Terminal project (origin 1000).

## Milestones

1. EREVID readable ← **here** (blocked by the rotate)
2. PHY ID / link up (link LEDs already work — chip and cable are fine)
3. Raw frame TX (watch in Wireshark)
4. RX + hex dump
5. ARP reply
6. ICMP echo — `ping 10.1.0.199` answers
7. UDP, then minimal TCP
