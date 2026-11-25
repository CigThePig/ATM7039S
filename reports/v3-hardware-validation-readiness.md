# V3 hardware validation readiness (PR #7)

Scope: hardware test **V3**, the read-only runtime capture on a spare Koriki v1.0 card, on the **original 2022–2023 RG35XX** (Actions ATM7039S). PR #7 upgrades the capture tooling to **script version 3**. It is not test V7 and changes nothing about V4–V7. Everything here was done offline. No device was touched, and nothing here authorises a session.

Findings added: **FW-018, FW-019, FW-020, STOR-002, UI-003**. Contradiction added: **C-BOOTSLOT**. Predictions: 9 → **16**.

## 1. Executive summary

The version 2 capture would have run, but it could not answer several of the questions PRs #5 and #6 now pose, and some of its answers could have misled:

* **The memory prediction relied on a file the kernel does not have.** P-RAM read `/sys/firmware/fdt` first. The Koriki v1.0 kernel has no such export (FW-018), so P-RAM would always have fallen back to `/proc/iomem`. It would then have reported kernel-accepted RAM as if it were the size the bootloader handed over.
* **Removability was inferred from the name `mmcblk*`.** Every MMC disk reports `removable=0` by kernel design (STOR-002), and eMMC also appears as `mmcblk*`, so P-NAND could not tell an SD card from soldered storage.
* **A partial capture looked complete.** The item loop ran in a pipeline subshell, so nothing could be aggregated. A missing `DONE` marker produced only a warning, and failed reads were not distinguished from denied or truncated ones.
* **P-BOOTDEV hid a real contradiction.** It treated "boot card on `b0238000`" as the matching outcome. PR #5's U-Boot reading puts `mmc 0` on SD0 at `0xb0230000`. Which controller holds TF1 is open (**C-BOOTSLOT**), and it matters for any replacement bootloader.

Version 3 fixes these and adds what PRs #5–#6 make testable after boot: the exact reconstructed command line, how the kernel used it, the `/chosen` initrd location, the AFI boot device and the board strap. It was executed against synthetic trees under dash, bash `--posix`, a host BusyBox, and **Koriki v1.0's own BusyBox 1.36.1 and applets under qemu-user**. It was also run against the real KERNEL.DTB laid out as a procfs tree. A new offline preflight verifies the image, every catalogued component, the `SFVD` marker, the BusyBox applets and the prepared card.

**Assessment: ready for a separately approved first V3 session** (section 11), with the residual uncertainties in section 10. The launch from SimpleMenu, real procfs/sysfs content and real timing have not been observed and cannot be observed without hardware.

## 2. Method

1. Read the V3 lifecycle end to end: firmware selection, image verification, card preparation, launch, capture, copy, authentication, parsing, prediction, evidence record.
2. Downloaded the pinned Koriki v1.0 image through `tools/acquire_firmware.py`, which verifies its size and SHA-256. Read its kernel, DTB, RAM disk, init scripts, launcher and BusyBox as bytes. The kernel symbol table was recovered with `tools/kallsyms.py`. The relevant vendor kernel sources were read at the pinned revision (`rg35xx-cfw/s500_kernel@81cc77b5`).
3. Ran the real script, never a re-implementation, against fixture trees (`tests/capture_fixture.py`), then the real parser. The firmware's BusyBox was run through qemu-user from a sysroot whose files are checked against the rootfs catalogue (`tests/target_busybox.py`).

## 3. Coverage audit

"After boot?" says whether a running Linux can observe the quantity at all.

