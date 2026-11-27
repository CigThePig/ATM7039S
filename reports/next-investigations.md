# Prioritized continuation roadmap

Every task begins from the pinned sources and unresolved claims, not a presumed ATM7039S/S500 equivalence. No hardware task below is authorized for execution yet.

| Rank | Concrete task | Expected benefit | Dependencies | Difficulty | Required evidence / completion test | Mode |
|---|---|---|---|---|---|---|
| 1 | Acquire a hash-identified public original-RG35XX boot bundle and component manifest | Anchor all boot claims to actual shipped bytes | Lawful source/download, redistribution review | Moderate | Bootloader/U-Boot/kernel/DT/initrd/modules/userspace hashes, format and release provenance; no execution | Offline |
| 2 | Trace early loader DDR/AFI production and U-Boot fixups | Resolve memory handoff and major closed dependency | Task 1; disassembler and load-address evidence | High | Exact binary hash/offset records; trace DDR size, AFI and final DT changes; distinguish pointer spaces | Offline |
| 3 | Compare selected S500 manual sections against vendor and upstream fields | Turn named offsets into supported register semantics | `s500-pdf` hash; exact source paths | Moderate | Per-field matrix, reset/access evidence on S500, target applicability kept inferred; record differences | Offline |
| 4 | Audit source recipe to complete reproducible old-kernel build | Establish which dependencies can actually build from source | Source/toolchain pins; investigate missing 2600 DTB and boot image names | Moderate–high | Build log/config/toolchain hash, component hashes, no board execution claim | Offline |
| 5 | Resolve CPU masks and final RAM from an existing trustworthy log | Narrow CPU count and actual memory layout | Existing saved log or separately approved diagnostics | Low for log analysis; hardware route pending | Image/board identity, cmdline, SCU count, possible/present/online, final memory resources | Offline first; hardware only with approval |
| 6 | Build a CMU/reset/power-domain compatibility matrix | Unblock most Linux drivers | Manual/source comparison, Task 2/3 | High | Compare masks/parents/gates/acks and silicon-specific branches; no guessed safe rates | Offline |
| 7 | Reconcile MMC DMA routing, slot detect and timing controls | Improve core OS support | CMU/pinctrl/DMA source audit | Moderate | Offset/field/request-ID diff; source unit fixtures; later read-only spare-card transfers under approval | Offline, future hardware |
| 8 | Reconstruct display initialization and framebuffer ownership | Usable modern-kernel route | Memory/power/clock handoff | High | Panel control trace, format/stride/pixel clock units, reserved-memory lifetime, source/binary agreement | Offline, future hardware |
| 9 | Match PowerVR module/userspace ABI and renderer provenance | Preserve achievable acceleration without false open-driver promise | Exact firmware pair; selected DDK 1.14 paths | High | Module/version/IOCTL/allocation/display bridge matrix, licensing; renderer log later | Offline, future hardware |
| 10 | Review reMESA SGX544 compiler/command evidence for transferable knowledge | Avoid duplicating prior reverse engineering | Exact core/DDK/platform comparisons | High | Source-referenced applicability report, no SGX535 command assumptions; identify missing firmware/compiler components | Offline |
| 11 | Recover audio and USB wrapper/PHY dependencies | Complete handheld functionality | PMIC/DMA/display/clock baseline | High | SoC versus external-device boundary, GPIO/polarity/routing, IRQ/clock matrix | Offline, future hardware |
| 12 | Assess safe spare-card validation environment | Enable target observations with rollback | Reviewed images, spare card, explicit permission | Moderate | Concrete artifacts/test script/recovery assessment approved before use; owner's cards excluded | Hardware approval required |

## Additional evidence or equipment worth obtaining

Prefer public boot-only bundles and vendor-origin manuals before more hardware. Exact board-revision photographs already publicly available may resolve fitted parts, but must not be treated as the owner's board. An existing runtime log may answer CPU/RAM questions without firmware changes. A later spare microSD would isolate experiments from the working system. UART equipment should be selected only after pin function and voltage are established; neither opening nor soldering is requested by this roadmap.

The project does not need a firmware rewrite to improve immediately: a reliable image/component manifest, DDR/AFI handoff analysis and a field-by-field S500/ATM7039S compatibility study would remove more uncertainty than speculative driver code.

## Continuation status and revised immediate priorities

