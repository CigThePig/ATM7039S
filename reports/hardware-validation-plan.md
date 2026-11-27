# Future non-destructive validation plan

> V3 has been executed once (OBS-001, 2026-11-27; [report](v3-first-hardware-capture.md), [retrospective](v3-session-retrospective.md)). V1, V2 and V4–V7 have not. A ranked proposal for what to ask next is in [next-hardware-research.md](next-hardware-research.md); it authorizes nothing.

The owner's working GarlicOS card and failing factory card are excluded. Do not image, repair, repartition or stress either one. None of these procedures is authorization to modify hardware, launch services, write registers, change clocks/voltages or boot an experimental image. Every actual test requires a separate concrete approval. A software read may still have hardware side effects; direct MMIO is not treated as inherently safe.

| Test | Objective / equipment | Prerequisites and procedure | Expected observation | Risks / recovery | Read-only? | Spare card? | Approval |
|---|---|---|---|---|---|---|---|
| V1 Existing logs supplied voluntarily | Establish exact firmware/CPU/kernel; ordinary computer | Analyze a previously saved log file offline; record hash, source and date | Kernel version, command line, CPU bring-up count | No device access; delete derivative output if misattributed | Yes, file-only | Unneeded | Permission to access the provided file |
| V2 Offline public image bundle | Bind boot chain to hashes; disk space and Python/binutils | Download lawful original-RG35XX release; hash; extract components as files without mounting/executing | Bootloader/uImage/DT/module identity; partition entries | Untrusted data/resource use; remove scratch copy; preserve manifest | Yes to downloaded bytes | Unneeded | Already within offline research scope, subject to source availability |
| V3 Existing diagnostic connection | Read CPU masks, cmdline, iomem, logs and final DT | Only if a diagnostic service is already active and separately authorized; use an explicit allowlist: `uname -a`, `cat /proc/cmdline`, `cat /sys/devices/system/cpu/{possible,present,online}`, `cat /proc/iomem`, `dmesg`; collect `/sys/firmware/fdt` only if present | Exact running topology and final mappings, or explicit missing/permission errors | Reads run on active device; logs may be restricted; stop commands and disconnect; no config changes | Commands only read; connection behavior reviewed first | Prefer independently prepared spare-media environment; owner's cards excluded | Explicit approval and actual connection details |
| V4 Spare-card source comparison boot | Compare known boot chain and source kernel | Separate new card, externally backed-up baseline image, reproducible build and reviewed DT; **not run now** | Boot log, conservative peripherals, rollback identity | Boot/power/storage risk; remove spare and return to known working configuration; do not alter working card | No, preparing spare writes storage | Required | Explicit approval after artifact/build review |
| V5 Passive display behavior | Establish mode/refresh evidence; camera or optical measurement | Observe existing normal operation without altering firmware, clocks or power | Measured refresh/scanout characteristics with method uncertainty | Ordinary use only; stop observation | Passive | Not necessary | Approval for observation/equipment arrangement |
| V6 External power observation | Investigate normal charging behavior; approved USB meter | Review meter compatibility; observe normal operation only; no no-card or undervoltage experiments | Time/current/voltage traces of normal use | Meter/cabling may alter negotiation; remove meter and restore original cable | Passive measurement with connection impact | Not necessary | Explicit equipment/test approval |
| V7 UART feasibility review | Identify if safe serial access exists | First obtain trustworthy board photos/documentation; determine signal voltage and pad function offline | Candidate signal/pad references with confidence | Opening, probing, soldering and adapter connection are excluded | Offline review only | Unneeded | Any later physical work needs separate explicit approval |

No recovery method is assumed for a bricked boot chain. Physical reset, service modes and recovery straps have not been documented sufficiently to justify risky writes. Read-only runtime observations should precede any separately approved spare-card experiment, and every result must name board revision, image hash and tool version.

Specific unapproved exclusions: arbitrary `/dev/mem` access, `devmem`, register poking, PMIC reads/writes, `i2cdetect`, clock debug writes, regulator controls, destructive storage tests, no-card power experiments, bootloader flashing, opening/soldering or disabling thermal safeguards.

## Selected baseline and V3 tooling (2026-11-23)

