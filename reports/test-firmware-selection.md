# Baseline firmware for physical testing

**Decision (2026-11-23): use Koriki v1.0 for the original RG35XX (`koriki-rg35xx-v1.0_20231112.img.gz`), booted with its default `/uImage`, on a separate spare microSD card.** The device owner has said any firmware may be installed on a spare card, so the choice is made purely on research value. The owner's working GarlicOS card and failing factory card remain excluded.

## Why this image

A runtime capture only becomes evidence when it can be tied to known bytes. Koriki v1.0 is the only candidate where that link already exists in this repository:

1. **Already fully catalogued.** Whole-image, boot-region, U-Boot, kernel, DTB, ramdisk and selected rootfs hashes are committed in [koriki-v1.0.json](../evidence/firmware/koriki-v1.0.json). The AFI writer, U-Boot getters, kernel version string and PowerVR module/library set were all analysed from these exact bytes ([firmware analysis](firmware-analysis.md), [AFI handoff](../docs/afi-handoff.md)). A capture from this image can confirm or refute those static results directly.
2. **Pinned, public and reproducible.** The image is a GitHub release asset with a recorded size and SHA-256 in [acquisitions.json](../evidence/firmware/acquisitions.json). `tools/acquire_firmware.py` refuses anything else. Anyone can rebuild the same card.
3. **Kernel matches the pinned source tree.** The v1.0 kernel identifies as `Linux version 3.10.37 (ctalon@endymion) (gcc version 4.9.4 (Linaro GCC 4.9-2017.01)) #75 SMP PREEMPT Mon Jul 17 20:23:47 UTC 2023`, a community build in the same lineage as the pinned `rg35xx-cfw/s500_kernel`. Its boot messages (for example the `owl_smp_init_cpus(): ncores` line analysed in [cpu-topology.md](cpu-topology.md)) can therefore be read against source. Later Koriki releases (1.0.2 onwards) say they "changed completely the kernel and init mechanism to resemble the stock one", which is useful later but loses that source correspondence.
4. **A way to run a script without a debug connection.** Koriki v1.0 uses SimpleMenu on a Batocera base. Its shipped configuration lists `.sh` files from `/userdata/roms/ports/` (UI-001), and first boot turns partition 3 into a FAT32 `SHARE` partition that a computer can write to (FW-005). The capture script can therefore run from the menu with the default kernel. The image also ships a separate `/adb_uImage` (build #19, FW-007), so an ADB fallback exists without installing anything outside the release.
5. **Hardware coverage.** The v1.0 release notes say "All hardware revisions should work without requiring bootfixes", and the older V6C boot fix is already catalogued for comparison.

## Alternatives considered

| Candidate | Research value | Why not the baseline |
|---|---|---|
| Koriki/Batocera Lite 1.0.3.1 (2024-01-05, `batocera-rg35xx-rg35xx--20240103.img.gz`) | Newest public RG35XX Koriki build; stock-like kernel | Not yet acquired or catalogued. Its kernel no longer corresponds to the pinned source. **Recommended as the second capture**, to compare stock-like and source-built kernels on the same board. |
| GarlicOS 1.4.9 | The owner's current daily firmware; closest to stock | Distributed through a Patreon post (HTTP 403 to automated fetches), with no public checksum. Kernel is a closed stock-derived binary. GarlicOS 2.x on GitHub does not list the original RG35XX. The owner's own Garlic card is excluded, so there is no reproducible copy to tie a capture to. |
| Anbernic stock firmware | Ground truth for shipped behaviour | Google Drive/WeTransfer links with no version, size or checksum on the official page. No documented shell route; Tinyhack obtained ADB only by replacing the launcher. Worth acquiring and cataloguing later. |
| KNULLI | Active Batocera derivative | KNULLI's RG35XX page says "The RG35XX is currently not supported by KNULLI"; no original-RG35XX image appears in current releases. |
| MinUI (legacy RG35XX) | Runs on an unmodified stock kernel | Repository archived in Nov 2023. Its notes say it "probably won't work" on units received after Feb 2023. No shell route. |
| muOS | Active project | Current device pages list H700 models; no release for the original RG35XX was found. |

## What this does not establish

Choosing Koriki v1.0 does not make its kernel, DT or boot policy the same as stock or GarlicOS. Observations are scoped to "Koriki v1.0 on board revision X". The [CPU topology](cpu-topology.md) question in particular may have firmware-specific answers, which is why a second capture on 1.0.3.1 or stock is recommended before generalising.

## Sources

Retrieved 2026-11-23. Recorded in [sources.json](../evidence/sources.json) as unpinned web pages (`koriki-releases`, `knulli-rg35xx`, `garlic-links`, `anbernic-download`, `minui-legacy`), alongside the existing pinned `koriki`, `cfw-wiki` and `tinyhack` sources.

- Koriki releases: https://github.com/rg35xx-cfw/Koriki/releases
- Koriki RG35XX changelog and FAQ: https://rg35xx-cfw.github.io/1_ChangeLog, https://rg35xx-cfw.github.io/1_FAQ
- KNULLI RG35XX page: https://knulli.org/devices/anbernic/rg35xx/
- GarlicOS links page: https://www.black-seraph.com/ and https://github.com/GarlicOS/buildroot/releases
- Anbernic RG35XX download page: https://win.anbernic.com/download/270.html
- MinUI legacy releases: https://github.com/shauninman/MinUI-Legacy-RG35XX/releases
- Tinyhack stock firmware analysis: https://tinyhack.com/2023/12/31/reverse-engineering-rg35xx-stock-firmware/