| Question | v2 evidence | v3 evidence | After boot? | Prediction | Limits / future test |
|---|---|---|---|---|---|
| Final command line = reconstruction (BOOT-017) | `cmdline` (console, uEnv only) | byte comparison with both strap variants; serial term ignored | yes | P-BOOTARGS | ramboot/charger/PRODUCE paths not exercised |
| Does the kernel use `/chosen` bootargs? | none | `cmdline` vs `/chosen/bootargs` vs boot log | yes | P-CMDLINE-SRC | build option itself not exported (no IKCONFIG) |
| uEnv.txt applied (C-UENV) | `init=/init` | same | yes | P-UENV | — |
| AFI boot device / ROM boot code (C-DEVCLK) | not evaluated | `boot_dev=` | yes | P-AFI-BOOTDEV | which clock gate the bit is stays open |
| Board strap GPIOC6 | not evaluated | `allenS500=1` | yes | P-STRAP | variant, not silicon |
| Console UART | ttyS0/3/5 lumped together | ttyS3 singled out | yes | P-CONSOLE | pads/voltage: V7 |
| Bootloader-reported memory | FDT blob (absent), else iomem | every DT memory node, decoded with root cells | yes | P-RAM | physical DRAM size: not observable |
| Kernel-accepted / usable memory | iomem, MemTotal | iomem, boot-log `Memory:` line, MemTotal, vendor carve-out, `mem=` | yes | P-RAM | heap-set selection not traced (FW-019) |
| initrd handoff | none | `/chosen linux,initrd-*`, initrd log lines | partly | P-INITRD | `/memreserve/` not exported by procfs |
| Which controller holds the boot card (C-BOOTSLOT) | `ls -l /sys/block` | sysfs ancestry of the disk mounted at `/boot`, kernel boot-card lines | yes (TF2 empty) | P-BOOTDEV | — |
| Non-removable storage | names | card type per MMC disk, every block device | partly | P-NAND | unenumerated storage stays invisible |
| CPU discovery vs policy (C-CPU) | masks, SCU line | plus cmdline caps, `powersave now`, DT CPU nodes, mask consistency | partly | P-CPU | SCU line only while in the 128 KiB log |
| Running kernel identity | version string | same | yes | P-KERNEL | string, not image hash |
| Kernel configuration | expected `config.gz` | absent expected (FW-018) | — | P-KCONFIG | — |
| Card configuration, overclocking | none | `/boot/uEnv.txt`, `/boot/batocera-boot.conf` hashes | yes | P-CARDCONFIG | large boot files verified on the computer |
| GPU stack | modules, `/proc/pvr/version` | same | yes | P-GPU | no IOCTLs |
| Display baseline | fb0 attributes | plus current mode | yes | — | no mode changes |
| DRAM training, rank retry, memory test, PMIC flags | not addressed | loader-format lines searched for in dmesg | **no** | P-DRAM-LOG | early serial capture only |
| Boot ROM, loader and U-Boot console | — | — | **no** | — | early serial capture only |

Candidates considered and **not** added: `/proc/zoneinfo` (redundant with iomem plus the boot-log totals); `/sys/kernel/debug` and `cpuinfo_cur_freq` (excluded, hardware side effects); card `serial`, `cid`, `csd` and `date` (identifiers); hashing the multi-megabyte boot files on the device (more I/O and access-date updates on a read-write `/boot`; verified on the computer instead); `/var/log/messages` (userspace content, and unnecessary while dmesg starts near boot); `/dev/kmsg` (blocks, and is a device).

## 4. Problems found in the version 2 implementation