The baseline for physical testing is **Koriki v1.0 on a spare card**, chosen because every boot component is already hash-catalogued and analysed ([selection rationale](test-firmware-selection.md)). V3 no longer depends on a pre-existing diagnostic service: [device/capture.sh](../device/capture.sh) runs the read-only allowlist above from Koriki's SimpleMenu (a `.sh` in `roms/ports` on the SHARE partition) with the default kernel and writes only to its own output folder on the card. See the [operator guide](../device/README.md). The allowlist adds `/proc/config.gz`, `/proc/device-tree`, cpufreq limits, framebuffer attributes and module/mount/partition tables to the commands originally listed. It still excludes power_supply/PMIC attributes, `/dev/mem`, I2C, debugfs and every write. *Superseded in detail by script version 3 (PR #7, below).*

Results enter the repository only through an [observation record](../evidence/schemas/observations.schema.json), which names the approval, board revision, firmware image hash, booted kernel, card modifications and tool hash. `research.py validate` rejects a finding marked `hardware-observation` that does not cite such a record. Running the script is still a separately approved session.

### Offline narrowing for V4 and V7 (2026-11-23)

- **V4 rollback:** [spare-card-risk.md](spare-card-risk.md) shows that, for Koriki v1.0, Linux writes only to the boot card and any TF2 card, and has no NAND driver. Prediction P-NAND verifies this from the V3 capture before any V4 work. TF2 must be empty during tests.
- **V7 UART:** [serial-console.md](../docs/serial-console.md) shows the kernel console index is injected by U-Boot from the runtime AFI record (P-CONSOLE), and records a vendor "UART over TF2" pin state that this DTB does not enable. No adapter, breakout or DTB change is proposed.
- **Pre-registered outcomes:** every V3 question has declared outcomes in [predictions.json](../evidence/predictions.json). The parser can only report one of those outcomes.

## Questions narrowed by the offline firmware continuation

No new hardware procedure was executed. Prefer existing public logs first.

| Objective | Prerequisites and equipment | Minimal later procedure | Outcomes / effect on reference | Risk / recovery / capture |
|---|---|---|---|---|
| CPU discovery versus online policy | Explicit authorization; already booting, identified original RG35XX; existing normal shell/log access | Read cmdline, CPU possible/present/online/offline masks, cpuinfo and saved SMP initialization messages | Separates discovery/software cap from runtime policy; see cpu-topology.md | Low through ordinary exported files; no writes/reboots needed; save raw text with release/board ID |
| Actual RAM and final handoff | Same; final DT exported by an existing kernel if available | Capture boot memory log, `/proc/iomem`, `/proc/meminfo`, final exported DT | Reconciles AFI size with reservations and usable memory; absence of export leaves gap | Low ordinary-file reads; no arbitrary AFI/MMIO dump; capture full context and hash DT |
| Loaded GPU software versus bundled artifacts | Same; driver/log interfaces already available | Read module/version metadata and existing renderer logs; do not run new stress tools initially | Determines whether hash-identified bundled module/library set is actually used | Low read-only files; no services IOCTL experiment; preserve logs and loaded module identity |
| Display ownership/timing | Existing logs/exported framebuffer or DRM metadata | Record current mode, format and memory resources through normal exported interfaces | Narrows panel mode/scanout ownership; cannot establish undocumented electrical timings | Low; do not alter modes/backlight/regulators; record missing interfaces |
| Storage slot mapping | Existing mount table/sysfs and logs | Read block-device ancestry and MMC probe messages | Connects OS device names to controllers; no assumption based on mmcblk numbering alone | Low file reads; do not mount/write/benchmark cards; save ancestry and exact firmware hash |

These procedures require separate owner authorization even if described as low risk. Existing access is a prerequisite, not permission to enable ADB, alter boot arguments or write another card. No procedure begins with raw MMIO, PMIC, clocks or CPU-online writes. Passive UART work still requires established pads/voltages and separate approval; no opening or soldering is implied.

## DRAM observations prepared by PR #6 (not executed)

The [DRAM reconstruction](dram-complete-reconstruction.md) predicts exactly which strings and values a stock or Koriki v1.0 boot produces. The table separates what the existing read-only V3 capture can show from what only an early-boot serial log can show. None of these tests is authorized by this document.

