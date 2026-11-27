# Hardware test V3: read-only runtime capture

`capture.sh` (script version 3) records what a running original RG35XX reports about itself: kernel identity, boot command line, CPU masks, memory map, final device tree, storage ancestry, framebuffer settings, loaded modules and the boot log. On a computer, `tools/runtime_capture.py` checks that nothing was altered and compares the result with what the firmware reconstruction predicts (PRs #3–#6).

**Running it on a device is test V3 in the [validation plan](../reports/hardware-validation-plan.md). It needs the device owner's explicit approval for that session.** Nothing in this repository grants that approval. The [readiness report](../reports/v3-hardware-validation-readiness.md) explains what was checked and what is still uncertain.

**The normal way to run V3 is the lab: double-click `ATM7039S-Lab.cmd` and follow [V3-LAB-QUICKSTART.md](V3-LAB-QUICKSTART.md).** It does every computer-side step below automatically. The fully manual walkthrough, [V3-STEP-BY-STEP.md](V3-STEP-BY-STEP.md), is the fallback when the lab cannot be used.

The whole session is seven steps: verify and prepare a spare card, copy the script, boot normally, run one capture, shut down, copy the results, and analyse them on the computer.

## Before you start

| Requirement | Why |
|---|---|
| An **original 2022–2023 RG35XX** (Actions ATM7039S). Not the RG35XX Plus/H/SP/2024 or any H700 model. | Everything here was reconstructed for the ATM7039S. |
| A **separate spare microSD card**, 8 GB or larger, that you are happy to erase. The image is 4.30 GB, which does not fit on a "4 GB" card. | It will be overwritten. **Never use the owner's GarlicOS card or the failing original card.** Keep both away from the computer while you image. |
| **Koriki v1.0** (`koriki-rg35xx-v1.0_20231112.img.gz`), fetched and checked by the tools below. | It is the only firmware whose every boot component is catalogued here ([why](../reports/test-firmware-selection.md)). |
| Python 3.11 (CI-tested minor version) with `pip install -r requirements-dev.txt -r requirements-firmware.txt`. | For the checks and the analysis. |
| The handheld's battery charged beforehand, and **no charging cable during the test**. | Charging selects a different boot path (240 MHz cap, backlight off). |
| **TF2 (the second card slot) empty.** | Koriki mounts and writes to any card in TF2, and would then look for the script there. TF2 is the SD0 controller; the boot card in TF1 is on SD2 (BOOT-022). |
| **`overclocking` left unset** (never change the CPU setting). | The baseline is the default 1008 MHz cap; anything else is an experiment. |

### What the capture reads, and what it never does

It reads only the fixed list at the top of `capture.sh` (`sh capture.sh --list` prints it without reading anything):

| Group | Items | Purpose |
|---|---|---|
| Identity | `/proc/version`, `uname -a`, `/etc/os-release`, Batocera and Koriki version files | Ties the capture to catalogued kernel and firmware bytes (P-KERNEL). |
| Boot handoff | `/proc/cmdline`, `/proc/device-tree` (archived and listed), `/sys/firmware/fdt` if present, `/boot/uEnv.txt`, `/boot/batocera-boot.conf` | Compares the boot arguments, memory node and RAM-disk location with the reconstruction (P-BOOTARGS, P-CMDLINE-SRC, P-UENV, P-RAM, P-INITRD, P-STRAP, P-AFI-BOOTDEV, P-CARDCONFIG). |
| CPU | `/proc/cpuinfo`, `possible/present/online/offline` masks, `kernel_max`, cpufreq policy values | The two-versus-four-core question (P-CPU). |
| Memory | `/proc/meminfo`, `/proc/iomem` | What Linux accepted and what is left after reservations (P-RAM). |
| Storage | `/proc/partitions`, `/proc/mounts`, link targets and card **type** under `/sys/block`, `/sys/bus/mmc/devices`, `/sys/class/mmc_host` | Which controller holds the card, and whether any non-removable storage is visible (P-BOOTDEV, P-NAND). |
| Display, GPU, modules | `/proc/fb`, `fb0` attributes, `/proc/pvr/version`, `/proc/modules`, `/proc/interrupts` | Baseline for later driver work (P-GPU). |
| Boot log | `dmesg` (read without clearing it) | SCU core count, memory and boot-card messages. |

It writes only inside one new `atm-capture-<time>-<number>-<n>/` folder next to the script, then flushes the card. It never writes to `/sys` or `/proc`, opens nothing under `/dev`, never reads a raw block device, never mounts, loads modules, changes CPU, clock, regulator or backlight state, and deliberately skips battery/PMIC attributes, `cpuinfo_cur_freq`, `/proc/kmsg` and debugfs. It does not read card serial numbers or CIDs. It shows nothing on screen.

### What it cannot tell you

A capture taken after Linux has booted shows what the boot chain **handed over**. It cannot show the Boot ROM, the loader's or U-Boot's own console output, DRAM training, the memory test, or the physical DRAM size. Those need a separately approved early serial capture (prediction P-DRAM-LOG). It also cannot prove that storage Linux does not see is absent.

## 1. Prepare and verify the spare card

1. Fetch and check the image (size and SHA-256 of both the download and the expanded image):
   ```sh
   python tools/acquire_firmware.py koriki-v1.0-release INPUTS --expand
   python tools/v3_preflight.py --image INPUTS/koriki-v1.0.img --archive INPUTS/koriki-v1.0.img.gz --json /private/results/preflight-image.json
   ```
   The preflight must end with **0 FAIL, 0 WARN**. It confirms the loader, U-Boot, kernel, DTBs, RAM disk and boot configuration are the catalogued ones, that the `SFVD` marker is present (without it the loader rewrites part of the card on every boot), and that the image's BusyBox has every command the script needs. It only reads; it never repairs anything.
2. **Identify the right card before writing.** Remove every other memory card and USB drive from the computer. Insert only the spare card. In balenaEtcher, the target list must show one drive of the spare card's size. On Linux, compare `lsblk -o NAME,SIZE,MODEL,TRAN,RM` before and after inserting it; the new removable entry is the card. If in doubt, stop.
3. Write `INPUTS/koriki-v1.0.img` to the card with balenaEtcher (it verifies the write) or `dd`. Do not open or "repair" the card afterwards in any disk utility.
4. Before any boot, follow the mandatory raw-card verification in [Part 3.4](V3-STEP-BY-STEP.md#34-mandatory-raw-boot-region-verification-before-the-first-boot). All three raw checks must PASS. Put the card in **TF1**, leave TF2 empty, no cable. Switch on and wait. The first boot shows a "Resizing Partition — Do not switch off your device!" screen, then the menu. Power off with Volume Up + Power, the documented [Koriki v1.0 shutdown shortcut](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0). A short Power press suspends. This first boot turns partition 3 into a FAT32 partition labelled `SHARE`.
5. Put the card back in the computer. Two partitions appear: the boot partition (with `uImage`, `KERNEL.DTB`, `uEnv.txt`) and `SHARE`. **Change nothing on the boot partition.**
6. On `SHARE`, create the folder `roms/ports/` if it does not exist, and copy `device/capture.sh` into it as **`ATM7039S-capture.sh`**. Copy the file; do not open it in an editor (that can change its line endings and therefore its hash). Use a name with only letters, digits, `.`, `-` and `_`: the launcher evaluates the path as a shell command, so spaces would break it.
7. Check the prepared card:
   ```sh
   python tools/v3_preflight.py --boot-dir /path/to/BOOT --share-dir /path/to/SHARE --json /private/results/preflight-prepared.json
   ```
   Again **0 FAIL, 0 WARN**. It confirms the boot files are unchanged, `overclocking` is unset, exactly one registered script is in `roms/ports`, and no earlier capture folder is left there.
8. Repeat the mandatory raw check after first boot (save `preflight-raw-prepared.json`), then eject safely.

Use the guided Windows `--windows-boot-letter` or POSIX `--card-device` helper. No `dd` or raw dump is required. Save the JSON to a private local folder outside the SD card and project. Stop on any FAIL or unresolved WARN.

## 2. Run the capture

1. Card in TF1, TF2 empty, no cable. Switch on and wait for SimpleMenu.
2. Switch SimpleMenu to the **"apps and games"** section group, open **GAMES**, select **ATM7039S-capture** and launch it **once**.
3. There is no progress screen. The reconstructed launcher is expected to return to the menu when the capture finishes; under a minute is an unmeasured estimate. **Wait at least three minutes** before deciding something is wrong. Do not press buttons in the meantime.

If something goes wrong:

| What you see | What to do |
|---|---|
| No "ATM7039S-capture" entry | Stop. Do not try other ways of starting it. Check on the computer that the file is in `SHARE/roms/ports/` and ends in `.sh`. Launching from this list has not yet been observed on hardware. |
| The menu returns at once | Power off with Volume Up + Power, the documented [Koriki v1.0 shutdown shortcut](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0). A short Power press suspends. On the computer, look for a new `atm-capture-*` folder. If there is none, stop and report. Do not run it again without analysis. |
| Nothing returns after 5 minutes, or the device reboots | Note the time and what was on screen. Use the normal shutdown shortcut if responsive; a forced Power hold is an emergency fallback only and can corrupt pending writes. Copy the card on a computer **before** booting it again (see below). Do not retry. |

Not part of this test: opening other apps or settings, Wi-Fi, ADB, USB cables, charging, sleep/suspend, inserting a TF2 card, changing CPU or display settings, and running the capture "once more to be sure".

## 3. After the capture

1. Power off normally with **Volume Up + Power** (not sleep), confirm the power indicator is off, and wait 10 seconds. A forced hold is not guaranteed safe.
2. Take the card straight to the computer. **Do not boot the handheld with this card again first:** on every boot Koriki runs an automatic `fsck.vfat -a` repair on `SHARE`, which could alter an interrupted capture (FW-020).
3. Copy the whole `SHARE/roms/ports/atm-capture-*` folder to a private folder on the computer. Do not edit, rename or open-and-save anything inside it.
4. Analyse it:
   ```sh
   python tools/runtime_capture.py PATH/atm-capture-... summary.json --report summary.md \
       --reference-dtb PATH/TO/BOOT/KERNEL.DTB
   ```
   Look for **State: authenticated-complete** near the top of `summary.md`. `authenticated-partial` means some essential item is missing (listed); `quarantined` means the capture failed an integrity check and must not be used as evidence (the reason is listed). `--reference-dtb` compares the running device tree with the card's `KERNEL.DTB`, which shows exactly what U-Boot changed.
5. Re-check the card with `--boot-dir`, `--share-dir`, and `--json` (save `preflight-after.json`), then repeat the raw check (`preflight-raw-after.json`). A warning about the new capture folder is expected; report every FAIL or unexpected WARN.

### Privacy

The **raw folder is private**. It contains the board serial number (in the command line, boot log and device tree) and may contain other identifiers. `summary.json` and `summary.md` are redacted (serial numbers, card IDs, UUIDs, MAC addresses) and are what you share. Read them once before sharing anyway. Never commit the raw folder.

### Handing over the evidence

Send `summary.json`, `summary.md`, the six saved preflight JSON files, the board revision if it is already known (otherwise `unknown`; do not open the device to find it), the date, and a note of anything that deviated from this procedure. The repository then records an observation in `evidence/observations.json` (below).

## For maintainers: turning a capture into evidence

1. Copy the parser output to `evidence/observations/OBS-NNN.json` and add a record to `evidence/observations.json` following `evidence/schemas/observations.schema.json`: approval, board revision, firmware image hash, booted kernel component, every card modification (at least "capture.sh copied to roms/ports"), the capture tool hash and the manifest hash.
2. Only then may a finding use `"validation": "hardware-observation"`, listing the observation and citing capture items: `{"source": "koriki-v1.0-release", "observation": "OBS-001", "item": "cmdline"}`.
3. `python tools/research.py validate` checks schemas, the image and tool hashes, the manifest hash, that the summary is authenticated, not from a test fixture or PATH override, and that cited items exist.

Prediction outcomes are hints with a class (`expected`, `alternative`, `unexpected`, `insufficient`, `review`). An `insufficient` outcome is missing information, never a negative result.

### Authentication

The parser rejects (quarantines) a capture if: the script hash is not in `capture-versions.json`; the recorded version or format disagrees with that hash; the allowlist, manifest or any item hash differs; the `DONE` marker is missing; the script reported failed writes; or the device had no SHA-256 tool. Captures from script versions 1–2 remain parseable. Any change to `capture.sh` needs a new version entry with its SHA-256; `research.py validate` enforces this.

### ADB route (fallback only, separate approval)

Koriki v1.0 ships `/adb_uImage`, a different kernel build (FW-007). Using it changes the booted kernel: record `boot_kernel: adb_uImage` and the swap under `modifications`, run `adb push capture.sh /tmp/`, `adb shell sh /tmp/capture.sh /tmp`, `adb pull /tmp/atm-capture-<...>`, and restore `/uImage` afterwards.

### Testing the script without hardware

`ATM_CAPTURE_ROOT=/fixture` reads a synthetic tree (`tests/capture_fixture.py`) instead of `/`, and `ATM_CAPTURE_PATH` replaces `PATH`. Both are recorded in the capture and make it inadmissible as evidence. `tests/test_capture_shells.py` runs the script under dash, bash `--posix`, BusyBox, and Koriki's own BusyBox 1.36.1 under qemu-user when `ATM_FIRMWARE_DIR` holds the pinned image.
