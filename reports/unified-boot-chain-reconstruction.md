# Unified ATM7039S boot-chain reconstruction

## 1. Result

One ARM machine executes block 0, the early loader, its pre-DRAM and DRAM routines, the normal post-DRAM loader and `app.bin`. The machine stops at the loaded U-Boot entry. Bounded U-Boot invocations use the loaded executable and the exact AFI bytes from SRAM. A model runs the selected environment commands against the selected controller's verified image. The loaded files feed U-Boot's actual FDT fixup and Linux jump routines. The final stop precedes the first kernel instruction.

The five-release suite includes SD0 and SD2 references on each image, plus fault and configuration controls on Koriki. [Machine-readable results](../evidence/firmware/unified-boot-chain.json)

## 2. Architecture

`tools/unified_boot_chain.py` schedules the stages. `unified_loader.py` extends the SD2 comparison harness and retains its diagnostic, training and return instrumentation. `unified_environment.py` models the pinned command subset and FAT loads. `unified_uboot.py` executes the AFI consumers and validates the boot-file formats. The original tools and evidence retain their independent entry points.

## 3. Firmware provenance

The acquisition catalogue provides the expected whole-image digest and length. A single open read-only regular file supplies the verified image, loader anchors, ROM sector service, persistent environment reads and FAT files for its run. The suite covers Anbernic 221203, 221223, 230309 and 20231014, and Koriki v1.0. It records the loaded block-0 and loader identities, both configuration records, app.bin and loaded U-Boot identities, and the boot files from each selected partition. Only the named INI, AFI, image-header and device-tree controls modify in-memory inputs.

## 4. Stage graph

| Stages in execution order | Dependency |
| --- | --- |
| ROM boundary → block 0 → loader entry | Block 0 sets the SRAM boot word and requests the loader's sectors. The next stage requires that load and the actual entry. |
| Pre-DRAM → recovery/resume decision | Loader initialization runs on the same registers, SRAM and peripherals. The decision must reach a supported DRAM or resume entry. |
| DRAM and main dispatch | Live instructions perform training, capacity detection, the diagnostic, INI write-back, AFI stores and main's dispatch. Ordered milestones record which subpaths ran. |
| App/U-Boot reads → app.bin → U-Boot entry | The cold dispatch must reach `0xb4065440`. The loader must reach app.bin with a verified U-Boot header and entry argument. |
| AFI and RAM consumers → MMC registration → boot device | Exact AFI, loaded U-Boot payload and inherited pin mux feed bounded ARM invocations. |
| Environment and storage → boot-file validation | Boot flag mutations choose the script. Its executed commands determine controller, partition, file and address. |
| Device tree → Linux entry | Valid image buffers, generated environment and consumed board memory feed U-Boot's fixups. Successful fixups permit the final jump. |

## 5. State-transfer contract

The version 1 envelope hashes canonical JSON covering firmware SHA-256, scenario, stage, execution method, predecessor digest and a stage-specific payload. The orchestrator checks it before invoking the successor. Live loader stages also compare the current CPU and SRAM summary with the recorded predecessor. Runtime state carries the original bytes and mutable emulated hardware. See the [architecture reference](../docs/boot-chain-emulation.md).

## 6. Modeled Boot ROM

The initial sector, clock gate, SP, CPSR and Unicorn CP15 defaults are supplied. The physical ROM contents and CPU state are unknown. The boot-code word starts with an unsupported sentinel. Selector 4 in `r9` models a read-only sector service. It logs LBA, sector count, destination, byte length and digest. The absent ROM is represented as a service boundary.

## 7. Block 0

Clock register `0xb01600a0` bit 7 produces code 2 and bit 4 produces code 0 in the executed block. The write is to `0xb4064c00`, the getter is `0xb40664f0`, and zero can be distinguished from an unwritten word. The firmware requests LBA `0x102b`, 80 sectors to `0xb4065400`, where it then actually transfers.

## 8. Pre-DRAM and DRAM continuity

Main reloads the INI from LBA `0x1013` and executes timer, UART, board pin mux, PMIC detection and PMIC initialization. ARM I2C transfers terminate at the model's PMIC register file. Clock register writes and real timer-based delays run against named synthetic responses. The same CPU and peripheral objects carry GPIO direction/data/pull effects, PMIC writes, the selected record and the real argument and LR into the cold or resume branch.

At `0xb40690b8`, the DDR harness models PHY status, controller transitions and memory aliasing. It retains core return, detected capacity, test outcome, actual SRAM configuration write-back and AFI stores. The five-release 520-run comparison remains the foundation for detailed training and geometry claims. The integration suite adds the earlier real initialization and later consumers.

## 9. AFI transfer

| Path | Exact 16-byte record |
| --- | --- |
| SD0 reference | `414649000020030000c2010000000010` |
| SD2 reference | `414649000022030000c2010000000010` |

