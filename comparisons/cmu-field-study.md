# Selected S500 clock/reset field comparison

Evidence: CLK-004, CLK-005; [machine-readable fields](cmu-fields.json). Manual: mirrored Actions-branded S500 v1.4, hash in source catalogue. Linux: pinned v6.12. ATM7039S behavior remains unverified.

| Function | Register offset | Bit | Manual printed page | Linux line | Comparison |
|---|---:|---:|---:|---:|---|
| GPIO gate | `0xa0` | 18 | 75 | 187 | Position agrees |
| UART0 gate | `0xa4` | 6 | 76 | 333 | Position agrees |
| UART1 gate | `0xa4` | 7 | 76 | 339 | Position agrees |
| UART2 gate | `0xa4` | 8 | 76 | 345 | Position agrees |
| UART6 gate | `0xa4` | 18 | 76 | 369 | Position agrees |
| GPIO reset | `0xa8` | 15 | 77 | 547 | Position agrees |
| UART0 reset | `0xac` | 5 | 77 | 561 | Position agrees |
| UART1 reset | `0xac` | 6 | 77 | 562 | Position agrees |
| UART2 reset | `0xac` | 7 | 77 | 563 | Position agrees |
| UART6 reset | `0xac` | 4 | 77 | 560 | Position agrees |

The manual's reset description specifies writing zero to reset a block; its reviewed fields have reset value one. Gate reset values differ (GPIO one, reviewed UART gates zero). These values are stored as **related-chip** metadata, never as target register reset values or a hardware-safe programming sequence. The ATM7039-labelled header supplies matching offsets, not these field semantics. Upstream and vendor material may share manufacturer ancestry.

## Discrepancies retained

The manual describes UART0DIV as bits 8:0, including non-linear encoding 312. Linux configures an eight-bit generic divider with no custom table. This is C-UART-DIV, not a corrected target register specification.

Manual tables also mark some positions reserved that upstream names, such as DEVRST1 bit 14 versus `RESET_USB3`. The manual may be incomplete, revision-specific or incorrect; upstream can also be incomplete. Neither source wins solely through apparent authority. No additional bitfield was promoted from these disagreements.

For UART operation the candidate dependency model is APB access plus selected UART source/divider, gate, reset and pinmux. Physical polarity, clock rate and safe sequencing on ATM7039S require additional evidence. This study supplies lookup fields for comparison, not a driver-ready clock tree.
