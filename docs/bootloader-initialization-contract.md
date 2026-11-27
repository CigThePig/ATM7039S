# ATM7039S independent bootloader initialization contract

This specification covers the original Anbernic RG35XX and five hash-pinned firmware images. It describes the stock initialization sequence, the state its consumers use, and the prerequisites for independently authored stages. The [machine-readable contract](../evidence/firmware/bootloader-initialization-contract.json) contains stable operation, register, dependency, and uncertainty identifiers. The [operation reference](bootloader-operation-reference.md) and [ordered trace](../evidence/firmware/boot-initialization-trace.json) give instruction locations, widths, values, model rules, and stage boundaries.

## 1. Scope and evidence

The source research baseline is verified PR #9 head `c525a28bd4fb1b758e5a784075e3c6a0a91d9edc`. Its tree matches the initial local research checkout byte for byte. The common bootloader instruction region is identified by SHA-256 `6b17b88c92e4d9f90f3f123e4a340b692d001bada4f78f24889481b73adf6ea9`. Whole-image hashes, config values, and downstream component hashes are in the structured contract and the [acquisition manifest](../evidence/firmware/acquisitions.json).

| Evidence | Establishes | Limit |
|---|---|---|
| Physical observation | OBS-001 ties one running Koriki boot to the SD2 controller, kernel memory map, initrd range, command line, and CPU exports | ROM state, live AFI, early serial, rails, DRAM device geometry and timing remain unmeasured |
| Executed firmware and synthetic responses | Instruction behavior, read requests, stores, ordering, branches, and effects under named rules | The model supplies initial CPU state and peripheral, memory decoder, and status responses |
| Verified static instructions | Untaken alternatives, call conventions, masks, and computed values in pinned executable regions | Conditional paths and physical effects need their own evidence |
| Pinned source and related-SoC layouts | Candidate register names, layouts, and software conventions | Similar offsets leave the target revision and electrical semantics open |
| Independent software model | Arithmetic and software decisions across stated input ranges | Shared synthetic hardware rules bound the comparison |
| Hypothesis and unknown | Candidate explanation or missing prerequisite | No physical guarantee assigned |

Implementation classifications are independent of evidence confidence. A demonstrated consumer requirement applies only when keeping that interface. Conservative ordering preserves the stock sequence pending evidence about hardware necessity. A candidate for replacement or omission still needs an explicit entry/exit contract and validation. [Physical observation](../evidence/observations/OBS-001.json) · [Unified study](../reports/unified-boot-chain-reconstruction.md)

## 2. Execution boundaries and Boot ROM contract

| Item | Established firmware behavior | Supplied or unresolved state |
|---|---|---|
| Initial execution | Block 0 is A32 and linked for SRAM at `0xb4060000`. The loader image places the initial sector at LBA `0x1001` | Model installs the 512-byte sector and starts at its first word. Physical PC, search order, acceptance checks and initial contents are open |
| Mode and stack | The SD block-0 branch reaches the ROM interface before assigning a stack. The early loader pushes a frame using the inherited SP. They leave CPSR and pre-DRAM CP15 state inherited | Emulator supplies `SP=0xb409f000`, `CPSR=0x1d3` (A32 SVC, A/I/F masks) and Unicorn CP15 defaults. Physical privilege, SP, vectors, exception masks, MMU, I-cache and D-cache are unknown |
| Selection | Block 0 samples `0xb01600a0` at `0xb4060004`. Bit 7 wins and stores code 2. Bit 4 next stores code 0. Code is at `0xb4064c00`, getter `0xb40664f0` | The two fixture gate words are `0x80` and `0x10`. C-DEVCLK's SD2 interpretation is inferred from the observed boot. Hardware reset and ROM gate state per medium are unknown |
| ROM handoff to main | A call to `0xb4060400` supplies `r9=4`, `r0=0x102b` LBA, `r1=80` sectors, and `r2=0xb4065400`. Firmware enters that address on the successful path | The shim copies bytes from the verified image and returns success. A synthetic error reaches idle at `0xb4060120`. Physical return codes, clobbers, retries, timeouts and error behavior remain open |
| Other ROM paths | With both gate bits clear, the tested word at `0xb4060408` distinguishes codes 4 and 5. Historical static evidence shows other service users and a code-5 reader at `0xb40612b0` | The SD contract does not generalize their selectors, service bytes, or alternate-media loading |
| ROM code ownership | Calls target `0xb4060400..` inside an on-disk zero-filled interval | ROM population is an inference. ROM contents and callable extents remain unavailable |