| # | Problem | Consequence | Fixed by |
|---|---|---|---|
| 1 | P-RAM used `/sys/firmware/fdt` first; the 3.10 kernel has none (FW-018) | The DT path never ran; iomem would have been reported as the bootloader's size | DT memory from the directory export, five quantities kept separate (§6) |
| 2 | The parser read only `device-tree/memory/reg` and `device-tree/chosen/bootargs` by fixed path, as raw 32-bit words | `memory@0`, multiple banks, two-cell layouts and reserved memory were invisible or misread | Structural analysis with `#address-cells`/`#size-cells` |
| 3 | `tar` of the export by base name, with no path resolution | On a kernel whose `/proc/device-tree` is a link, only the link could be archived | Resolve with `pwd -P`; accept only `/proc/device-tree` or `/sys/firmware/devicetree/base`; reject anything else |
| 4 | Item loop in `printf | while` (a subshell) | No completeness or write-failure tracking was possible | Here-document loop; counters; `capture_status` |
| 5 | Missing `DONE` was only a warning; statuses `ok`/`missing`/`error` only | An interrupted or partial capture could pass as evidence | `DONE` required; `denied`, `truncated`, `unsupported`, `rejected`; essential items |
| 6 | `cat` with no bound | Unlimited output growth on a 256 MiB device | `head -c` to 4 MiB + 1; `truncated` status |
| 7 | `mmcblk*` assumed removable | eMMC indistinguishable from an SD card | Card type from sysfs; MMC disks report `removable=0` by design (STOR-002) |
| 8 | P-BOOTDEV's "match" encoded one side of an unrecognised contradiction | C-BOOTSLOT would have been reported as confirmed | Both outcomes `alternative`; C-BOOTSLOT recorded |
| 9 | P-CONSOLE accepted ttyS0/3/5 alike | A wrong AFI uart_index would have looked like a match | `ttys3` separated |
| 10 | P-KCONFIG expected `/proc/config.gz` | The kernel has no IKCONFIG; absence is the expected result | Expectation corrected |
| 11 | `PATH` inherited from the launcher; date-only folder names | Unknown tool resolution; collisions possible with an unset clock | Fixed `PATH`; PID + counter + `mkdir` without `-p` |
| 12 | Redaction covered `androidboot.serialno=` and colon-separated MACs only; capture errors and stderr were not redacted | `/proc/cpuinfo` Serial, card CIDs, UUIDs and dash-separated MACs could reach summaries | Wider patterns over the whole output; card identifiers never read |
| 13 | Tests replayed canned `ls -l` output | The storage logic was never exercised | Probes run against fixture sysfs trees |
| 14 | The plan said V3 shows `/memreserve/` | Overstated | Corrected (FW-019) |
| 15 | Old fixture used `console=ttyS5 boot_dev=sd2` | Did not test the reconstruction | Fixture follows BOOT-017 |

The parser also accepted a truncated tar silently: Python's `tarfile` treats a cut-off archive as ended. Version 3 requires the end-of-archive blocks and cross-checks every member against an independent `find` listing.

## 5. Firmware facts established for this PR

* **FW-018 (kernel).** `default_command_line` is all zero, so `CONFIG_CMDLINE` is empty. There is no `IKCFG_ST` marker and no ikconfig symbol. `proc_device_tree_*` is present, and there is no `/sys/firmware/fdt` or devicetree sysfs. The log buffer is 128 KiB. The vendor `drivers/of/fdt.c` backport makes the three policies observable at runtime: FROM_BOOTLOADER gives `/proc/cmdline == /chosen/bootargs`, EXTEND gives `CONFIG_CMDLINE + " " + bootargs` (a leading space with an empty built-in), and FORCE ignores bootargs. This answers PR #5's open question about the command-line source for Koriki v1.0.
* **FW-019 (DTB).** Root cells are 1/1. There is one `/memory` node with `<0 0>`, no `/reserved-memory`, no `/memreserve/`, and vendor heap sizes under `/reserved/{tiny,normal}`.
* **FW-020 (every boot).** `S03checkfat` runs `fsck.vfat -aw` on `SHARE`, so an interrupted capture can be "repaired" away on the next boot. `/boot` is mounted read-write. `SHARE` is mounted with vfat defaults, so files carry mode 0755.
* **STOR-002.** The kernel names MMC cards by role (`emmc_boot_card`, `sd_card`, "sd0 as boot card"). Koriki's scripts hard-code the boot card on `b0238000`.
* **UI-003.** SimpleMenu → `invoker.dge` → `cmd_invoker.dge` (bash) → `eval "$path" &`. The script runs by path, so it needs the execute bit and a file name without spaces. There is no terminal and no output on screen.
* **C-BOOTSLOT.** See §1. With TF2 empty, V3 decides it.

## 6. The U-Boot → Linux handoff: predicted versus observable

