# Spare-card boot: risk and rollback assessment

Covers booting the **unmodified Koriki v1.0 image from a spare card** (V3 baseline) and, later, V4 source-comparison boots. Findings: STOR-001, FW-005, FW-006, FW-007, UI-001, BOOT-006. This is an offline assessment, not authorisation. The owner's GarlicOS and failing factory cards stay excluded.

## Rollback model

Every V3 write in this procedure lands on removable media. The evidence for that:

- **Boot media is the TF1 card.** The ramdisk init mounts `/dev/mmcblk0p1`. Release scripts name `mmcblk0` under `b0238000.mmc/.../emmc_boot_card` and `mmcblk1` under `b0230000.mmc/.../sd_card`. U-Boot loads `uImage`, `ramdisk.img` and `kernel.dtb` from FAT on the card (BOOT-006). Prediction **P-BOOTDEV** checks the controller mapping at runtime.
- **The Linux in this release cannot write NAND.** The DTB's `nand@b0210000` node has no status, but the release kernel contains no NAND compatible string and the rootfs ships no NAND or block modules (STOR-001). Prediction **P-NAND** checks `/proc/partitions` for any non-removable block device.
- **No bootloader is written.** Nothing in V3 touches the raw region before the first partition (`0x200200`, `0x300000`). U-Boot does contain NAND commands; with this boot flow they are not exercised, but that is inferred, not observed.

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

## Residual risks

- Electrical or thermal effects of normal operation are the same as any user running Koriki, but they are not measured here.
- First-boot partitioning can fail on a faulty card. Use a known-good spare and keep the downloaded image to re-flash it.
- The ADB fallback boots a different kernel build (`adb_uImage`, build #19, FW-007). Record it as a modification, and restore `/uImage` afterwards.
- V4, booting a source-built kernel or modified DTB, changes the kernel and boot policy. It needs its own review once a build exists (see [build reproduction](build-reproduction.md)), and P-NAND should have returned `removable-only` first.

## Checklist before V3

1. Owner approval recorded for this session (observation `approval`).
2. Spare card flashed from the hash-verified image; write verified.
3. **TF2 slot empty**, no charger cable, `overclocking` left unset.
4. Boot once and power off from the menu, so first-boot resizing completes.
5. Proceed with [device/README.md](../device/README.md).