These bytes come from executed firmware at `0xb4060300`. They remain unchanged through the loaded U-Boot entry and are injected raw into the consumers. The first three bytes are the magic checked by U-Boot. The fourth is retained, as proven by a separate `0xa5` control. Mode, device, UART index and pad are bytes at +4 through +7. Baud and size are little-endian words at +8 and +12. The reference UART is index 3, pad 0, 115200 baud.

## 10. Loader continuation

The test resumes the live CPU at `0xb4065440`, with its registers, stack, INI and MMIO. The code sets SCTLR.I in Unicorn and executes its storage clock setup. Reads include the 248-sector app span to `0x1000`, the staged U-Boot header at `0x300000` and the image at `0x05000000`. The returned app entry argument is `0x05000040`. The normal path validates the legacy headers and CRCs as research checks in addition to the recorded firmware branches. Localized linear memory after the DRAM test is a model boundary. It preserves mapped bytes and bounds new accesses by the detected capacity.

## 11. app.bin

The live entry saves the incoming target at `0xb4060018`, sets masked SVC mode and retains the inherited SRAM stack on the normal path. It uses configuration globals and a synthetic response to its CHIPID query. It reads the SFVD marker at `0xb4062800`, takes `0x8264` and reaches the saved target via `0x1030`. It leaves the AFI untouched. With the marker cleared in scratch memory, it enters the write-back dispatch `0x806c`. The run records the arguments and stops there. Static writer coordinates remain LBA 4115, 20 sectors, source `0xb4062400`.

The word-aligned scan identifies a direct call at `0x9e8c` to `0x9430`. Its SD0 branch at `0x945c`–`0x9470` can set PULLCTL1 bit 17 while rewriting that word's field. The trace reaches neither the caller nor `0x9430` on the normal SFVD-present path. There are no observed app.bin writes in the pad window for those runs. Reachability under other app configurations remains open.

## 12. U-Boot AFI consumers

The loaded payload executes the six getters and `dram_init`. A console stub stands in for printf. The firmware writes the selected size to `gd+0x34`. Isolated controls show 496 MiB for missing AFI or a size below 8 MiB and acceptance at exactly 8 MiB. Those controls do not enter the integrated boot flow. A normal run requires its size to equal the loader's validated AFI and cold result.

The startup and relocation work before these bounded invocations is modeled. The handoff helper's board memory bank is populated from the value read at `gd+0x34`.

## 13. Environment and MMC

`mmc_initialize` and the registration helpers execute with the embedded U-Boot DTB, the transferred loader pin-mux word and named card-init outcomes. With SD2 as the boot medium and TF2 absent, the SD0 controller is still device 0 and SD2 is device 1. MMC environment storage is device 1, at byte offsets `0x5000` and `0x25000`. If the verified backing image is reachable there, both copies undergo CRC checking before compiled defaults are selected. Valid redundancy arbitration is outside the model and would stop execution.

The executed `check_boot_flag` sets `run mmcboot` for AFI device 0x20 and `run emmcboot` for 0x22. The script then selects MMC device 0 or 1 and partition 1. The vendor's eMMC name describes a role. On OBS-001, the physical card is SD.

## 14. Boot-file loading

The bounded interpreter follows `run`, `if/then/fi`, `test -n`, `setenv`, `echo`, `fatload`, `env import -t` and the final `bootm`. It records mutations and their origins, including imported `uEnv.txt` and the resulting `uenvcmd`. Missing optional `boot.scr` chooses the other branch. A present script would reach unsupported `source` and stop. Required files are validated from the actual buffers requested by `bootm`. Checks cover legacy image CRC, type, compression, ARM zImage header, entry address, FDT structure and reservation boundaries, supported load layout, RAM bounds and occupied overlaps.

## 15. FDT and memory

Actual `image_setup_linux` executes with the loaded DTB, relocated-in-place policy, the loaded ramdisk range, post-script environment, raw AFI and modeled board/global data. The LMB contains the declared RAM bank, in-bank input reservations and the bounded helper scratch range. The model checks occupied input intervals and records generated DT reservations. The real U-Boot relocation and runtime reservation map remain unknown. The in-place path does not allocate external relocation space in these runs.

For Koriki SD2, the resulting FDT starts at `0x03800000`, totals 28800 bytes, and reserves its aligned 0x7000-byte range plus the exact initrd payload. `/memory/reg` reports base 0 and 256 MiB for the reference, 128 or 512 MiB in the alternate cases. The initrd payload is `[0x02000000, 0x023a43b1)`.

## 16. Linux entry

The validated FDT handoff permits `boot_jump_linux` from the same U-Boot helper machine. It receives `images->ep` from the kernel header and uses the actual `images->ft_addr` from the fixups. Bootstage and console calls are stubbed. The actual cleanup instructions run, then Unicorn stops at `0x8000` with `r0=0`, `r1=0` and `r2=0x03800000` on the reference. The modeled CPU is in ARM SVC mode, IRQ/FIQ masked, with MMU and caches disabled. These registers describe the bounded invocation.