1. **Image evidence: completed for one CFW release, partial overall.** Koriki v1.0 and V6C bootfix are catalogued; acquire authenticated stock/Garlic next and compare component hashes.
2. **AFI: partially completed.** Writer, layout, size conversion and getters reconstructed. Trace `0xb4070820` producer, DDR paths and final memory fixups before replacing early boot.
3. **CMU semantics: partially completed.** Ten reviewed gate/reset positions; resolve UART divisor/manual discrepancies and expand dependencies rather than asserting whole-block compatibility.
4. **Builds: unmodified source now builds with GCC 4.9.3 (BUILD-001).** The release kernel comes from a vendor-derived tree with 122 extra functions and a different configuration (FW-008/009). Search done (FW-010): 20 of those functions are the prebuilt `libcidop` archive already in the public tree and 6 are older Actions BSP code. 96 product functions ("allen"-tagged board code, USB upgrade stub, Bluetooth PCM) are in no public tree searched. Koriki 1.0.3.1 build #40 is the same product tree (FW-011); MiaUI's reconstruction recovers 29 of the 96 (FW-012). Early releases catalogued (FW-013): only RetroArch alpha 0.1 and Batocera alpha 0.2 used public-source kernels (GCC 7.3.0); everything from alpha 0.3 is the vendor tree. Alpha 0.1's kernel is now reproduced to 99.92% of bytes from public source (BUILD-002). Next: optionally rebuild the exact Buildroot 2018.11-git toolchain for byte identity, decide whether to ask the Koriki maintainers or send a GPL source request, reconstruct a release-like config from symbols (enable libcidop, Android gadget), and keep the source DTB out of any boot (DT-003).
5. **CPU: investigation documented, unresolved.** Prefer existing logs with final cmdline/SCU/masks; physical tests require separate authorization.
6. **GPU: concrete artifacts acquired, ABI map partial.** Match exact kernel build configuration and bridge layouts to bundled libraries, then trace buffer/display ownership and synchronization. Preserve reMESA attribution.

NAND/media/security/OTP, broad historical SDK archaeology, a complete candidate board DTS and modern-kernel driver implementation were not completed in this phase. The initial long-term roadmap still applies to those dependencies.

## Status after stock-firmware analysis

1. **Rank 1 (boot bundle): completed for stock.** Four releases are hash-pinned. Manufacturer-hash authentication remains impossible (FW-014).
2. **Rank 2 (early loader DDR/AFI): substantially advanced.** The AFI producer, DRAM record and register-level bring-up are documented (MEM-005, DDR-001). Next: symbolic evaluation of the timing computations in `0xb40673f4`, and the Boot ROM interface of block 0.
3. **Rank 9 (PowerVR ABI):** stock adds a DDK 1.12 Android module but no userspace, so it does not help a working stack (GPU-011).
4. **Rank 11 (USB):** stock defaults and the umonitor interface are documented (USB-002); hardware role switching remains a device test.
5. **New:** ~~trace the stock U-Boot path that pre-loads kernel/ramdisk/DTB (BOOT-007)~~ done in PR #5 (BOOT-015/016); resolve the board meaning of the GPIOC6 strap (BOOT-011) from board photographs.

The highest-value continuation is now **recovering the computed DRAM timing values** in the stock loader. With the documented controller/PHY layout, this would give an independently reimplementable DRAM init for the original RG35XX, the single largest remaining closed dependency before U-Boot.

## Status after DRAM timing reconstruction (2026-11-25)

**Done offline** ([report](ddr-timing-reconstruction.md); MEM-006, DDR-002, DDR-003, C-INI-RECORD): every value the stock DDR3 path writes is reproduced by three agreeing methods and traced to a call site and to its inputs (constant, ini field, hardware-detected outcome or unknown reset value). Cold boot uses the second ini record and detects ranks and geometry; the shipped primary record matches the write-back for one ×16 2 Gb rank.

Remaining, in order of value:

1. **Read-only serial log** of a normal stock boot (V1 if a log already exists, otherwise V7 after explicit approval): confirms or falsifies the training-retry and probe hypotheses via the four predicted console lines (report §8). No register access.
2. **DMM and PUBL semantics** for the undocumented constants (report §10), by comparison with any public DesignWare PUBL databook-derived source or a second Actions SoC loader.
3. **Resume path (mode 1)** and the memory test `0xb406631c`, with the same tools (the symbolic interpreter accepts other entries).
4. A clean-room DRAM init (U-Boot SPL style) is now specifiable from DDR-002, but must not be run on hardware without the approvals in the hardware validation plan.

## Status after the boot-chain reconstruction (PR #5, 2026-11-25)

**Done offline** ([report](stock-boot-chain-reconstruction.md); BOOT-012..020, BOOT-007 revised; C-UENV resolved, C-APPBIN, C-DEVCLK, C-OPAQUE). Every link from loader block 0 to the Linux jump is traced in all four stock releases and reproduced by `tools/boot_chain.py`. The kernel, RAM disk and DTB are FAT files loaded by U-Boot `mmcboot`. The only parts not reconstructable offline are the Boot ROM (service `0xb4060400`, media search) and runtime values (DRAM size, GPIOC6, serial number).

Handoff to **PR #6 (DRAM)**:

