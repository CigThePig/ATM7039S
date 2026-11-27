# V3 first physical capture (OBS-001)

Session date: 2026-11-27 (host-side date; device clock reported 2022 and is not authoritative). The device owner performed the capture on a spare card. No additional hardware work is authorized by this report.

## Evidence and provenance

- [Parser summary](../evidence/observations/OBS-001.json): authenticated-complete, 42 of 45 items OK, all 12 essential items OK, no errors, no fixture or PATH override. The raw capture stays private. The parser result is an integrity check, not independent attestation of procedure or silicon.
- [Pre-capture root filesystem comparison](../evidence/observations/OBS-001-rootfs.json): 27,112 original paths, 27,114 card paths, zero removed paths, two added paths, two changed paths; no existing regular file content hash changed within the diagnostic scope.
- [Postflight](../evidence/observations/OBS-001-postflight.txt): eight boot files match, overclocking unset, capture script matches, rootfs FAIL and expected prior-capture WARN. No post-capture rootfs digest was collected; the same failure category is not proof of identical content.
- Original guide revision c62d504; current main's additional mandatory raw boot checks were not supplied. Original image/prepared preflight logs, dated approval/checklist and complete shutdown notes were not supplied. Board silkscreen unknown (kernel model string V6C is not physical inspection). Do not infer compliance from a parser PASS.

## Observed vs inferred

| Topic | Observed on this firmware | Limits |
|---|---|---|
| CPU | Four ARM part 0xc09 (Cortex-A9) cores possible, present, online; SMP activated four. | Not a silicon-wide guarantee. DT lists only two CPU nodes; investigate mismatch offline. |
| Clock policy | 240–1488 MHz exposed; scaling_max and scaling_cur 1008 MHz, performance governor. | Exposed OPPs are not validated safe limits; no overclocking authorized. |
| Memory | DT and /proc/iomem each describe 256 MiB; MemTotal 237548 KiB; boot log available 150452 KiB; 32 MB vendor reservation and 48 MiB CMA reported. | Distinct quantities; physical capacity, AFI and DRAM training not directly observed. Do not subtract reservations twice. |
| Console | ttyS3 in running cmdline. | No early UART or ROM console observed. |
| Boot | boot_dev=sd2, androidboot.bootdev=sd; /boot mmcblk0p1, SD media, controller 0xb0238000; host_id 2 -> index 0. | Resolves Linux side of C-BOOTSLOT for this session; exact ROM/AFI/U-Boot path not directly observed. |
| Boot arguments | /chosen and /proc/cmdline agree; missing predicted sd0, extra sd2. | Equality does not alone prove exact CONFIG_CMDLINE policy or executed U-Boot branch. |
| Strap | allenS500=1 in cmdline. | Consistent with strap-high reconstruction; not direct GPIO measurement. |
| Initrd | DT initrd bounds match reconstructed addresses; kernel frees 3728 KiB. | No /memreserve/ export or direct U-Boot trace. |
| GPU | pvrsrvkm loaded, DDK 3625561 user/kernel match, SGX revision 115. | Does not establish GPU model, clock or maximum speed independently. |
| Kernel | Linux 3.10.37 #75; /proc/config.gz and /sys/firmware/fdt missing. | No inference that all firmware variants share these properties. |
| Storage | Only physical MMC disk enumerated is SD boot card. | Does not establish absence of fitted but unenumerated NAND/eMMC. |

Prediction ledger: 11 expected, 3 alternative, 2 unexpected. Preserve the original predictions and evaluator output as historical evidence, not as a retroactively corrected score. P-BOOTARGS and P-AFI-BOOTDEV both reflect the same sd0/sd2 discrepancy. P-DRAM-LOG is an expected limitation, not a confirmed mechanism.

## Rootfs discrepancy

The original container SHA-256 matches the catalogue. After first boot the card container hash differed; block comparison reported 779 changed 4 KiB blocks. The local tree comparison found added /run/initctl and /run/utmp, /etc link count 15→16, and /etc/dropbear symlink (/var/run/dropbear) replaced with a directory (mode 040755). The actual pinned S50dropbear script was inspected on the card: when the original symlink is present and removable, it removes it and creates a directory. This explains that change and the parent link count; the /run entries are consistent with init/session bookkeeping but their contents/type were not recorded in the supplied report. No change to the 28 catalogued components. Journal, timestamps, free space, unreferenced inodes and allocation state were outside the tree comparison scope. This is a documented exception for OBS-001, not a new trusted firmware hash and not automatic approval to boot another card.

## Offline follow-up

Trace all boot-code and MMC paths against SD2 evidence before changing the reconstructed boot chain. Preserve competing explanations until supported; use early serial only under a separate approved plan. Fix operator tooling before another physical test: automatic drive discovery, UTF-8, dependency setup, progress, verified local snapshots, resumable checkpoints, readable errors, no raw dumps by default, and no bypass of unknown mismatches. Keep private capture and local caches out of version control.

## Diagnostic implementation

The working local-snapshot and SQLite recovery diagnostic from the session is now in `tools/v3_rootfs_review.py`. It checks source availability before scanning, re-verifies local snapshots, commits checkpoints every 50 paths or five seconds between paths, detects the boot volume on Windows and runs with background CPU priority. The scan can be restarted; partial file copies restart, completed copies and matching checkpoints are reused. The tool produces a private report including added and removed records; a human must review a mismatch against the live card's current hash and scope. No blanket allowlist or bypass is provided. Regression tests use synthetic filesystem nodes; actual Windows integration and pinned firmware testing remain necessary.