The selected first stage needs verified load bounds, executable memory and a compatible initial instruction state before it can establish its own aligned SRAM stack, writable data, and exception policy. Initial privilege must allow any eventual CPSR and CP15 changes. If a ROM service is retained, define register preservation, allowed destinations and exact transfer semantics before reusing its workspace or changing the inherited CPU state. Otherwise the independently selected transport still needs an established medium and clock/pad state. [Block-0 dispatch](../reports/stock-boot-chain-reconstruction.md#4-earliest-stages-boot-012-boot-019) · [C-DEVCLK and C-PREDRAM-PATH](../evidence/contradictions.json)

## 3. SRAM layout, ownership and lifetime

Ranges use a half-open end. The emulator maps `[0xb4060000, 0xb40a0000)`. Only specific firmware accesses and loaded spans below establish use. SRAM physical extent, mirrored addresses, reserved ROM work areas and usable alignment remain open.

| Range or anchor | Stock owner and evidence | Lifetime and constraints |
|---|---|---|
| `[0xb4060000,0xb4060200)` | Initial 512-byte block 0; first instructions and literals | Executed from entry. app.bin uses word `0xb4060018` to save the U-Boot target. ADFU copy targets this region |
| `[0xb4060200,0xb4060400)` | Additional disk block in historical loader layout; colocated with runtime AFI | Its presence in the ROM's entry SRAM is unknown. The integrated model installs only the first sector |
| `[0xb4060300,0xb4060310)` | AFI producer and U-Boot getters | Preserve 16 raw bytes until the last compatible consumer. ADFU overwrites the interval if the physical copy succeeds |
| `[0xb4060400,0xb4061e00)` | On-disk hole including ROM service entry, alternate-path reader workspace | Reserve while using ROM and never infer availability from disk zeroes. `0xb4060408` is read in the alternate dispatch |
| `[0xb4062400,0xb4063400)` | 4 KiB INI loaded by main from LBA `0x1013` | Contains primary, selector, secondary and SFVD at `0xb4062800`. Live across DRAM dispatch and app.bin. Recovery overlaps through `0xb4062e00` |
| `[0xb4063400,0xb4064c00)` | Remainder of 20-sector alternate write-back source. Contains disk code fragment and opaque bytes | Main's normal SD INI load covers only the first eight sectors. Treat remaining contents and provenance as unresolved for any persistence path |
| `[0xb4064c00,0xb4064c04)` | Boot-code word | Produced by block 0. Read by main, boot-code getter, recovery policy and AFI logic |
| `[0xb4064c60,0xb4064c78)` | Stock pointer table | Published before record dispatch. Preserve if retaining an app or service that consumes it |
| `[0xb4065400,0xb406f400)` | 80 sectors installed by the verified block-0 call | Includes early loader instructions, literal pools, UART/PMIC tables and I2C cache near `0xb406ba10`. The broader disk code region through `0xb4093c00` is a provenance span |
| `[0xb4070800,0xb407087c)` | Main clears this globals region; working records at `0xb4070820` and `0xb407084c` | UART index/pad/baud at `0xb407082c/30/34`. PMIC settings at `0xb4070858`, alarm/flag/vector at `0xb4070870/74/78`. Resume and app paths depend on selected contents |
| `0xb4070800` | SP assigned at the recorded ROM re-entry exit | Down-growing recovery stack and abandoned main globals represent a distinct lifetime. Recovery stack depth is unknown |
| `0xb409f000` | Emulated initial SP | The pre-DRAM trace sampled 136 bytes of stack use. Physical extent, alternate path depth, and exception stacks are open |
| `0xffff0000` and `0xffff5200` | Recovery VBAR and expected ROM copy source respectively | The copy runs through a shim. Memory aliasing and actual exceptions remain unresolved |

An independent placement needs space for code/literals, writable data, call and exception frames, service scratch, and any compatible AFI or INI bytes still read later. Validate non-overlap against measured or documented ownership, including stack growth, sector-rounded destinations and the recovery overwrite. A complete physical map could allow reclamation after the last consumer. [Pre-DRAM map](predram-initialization.md#execution-environment) · [ROM re-entry](../reports/adfu-loopback-reconstruction.md)

## 4. SRAM initialization, clocks and timer

The stock sequence clears globals, loads and decodes the INI, sets up timer and UART, logs the config and checks version `1.1`, sets board mux, identifies and configures the PMIC, then makes recovery and resume decisions. The primary record, secondary record, and board configuration originate in the INI. A loader with a different configuration format can preserve their roles while removing vendor print fields, including the misleading `bootdev= 0x22` line shared by both SD paths.

| Segment | Instruction-backed contract | Qualification |
|---|---|---|
| Oscillator | Timer and UART arithmetic use 24 MHz; DDR PLL arithmetic uses a 12 MHz multiplier basis | Requested and calculated quantities are firmware values. Kernel-reported clocks describe later software state. OBS-001 exports a later CPU scaling value of 1008000 kHz. The physical oscillator, rates and lock times were not measured |
| Timer gate and words | Set `0xb01600a4[27]`. At `0xb0168008 + 12n` (n=0), startup writes zero to control, count (+8) and +4 twice, then sets control to 4 | Clock and reset prerequisites are conditional on inherited state. The +4 semantics remain open |
| Delays | `0xb40693f8` waits for signed `count - (start + 24*us) >= 0` in 32-bit arithmetic. `0xb4069434` scales ms by 1000 | Wrap handling is valid for intervals shorter than half the counter range. A stopped counter never ends the wait. Early replay advances 2400 ticks/read and DRAM delay calls use a stub |
| DDR gate/reset order | Starting per attempt at `0xb406800c`, clear DDRPLL bit 8, clear gate0 mask `0xa`, clear then set reset0 mask `0x5`, write the DDRPLL word, then set gate0 mask `0xa` | Keep RMW-preserved bits. Names of individual domains are from related sources. Physical clock settling, lock behavior and reset values remain open |
| After DRAM | Main at `0xb4065440` sets SCTLR.I and runs clock setup. The reference stream writes `0xb016001c=0x1c710000`, `0xb0160038=0x2e004`, `0xb0160000=0x332` and `0xb0160058=0xc` among other writes and RMWs | The older dossier includes static neighboring paths. Use live order for the selected SD scenario. A vendor interpretation of the 0x332 multiplier yields 600 MHz, while the status and physical rate remain open |

Treat delays as requests and bounded-loop counts as iteration budgets. DRAM's `F=12*floor(requested_MHz/12)` yields 468 MHz from both shipped records. The PLL word `(F/12) | 0x300` is `0x327`; the related vendor tree identifies bit 8 as enable. Bit 9 and the actual physical relation between DDR PLL, bus, and memory clocks remain qualification items. `C-DEVCLK` retains its SD2 inference and historical SD0 naming conflict. [Clock evidence](clock-notes.md) · [Timing and writes](../reports/ddr-timing-reconstruction.md)

## 5. UART and diagnostics

INI bytes +0x0e/+0x0f and the little-endian word at +0x10 select index 3, pad 0, and requested 115200 baud. The matching table entry resides in the 24-entry table at `0xb406b520`. Control is at `0xb0126000`, TX at +8, status at +0xc. The gate RMW sets bit 19 of `0xb01600a4`; reset bit 15 of `0xb01600ac` is cleared, held for a requested 1 µs, and set. Firmware writes control `0x8003` and divider 25 to `0xb01600b0`. Integer division gives `floor(24000000/(8*115200)) - 1`; at 24 MHz the calculated line rate is about 115385 baud. The controller transmit helper waits for bit 6 clear, writes TX, then waits for bit 10 set. Both polls are unbounded. FIFO capacity and physical timing remain open.

This table entry carries zero mux writes. Controller configuration, routing to an external signal, and `ttyS3` via the OS and DT are separate requirements. For an independent loader, progress reporting should distinguish entry, config validation, PMIC decision, DRAM status and retry, size, diagnostic result, and attempted handoff. It can use a bounded interface and preserve failure state if the console is unavailable. UART initialization preceding DRAM supports stock diagnostics and does not establish a physical DRAM prerequisite. [UART evidence and routing](serial-console.md)

## 6. PMIC and board configuration

The modeled type-2 PMIC is on I2C1 (`0xb0174000`) at 7-bit slave `0x65`. Register index is 8 bits and data is two bytes big-endian. The board DT describes an ATC2603C-related node at this address. That identifies the software expectation. At the pinned Linux revision, the ATC2603C header labels 0x11 and 0x14 as DC1_CTL0 and DC2_CTL0. It names 0x39 CHARGER_CTL0, 0x29 SWITCH_CTL and 0x35 UV_STATUS. The stock recovery interpretation of bit 1 at 0x35 is an executed software decision. Its electrical meaning on this board remains open. The header labels 0xff SADDR and 0x32 OC_INT_EN, so the observed comparisons are firmware probe checks rather than a documented dedicated part ID. The Linux regulator descriptors give a candidate field layout for DCDC1/2 (selector bits 11:7 and 12:8). Board rail mapping, physical part revision and the unqualified auxiliary control words still need evidence. [Pinned ATC2603C register header](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/include/linux/mfd/atc260x/atc2603c.h) · [Pinned regulator driver](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/drivers/regulator/atc260x-regulator.c)

Clock-out selection at `0xb4069710` clears `0xb01b004c[30]`, checks `0xb0160084[0]` and requests 300 µs when enabling it, sets `0xb01b0084[31:30]=2`, and writes `0xb01600d0=0x8000002d`, `0xb01b0090=0x10`, `0xb01b0094=0x20000000`. Bus setup clears mux bits under `0x50000` at `0xb01b004c`, gates bit 15 in `0xb01600a4`, sets `0x600` at `0xb01b0068`, and writes divider `0x10` at `0xb0174004`. Stock I2C helpers poll FIFO/transaction status using the timer with a per-transfer bound of approximately 501 ms. The integrated case executes setup and probe instructions, with selected read/write transactions intercepted at `0xb406ac10/ac60`. Probe status is modeled ready. The fallback after reg 0xff mismatch includes alternate clock-out selection and a GPIO 90 pulse. The reference did not take it.

| PMIC reg | Access and stock type-2 value or meaning | Original caller site where established |
|---|---|---|
| `ff`, `32` | Read `0x00ca` and `0x1bc0`; mismatch checks and probe after clock/bus setup | `pmu_detect` `0xb4069890` and initialization check |
| `dc` | Version read; modeled value 1, version 0 hits an unsupported loop | `0xb4069e8c`, `0xb406a130` |
| `51` | RMW set `0x0800` | `0xb4069eac` |
| `39` | RMW retain `0x7fff` | `0xb4069ec4` |
| `11`, `12` | Write `0xe84f` then read back 0x11; write `0x68cc` | `0xb4069ed0`, `0xb4069ed8`, `0xb4069ef8` |
| `14`, `62` | Read 0x14, then write `0x80ca \| (adj << 8)` with INI value 3 mapping to 9 (`0x89ca`); separately read 0x62 | `0xb4069f00`, `0xb4069f44`, `0xb4069f4c` |
| `15`, `16` | Write `0xe8ce` and `0x334b` | `0xb4069f60`, `0xb4069f6c` |
| `29` | RMW retain `0x7fc5` | `0xb4069f88` |
| `03`, `01` | 0x03 bit 4 and 0x14 bit 15 inform S2/resume; 0x01 wake test is `(word & 0xf100)==0x100` | `0xb4069fa8`, resume path through `0xb406a08c` |
| `08`, `5d` | Read retained vector as `reg8 \| (reg5d << 16)`. Reg 0x5d bit 14 is handled by alarm policy | Vector store `0xb406a044` |
| `00` | Cold status RMW `(read & 0x1f) \| 0xe0c0` | `0xb406a128` |
| `35` | Read status first in recovery decision; if bit 1 set write back `word & ~3` | Read call `0xb4069268`; write and branch in `adfu_check` |
| `53..55` | RTC alarm updates on selected resume paths | `0xb4066eac` and alarm dispatcher |

The sites above describe original caller coordinates for the analyzed type-2 path. The integrated timeline uses the lower-level I2C boundary and models values and failures. Keep the regulator writes ordered for stock fidelity. A future implementation needs exact electrical semantics, supported PMIC variants and settling prerequisites before treating them as a physical initialization contract. No voltage is derived from the opaque words. [Power evidence](predram-initialization.md#pmic-pmic-002) · [Resume state](../reports/dram-complete-reconstruction.md#32-who-sets-the-resume-state)

| Board dependency | Reference setting and evidence | Portability |
|---|---|---|
| Pin mux | INI board index 1, `0xb406a608` RMW `(MFP_CTL2 & ~0xe39e0) \| 0x619c0` | Vendor pad values map D0/D2/D3/CMD/CLK to a JTAG-named state; D1 inherits earlier state. Later MMC sees the resulting word |
| GPIO/pulls/drive | Loopback temporarily changes direction and leaves selected data and pull state. I2C RMW sets pull bits. Additional clock-out pad words and the common memory margin RMW are observed | Retain uncertainty about output latch versus pad readback, mux priority, actual pulls and pad electrical drive |
| Card slots | OBS-001 identifies TF1's running SD card on SD2. Software ties TF2 to SD0 | TF2 wiring and direct physical pad assignment remain inferred |
| Variant strap | Later U-Boot from 230309 samples GPIOC6. Its modeled high path yields `allenS500=1` consistent with OBS-001 | Independent input from early GPIOC10. The observed bootargs do not directly sample the strap |
| DRAM and PMIC | Shipped records, board device trees and model expectations constrain a candidate configuration | Release date and changed ODT/drive operands do not identify a physical board revision |
| UART | UART3/pad 0 by INI and AFI | Physical pin match unresolved. The alternative UART5 pad-sharing lead is a different route |

[Board evidence](rg35xx-board.md) · [GPIO pad evidence](../reports/adfu-loopback-reconstruction.md) · [SD2 reconciliation](../reports/sd2-boot-path-reconciliation.md)

## 7. Recovery and conditional paths

`adfu_check(ini_word_0x14)` at `0xb4069254` reads PMIC status before testing boot code. PMIC bit 1 set triggers recovery and clears bits 0–1 in the written value. An I2C read failure returns −1 through the wrapper and becomes `0xffff`, leading to write-back `0xfffc`. Code 0 suppresses the GPIO loop. For nonzero code with a nonzero argument, the firmware clears `0xb01b0064[17]`, saves GPIO C output/input-enable words, drives C11 through all 32 LSB-first bits of `0x55aa55aa`, requests 1 ms per bit, and samples C10 after each wait. An exact echo enters recovery. Direction words are restored, while pull bit 17 stays clear and the last data bit for C11 is low. Other data bits depend on unknown readback rules. Vendor pinctrl associates C10/C11 with SD0 DAT0/DAT1. The loop's later physical pad effects and factory purpose remain unresolved.

The paired executions found no later DRAM consumer of those persistent GPIO values. An independent recovery design can replace the loopback if it establishes the resulting pad state and the desired board/factory recovery policy. The stock re-entry routine at `0xb40691a4` requests ROM `[0xffff5200,0xffff8000)` copied to SRAM `[0xb4060000,0xb4062e00)`, changes clocks, sets VBAR `0xffff0000` and SP `0xb4070800`, then jumps to SRAM. The integrated early-recovery trace ends at the target with the copy logged. The returned cold-error cases stop earlier at main recovery dispatch `0xb4065494`. [Recovery execution and persistent state](../reports/adfu-loopback-reconstruction.md)

## 8. DRAM records and configuration selection

Main calls `0xb40665d0` with the INI and produce flag zero. It copies record fields into SRAM before timer, UART and power setup. A nonzero resume flag and vector select resume before the secondary-record test. Cold mode selects the secondary record when INI +0x2c is nonzero. The shipped records have this selector set. The working global has 12 bytes and uses little-endian 16-bit values where marked.

| Field | Working offset | Primary INI offset | Secondary INI offset | Reference and use |
|---|---:|---:|---:|---|
| Clock (MHz, u16) | +0 | +0x1c | +0x4c | 468 requested. Cold mode rounds down to 12 MHz step |
| Capacity (MiB, u16) | +2 | +0x20 | +0x50 | 256 / 0. Cold timing calculation begins with forced 2048 MiB. Final stored value comes from probes or failure fallback |
| Bus selector | +4 | +0x24 | +0x54 | 1 for x16. Auto zero begins x32 and may fall back to x16 |
| Chip selects | +5 | +0x25 | +0x55 | 1 / 0. Auto zero tries two then one; explicit 1/2 fixes initial configuration |
| Type | +6 | +0x26 | +0x56 | `0x10`. Low nibble 0 selects DDR3-style operations. Low nibble nonzero selects an LPDDR-class path. High nibble 1 skips idle self-refresh programming |
| Row/column/bank | +7 | +0x27 | +0x57 | `0x48` / 0. Row code bits 7:6, column bits 3:2, banks bits 1:0 with zero as eight-bank encoding |
| Read/write ODT | +8 / +9 | +0x28 / +0x29 | +0x58 / +0x59 | 1/1 in Koriki and three earlier stock releases, 2/2 in 20231014 |
| Drive operand | +0xa | +0x2a | +0x5a | 0xc before 20231014 and 9 in 20231014 |
| Preserved byte | +0xb | +0x2b | +0x5b | Zero in reference; significance open |

The patched LPDDR cases show DCR `0x1000000c` versus DDR3 `0xb`, distinct MR1/MR2/MR3 and timing branches, initialization request `0x5f` and the same training request `0x81`. Type 1 selects a distinct MCFG field from other nonzero low-nibble values. Only exact type 2 writes the PUBL +0x3fc word. Shipped images exercise the DDR3-style branch only. A fixed independently supported hardware table needs its own validation and input rejection. [Caller comparison and record offsets](../reports/sd2-dram-reconstruction.md) · [Type branches](../reports/dram-complete-reconstruction.md#6-lpddr-branch-type--0xf--0)

## 9. DRAM sequencing and register contract

Readiness requires accessible clocked controller MMIO, correct reset transitions, qualified board power and timing, and acceptable hardware responses. uPCTL is based at `0xb01c0000`, PUBL at `0xb01c8000`, and DMM at `0xb0290000` in the traces. Register labels document applicable evidence, including related IP inference. For the individual MMIO words, see the [ordered trace](../evidence/firmware/boot-initialization-trace.json) and the historical [full successful pass with formula sources](../reports/ddr-timing-reconstruction.md#6-every-write-of-the-successful-pass-468-mhz).

| Order | Firmware work | Condition and outcome |
|---|---|---|
| 1 | Compute timing from working record. Clock and reset per §4; toggle ACDLLCR 0/0x40000000 then write PIR `0x10000000` | Repeated each attempt. Restored or preserved unrelated bits remain unknown physically |
| 2 | DFI update timing, TOGCNT1U/100N, TINIT, TRSTH, DMM+0x64 pulse, POWCTL=1, MCFG/MCFG1 | uPCTL readiness and clock semantics are shared model assumptions |
| 3 | PUBL DCR, MR0/1/2, PTR0–2, DTPR0–2, DTAR, IO/ODT and ZQ registers. Disable upper lanes on x16. Set PGCR rank mask according to attempt | MR1 and ZQ values are configuration-derived. 20231014 produces `0x42` and `0x29` versus `0x6` and `0x4c` |
| 4 | Poll ZQ0SR0 then PGSR reset readiness. DDR3 cold writes PIR `0x7f` at site `0xb4068700`. Wait for PGSR `0xf` | Bounded initial status polls, then unbounded exact-value poll |
| 5 | Training writes PIR `0x81` at `0xb406879c`; test PGSR `0x1f` or `0x3f` | Error branch logs four DXGSR0 lane words and may retry. Reference synthetic two-rank attempt fails then one rank passes. A different status can hang |
| 6 | Poll DFI readiness. Program controller timing, MCMD, Config and DFI settings. Apply TSTATEN and check CMDTSTAT/STAT. Request GO to Access | Uses rank-specific commands. CMDTSTAT and controller state polls can hang. Optional idle low-power path follows the type high nibble |
| 7 | Set DMM timing and probe geometry when enabled. Program final DCU_CFG and DMM settings. The low 16 bits of `0xb01b00b4` are updated with `0x3ff` | Geometry probes are cold only; resume uses stored geometry. Memory margin field interpretation is a candidate |
| 8 | Return controller/PHY result. On cold success run memory diagnostic, then write back config and AFI, then dispatch | Diagnostic result is independent of the core return |

### Timing arithmetic

The [DDR timing table](../reports/ddr-timing-reconstruction.md#5-recovered-formulas-ddr3-branch-mode-0) gives every recovered DDR3 formula and band. Use integer division and units from that table. In the reference 468 MHz band CL/CWL are 8/6, tRP and tRCD are `F*15/1000+1 = 8` cycles, tRAS is `F*375/10000+1 = 18`, tRC = tRP + tRAS, and tRRD is `F/100+1 = 5`. DDR3 tREFI = `F*78/10 = 3650` memory clocks. TOGCNT1U = `F/2 = 234`, TOGCNT100N = `F/20 = 23` use the computed half-rate controller clock. Cold mode begins at 2048 MiB for timing; reference x16 candidates take the 350 ns tRFC class (`F*350/1000+1 = 164` cycles). Resume uses the stored capacity and reference tRFC = 75 cycles. General density uses integer `capacity / (x16 ? 1 : 2) / cs` and the four 110/160/260/350 ns classes. These are instruction-derived calculations. Real timing and mode-register forwarding require the identified hardware.

MR1 packs `RTT_NOM[wrodt] | 2`. ZQ0CR1 packs `ZQ_ODT[rdodt] | drv`. PTR/DTPR and MR0 bit packing are linked above. In particular the observed MR0 at 468 MHz is `0x1140`; the firmware places tWR cycles at bit 9 and the interpretation of WR code zero and actual forwarding remains open. Many PHY and DMM fields lack matching target documentation. Preserve RMW masks with reads of the current state and keep delta from reset distinct from the resulting sampled values.

### Polling, retry and error results

| Wait/site | Predicate | Bound and outcome |
|---|---|---|
| ZQ0SR0 `0xb4068654` | bit 31 set | 101 reads, then internal `0x2a00fa11` |
| PGSR `0xb40686a8` | `(status & 7) == 7` | 101 reads, then `0x9a00fa11` |
| PGSR `0xb4068708` | exactly `0xf` | Unbounded. The trace's cutoff is an emulator instruction budget |
| PGSR `0xb40687a4` | exactly `0x1f` pass or `0x3f` error | Unbounded for other statuses, including synthetic `0x5f` |
| DFI `0xb40687cc` | bit 0 set | 101 reads, then `0xdf00fa11`; eligible first attempt can retry |
| MCMD, CMDTSTAT, STAT | Start clears, command status bit 0 set, or target state reached | Unbounded in the normal setup path. Resume self-refresh entry has a separate 1001-read STAT `0x45` wait that continues afterward |

The error branch retries the full clock/reset/programming pass where eligible. With auto rank and width the attempt sequence is (2,x32), (1,x32), (2,x16), (1,x16). The shipped x16 record reaches the last two. Persistent training error returns `0x1017fa11`. Other internal failure codes, including ZQ, initial PHY, terminal DFI and capacity exponent, generally collapse to `0x1747fa11`; inspect internal console and exact stop PC for diagnosis. An unbounded wait has no firmware return. The out-of-range row exponent check `0xf000fa11` is unreachable in the analyzed algorithm because exponent 31 ends the probe. [Status and failure analysis](../reports/dram-complete-reconstruction.md#5-training-failure-handling-and-the-controller-state-machine)

## 10. Geometry, training and diagnostic policy

Cold auto-detection uses training to choose a candidate rank count and width. This measures trainability under a particular recipe. A physically present rank that does not train remains ambiguous. It then programs DMM and measures memory aliasing using `0x6996` at base byte 4 and candidate addresses, using halfwords on x16. The column probe tries indices 0–3 and takes the first alias or uses code 3 if none appears. The row probe uses the chosen column code and, on x16, exponents `0x19 + c + k`. It takes k on alias or exponent 31, else the code remains zero (13 rows). The bank count comes from the INI. Under eight-bank firmware encoding, capacity = `2^(r + c + bus + cs + 3)` MiB, with firmware bus selector `bus` and numeric chip-select count `cs`. The derived size is stored in MiB before AFI conversion. The model's field widths (columns 8+c, rows 13+r) are decode hypotheses. [Geometry methods and outcomes](../reports/sd2-dram-reconstruction.md#6-geometry-and-diagnostic)

| Category | Evidence |
|---|---|
| Generalized algorithm | Training/retry, fixed probes and source-record banks determine the firmware output |
| Reference synthetic configuration | DDR3-class x16, one rank, eight banks, ten columns, fourteen rows, column → bank → row. The modeled outcome is 256 MiB, rcc `0x48`, DCU_CFG `0x202c` |
| Physical runtime observation | OBS-001 established the 256 MiB kernel-addressable span. It does not independently identify a device, row/column/bank geometry, bus width, or timing |
| Tested alternatives | Four banks with the same x16/row/column layout can match the reference record under the model despite conflicting with the DDR3 part hypothesis. Smaller row counts may overreport and pass the diagnostic. Two trainable ranks can report 512 MiB. Alternate decode orders give different results for the tested input |
| Isolated study | 180 modeled cases, 64 distinguishable outcome classes, 128 incorrect size reports, and 73 incorrect reports with a diagnostic pass |

A verified fixed board configuration removes uncertain discovery behavior for a known part and needs strict revision identity. Reproducing adaptive stock detection retains stock behavior across known inputs and shares its alias blind spots. A multi-revision design must associate each supported revision with independently established timing, geometry and board settings. Unsupported or ambiguous revisions should stop before executable loading.

The stock diagnostic at `0xb406631c` computes `N = capacity_MiB << 18` words with 32-bit arithmetic. Phase A writes i to word index i for 4, 8, 16 and successive powers of two below N, then verifies in order. Phase B writes and verifies word value and index `0x10 + k*0x41114` below N (byte stride `0x104450`). The reference 256 MiB success has 24 phase-A and 252 phase-B samples, or 276 reads and 276 writes. First mismatch reports an `addr:` or `tmp:` failure, and returns. It restores no contents. The highest power-of-two point can alias the unvisited byte zero on a twofold overestimate. The odd-factor stride avoids collisions between the finite phase-B test points for many wrapping geometries. A missed address or zero/wrapped diagnostic size may also pass without useful coverage.

An independent contract should track controller-ready, training-pass, calculated capacity, diagnostic result and physical memory qualification as separate outcomes. A failed diagnostic or unsupported decode requires a deliberate failure handling policy before memory admission. Any later broader diagnostic would need known-safe scratch regions and justified data/address coverage, including cross-boundary alias checks and a validated cache policy. [Memory diagnostic evidence](../reports/dram-complete-reconstruction.md#4-memory-test-0xb406631c)

## 11. Configuration write-back and exact AFI bytes

After a returned cold attempt, `0xb4066280` updates SRAM at INI+0x1c..0x2b from the working record. For the 16-byte INI representation it zeroes the unused positions +0x1e/+0x1f/+0x22/+0x23. It preserves the selector at +0x2c and secondary bytes. This includes the error path where the capacity remains the forced 2048 MiB. Writes in this phase are SRAM stores. Conditional disk persistence is attributed to the later app.bin branch.

The caller `0xb4066588` derives mode and device then invokes the producer `0xb4066500`. The 16 bytes at aligned `0xb4060300` are cleared before copying the three magic bytes and storing the fields. Words are little-endian.

| Byte offset | Size | Contents | Demonstrated use |
|---:|---:|---|---|
| 0 | 3 | `41 46 49` (AFI) | Checked by U-Boot getters |
| 3 | 1 | Zero from reference producer | Preserved in transfer. Distinctive-byte control shows the pinned getters check the first three bytes only |
| 4 | 1 | Boot mode | Downstream mode/boot policy |
| 5 | 1 | Boot device `0x20` or `0x22` | Derived from boot word, then consumed by MMC, boot flag and Linux bootargs |
| 6 | 1 | UART index 3 | Selects `ttyS3` in the target command line |
| 7 | 1 | UART pad 0 | Compatible getter, physical routing open |
| 8 | 4 | UART baud 115200 | Compatible getter word |
| 12 | 4 | `(uint32)(capacity_u16 << 20)` | U-Boot uses at least 8 MiB; otherwise fallback 496 MiB, including when magic is absent |

```text
SD0  414649000020030000c2010000000010
SD2  414649000022030000c2010000000010
```

Cold returned errors may emit a valid-looking AFI size `0x80000000` before taking recovery. A stalled poll may emit nothing. Resume has no AFI generation. Main's actual declared cold continuation, verified memory and complete image placement govern a legitimate transfer. An independent protocol may replace AFI when all consumers are changed. [AFI and consumer evidence](afi-handoff.md)

## 12. Post-DRAM loading and app.bin

At `0xb4065440` the live loader takes the successful cold branch. Main enables I-cache, configures clocks and requests the following sectors through the modeled selector-4 service. The loader writes `0xc` at `0xb0160050` for SD0 or `0xb0160058` for SD2. Both paths write DEVPLL `0x164` then set its bit 12 and update the low clock-selector bits to 2. The clock assumptions remain board-scoped.

| Stage | LBA and span | Destination and interpretation |
|---|---|---|
| App | `0x10c9`, 248 sectors | `0x1000`, stock ActBrm check |
| U-Boot staged header | `0x1800`, one sector | `0x300000` staging buffer |
| U-Boot image | From `0x1800`, header-sized sector-rounded chunks of up to 256 sectors | `0x05000000` for the vendor header and image, entry `0x05000040` |
| Handoff | app.bin gets the U-Boot entry in r0 | Validate compatibility and executable visibility before branching |

The unified research tool checks header, type, architecture, sizes, CRCs and layout as independent guards. The older stock trace describes which checks the loader itself performs. Validate entire sector-rounded spans, uncompressed and temporary buffers, saved state, and all potential memory overlaps with overflow-safe arithmetic. The 64 MiB synthetic case succeeds in DDR and diagnostics yet rejects the first U-Boot chunk at the 80 MiB base. Stock addresses describe the compatible payload. An independent stage may choose different addresses when its ABI and validated memory map allow them.

app.bin saves its incoming target at `0xb4060018`, enters masked SVC mode using the live SRAM stack and uses early configuration and timer/UART state. The CHIPID exchange responds to `0x746e3531` with modeled ready/status and zero data, with revision `0x41`. The replay observes 21 matching CHIPID accesses at the known helper site. With SFVD present app.bin follows its normal branch at `0x8264` and transfers from `0x1030` to the saved U-Boot target. AFI is unchanged. With SFVD absent the replay stops at dispatch `0x806c` and records write intent. Static analysis identifies 20 sectors from `0xb4062400` at LBA `0x1013`; the alternate writer and storage side effects were not executed. The static call `0x9e8c → 0x9430` can update the SD0 pull field including bit 17. Normal SFVD-present runs reach neither site. Retain or replace the relevant CPU-state setup, target passing, board/CHIPID checks, persistence policy, and pad state when removing app.bin for a specific U-Boot consumer. [Live continuation and app boundaries](../reports/unified-boot-chain-reconstruction.md#10-loader-continuation)

## 13. U-Boot or independent second-stage entry

The live trace reaches U-Boot with a verified image, exact AFI, transferred pin-mux word and CPU snapshot. Subsequent consumers are bounded invocations in reconstructed contexts. The runtime startup, relocated globals and full reservation state have not been executed continuously.

A targeted reading of the pinned Koriki payload anchors these static startup facts. They apply to the audited image hash only.

| Site | Static behavior | Outstanding compatibility requirement |
|---|---|---|
| `0x05000040 → 0x05000300 → 0x05000304` | Reset stub reaches CPU setup, masks IRQ/FIQ, selects SVC in the non-HYP branch, clears high-vector selection and writes VBAR | Compatible ARM entry privilege and execution state; writable stack and accessible vector address |
| `0x050003b0`, `0x050036b4` | Initial SP loads from a literal with value `0x050ffff0`. Aligns and reserves a `0xa8` region with r9 as a startup data pointer | Preserve space for the startup stack, global-data frame, nested calls and early board-init dependencies |
| `0x050036e8`, `0x05003704`, `0x05003760` | Loads a computed stack and relocation destination from global data. Copies linked image/data and adjusts type-23 relocations | Actual relocation source extent, destination, BSS, malloc/board-data and reserved blocks need complete startup accounting |
| `0x05003758` | Writes VBAR from relocated address | Full vector, cache and relocation validity remain startup prerequisites |
| `0x05003f84` and AFI getters | In the bounded invocation the exact AFI is read and `gd+0x34` receives RAM size | Fixed helper addresses for GD/SP and modeled board data are test fixtures. Verify their real allocation and the embedded U-Boot DT lifecycle |

The remaining bounded calls exercise boot flags, early MMC registration, part of environment initialization, FDT fixups and cleanup with the embedded DT, selected inputs and stubs. Runtime board initialization, reservations and the complete relocation path remain explicit compatibility blockers. A separately designed second stage needs an agreed entry mode and stack ownership, supported image type, versioned boot source/board/memory parameters, and reservations for still-live regions. It can use that interface without the proprietary AFI, INI or app.bin once all relevant compatibility duties are addressed. [Startup landmarks](../evidence/firmware/boot-initialization-trace.json) · [Bounded consumer methods](boot-chain-emulation.md)

## 14. Storage and executable policy

| Quantity | SD0 reference | SD2 reference |
|---|---|---|
| RG35XX slot/controller association | TF2 inferred, controller `0xb0230000` | TF1 and SD `0xb0238000` from OBS-001 |
| Loader boot word and AFI device | 0 / `0x20` | 2 / `0x22` |
| U-Boot registration | Device 0. Registration persists when card init fails | Device 1 in the SD2 role, after SD0 even if SD0 has no card |
| Boot command / FAT selector | `run mmcboot`, `mmc 0:1` | `run emmcboot`, `mmc 1:1` |
| Linux numbering | Depends on pinned driver boot-device policy and available cards | OBS-001 SD2 was Linux `mmc0/mmcblk0` |
| Loader recovery test | PMIC check, GPIO loop suppressed | PMIC check, then GPIO loop if enabled and PMIC allows |

Later direct MMC requires controller clock and reset, pin mux and electrical state, card response, and selection of the correct partition and files. The ROM-specific early read interface and U-Boot bounded device registration establish different contracts. A future driver must qualify actual controller and card initialization. Use controller address and an explicit partition/content selection policy so enumeration changes cannot silently change the medium. Vendor eMMC role names refer to a design convention; the physical boot card in OBS-001 is SD.

The binary persistent-environment layout uses device 1, byte offsets `0x5000` and `0x25000`, 0x20000 bytes each. In the backed cases the CRC check rejects invalid copies and the defaults are used. With no backing medium the environment read is modeled unavailable. Validated redundant arbitration remains outside the bounded execution. Scripts support the inspected subset (`run`, `if`, `test -n`, `setenv`, `echo`, FAT loads, text import and `bootm`). A present `boot.scr` reaching `source` is unsupported. Stock file loads include `uEnv.txt` and boot payloads from partition 1. Missing required file, selected card failure, corrupt CRC/DT or unsupported placement is a separate failure. An independent loader should explicitly define the supported storage layout, verification and configuration format. [Storage and script evidence](../reports/unified-boot-chain-reconstruction.md#13-environment-and-mmc)

## 15. ARM Linux handoff

The Linux ABI is independent of AFI. For a future AArch32 DT boot, confirm the contract of the selected kernel. Standard ARM boot conventions require r0=0, a machine ID policy in r1, a **physical** DTB pointer in r2 for DT boot, IRQ/FIQ masked, MMU and D-cache off, and defined entry privilege and instruction state. Use ARM SVC for the pinned legacy case. For an eligible virtualization-capable CPU, confirm the chosen kernel's HYP entry policy and configure PL1/HYP state and traps accordingly. Upstream recommends all ones in r1 for DT-only machines. It permits either I-cache state at entry. The pinned run's r1=0 results from its modeled board data and actual branch instructions.

Use a valid 8-byte-aligned FDT in accessible low memory, outside the decompressor and live payloads. Upstream recommends a RAM zImage within the first 128 MiB and placement above 32 MiB to avoid one relocation. Its suggested FDT placement is just beyond the 128 MiB boundary when memory permits. The pinned Koriki layout uses its own validated reference intervals. The memory nodes must state validated available banks. Reserve live firmware and platform-owned regions and include the exact initrd payload bounds in `/chosen`. Account for kernel decompression, relocation and DTB padding. Clean the relevant dirty data to the point visible to the kernel before cache shutdown, invalidate I-cache and branch prediction as needed, synchronize with DSB/ISB around the control-state and instruction transitions, quiesce DMA and loaded peripherals, and mask interrupt sources and CPU interrupts. Qualify secondary-core startup/hold state, coherency and platform-specific reset/address policy independently. Kernel-visible SMP symptoms in OBS-001 are late observations.

| Property | Koriki SD2 reference |
|---|---|
| Executed jump | First-instruction boundary at `0x8000`; r0=0, r1=0, r2=`0x03800000` |
| CPU state | A32 SVC, IRQ/FIQ masked, MMU and both caches modeled off after actual cleanup path |
| RAM bank | `[0,0x10000000)` from AFI-derived bounded board data |
| FDT | `0x03800000`, totalsize 28800, aligned reservation 0x7000 bytes |
| Initrd payload | `[0x02000000,0x023a43b1)`; 64-byte legacy header before payload |
| Bootargs | OBS-001-matching `console=ttyS3` and `boot_dev=sd2`, with modeled GPIOC6 high and SN absent |
| Gaps | Physical cache/coherency behavior, actual U-Boot reservation map, zImage self-relocation and execution, SMP/timer/IRQ/DT/storage support for a future kernel |

The actual helper invokes FDT fixups with modeled board data and reservations. The cleanup call masks IRQ/FIQ, disables and invalidates instruction state, flushes data state and clears SCTLR.C/M before the transfer. The kernel is intercepted at the first instruction. This is useful as a reference layout and interface. The selected modern kernel requires independent entry, memory, device tree, timer, interrupt controller, MMC and SMP audit. The upstream boot protocol was checked at the exact revision recorded in the source ledger. [Unified kernel handoff](../reports/unified-boot-chain-reconstruction.md#16-linux-entry) · [ARM Linux boot protocol at the pinned upstream revision](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/Documentation/arch/arm/booting.rst)

## 16. Cold, resume and failure contracts

| Path | Required entry and terminal classification |
|---|---|
| Cold success | Valid INI and cold selector, qualified DRAM clock/power, completed readiness/training/geometry and adequate memory validation. Stock main reaches the load path after AFI. Future success also requires a valid target image and placement |
| Cold diagnostic failure | Stock can continue without changing AFI. Future implementation should surface the failed test and withhold normal transfer until memory admission is justified |
| Cold returned error | May emit AFI with 2048 MiB. Dispatches to main recovery and does not load app.bin/U-Boot |
| Unsupported or stalled init | Stop at typed boundary for bad config, I2C/PMIC fault, software deadline, hardware status, unsupported medium or memory layout. A model budget is a trace outcome and establishes no physical timeout |
| Recovery | Classify early PMIC/GPIO decision separately from a returned cold error. Stock copy/ROM re-entry is conditional and target bytes are absent |
| Resume | Requires exact prior DDR record and retained-memory state, valid PMIC flag and vector, plus verified mode-1 electrical effects. Resolve the retention contract independently before enabling resume |

In mode 1 the stored primary record supplies clock, geometry and capacity. No cold capacity probe, memory diagnostic, write-back or AFI generation runs. The reference still resets controller/PHY, changes timing from stored density, sends PIR `0x3f`, issues eight PREA and eight REF commands before training, then another group of eight REF before GO. It trains with PIR `0x81` using the programmed training location. The path uses the retained vector after success, or a resume alarm and PMIC power-off branch after failure. Alarm wake/sleep decisions have further conditional behavior. `C-RESUME-DRAMRST` remains open. A matching PIR reset bit in related IP does not establish whether this PHY asserts the physical reset output for `0x3f`. Initial independent profiles leave retention unavailable until the electrical and software contracts are established. [Mode-1 comparison](../reports/dram-complete-reconstruction.md#34-mode-1-against-mode-0-ddr3-468-mhz-reference-responses) · [Resume contradiction](../evidence/contradictions.json)

## 17. Implementation profiles and blockers

| Profile | Prerequisites and evidence maturity | Advancement condition |
|---|---|---|
| A. ROM-compatible SRAM entry | Verify ROM loading, entry state, medium and ownership. Establish a private stack and explicit CPU/exception state. Optional early diagnostics can use a separately qualified channel. Excludes DRAM, resume and vendor recovery | Demonstrate bounded independent SRAM-only execution with validated load/code/stack layout |
| B. Independent DRAM initialization | A plus qualified PMIC, board clocks/resets and DRAM device. Firmware-level timing, flow and failure results can guide offline design. Retention and proprietary consumers are outside this profile | Demonstrate distinct ready/trained/size/diagnostic results and usable memory under agreed validation, with unsupported states rejected |
| C. Independent loader with compatible U-Boot | B plus supported compatible image/entry, exact AFI, relevant app duties and real startup/relocation reservations. Excludes unqualified persistence and resume | Preserve consumer inputs and prove complete startup placement/ABI compatibility |
| D. Independent Linux handoff | B plus supported controller/storage selection, payload integrity and placement, versioned config, DT, ARM/Linux entry state and exact kernel support. Excludes vendor scripts, AFI and resume | Establish the required kernel and board interfaces for its first instruction and subsequent platform initialization |

Priorities are by earliest profile affected. **A** needs the actual ROM entry contract and SRAM ownership. **B** additionally needs part identity/geometry, valid timing/reset behavior, PMIC electrical semantics and real training. **C** needs startup and app side effects. **D** needs a kernel-specific platform contract; the legacy transfer gives one reference. The full uncertainty register includes potential offline evidence and future observations, plus their discriminatory value. [Machine-readable profiles and uncertainties](../evidence/firmware/bootloader-initialization-contract.json)

## 18. Dependencies, provenance and reproduction

The [dependency analysis](../reports/boot-initialization-dependencies.md) explains the graph edges and recorded discrepancies. Use the generated operation and register reference to navigate from stable IDs to trace checks. Raw hook data include actual instruction PC, caller/poll site when distinct, width in bytes, access type, value and named rule where supplied. Delay requests, selected SRAM stores and CPU control writes are supplemental observation points indexed into the loader stream. Each U-Boot/helper segment has a separately recorded model boundary and state envelope.

Record definitions, formulas, externally visible behavior and constrained source comparisons support independent implementation. Input executable images remain separate verified dependencies. Pinned public Linux/vendor source and related U-Boot layouts have their own file-level licensing. Repository source and license review remains necessary before reusing code. The specification contains behavioral evidence and limited static anchors. [Source ledger](../evidence/sources.json) · [Licensing inventory](../reports/licensing.md)

From the repository root with local Python requirements installed and verified inputs already available:

```sh
python tools/bootloader_contract.py generate
python tools/bootloader_contract.py validate
python tools/bootloader_contract.py compare
ATM_FIRMWARE_DIR=FW python tools/bootloader_contract.py replay --check
python -m unittest discover -s tests -v
python tools/research.py validate
python tools/research.py generate --check
python tools/render_catalogue.py
python tools/render_html.py
```

Use replay without `--check` to regenerate the ordered trace from matching images. `ATM_FIRMWARE_DIR` holds regular files named by release ID with `.img` suffix. `ATM7039S_STOCK_LOADERS` holds the historical extracted `loader-<date>.bin` files for DDR/regression tests. `ATM_SOURCES_DIR` is the local layout accepted by the pinned source consumers, including `s500_kernel/arch/arm/boot/dts` and `s500_kernel/arch/arm/mach-owl` for ADFU reproduction. Replay checks archived acquisition identities before execution. [Persistent research handoff](../reports/pr9-research-progress.md)
