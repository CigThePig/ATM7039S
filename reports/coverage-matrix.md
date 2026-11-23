# Research coverage

`S` = inspected software declaration; `R` = related-chip source candidate; `M` = manufacturer claim; `?` = insufficient evidence. **No row has target hardware validation.** A named block is not a documented peripheral. Counts below refer to artifacts, not chip completeness.

| Subsystem | Identified | Address range | IRQs | Offsets | Meanings / fields | Implementation inspected | Main gap |
|---|---|---|---|---|---|---|---|
| CPU | S/M | SCU/GIC R/S | S | ARM standard leads | Partial software startup | Vendor SMP | MIDR/topology/final masks |
| Cache / MMU | S | PL310 S | S | Related/standard | Capacity/coherency ? | Memory/SMP source | Exact cache geometry/attributes |
| RAM / DDR | M/S | Physical usable layout ? | ? | UPCTL/PUB R | ? | AFI + reservation paths | Pre-Linux training and handoff |
| Boot ROM / SRAM | ? / R labels | ? | ? | ? | ? | No ROM image | Reset/media rules/internal memory |
| CMU / reset | R | R; auxiliary S | N/A | R + upstream match | S500 definitions | Mainline CMU | Target rates/fields/gates |
| IRQ / SIRQ | S | S | S | Standard/R | Binding-level | GIC + tree | Wake/routing confirmation |
| DMA | S/R | S | S | R | Partial upstream | Mainline | Descriptor/request/coherency proof |
| GPIO/pinmux | S/R | S partial | S | R | Related code | Tables sampled | Target mux/pads/package |
| UART | S/R | S | S | R + upstream | S500 masks | Mainline | Physical exposure/clock |
| I2C | S/R | S | S | R + upstream | Partial | Mainline | Target transactions/PMIC |
| SPI | S/R | S | S | R | Partial | Vendor/U-Boot leads | No upstream driver found |
| SD/MMC | S/R | S | S | R + upstream | S500 masks | Mainline/U-Boot | Slots, DMA, timing |
| USB | S/R | Conflicting S/R | S | R | Incomplete | Wrapper leads | PHY/role/VBUS/layout |
| Display / DE | S/R | S | LCD S | R | Partial vendor leads | Vendor files | Scanout/panel/format/KMS |
| GPU | M/S/R | S | S | R/DDK | Commands ? | Kernel/glue/config | ABI/userspace/revision |
| Audio | S | S / I2C | Partial | R | Routing ? | DT + source leads | Codec/PCM/DMA/rates |
| Video / ISP | M/S/R | S | S | R | ? | Driver discovery | Commands/microcode/ABI |
| PMIC / battery | S | I2C address S | S parent chain | Not recovered here | Board settings S | DT children | Exact chip/rail/charge behavior |
| Timer / watchdog | R/S | Mismatched S | S | R | Partial upstream | Source compared | Timer/watchdog split |
| Thermal / DVFS | S/R | R/S | ? | R | Safe transitions ? | Discovery only | Silicon limits/sensors |
| Security / OTP | Source leads | ? | ? | Candidate chip-ID only | ? | Not reconstructed | ROM security/fuses/TRNG/crypto scope |

## Measured work products

The canonical map contains **51 DT resource tuples and 72 related-header base groups**, with **1,760 explicit register symbols**. The 123 total records are not 123 distinct peripherals: several are sub-blocks, auxiliary or overlapping resources. The complete inspected header yields 1,841 resolvable constants; not every constant becomes a register.

There are 35 claim records, nine contradiction records, two statically analyzed public binary components, and a 26-pair numeric resource comparison with mainline S500. These counts describe the research database, not how much of the physical chip has been reverse engineered.

## Adequacy for developers

The foundation is adequate for finding source-observed resource addresses, locating candidate register offsets and existing drivers, tracing dependencies, and repeating the extraction. It is not yet adequate for a safe full driver rewrite, DDR initialization, PMIC programming or full mainline bring-up without further evidence. No subsystem is claimed to have a complete ATM7039S programmer's reference.
