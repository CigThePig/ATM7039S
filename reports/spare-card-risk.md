# Spare-card boot: risk and rollback assessment

Covers booting the **unmodified Koriki v1.0 image from a spare card** (V3 baseline) and, later, V4 source-comparison boots. Findings: STOR-001, FW-005, FW-006, FW-007, UI-001, BOOT-006, BOOT-014. This is an offline assessment, not authorisation. The owner's GarlicOS and failing factory cards stay excluded.

## Rollback model

Every V3 write in this procedure lands on removable media. The evidence for that:

- **Boot media is the TF1 card.** The ramdisk init mounts `/dev/mmcblk0p1`. Release scripts name `mmcblk0` under `b0238000.mmc/.../emmc_boot_card` and `mmcblk1` under `b0230000.mmc/.../sd_card`. U-Boot loads `uImage`, `ramdisk.img` and `kernel.dtb` from FAT on the card (BOOT-006). Prediction **P-BOOTDEV** checks the controller mapping at runtime.
- **The Linux in this release cannot write NAND.** The DTB's `nand@b0210000` node has no status, but the release kernel contains no NAND compatible string and the rootfs ships no NAND or block modules (STOR-001). Prediction **P-NAND** checks `/proc/partitions` for any non-removable block device.
- **No bootloader is written, provided the `SFVD` marker is present.** Nothing in the V3 *procedure* touches the raw region before the first partition (`0x200200`, `0x300000`). The *firmware*, however, can: on every boot where the 4-byte magic `SFVD` is missing from `bootloader.ini`+0x400 (disk `0x202a00`), app.bin writes 20 sectors from SRAM to disk `0x202600`–`0x204e00` (BOOT-014; see below). The hash-verified Koriki v1.0 image has the marker (`SFVD`, `0xc582bb73`), so the unmodified baseline does not write there. U-Boot does contain NAND commands; with this boot flow they are not exercised, but that is inferred, not observed.

So removing the spare card and reinserting the owner's card should restore the previous state, **unless** the board has writable non-removable storage that something other than this Linux writes to. Nothing found so far suggests that, but it is not ruled out. P-NAND is the first check. If P-NAND reports `other-block-device`, stop and reassess before any further boot.

## What the baseline firmware itself changes

These are Koriki behaviours on every boot, separate from the capture tool (FW-005, FW-006):

| Behaviour | Where it writes | Control |
|---|---|---|
| First boot: resize partition 3, retype to FAT32, format `SHARE` | Spare card only | Expected; boot once before copying files |
| Mount TF2's last partition as `/userdata` and copy default folders | **Any card in TF2** | **Leave TF2 empty** |
| `/boot/boot/reboot` marker each boot | Spare card FAT | Harmless |
| Governor `performance`, `scaling_max_freq` from `overclocking` in `batocera-boot.conf` (default 1008000 kHz, up to 1488000) | Runtime cpufreq | **Leave `overclocking` unset**; the default applies |
| Charging at boot: interactive governor, 240 MHz cap, backlight off, wait for power key | Runtime | **Boot on battery with no cable**, for a predictable path |
| MMC power control `on`, noop scheduler | Runtime sysfs | Baseline behaviour |
| USB gadget modules, `idpin_debug=1` (S01adb) | Runtime sysfs | Baseline behaviour; ADB route uses this |
| SSH (dropbear) unless `system.ssh.enabled=0` | Network service | Only reachable with a network adapter; none is used in V3 |

Whether 1008000 kHz equals the stock frequency limit is unverified. Using an overclock setting would be an experiment, not a baseline.

## Loader write-back (`SFVD` condition)

The stock loader, which Koriki v1.0 uses byte for byte, can rewrite part of its own raw region on the card. This is the one firmware-initiated write outside the partitions (BOOT-014, BOOT-019; [boot-chain report](stock-boot-chain-reconstruction.md) §5).

| Item | Value |
|---|---|
| Trigger | The 32-bit word at SRAM `0xb4062800` (bootloader.ini+0x400, disk `0x202a00`) is not `SFVD` (`0x44564653`). Only the magic is compared; the value after it is not checked. It is evaluated on **every** boot, not only the first |
| Writer | app.bin `0x806c` → MMC block writer `0x851c` (CMD24/25, CMD12), after the chip-identity check and before U-Boot starts |
| What is written | 20 sectors (10 KiB) from SRAM `0xb4062400` to disk sector `0x1013` = `0x202600` (the whole `bootloader.ini`) |
| Content | The marker plus `0xc582bb73`; ini `0x0–0x1000` as reloaded, with the DRAM write-back record from detection (MEM-006); ini `0x1000–0x2800` as **whatever SRAM held** (on the SD path that part is never loaded from the card) |
| Not touched | bootloader.bin code, app.bin, U-Boot, partitions. The write is outside every checksummed block, so the loader still validates afterwards |
| Baseline status | Verified offline: the hash-verified Koriki v1.0 image (`d5bd3007…`) and all four stock images hold `SFVD 0xc582bb73` at disk `0x202a00`; Koriki's 20 ini sectors equal stock 230309's. **No write is expected for V3.** This is static analysis, not an observation |

**For modified boot images:**

* Any image whose `bootloader.ini` lacks the marker gets its ini rewritten on first boot. This happens if it was rebuilt from a vendor `bootloader.img`, zeroed, re-packed by a tool, or has a regenerated ini.
* After a rewrite, a card is no longer byte-identical to its image: reflash comparisons, card hashes and DRAM-record observations change.
* The rewritten ini `0x1400–0x2800` holds per-boot SRAM contents. That is where the per-release "opaque" bytes come from.
* Keep the 10 KiB at `0x202600` byte-identical to a verified image unless the write-back is itself the subject of the test.
* Check before flashing, offline:

  ```sh
  python tools/boot_chain.py sfvd IMAGE   # exit 0 = marker present, 1 = app.bin would rewrite the ini
  ```

* A replacement loader that skips app.bin removes this write. One that keeps app.bin must preserve the marker.

## Residual risks

- Electrical or thermal effects of normal operation are the same as any user running Koriki, but they are not measured here.
- First-boot partitioning can fail on a faulty card. Use a known-good spare and keep the downloaded image to re-flash it.
- The ADB fallback boots a different kernel build (`adb_uImage`, build #19, FW-007). Record it as a modification, and restore `/uImage` afterwards.
- **Do not boot the source-built DTB as is.** It adds `vdd-core-dcdc`/`vdd-gpu-dcdc` regulator nodes and a GPU supply that the release DTB lacks (DT-003). Letting Linux drive core and GPU voltages differently from shipping firmware is an electrical risk, not just a software one.
- V4, booting a source-built kernel or modified DTB, changes the kernel and boot policy. A build now exists but has not been booted; it runs a different configuration from the release and needs its own review (see [build reproduction](build-reproduction.md)), and P-NAND should have returned `removable-only` first.

## Checklist before V3

1. Owner approval recorded for this session (observation `approval`).
2. Spare card flashed from the hash-verified image; write verified. Confirm `python tools/boot_chain.py sfvd` reports the marker for the image (it does for Koriki v1.0).
3. **TF2 slot empty**, no charger cable, `overclocking` left unset.
4. Boot once and power off from the menu, so first-boot resizing completes.
5. Proceed with [device/README.md](../device/README.md).
