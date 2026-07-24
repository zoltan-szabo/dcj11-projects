# net-discovery — the Ethernet bring-up campaign (complete, archived)

The discovery phase of putting the DCJ-11 on the network, 2026-07-22..25.
Every rung was climbed here; continued development lives in `../netmon`.
This directory stays as the record — the war stories are in ../HISTORY.md.

What happened, in order:

1. **ENC28J60 first** (`enc.mac`, `nettest.mac`) — full register-level
   driver, shelved: the module rotates every SPI read left by one bit
   (377→377 wrap; wiring later exonerated by the W5500 reading clean on
   the same pins). Kept as the evidence and the diagnostic ladder.
2. **W5500** (`w5500.mac`, `w5test.mac`) — VERSIONR, link, IP config:
   the machine answers ping as 10.1.0.199/24 (MAC 02:DC:11:00:01:99),
   ARP/ICMP in silicon, 4/4 replies at ~2 ms.
3. **UDP echo** (`w5udp.mac`) — port 7, packet counter on the VQC10
   panel, 50/50 byte-correct; latency set by the panel scan.
4. **TCP listener** (`w5tcp.mac`) — port 23, greeting carries live
   DS3231 time over I2C, echo + byte count, FIN handled, re-listens.
5. **netcon + netmon** (`netcon.mac`, `netmon.mac`) — the TCP/SLU
   mirrored console and the ODT-style monitor on top: examine/deposit,
   trap CATCH with register frame, G; telnet IAC negotiation with
   character mode. Copied into `../netmon` as the living project.

## Wiring (Multi IO card, VIA port B → W5500 module)

| VIA | Module | Note |
|-----|--------|------|
| PB3 | SCS    | active low |
| PB4 | RSTn   | active low, hard reset |
| PB5 | MOSI   | |
| PB6 | SCLK   | |
| PB7 | MISO   | 3.3 V out, reads fine into the 5 V VIA |

W5500 is NOT 5 V tolerant: the four VIA→module lines go through
dividers. PB0/1 (I2C), PB2 (SQW) untouched — RTC and network share
port B; the VQC10 panel lives on port A. `../spi/spi.mac` is the
shared bit-banged SPI master.
