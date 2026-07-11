# Software I2C master

Bit-banged two-wire I2C master for the DCJ-11, on the Multi IO card's VIA
port B. Open-drain is done correctly: a line is released high by making the
pin an input (the bus pull-up pulls it up) and driven low by making it an
output whose data bit is held at 0. Only PB0/PB1 are touched.

## Wiring

| Bus | VIA (port B) |
|---|---|
| SDA | PB0 |
| SCL | PB1 |

The bus needs pull-ups to Vcc (most breakout modules include them).

## API

| Routine | Arguments |
|---|---|
| `I2CINI` | release the bus (idle high); call once |
| `I2CSTA` | send a START |
| `I2CSTO` | send a STOP |
| `I2CWR` | R0 = byte; returns R0 = 0 if ACKed, 1 if not |
| `I2CRD` | R1 = 0 ACK / non-zero NACK; returns byte in R0 |
| `I2CPING` | R0 = 7-bit address; returns R0 = 0 if a device answers |

`I2CWR`/`I2CRD` preserve R2/R3; all routines preserve R4/R5. Bus speed is
well within standard mode (a fixed inter-edge delay, no clock stretching).

Include it before any device driver that uses it.
