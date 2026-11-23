# Read-only runtime capture (test V3)

`capture.sh` records what a running original RG35XX reports about itself: kernel identity, boot command line, CPU masks, memory map, loaded modules, storage ancestry, framebuffer settings, the kernel's exported device tree and the boot log. It answers the CPU-count and final-memory questions in [cpu-topology.md](../reports/cpu-topology.md) and [afi-handoff.md](../docs/afi-handoff.md) without touching registers, clocks or power.

**Running it on a device is test V3 in the [validation plan](../reports/hardware-validation-plan.md) and needs the device owner's explicit approval for that session.** The repository does not grant it.

## What the script does and does not do

- It reads only the fixed allowlist at the top of `capture.sh` (`sh capture.sh --list` prints it without reading anything). Each entry is an ordinary `/proc` or `/sys` file, or one of four fixed commands: `uname -a`, `ls -l /sys/block`, `ls -l /sys/bus/mmc/devices` and `dmesg`. `dmesg` is run without `-c`, so the log is not cleared.
- It writes only inside a new `atm-capture-<UTC time>-<pid>/` folder, then calls `sync`.
- It never writes to `/sys` or `/proc`, opens `/dev/mem` or I2C devices, mounts anything, loads modules, reads `/proc/kmsg`, or changes CPU, clock, regulator or backlight state.
- It deliberately skips `/sys/class/power_supply` and `cpuinfo_cur_freq`, because reading them can start PMIC or clock-hardware transactions. Both are excluded by the validation plan.
- Missing files are recorded as `missing`. The script does not try alternatives.

The parser rejects a capture if the script's hash is not listed in `capture-versions.json`, or if the recorded allowlist differs from that version. To change the script, add a new version entry. `research.py validate` enforces this.

## Preparing the spare card

Use a new or spare microSD card. Never use the owner's GarlicOS card or the failing factory card. Firmware choice: [test-firmware-selection.md](../reports/test-firmware-selection.md).

1. Acquire and verify the image on a computer. This checks the size and SHA-256 of both the download and the expanded image:
   ```sh
   python tools/acquire_firmware.py koriki-v1.0-release /path/to/inputs --expand
   ```
2. Write `/path/to/inputs/koriki-v1.0.img` to the spare card with a raw imaging tool such as balenaEtcher (which verifies the write) or `dd`. Double-check the target disk first.
3. Boot the handheld once with the card to confirm it starts normally, then power off from the menu.
4. On the computer, copy `device/capture.sh` into the card's `roms/ports/` folder. A file name like `ATM7039S-capture.sh` makes it easy to find in the menu. If no `roms/ports/` folder is visible from the computer, stop and use the ADB route below instead of guessing a location.
5. Record the SHA-256 of the `capture.sh` you copied. It must match an entry in `capture-versions.json`.

## Running it

1. Insert the card, boot, open the **Ports** menu, and launch the capture script. It takes a few seconds. Batocera may briefly show a black screen and then return to the menu.
2. Power off normally from the menu.
3. On the computer, copy the whole `roms/ports/atm-capture-*` folder off the card. Do not edit its contents.

**ADB route (fallback only).** Koriki v1.0 ships `/adb_uImage`. Swapping it for `/uImage` changes the booted kernel, so record `boot_kernel: adb_uImage` and the swap under `modifications`. Then run `adb push capture.sh /tmp/`, `adb shell sh /tmp/capture.sh /tmp`, and `adb pull /tmp/atm-capture-<...>`. Restore the original `/uImage` afterwards.

## Turning a capture into evidence

```sh
python tools/runtime_capture.py /path/to/atm-capture-<...> /tmp/OBS-001.json
```

The parser verifies every item's size and hash. It links `/proc/version` to catalogued kernel builds and the exported FDT to catalogued DTBs. An exported FDT normally includes bootloader fixups, so expect a hash mismatch and compare it property by property. The parser summarises CPU, memory, storage, display, module and kernel-config data, and maps the CPU numbers onto the outcomes pre-registered in `cpu-topology.md`. That mapping is a **hint**, not a finding.

Then:

1. Review the raw capture for anything private. `dmesg` and the MMC listing can include card serial numbers or MAC addresses. By default the raw folder stays outside the repository (record where it is kept in `raw_location`). Commit it only after the owner has reviewed it.
2. Copy the parser output to `evidence/observations/OBS-NNN.json` and add a record to `evidence/observations.json`, following `evidence/schemas/observations.schema.json`. The record names the approval, board revision (silkscreen text, or `unknown`), firmware image hash, booted kernel component, every modification to the card, the capture tool hash and the manifest hash.
3. Only then may a finding use `"validation": "hardware-observation"`, listing the observation in `observations` and citing capture items as evidence: `{"source": "koriki-v1.0-release", "observation": "OBS-001", "item": "cpu-possible"}`.
4. Run `python tools/research.py validate`. It checks schemas, the observation-to-firmware link, the tool version, the manifest hash, that the summary did not come from a test fixture, and that cited capture items exist.