| Priority | Observation | Collected by | Confirms or refutes | What it cannot show |
|---|---|---|---|---|
| 1 | `MemTotal` (`/proc/meminfo`), System RAM ranges (`/proc/iomem`), `/memory` in the final DT | V3 (existing allowlist) | AFI `ddr_size` → U-Boot `/memory <0 0x10000000>` (P-RAM, MEM-010); a 512 MiB or 128 MiB result would refute the single-rank 2 Gb hypothesis | training path, rank retry, memory-test result (MemTotal alone does not prove DRAM training behaviour) |
| 2 | `/proc/cpuinfo`, `/proc/cmdline` (`boot_dev=sd0`, `allenS500=1`), kernel version | V3 | board and boot identity (P-CPU, P-BOOTDEV, P-UENV) | the loader's DRAM decisions |
| 3 | `/proc/device-tree` (final), `dmesg` memory and reservation lines | V3 | `/chosen` initrd placement (P-INITRD), kernel reservations around low memory | `/memreserve/` (not exported by the 3.10 procfs tree, FW-019); DTAR training area and DRAM 0x400 use (needs kernel analysis) |
| 4 | Loader console: `DRAM init mode0,type16,2cs,…` → `Fail:<4 words>;` → `…1cs…` → `Ok:DCU_CFG:0x202c,256MByte Cap.` → `==ddr_test 256 MB ==` → `== ok==`; plus `PMU_CTL3 = 0x…`, `pmu_status = 0x…` | **UART only** (V7; pads and voltage not yet established; opening the device excluded) | cs 2 training failure and cs 1 success (MEM-006, DDR-004), probe result (MEM-009), memory-test result (MEM-007), real DXGSR0 lane words, PMIC flags at boot | nothing after the loader |
| 5 | A suspend/resume cycle: `in s2`, `cpu_resume = …`, `DRAM init mode1,…`, `Ok:…` or `re-wakeup at …` | UART during an ordinary suspend (a separate approval; not part of V3) | MEM-008 and whether data survive (C-RESUME-DRAMRST) | — |

A running Linux system cannot expose the early loader's training-status words or the memory-test output. Those are printed once on the loader's UART and are not stored. V3 confirms only the end result of the handoff.

Additional restrictions for any future DRAM-related session, beyond the exclusions above:

* no memory stress tests;
* no `/dev/mem` reads of the AFI, DMM, uPCTL or PUBL;
* no suspend experiments without a dedicated approval (resume failure powers the device off and re-arms an RTC alarm);
* no card prepared without the `SFVD` marker (BOOT-014: app.bin would rewrite `bootloader.ini`, including the detected DRAM record).

## V3 refresh for the first physical session (PR #7, 2026-11-25)

V3 keeps its meaning: one read-only runtime capture on a spare Koriki v1.0 card. PR #7 upgrades the tooling to **capture script version 3** and re-registers the predictions; it does not authorise running it, and V4 to V7 are unchanged. Details and the go/no-go assessment: [v3-hardware-validation-readiness.md](v3-hardware-validation-readiness.md).

| Area | Version 2 | Version 3 |
|---|---|---|
| Device tree | `tar` of `/proc/device-tree` by base name; parser read only `/memory/reg` and `/chosen/bootargs` by fixed path | Resolved to an approved kernel path (`/proc/device-tree` or `/sys/firmware/devicetree/base`), links elsewhere rejected; relative archive plus an independent `find` listing; parser never extracts, rejects unsafe members, decodes `#address-cells`/`#size-cells`, every memory node and bank, `/reserved-memory`, vendor heaps and `/chosen` initrd |
| Storage | `ls -l` of `/sys/block`, names `mmcblk*` assumed removable | Link targets plus card `type` for every block and MMC device; `removable` is 0 for all MMC disks by design (STOR-002) |
| Reliability | Item loop in a pipeline subshell, unbounded reads, `ok`/`missing`/`error` only, interrupted captures accepted with a warning | Bounded reads, statuses `denied`/`truncated`/`unsupported`/`rejected`, essential-item completeness, write-failure tracking, missing `DONE` quarantines, collision-proof folders, fixed `PATH` |
| Predictions | 9, before PRs #5–#6 | 16 with outcome classes; boot arguments, command-line source, initrd, AFI boot device, strap, memory chain and card configuration added; DRAM training explicitly marked as needing an early serial capture |
| Preflight | Manual hash and `sfvd` checks | `tools/v3_preflight.py` for the package, image, prepared card and mandatory raw card checks before first boot and after preparation |

New offline findings that change what V3 can see: the release kernel uses `/chosen` bootargs unchanged and has no `/proc/config.gz` or `/sys/firmware/fdt` (FW-018); the DTB memory description and the invisibility of `/memreserve/` (FW-019); every-boot `fsck.vfat -a` of `SHARE` and a read-write `/boot` (FW-020); role-based MMC naming (STOR-002); the SimpleMenu launch chain (UI-003); and contradiction **C-BOOTSLOT** on which controller holds the boot card, which V3 decides.
