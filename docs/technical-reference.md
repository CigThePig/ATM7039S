# ATM7039S technical reference — research edition

Edition 0.1 · Evidence examined 2026-11-22 · Original Anbernic RG35XX only

This is an independently assembled, partial technical reference. It is not a vendor manual, electrical specification, register-access guide or mainline board port. No physical ATM7039S hardware was accessed. Numerical definitions extracted from a related vendor header are explicitly candidates. No chapter establishes safe voltage, clock, power-management or arbitrary register settings.

## Navigation

1. [Scope and evidence](#1-scope-and-evidence)
2. [Identification and variants](#2-identification-and-variants)
3. [Architecture](#3-architecture)
4. [CPU](#4-cpu)
5. [Memory](#5-memory)
6. [Address map](#6-address-map)
7. [Clocks and resets](#7-clocks-and-resets)
8. [Interrupts](#8-interrupts)
9. [DMA](#9-dma)
10. [GPIO and pinmux](#10-gpio-and-pinmux)
11. [UART](#11-uart)
12. [I2C](#12-i2c)
13. [SPI](#13-spi)
14. [SD/MMC](#14-sdmmc)
15. [USB](#15-usb)
16. [Display](#16-display)
17. [GPU](#17-gpu)
18. [Audio](#18-audio)
19. [Multimedia](#19-multimedia)
20. [Power](#20-power)
21. [Timers and watchdogs](#21-timers-and-watchdogs)
22. [Boot](#22-boot)
23. [Firmware](#23-firmware)
24. [Linux compatibility](#24-linux-compatibility)
25. [RG35XX board](#25-rg35xx-board)
26. [Family comparison](#26-family-comparison)
27. [Contradictions and errata](#27-contradictions-and-errata)
28. [Register appendix](#28-register-appendix)
29. [Provenance](#29-provenance)
30. [Open questions](#30-open-questions)

## 1. Scope and evidence

The target is the ATM7039S, using the 2022–2023 RG35XX as a board reference. Owner-supplied context identifies 256 MB RAM and GarlicOS 1.4.9; neither was measured here. Newer RG35XX Plus/H/SP/2024 use a different platform and are excluded.

Each important conclusion references a finding in the [ledger](../evidence/findings.md). `Verified` means the narrowly stated claim is directly established: for example, a source really defines an address. It does **not** mean that address has been tested on ATM7039S. Scope is therefore mandatory. `Strongly supported` means multiple relevant observations support the conclusion; shared vendor ancestry limits their independence. `Inferred`, `speculative` and `unknown` remain separate. No speculative constants were added.

Software observation, manufacturer specification and hardware observation are separate kinds of evidence. A DT node can remain from an ancestor board. An enabled node does not demonstrate working hardware; a disabled node does not demonstrate absent hardware. A resource size is not the number of meaningful register bytes. [DT-001, MAP-001]

## 2. Identification and variants

The 2015 Actions annual report contains an explicit ATM7039S product row: four CPU cores, up to 1.6 GHz, SGX544 graphics, 32-bit DDR up to 533 MHz, BGA359, 28 nm and introduction in December 2014. These are manufacturer product specifications, not measured RG35XX operating parameters. The same table distinguishes ATM7039, ATM7059 and S500. [ID-001, ID-002]

The 2013 ATM7039 announcement explicitly names Cortex-A9, while the available RG35XX DT describes Cortex-A9. This supports the architecture lead but does not identify the S revision's MIDR, cache sizes, fuse configuration or package marking. The ATM7039's wider DRAM specification must not be copied to ATM7039S. [ID-001..003, DT-002]

The root compatibility strings `actions,gs705a` and `actions,atm7059a`, plus `actions,atm7039c-gpu`, establish which driver names firmware expects. They do not establish an ATM7059A/ATM7039C/ATM7039S silicon identity. The gist has one listed revision from December 2022 and no accompanying explanation of extraction method or firmware hash; decompiled syntax is suggestive, not proof of origin. [DT-001, GPU-001]

## 3. Architecture

The observed software model comprises a Cortex-A9 CPU complex, GIC, PL310 L2 controller, CMU, system power controls, GPIO/pinmux, DMA, storage, serial controllers and multimedia blocks. The SGX GPU, LCD, display engine and video codec blocks have separate resources; graphics rendering is not synonymous with display scanout. The external ATC2603C node hosts several power and audio functions. [DT-002, IRQ-001, PMIC-001; address catalogue]

A related [S500 manual](../reports/related-manual.md) was retrieved and scoped separately. Its target-specific fields have not been imported as ATM7039S facts.

A complete interconnect topology, arbitration/QoS specification, DMA coherency contract and security architecture remain unavailable. The header's `NIC`, `DMM`, `UPCTL` and `PUB` symbols are leads rather than a recovered bus architecture. No TrustZone/secure-boot capability is asserted for ATM7039S based on S900 or ATM9009 descriptions.

## 4. CPU

Both examined RG35XX tree artifacts contain two Cortex-A9 CPU nodes. The selected vendor kernel defconfig enables SMP with a four-CPU compile-time limit. Its SMP initialization queries the SCU, caps the result at `nr_cpu_ids`, and optionally forces two possible CPUs when the `powersave` early parameter is present. The default of that parameter is false. [DT-002, CPU-001, CPU-002]

This provides a concrete software mechanism to investigate, but does not settle whether a particular image uses two or four cores. Required evidence is a known-provenance runtime command line, SCU-reported count, CPU possible/present/online masks, and boot log. DT inheritance, a software limit and a physical silicon difference remain distinct explanations.

The DT names PL310 at `0xb0022000`, a unified level-2 cache, and supplies latency properties. Cache capacity/associativity and actual enabled features must be read from authoritative implementation documentation or a permitted runtime observation; they cannot be derived from the controller name alone. Standard ARM MMU and cache semantics do not establish Actions-specific coherency, secondary startup, DVFS or idle behavior. Vendor `platsmp-owl.c`, `headsmp-owl.S` and powergate code are the next source-analysis targets. [IRQ-001; gist cache node; vendor-kernel source]

## 5. Memory

`/memory/reg=<0 0>` appears in both observed board DT artifacts. It is a placeholder, not a zero-RAM result and not evidence for a complete `0x00000000..0x0fffffff` usable map. The related U-Boot source consults an AFI parameter structure for DDR size. The kernel reserves low 16 KiB for DQS training and allocates framebuffer/kinfo/ION areas relative to runtime memory limits. [MEM-001..003]

The AFI source pointer `0xb4060300` belongs to that boot environment. Do not classify it as a physical peripheral, Boot ROM or SRAM solely because it is an absolute address. Likewise, source `IO_ADDRESS()` values may be mapped virtual addresses rather than physical bus addresses.

The header exposes UPCTL0/1 and PUB0/1 candidate blocks. Two named controllers do not establish two enabled channels on ATM7039S; the manufacturer explicitly differentiates the S variant's DRAM width. Initialization before Linux, DDR training sequences, timing values, RAM aliases, ROM mapping, internal SRAM capacity and exact reserved regions remain unresolved. [ID-001, MAP-001]

## 6. Address map

Use the [generated reference](../registers/generated/reference.md), [CSV](../registers/generated/registers.csv) and [canonical JSON](../registers/canonical/hardware.json). There are two separate namespaces:

- `dt:` records: exact resource declarations in the RG35XX-labelled gist.
- `candidate:` records: explicit `BASE + offset` facts from the ATM7039-labelled vendor header, with ATM7039S applicability inferred.

Register width, access type, reset values and bit meanings are unknown unless separately supported. Reserved addresses are not safe to read. The extractor preserves multiple resource tuples and does not turn I2C device address `0x65` or CPU number `1` into physical MMIO. It records parent-bus geometry without silently translating buses. Root board resources have their address context in the source. [MAP-001, MEM-001, PMIC-001]

Selected resource observations:

| Block | Source address | Declared resource size | Caution |
|---|---:|---:|---|
| GIC distributor | `0xb0021000` | `0x1000` | Separate CPU interface at `0xb0020100` |
| PL310 | `0xb0022000` | `0x1000` | Cache implementation unknown |
| UART0 | `0xb0120000` | `0x2000` | Register spacing is not resource size |
| I2C0 | `0xb0170000` | `0x4000` | Child `reg` is a bus address |
| GPIO | `0xb01b0000` | `0x40` | Pinmux/interrupt resources extend elsewhere |
| SD0 / SD1 / SD2 | `0xb0230000` / `0xb0234000` / `0xb0238000` | `0x38` each | Slot mapping pending |
| DMA | `0xb0260000` | `0xd00` | Also referenced by NAND node |
| LCD | `0xb02a0000` | `0x20c` | Separate display engine |
| GPU | `0xb0300000` | `0x10000` | Gist disabled, modified DTB enabled |

The catalogue also retains disabled and inherited resources. Presence in the table is not proof that the RG35XX board exposes the feature. Source lines for every resource are embedded in the canonical file.

## 7. Clocks and resets

The vendor header and mainline S500 driver agree on important CMU offsets: COREPLL `0x00`, DDRPLL `0x08`, display PLL `0x10`, bus clock `0x1c`, SD clocks `0x50/54/58`, GPU clock `0x90`, enable banks `0xa0/a4` and reset banks `0xa8/ac`. This agreement is useful compatibility evidence, not a safe-frequency table. [CLK-001]

The mainline S500 driver describes PLL factors, parent selection, divider tables and gate/reset mappings. These can be compared with `clocktree-atm7059.c`. Analog lock delays, reserved bits, clock polarity, voltage dependencies and safe CPU/DDR/GPU operating points on ATM7039S are not validated. The gist's `clk_ignore_unused` is a boot argument, not a complete clock dependency description.

A limited S500 source-derived tree is in [clock notes](clock-notes.md). No ATM7039S clock-tree diagram is labelled hardware-verified. Clock writes and PLL experiments are outside this session's authorization.

## 8. Interrupts

The GIC resources are distributor `0xb0021000/0x1000` and CPU interface `0xb0020100/0x100`. Many nodes use three-cell tuples, for example GPU `<0 3 4>`, UART0 `<0 29 4>` and MMC0 `<0 42 4>`. Under the standard ARM GIC binding these are SPI indexes; they are not Linux virtual IRQ numbers. PMIC and GPIO children use other interrupt parents and different tuple geometry. [IRQ-001, GPU-001, MMC-001]

Always resolve the interrupt-parent phandle and `#interrupt-cells` first. A GIC SPI identifier conventionally corresponds to SPI index plus 32 at the GIC level, while Linux's assigned IRQ is a separate number. The watchdog tuple is a PPI and must not be interpreted as SPI. Complete routing, trigger behavior and wake sources still require driver and runtime correlation.

## 9. DMA

The gist describes DMA at `0xb0260000/0xd00` with four interrupt tuples; mainline S500 uses the same base, extent and SPI indexes 57–60. The vendor header names twelve channel blocks at offsets `0x100` through `0xc00`, with MODE, source/destination, frame length/count, stride, start and link-list symbols. These are source-defined channel candidates, not a confirmed ATM7039S channel count. [MAP-001; gist DMA node; linux owl-s500.dtsi DMA node]

Descriptor packing, request IDs, burst alignment, interrupt acknowledgement and coherency must be compared in vendor and mainline drivers before reuse. Some Owl variants share a driver but select different configurations. ION allocation does not itself establish hardware cache coherency. DMA is a prerequisite for dependable storage and audio testing; arbitrary DMA programs could corrupt RAM and are not authorized.

## 10. GPIO and pinmux

The gist has a GPIO controller at `0xb01b0000/0x40` and five IRQ tuples. The header additionally names mux controls at `+0x40..0x4c`, pull controls, pad drive controls and interrupt controls from `+0x204`. Thus the small GPIO resource does not encompass all pin configuration. [GPIO-001]

The [board pin-property table](rg35xx-board.md) resolves software phandles and preserves numeric offsets. It does not assign package balls or claim electrical polarity from misleading vendor comments. Pinmux group strings must be matched against `pinctrl_data-atm7059.c` and mainline `pinctrl-s500.c`. Per-bank sizes, mux widths, pull options and drive strengths need a reviewed translation before porting.

The vendor header assigns both `PWM_CTL5` and `SPEED_SENSOR_CTL` to `+0x7c`. This is recorded as an alias warning, not arbitrarily resolved as a mistake or an alternate-function proof. Unknown multiplexing or a source error are both possible. [MAP-001; consistency report]

## 11. UART

The gist lists seven UARTs from `0xb0120000` at `0x2000` spacing, with GIC SPI indexes 29–35 and a 48 MHz `clock-frequency` property. UART0, UART3 and UART5 are marked okay in this artifact. An okay controller is not proof of an accessible debug connector. [gist serial nodes; source catalogue]

Mainline `owl-uart.c` exposes offsets CTL `0x0`, RXDAT `0x4`, TXDAT `0x8`, STAT `0xc`. Its source defines CTL enable bit 15, RX/TX interrupt enable bits 18/19 and STAT FIFO flags. These remain S500-compatible driver semantics to validate on ATM7039S. Initialization should follow the source driver: acquire clocks, configure pinmux, establish the resource/IRQ, configure format and only then enable transfers. Do not copy an unreviewed raw register sequence.

No test pad, voltage level or working serial adapter connection has been established. Tinyhack's statement that serial is inaccessible is a research observation, not a proof that no physical UART signal exists anywhere. [BOOT-003; vendor U-Boot AFI serial parameters]

## 12. I2C

Four source resources are at `0xb0170000`, `0xb0174000`, `0xb0178000`, `0xb017c000`, each `0x4000`. The corresponding upstream S500 bases and interrupt indexes match. I2C1 contains ATC2603C at `0x65`; I2C2 contains HDMI-related child declarations; other inherited devices are not evidence of RG35XX population. [PMIC-001; generated address catalogue; mainline layout comparison]

Use `drivers/i2c/busses/i2c-owl.c` as a candidate implementation. FIFO sizing, divider calculations, interrupt status clearing and bus recovery need comparison with the vendor controller. Even a nominally read-only I2C scan causes bus transactions and can affect sensitive devices; no live scan is proposed as a first hardware test.

## 13. SPI

Four SPI resources are declared at `0xb0200000`, `0xb0204000`, `0xb0208000`, `0xb020c000`. The first two are explicitly disabled; absent status on the others means availability under DT rules, not proof of wired devices. The vendor header provides control/divider/status/RX/TX/count candidates. [generated reference; vendor-header source]

No Owl SPI driver was found in the inspected upstream v6.12 tree. The vendor implementation and related U-Boot SPI definitions are starting points for a new port. Compare CPOL/CPHA encoding, FIFO thresholds, chip-select control and clock/divider semantics before any binding adaptation. The panel's GPIO-based serial control properties must not be assumed to use one of these hardware SPI controllers. Board connector exposure is unknown.

## 14. SD/MMC

MMC0 and MMC2 are enabled in the gist; MMC1 is disabled. Alias `sdboot` names MMC0. This makes MMC0 a reasonable boot-storage lead, but does not independently identify the physical labels of both slots. The mainline S500 tree matches all three bases, `0x38` sizes and SPI IRQ indexes 42–44. [MMC-001, MMC-002]

Mainline register offsets run from SD_EN `0x00` through SD_BUF_SIZE `0x34`; command, argument and response buffers are separately named. The driver includes delay tuning and DMA integration, making it a better starting point than an SDHCI assumption. U-Boot's Owl MMC header independently names the same controller addresses. Hardware timing margins, high-speed modes, voltage switching, DMA request IDs and error handling remain to be checked on the target.

Do not extrapolate manufacturer NAND ECC claims into an SD-controller feature. This project has not read, repaired or tested the failing factory card, and has not altered or imaged the owner's working card.

## 15. USB

The board tree has two disabled legacy USB nodes at `0xb0600000` and `0xb0700000`, plus an enabled `actions,atm7059tc-usb` node at `0xb0400000` and a PHY-related additional resource. Related U-Boot code uses DWC3 naming. Meanwhile the header's `USB2_BASE` is `0xb02b8000`; this discrepancy must not be hidden by merging names. [USB-001, C-USB]

The controller's possible roles, PHY requirements, VBUS management and pin routing are separate from the RG35XX physical connector's usable speed and role. No USB3 capability is claimed for the handheld. The modified DTB changes legacy host plug-detection properties and the monitor VBUS GPIO, illustrating why board power policy matters. [DTB comparison]

## 16. Display

LCD, display engine, HDMI, DSI and CVBS have separate declarations. The gist describes an RGB LCD, a 640×480p60-labelled mode and explicit panel-control GPIOs. The enabled LCD node is at `0xb02a0000/0x20c`. The display engine is at `0xb02e0000` and also references `0xb0500108`. [LCD-001; generated reference]

The panel mode has xres 640, yres 480 and refresh property 60; actual refresh and pixel clock have not been measured. Vendor pixel-clock units, sync inversion, panel initialization and FIFO/scanout behavior must be traced through the vendor LCD code. The separate `de_atm7059.c` implementation provides leads on overlays and scaling; their presence in related code is not a verified feature list for this silicon/board.

No framebuffer address, stride, color order, overlay count or reset sequence is asserted without a matching image and driver path. A retained boot framebuffer could help an initial kernel port, but ownership, cache attributes and reserved memory must first be understood.

## 17. GPU

Manufacturer product data identifies SGX544 for ATM7039S. The board tree names `actions,atm7039c-gpu` at `0xb0300000/0x10000`, SPI 3. The gist disables it; the examined 2100mAh DTB enables it. [ID-001, GPU-001]

The selected kernel configuration builds `eurasia_km_linux`, not the sibling Android-oriented `eurasia_km` branch. The selected configuration names SGX544 revision 115, one MP core, DDK 1.14 build 3625561 and OMAP-named platform glue. These are build choices, not a measured GPU identity. The sibling branch's 1.12 version must not be reported as the selected Linux DDK. [GPU-002, GPU-003]

OMAP-named glue is not evidence of a TI OMAP physical address map: the selected glue defines dynamic platform resource lookup, which supplies GPU base and IRQ. A fallback `0x56000000` is therefore not an ATM7039S register discovery. [GPU-004]

The kernel side contains explicitly licensed source in inspected files; the build separately installs PowerVR userspace components from a driver repository. Kernel module, userspace EGL/GLES services, memory allocation, framebuffer/display bridge, command submission and power hooks must agree on the DDK ABI. This is a plausible integration route, not a full open driver replacement. Full command-stream semantics, shader ISA/toolchain, firmware requirements and target revision are not recovered. [GPU-006]

Upstream Linux v6.12 `DRM_POWERVR` targets Series 6 and later and requires ARM64 in that pinned version. SGX544 is not supported by that implementation. The pinned reMESA project reports SGX544 research without demonstrated independent submission/rendering; its SGX535 results do not transfer automatically. [GPU-007]

Open SGX work must be assessed individually for exact core/revision, render API and kernel/userspace coverage; no modern PowerVR announcement is treated as SGX544 support. [GPU-005]

## 18. Audio

The gist has ATC2603C audio under the external PMIC, plus separate SoC I2S/PCM-related declarations. The generic I2S node is disabled while a PCM audio node is okay. The modified DTB adds a second headphone-detect GPIO. This points to a board-specific routing problem rather than a generic codec-only task. [PMIC-001; source tree; DTB comparison]

The PMIC's analog codec, SoC digital interface, DMA, sample-rate clocking, speaker-enable GPIO and jack detection must be treated separately. Source nodes mentioning microphones or inherited amplifiers do not prove those parts are fitted. Exact supported rates, sample widths, DMA synchronization, routing registers and amplifier wiring are pending vendor audio-code inspection and matching runtime evidence.

## 19. Multimedia

The manufacturer markets video decode capabilities for ATM7039S. The related tree names VDE `0xb0280000`, VCE `0xb0288000`, ISP and other media blocks. A register-block name does not prove the shipped handheld exposes the feature, supports a particular codec profile, or has a redistributable acceleration stack. [ID-001; generated reference]

The related vendor sources contain VDE/VCE drivers, but this session did not reconstruct their complete IOCTL ABI, microcode, buffer requirements or command sequences. Decoder and encoder capability must not be conflated: the S product row is not a full codec matrix. DMA buffers, cache maintenance and display handoff remain major unknowns.

## 20. Power

The ATC2603C node is an external I2C device, not a SoC register range. Its source children include regulators, RTC, power, gauge, GPIO and audio functions. The source maps CPU supply through a regulator phandle; GPU supplies vary by board source. Do not copy another board's regulator voltages or charging thresholds into the RG35XX. [PMIC-001, GPU-001]

There is no measured evidence here establishing what happens electrically when bootable storage is absent, whether charging depends on particular software stages, or the battery/USB behavior of a failing card. Those remain explicit questions. The present research performed no no-card power test. Thermal and shutdown behavior, wake routing, suspend context and rail sequencing need a source audit plus authorized measurements.

## 21. Timers and watchdogs

The vendor header's timer block at `0xb0168000` includes T0/T1 control, compare and value symbols, secondary CPU entry/flag symbols and USB control symbols. These mixed-purpose definitions warn against assuming a simple timer-only register range. [MAP-001]

The board watchdog at `0xb0020600` declares a `0x100` extent plus CMU registers and is disabled. Mainline S500 separates the private timer at `0xb0020600/0x20` from the watchdog at `0xb0020620/0xe0`. A shared starting address is therefore not sufficient compatibility evidence. The layout comparison retains this difference rather than claiming a watchdog match. [gist watchdog node; mainline S500 private timer/watchdog nodes]

## 22. Boot

See the dedicated [boot-chain report](boot-chain.md). The identified image-layout recipe is not a Boot ROM specification. Initial execution address, ROM media search rules, signing/security policy, exact early loader format and DDR training remain unknown. The related U-Boot source expects AFI information and builds separately from an early `bootloader.img`. [BOOT-001, BOOT-002, MEM-003]

Stock userspace boot is reported through uImage, ramdisk, Android-style init and a launcher script. It has not been independently replayed here. No bootloader or boot ROM replacement was attempted. [BOOT-003]

**Stock boot chain (PR #5).** Block 0 at SRAM `0xb4060000` → ROM read service `0xb4060400` (r9=4) → bootloader.bin `0xb4065400`, which loads `bootloader.ini`, initialises DRAM, writes the AFI, loads app.bin to `0x1000` (ActBrm-checked) and U-Boot to `0x05000000` (not CRC-checked) → app.bin (chip check, optional ini write-back) → U-Boot. `check_boot_flag` turns `bootcmd=run ramboot` into `run mmcboot`, which fatloads `uEnv.txt`, `uImage` (`0x7fc0`), `ramdisk.img` (`0x1ffffc0`) and `kernel.dtb` (`0x03800000`) from SD0 partition 1 and runs `bootm`. Linux starts at `0x8000` with `r0=0, r1=0, r2=0x03800000`, MMU and caches off. [BOOT-012..BOOT-020; [report](../reports/stock-boot-chain-reconstruction.md)]

## 23. Firmware

Only public standalone components were analyzed: the published GPU DTB and a historical GPIO key module. Provenance, hashes, sizes and module metadata are in [artifacts.json](../evidence/artifacts.json). No complete stock, GarlicOS or Koriki release image was acquired, mounted or executed. Therefore there is no new whole-image partition map, kernel disassembly or early-boot binary reconstruction in this edition.

The component scanner identifies MBR entries, candidate FDTs, legacy uImage headers/CRCs and ELF identities. A valid header is not proof of device compatibility or absence of malicious code. Whole-image analysis should begin with a lawfully available, hash-identified image and extract components to scratch storage without mounting or executing them. [ART-001; tools documentation]

## 24. Linux compatibility

Read the [driver report](../reports/linux-compatibility.md). The strongest candidates are ARM standard blocks plus S500 UART/I2C/MMC/DMA and related CMU/pinctrl. Matching addresses and interrupt cells narrow the search but leave clocks, resets, power domains, pin assignments, DMA routing and runtime binding behavior unresolved.

The inspected build configuration actually selects a source-built kernel and a U-Boot source revision. This does not establish complete open firmware: the earlier loader is separate, working stock sources are not established, and GPU userspace remains an independent dependency. KNULLI's current page marks original RG35XX unsupported. [BOOT-002, GPU-006, KNULLI-001]

## 25. RG35XX board

The [board report](rg35xx-board.md) distinguishes DT properties from fitted parts. It covers regulator and GPIO references, storage aliases, panel controls, audio detection and inactive inherited features. It does not turn a disabled camera, touchscreen, Wi-Fi or vibration node into a claimed board capability.

Board revision, 2100/2600mAh battery variants and OS-specific DT changes must be captured with actual image hashes. Battery-named files are configuration labels, not a reliable hardware-identification procedure. Owner hardware observations remain pending.

## 26. Family comparison

See the [family matrix](../comparisons/chip-family.md). ATM7039S and ATM7039 differ in manufacturer-reported memory bus/package characteristics. S500 is a strong source-code analogue for selected blocks; S700/S900 differ in CPU architecture and variant-specific peripherals. ATM7039C and ATM7059A names appear in vendor software without establishing commercial silicon equivalence. [ID-001..003, FAMILY-001]

## 27. Contradictions and errata

Nine contradiction records are maintained in [contradictions.json](../evidence/contradictions.json). They include CPU count, memory placeholders, USB base naming, GPU enable state, kernel-version descriptions, changing support status, historical DDR wording, OMAP fallbacks and GPIO comment conflicts. None is presented as a confirmed silicon erratum. No authenticated ATM7039S errata document was found.

## 28. Register appendix

The generated reference contains 1,760 explicit related-header register symbols across 72 candidate base groups, plus 51 DT resource tuples. This is a source-extraction count, not a coverage score for the silicon. The header has 1,841 resolved constants; base constants and other non-register definitions are not inflated into the register count.

UART control/status and SD/MMC bit masks from mainline S500 are attached as separately scoped, inferred fields where offsets match. They are not target-verified meanings. Unknown reset/access/width fields remain explicit. In particular, adjacent offsets and names do not establish register width or read side effects. The generated C header uses `CANDIDATE_` prefixes and is unsuitable for unattended target access. All generated forms derive from the canonical JSON; the raw extraction does not evaluate preprocessor conditionals or prove an active build path. [MAP-001]

## 29. Provenance

The [source catalogue](../evidence/catalogue.md) links immutable repository revisions, file paths, hashes and exact URLs. The [licensing audit](../reports/licensing.md) distinguishes original writing/tools, source-licensed kernel/glue, unavailable/uncleared binaries and unlicensed research artifacts. Prior researchers retain attribution. Original code, arrangement and prose use MIT; that grant does not relicense third-party source material.

## 30. Open questions

The highest-value missing evidence is a known-provenance boot bundle linking early loader, U-Boot, kernel, final DT and PowerVR module/userspace. That would permit static reconstruction of DDR handoff and actual resource selection without touching the owner's cards. Next priorities are final CPU topology and memory layout, CMU/reset/power dependencies, and a source-to-binary comparison of the source-built kernel. [roadmap](../reports/next-investigations.md)

A complete TRM would additionally require silicon identification/revision semantics, electrical/package documentation, exhaustive register fields/access/reset behavior, ROM behavior, DRAM training, coherency/ordering constraints, safe power transitions, media command ABIs, GPU programming details and verified errata. This edition does not supply those missing facts.

## Offline firmware continuation

Edition 0.2 adds release-specific binary evidence without broadening related-chip claims. [The firmware report](../reports/firmware-analysis.md) identifies a full original-RG35XX Koriki v1.0 image, confirms raw boot-region placement and records kernel/DT/ramdisk/module/userspace hashes. It is not an authenticated stock/Garlic acquisition.

The [AFI chapter](afi-handoff.md) reconstructs a 16-byte producer/consumer interface and its MiB-to-byte size conversion. Final capacity, physical mapping, DDR training and Linux reservations remain unresolved. The [CPU study](../reports/cpu-topology.md) separates manufacturer topology, DT nodes, SCU discovery and software policy.

[Ten selected clock/reset fields](../comparisons/cmu-field-study.md) now have explicit S500 manual/source evidence. Related reset/access metadata is separate from unknown target values. The manual/upstream UART divisor discrepancy remains an explicit contradiction. [Graphics ABI work](../reports/graphics-abi.md) connects a released 3.10.37 module to versioned library candidates and maps the source bridge envelope without claiming a complete open driver.

[Historical build attempts](../reports/build-reproduction.md) preserve real compiler/DTC failures and exact inputs. No newly built image was booted and no hardware finding was added. See the [engineering report](../reports/offline-continuation.md) for scope and remaining priorities.

## Stock firmware continuation

Anbernic's own firmware is now part of the evidence base ([dossier](../reports/anbernic-stock-reverse-engineering.md)). Section-level updates:

- **§5 Memory / §22 Boot:** The loader container, stage load addresses and the DRAM configuration record (468 MHz, 256 MiB, x16, 1 CS) are documented, and the AFI size producer is traced (BOOT-009, MEM-005). DRAM bring-up uses two previously undocumented blocks at `0xb01c0000`/`0xb01c8000` whose offsets match the DesignWare uPCTL/PUBL layout (DDR-001; candidate blocks `firmware:DDR_UPCTL` and `firmware:DDR_PUBL` in the register model). The x16 setting is recorded against the manufacturer's 32-bit DDR claim (C-DDR-WIDTH).
- **§7 Clocks:** The loader sets core and device PLLs to 600 MHz and pulses DDR/DMAC reset and clock gates, which the vendor clock tree names exactly.
- **§10 GPIO / §25 Board:** From 230309, U-Boot reads GPIOC6 as a board-variant strap. Variant boards use alternative LED (GPIO 78–80) and earphone-detect (GPIO 81) pins (BOOT-011).
- **§11 UART:** All loaders configure UART3/115200, so the expected kernel console is ttyS3 (UART-003).
- **§15 USB:** Stock init leaves the port in host mode with the Actions umonitor stopped; ADB requires a device-mode script (USB-002).
- **§17 GPU:** Stock disables the GPU and ships a DDK 1.12 Android module without userspace (GPU-011).
- **§23 Firmware:** Stock kernels are flower/GCC 4.7.3 builds sharing 119 vendor-only functions with Koriki. Koriki's loader and U-Boot are stock 230309's. GarlicOS's kernel comes from the same tree (FW-016, FW-017, BOOT-010).

## Boot-chain edition (PR #5)

- **§22 Boot:** Complete instruction-level reconstruction of the stock chain from loader block 0 to the Linux jump; BOOT-007 revised (uEnv.txt is applied and the images are loaded by U-Boot `mmcboot`). The Boot ROM boundary is the SRAM service at `0xb4060400`, which is absent from every image (BOOT-012). See [the report](../reports/stock-boot-chain-reconstruction.md) and [`stock-boot-chain.json`](../evidence/firmware/stock-boot-chain.json).
- **§5 Memory:** the final DT gets `/memory reg=<0 ram_size>` (AFI `ddr_size`, else 496 MiB), `/memreserve/` entries for the DTB and the initrd, and initrd `0x2000000` (BOOT-017).