| Item | Reconstruction (source) | V3 item | If it disagrees | Not determinable from V3 |
|---|---|---|---|---|
| Command line | `console=ttyS3 earlyprintk clk_ignore_unused selinux=0 init=/init   androidboot.dvfslevel=0x705x [allenS500=1] androidboot.bootdev=sd boot_dev=sd0 [androidboot.serialno=…]` (BOOT-017) | `cmdline`, `/chosen/bootargs`, boot log | uEnv.txt changed; another bootargs path (PRODUCE adds `powersave androidboot.mode=upgrade`, charger adds `androidboot.mode=charger`); a different U-Boot | U-Boot's internal decisions not reflected in the string |
| How the kernel uses it | unchanged copy (FW-018) | the same three items | EXTEND (prefix) or FORCE (ignored) | — |
| `init=/init` | applied via mmcboot (BOOT-015/016) | `cmdline` | different AFI boot_mode | — |
| `boot_dev=sd0`, `androidboot.bootdev=sd` | AFI dev 0x20, block-0 code 0 (BOOT-012/013) | `cmdline` | ROM left another clock bit | which gate the bit is (C-DEVCLK) |
| `console=ttyS3` | AFI uart_index 3 (UART-003) | `cmdline` | ini changed; ttyS5 = getter fallback | signal on pads |
| `allenS500=1` | GPIOC6 high (BOOT-011) | `cmdline` | either value is legitimate | board wiring |
| `/memory` | `<0 0x10000000>` at 256 MiB (MEM-010) | DT memory node | 0x1f000000 = U-Boot fallback (no valid AFI size); 128/512/1024 MiB = different detection | physical DRAM, training path |
| initrd | `0x2000000`–`0x23a43b1` in place | `/chosen`, dmesg | different RAMDISK.IMG or placement | `/memreserve/` entries |

Memory is reported as five separate quantities, never merged: (1) physical DRAM (not observable); (2) the AFI size (inferred from 3 unless U-Boot fell back); (3) the DT `/memory` that U-Boot wrote; (4) kernel System RAM and the boot-log total; (5) MemTotal after reservations. P-RAM checks that 4 and 5 fit inside 3. A missing device tree gives `kernel-view-only`, never a capacity result.

**DRAM training evidence.** The rank-training, PHY-error, capacity and `ddr_test` lines are printed by the loader on its UART before Linux exists. Nothing stores them, and the Koriki kernel contains none of these strings (checked). U-Boot output is not in dmesg either. P-DRAM-LOG therefore expects `requires-early-serial`; their absence says nothing about the DRAM reconstruction. The matching patterns use the loader's exact formats, because the bare word `pmu_status` also occurs in a kernel audio symbol name.

## 7. Safety and compatibility

* **Reads:** fixed allowlist of 45 items. 38 are ordinary procfs/sysfs/config files. Two are fixed commands (`uname -a`, `dmesg` without `-c`). Three are bounded sysfs probes (link text plus fixed attribute names, at most 64 entries, safe names only). There is one device-tree archive and its listing. `tools/v3_preflight.py` lints the script for device nodes other than `/dev/null`, mount, module, `dd`, `fsck`, `chmod`, power and clock commands, writes to `/sys` or `/proc`, and excluded interfaces; the test suite checks that the lint catches each.
* **Writes:** one new folder next to the script; `sync`. The capture reads two files on the read-write `/boot`, which can update their FAT access date. Koriki already reads `batocera-boot.conf` on every boot.
* **Side effects not caused by the script:** SimpleMenu may write `scaling_max_freq` when launching an entry (UI-003; value not traced, default 1008000). The capture records `scaling_*` so that this is visible.
* **Shell compatibility:** shellcheck-clean for `sh` and `dash`. It ran cleanly under dash, bash `--posix`, host BusyBox 1.36.1 and **Koriki's BusyBox 1.36.1 ash and applets** under qemu-user. The firmware's BusyBox has every applet the script uses (the preflight reads its applet table). It has no `timeout` applet, so reads are bounded by size, not time; procfs/sysfs reads in the allowlist do not block.
* **Resources:** about 45 short-lived processes plus one per probed entry. Output is roughly 1–1.5 MiB, mostly the tar (real DTB: 203 nodes, 852 properties, under 2 MiB tested). No large buffers.

## 8. Privacy