1. Resume path: block-0/main return-2 branch `0xb40664e4` → `0xb4067094` → mode-1 wrapper `0xb40690d0`, gated by `0xb4070874/0xb4070878`. It skips the AFI write, so also check what U-Boot sees on resume.
2. Memory test `0xb406631c`, called from `0xb4066740` after a successful mode-0 init (stubbed in the boot-chain emulation).
3. The DRAM outcome feeds AFI `ddr_size` → U-Boot `gd->ram_size` → DT `/memory`; the boot-chain tool takes it as `--ram-mib`, so PR #6 results plug in directly.
4. `0xb4066280` write-back plus app.bin's ini persistence (BOOT-014) mean detected DRAM parameters are stored on the card. Treat stored and detected records separately.

Remaining offline items outside DRAM:

1. Check the stock kernel for `CONFIG_CMDLINE`/`CMDLINE_FORCE` (whether `/chosen` bootargs are used as traced).
2. Trace `read_mi_item("SN")` to its storage (the serial-number term).
3. Look for public ATM7039S/S500 Boot ROM documentation to settle C-DEVCLK.

The hardware V3 capture (read-only, approval required) would confirm C-DEVCLK, P-UENV, P-CONSOLE, DRAM size and the strap from `/proc/cmdline`, `/proc/meminfo` and `/proc/device-tree/chosen`.

## Status after the DRAM subsystem reconstruction (PR #6, 2026-11-25)

**Done offline** ([report](dram-complete-reconstruction.md); MEM-007..010, DDR-004..006, BOOT-021; C-PROBE-NOALIAS, C-FAILCODE, C-WRITEBACK-FAIL, C-PREDRAM-9254 resolved; C-RESUME-DRAMRST open):

* resume (mode 1) and its PMIC decision;
* the memory test and its blind spot;
* every poll, bound and failure code;
* rank/bus retries;
* the LPDDR2/LPDDR3-class branch;
* uPCTL+0x148;
* the geometry distinguishability study;
* the DRAM → AFI → U-Boot → `/memory` chain for every outcome;
* `boot_chain.py --dram-scenario`.

The DRAM code is identical in all releases and Koriki v1.0.

Remaining, in order of value:

1. **First hardware observation (V3, read-only, separate approval).** `/proc/cmdline`, `/proc/meminfo`, `/proc/iomem` and the final device tree confirm capacity and the U-Boot handoff. They do not show training.
2. **Read-only stock boot log over UART (V7, separate approval).** The only way to see the training retry, `Ok:DCU_CFG:0x202c,256MByte Cap.`, `==ddr_test 256 MB ==` / `== ok==` and the PMIC lines (`PMU_CTL3`, `pmu_status`).
3. **Offline: the stock kernel's suspend code.** Find who writes PMIC regs 8/0x5d and PMU_CTL3 bit 4, and what Linux reserves around DRAM 0x400 and the DTAR training address.
4. **Offline: PUBL v1 semantics** for PIR bit 5 in resume (C-RESUME-DRAMRST), DSGCR/ACIOCR/DXCCR fields, PUBL+0x3fc and the DMM block, from any vendor databook or an older Synopsys-PUBL driver.
5. **Offline: ATC260x PMIC register meanings** for the pre-DRAM regulator writes.
6. A clean-room DDR3 stage can now be written from DDR-002 and §13.1 of the report. It must not run on hardware without the approvals in the validation plan.

## Status after the V3 refresh (PR #7, 2026-11-25)

**Done offline** ([readiness report](v3-hardware-validation-readiness.md); FW-018..020, STOR-002, UI-003; C-BOOTSLOT opened). Capture script version 3, the parser, 16 pre-registered predictions and `tools/v3_preflight.py` are ready for an approved V3 session; the script was run under Koriki v1.0's own BusyBox through qemu. The PR #5 open item "check the stock kernel for `CONFIG_CMDLINE`/`CMDLINE_FORCE`" is answered for Koriki v1.0: the built-in command line is empty (FW-018), and V3's P-CMDLINE-SRC distinguishes FROM_BOOTLOADER, EXTEND and FORCE at runtime.

Remaining, in order of value:

1. **The approved V3 session itself** (separate owner approval): one capture settles P-BOOTARGS, P-CMDLINE-SRC, P-RAM, P-INITRD, P-AFI-BOOTDEV, P-STRAP and C-BOOTSLOT at once.
2. **Offline: trace U-Boot's MMC device numbering** against the runtime answer to C-BOOTSLOT (registration order, SD0 initialisation failure with TF2 empty, `board_mmc_init`), so a replacement bootloader reads the right controller.
3. **Offline: which vendor heap set (`/reserved/tiny` or `/reserved/normal`) the kernel selects**, and whether carve-outs are removed from or reserved inside System RAM, to predict MemTotal numerically.
4. **Offline: disassemble `invoker.dge`** to confirm the arguments and working directory it gives `cmd_invoker.dge` (UI-003).
5. Early serial capture (V7 review first) for everything P-DRAM-LOG marks as unobservable from Linux.