## 17. Failure propagation

A terminal stage records its classification and all successors are blocked by it. Early ADFU records the missing ROM-copy request and stops at the jump back to `0xb4060000`, with VBAR `0xffff0000`. A returned initialization error stops at main's recovery dispatch even if AFI stores succeeded. Resume transfer and power-off stop on their own branches. A failed diagnostic that really reaches cold continuation remains visible as a warning. MMC, file, validation, script and AFI faults block the handoff at their respective boundaries.

## 18. Scenario results

The 35 runs reach 17 pre-kernel boundaries and 18 earlier terminals. The suite separates both cold SD references, GPIOC6 and C10 states, secondary card status, 128 and 512 MiB capacity, diagnostic failure, training and ZQ failure, a bounded PHY poll, invalid INI, PMIC and GPIO recovery, two resume paths, loader read failure, SFVD write-back, and storage or transfer faults. The 64 MiB control reaches main’s cold continuation but cannot load the U-Boot destination at 80 MiB. The ROM read request is rejected by the modeled RAM bound.

Both SD references reach the Linux entry boundary for each release. Their AFI device byte differs by medium and the memory size remains 256 MiB. The SD2 cross-release differences follow the actual loaded inputs.

| Release | U-Boot payload SHA-256 prefix | Working DRAM record tail | Initrd end | Variant flag in bootargs |
| --- | --- | --- | --- | --- |
| Stock 221203 | `64c1f45fe80f` | `01010c00` | `0x020a3600` | Absent |
| Stock 221223 | `abafdff1c280` | `01010c00` | `0x020a3600` | Absent |
| Stock 230309 | `e0fdd70d5e6f` | `01010c00` | `0x020a3600` | `allenS500=1` |
| Stock 20231014 | `f71fa81758d9` | `02020900` | `0x020a3600` | `allenS500=1` |
| Koriki v1.0 | `e0fdd70d5e6f` | `01010c00` | `0x023a43b1` | `allenS500=1` |

The 20231014 ODT/drive bytes change the records and DRAM programming while retaining the reference outcome. Koriki uses the 230309 U-Boot payload and different FAT boot files.

## 19. Execution coverage

The stage rows identify continuous execution, execution with stubs, transferred-state execution, synthetic input, independent model or blocked. Static facts such as the app.bin caller and cleanup disassembly are labeled in the corresponding stage evidence. The working CPU controls and actual stop PCs are separate from the physical state in OBS-001. The [architecture reference](../docs/boot-chain-emulation.md) lists each transfer.

## 20. OBS-001 reconciliation

Under the pinned Koriki loader, GPIOC6 high and synthetic serial-number absence, the full command line, chosen bootargs, SD2 controller `0xb0238000`, 256 MiB addressable memory, initrd bounds and ttyS3 agree. The loaded uEnv.txt hash equals the captured file hash. The input DTB and kernel image match the catalogue linked by DT comparison and the running version string. The version string supplies a build link. The post-fixup DTB hash is synthetic, and the physical capture did not expose its reservation block.

Changing GPIOC10 from constant low to constant high, allowing TF2 registration or injecting diagnostic failure with continuation leaves the compared handoff fields the same. The secondary-card case may change Linux device inventory, which is outside this model. GPIOC6 low removes `allenS500=1`. OBS-001 captures no early UART, live AFI, Boot ROM state or physical training measurements. These results strengthen the causal reading of the pinned firmware.

## 21. Findings and remaining questions

`C-PREDRAM-PATH` remains open for medium-specific ROM state and physical timing, pad and memory behavior. The `C-BOOTSLOT` result is supported by the executed boot-flag and selected FAT loads. `C-DEVCLK` is unchanged by a modeled clock-gate input. `C-RESUME-DRAMRST` still requires evidence about electrical behavior. The most useful offline follow-up is to reconstruct U-Boot's startup and relocation reservations, then audit the CHIPID response and MMC environment redundancy under separately identified inputs.

## 22. Reproduction

Use the pinned image filenames in one local directory and the repository's firmware dependencies. These commands only read input files.

```sh
python tools/unified_boot_chain.py list
python tools/unified_boot_chain.py run --firmware-dir FW --scenario sd2-reference --coverage --compare-obs
python tools/unified_boot_chain.py run --firmware-dir FW --scenario diagnostic-failure --detail --output trace.json
python tools/unified_boot_chain.py suite --firmware-dir FW
python tools/unified_boot_chain.py evidence --firmware-dir FW evidence/firmware/unified-boot-chain.json
ATM_FIRMWARE_DIR=FW python -m unittest tests.test_unified_boot_chain -v
```

The reporter uses compact checkpoint summaries in the evidence and full state views and ordered events in local `--detail` output. Evidence hashes identify the first divergent stage and trace checkpoint without storing firmware or raw memory snapshots.