The raw folder is private: the kernel command line, boot log and `/chosen` contain the board serial number. Version 3 never reads card `serial`, `cid`, `csd` or `date`, and writes a `PRIVATE-README.txt` into the folder. The parser redacts the whole output, including errors and stderr: serial-number assignments in any case and spelling, cpuinfo `Serial` (unless all zero), `SN=`, long hex after `cid`/`serial`, `UUID=`/`PARTUUID=`, UUIDs, and colon- or dash-separated MACs. A redacted value stops at whitespace or quotes, so Markdown and JSON stay intact. The split is explicit: the raw folder is private; `summary.json` and `summary.md` are the shareable products.

## 9. Test results

| Suite | Where it runs | Result |
|---|---|---|
| `tests/test_runtime_capture.py`: reference scenario, device-tree variants (directory, relative and absolute links, escape, absent, `memory@0`, two banks, two nodes, 2/2 cells, malformed reg, reserved memory, conflicting or extended `/chosen`, missing bootargs, tar/index mismatch, reference DTB, FDT blob), tar safety, CPU/memory/storage scenarios, robustness (missing `tar`/`find`/`sha256sum`/`head`, read errors, truncation, permission denied as a non-root user, read-only output, repeated captures, frozen clock, no writes outside output, relative and default output, SimpleMenu-style `eval` launch), tampering, legacy v2 captures, redaction, static safety, observation ledger | CI and locally | 106 pass |
| `tests/test_capture_shells.py`: dash, bash `--posix`, host BusyBox, shellcheck, syntax | CI (BusyBox/shellcheck when installed) | pass |
| same: Koriki BusyBox under qemu | needs `ATM_FIRMWARE_DIR` + qemu-user | pass locally; skipped in CI |
| `tests/test_v3_preflight.py`: synthetic script and card checks | CI | pass |
| same, pinned image and card head | needs `ATM_FIRMWARE_DIR` | pass locally; skipped in CI |
| `tests/test_v3_firmware.py`: re-derives FW-018/019/020, STOR-002, UI-003; real DTB as a procfs tree, captured and compared | needs `ATM_FIRMWARE_DIR` | pass locally; skipped in CI |
| Whole repository (`unittest discover`) | CI: 334 run, 16 skipped; with the Koriki image: 334 run, 5 skipped (stock images not present) | pass |

`research.py validate`, `research.py generate --check`, `render_catalogue.py` and `render_html.py` pass. `tools/v3_preflight.py --image … --archive …` on the pinned download reports 0 FAIL, 0 WARN.

## 10. Remaining uncertainties

1. **The launch has never been observed.** `invoker.dge` was not disassembled. The argument order and working directory are inferred from `cmd_invoker.dge`. The script does not depend on the working directory (it uses `$0`).
2. Real procfs/sysfs content: vendor card names, whether `type` is populated by the vendor MMC stack, `dmesg` wording, and the uid the launcher runs as (Batocera runs as root; a non-root run is reported).
3. FAT behaviour on the device: execute bit, access-date updates, flush on power-off.
4. Timing on the device (qemu is not representative). The operator guide allows three minutes.
5. Whether the SCU line is still in the 128 KiB log at capture time.
6. Which heap set the kernel selects, so MemTotal is not predicted numerically.
7. Whether SimpleMenu writes `scaling_max_freq` for a `#` entry.

## 11. Readiness assessment

**Go for one first V3 capture, subject to:** recorded owner approval; `v3_preflight.py` with 0 FAIL on the image and on the prepared card; a spare card only; TF2 empty; no cable; `overclocking` unset; one launch; power-off from the menu; and the capture copied off **before** the card is booted again.

**No-go** if any preflight FAIL is present, if the `SFVD` check fails, if the entry is absent (do not improvise another launch method), or if anything other than the registered script would run.

**Limitations of the first capture:** it describes one boot of one board under one firmware. It cannot show the Boot ROM, loader or U-Boot output, DRAM training, the memory test, physical DRAM size or `/memreserve/`, and it cannot prove the absence of storage Linux does not enumerate. A matching prediction confirms the end state of the reconstruction, not every step behind it. CI passing is not evidence of physical readiness: the items in §10 remain untested assumptions until the session.
