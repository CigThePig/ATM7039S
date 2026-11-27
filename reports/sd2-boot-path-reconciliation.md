# The SD0/SD2 boot-path discrepancy, resolved (PR #8)

Scope: original RG35XX (ATM7039S), Koriki v1.0 (image `d5bd3007…`, whose loader and U-Boot are byte-identical to Anbernic stock 230309, BOOT-010), and the one physical observation OBS-001. Offline only: no card, register, clock or power state was touched. Findings **BOOT-022, BOOT-023, STOR-003**; revised BOOT-012, BOOT-016, BOOT-017, STOR-002, MMC-001; contradictions **C-BOOTSLOT** and **C-DEVCLK** resolved, **C-PREDRAM-PATH** opened. Machine-readable evidence: [`koriki-v1.0-boot-path.json`](../evidence/firmware/koriki-v1.0-boot-path.json), produced by `tools/boot_chain.py boot-path`.

## 1. The question

PR #5 traced the stock boot chain and concluded that U-Boot loads the kernel with `fatload mmc 0:1`, that `mmc 0` is SD0 at `0xB0230000`, and that a working SD boot therefore requires block-0 boot code 0 (BOOT-012, BOOT-016). OBS-001 then showed Linux mounting `/boot` from SD media on controller `0xB0238000` (SD2), with `boot_dev=sd2` in the command line and the kernel log lines

```
## boot_dev: 0x22
## host_id: 0 boot_dev 22 host->index: 1
## host_id: 2 boot_dev 22 host->index: 0
force sd2(emmc) host emmc_boot_card
mmcblk0: emmc_boot_card SD 58.2 GiB
```

Candidate explanations at the start of this PR:

* **H1** U-Boot's `mmc 0` can be SD2 (for example because an empty SD0 fails to initialise and is skipped).
* **H2** The loader produced a different AFI boot device than reconstructed, and U-Boot took a different branch.
* **H3** Linux renumbers controllers independently, and U-Boot really did load from SD0.
* **H4** The kernel/firmware on the card differ from the pinned image.

## 2. Result in one paragraph

**H2 is what happened, H1 is refuted, H3 is true for Linux but does not explain the command line, and H4 is not needed.** Executing the firmware's own code for every boot code that loader block 0 can write, exactly one path reproduces OBS-001's command line byte for byte: block 0 sees `CMU_DEVCLKEN0` bit 7 and writes **boot code 2**; bootloader.bin makes the AFI **`boot_dev = 0x22`** (otherwise identical, same raw reads); U-Boot's `check_boot_flag` selects **`run emmcboot`**; `emmcargs` sets `devpart = ${emmcdev}:${bootpart}` = **`1:1`**; U-Boot device 1 is **SD2 (`0xB0238000`)**; `owl_boot_fdt_setup` then writes `boot_dev=sd2` and, with the GPIOC6 strap high, `allenS500=1`. The TF1 slot is wired to SD2. The original reconstruction was right about every function it traced, but it assumed TF1 was SD0 and therefore followed the code-0 branch.

## 3. Stage by stage

| # | Stage | What happens on the observed device | How it is known |
|---|---|---|---|
| 1 | Boot ROM | Reads loader block 0 from the TF1 card (on SD2) and leaves SD2's clock gate on (CMU_DEVCLKEN0 bit 7; the mainline S500 driver names bit 7 the SD2 gate) | **Inferred** from stages 2–8. ROM code not available. |
| 2 | Loader block 0 | Bit 7 set → boot code 2 at `0xb4064c00`; ROM read of bootloader.bin (`0x205600`, 40 KiB) | **Reconstructed from instructions** and **reproduced in emulation** (BOOT-012); the bit itself is inferred |
| 3 | bootloader.bin / AFI | Code 2 → AFI `"AFI", mode 0, dev 0x22, uart 3, 115200, ddr_size 256 MiB`; raw reads identical to code 0 (ini `0x202600`, app.bin `0x219200`, U-Boot `0x300000`); console prints `bootdev= 0x22` (ini byte, informational) | **Reproduced in emulation** (`boot_code_map`, `loader_main(boot_code=2)`). AFI bytes **not observed**. |
| 4 | U-Boot boot-device interpretation | `check_boot_flag`: mode 0, dev `0x22` → `bootcmd = run emmcboot`, prints `emmc boot` | **Reproduced in emulation** with the firmware's own AFI getters (BOOT-015) |
| 5 | U-Boot MMC init and selection | `mmc_initialize` → `board_mmc_init`: SD0 registered as `mmc 0` (its `mmc_init` fails if TF2 is empty; it stays registered), SD2 registered as `mmc 1` **only because dev is 0x22**. `emmcboot` → `fatload mmc 1:1` reads `uEnv.txt`, `uImage`, `ramdisk.img`, `kernel.dtb` from SD2. The environment is read from `mmc 1` too, i.e. the boot card at `0x5000`/`0x25000` (zero → default environment) | **Reproduced in emulation** for every SD0/SD2 card-init outcome (BOOT-023); card protocol modelled |
| 6 | Kernel arguments | `image_setup_linux` + `owl_boot_fdt_setup`, GPIOC6 high: `console=ttyS3 earlyprintk clk_ignore_unused selinux=0 init=/init   androidboot.dvfslevel=0x705x allenS500=1 androidboot.bootdev=sd boot_dev=sd2`; initrd `0x2000000–0x23a43b1` | **Reproduced in emulation; equals OBS-001 byte for byte** (BOOT-022). Strap level is an input. |
| 7 | Linux MMC enumeration | `boot_dev=sd2` → `g_boot_dev = 0x22`; `mmc_alloc_host` gives index 0 to the host whose `(reg − 0xB0230000) >> 14` equals `0x22 − 0x20 = 2`, and index ≥ 1 to the others; SD2's card is named `emmc_boot_card` because the vendor driver labels slot 2 "emmc" by design | **Verified from binary and pinned source** (STOR-003), **directly observed** in OBS-001's log and sysfs |
| 8 | Root filesystem | ramdisk `/init` mounts `/dev/mmcblk0p1` as `/boot`, loop-mounts `boot/BATOCERA` read-write as `/` (FW-021) | **Verified from the ramdisk script**, **directly observed** (mount table) |

### Why each hypothesis stands or falls

* **H1 refuted (for U-Boot).** `mmc_create` assigns `block_dev.dev = cur_dev_num++` and links the device *before* `mmc_init` runs, and the failure path never unregisters it (`0x05023a2c`, `0x05024f04`). Executed for AFI `0x20`/`0x22` × SD0 ok/fail × SD2 ok/fail: with `0x22`, SD0 is always `mmc 0` and SD2 always `mmc 1`. With `0x20`, SD2 is never registered at all.
* **H2 established (by reproduction).** Six hypotheses were executed (block-0 codes 0, 2, 4 × strap low/high). Only code 2 + strap high equals the observation. Code 0 gives `boot_dev=sd0` and loads from SD0.
* **H3 true but secondary.** Linux numbering is independent of U-Boot's (it is chosen from `boot_dev=`), which explains `mmcblk0` on SD2 — but the `boot_dev=sd2` term itself can only come from U-Boot's AFI-driven fixup.
* **H4 not needed.** OBS-001's boot files match the catalogue (postflight PASS), the kernel version string matches the catalogued build, and the reproduction uses the pinned image. The raw loader region on the card was *not* checked in OBS-001, so equality of the card's loader with the image is an assumption (it is checked by the new lab before any future boot).

## 4. Physical media, controller, index, role and boot path are five different things

| Concept | Observed device | Where it comes from |
|---|---|---|
| Physical medium | SD card (SDXC, `type` = SD) | card's own registers, via sysfs |
| Controller | SD2, `0xB0238000` | board wiring of TF1 |
| U-Boot device number | `mmc 1` | registration order (SD0 first), BOOT-023 |
| Linux host index / block name | `mmc0` / `mmcblk0` | vendor `mmc_alloc_host`: boot host gets 0, STOR-003 |
| Firmware role label | `emmc_boot_card`, "emmc boot", `emmcboot`, `emmcdev` | vendor reference design (SD2 normally carries eMMC); a name, not a medium |
| Boot-path selection | AFI `boot_dev 0x22` | loader block 0 code 2 ← ROM's clock gate (inferred) |

Earlier records used "sd0", "mmc 0", "mmcblk0" and "TF1" as if they were one thing. They are not.

## 5. Consequences

* **BOOT-016** remains a correct description of the AFI `0x20` path, which this unit does not take. Its statement that `board_mmc_init` registers SD0 then SD2 unconditionally was incomplete (SD2 needs AFI `0x22`).
* **C-DEVCLK** is resolved by inference: the device took the bit-7 branch, matching the mainline name "SD2 gate"; the bit-4 → code 0 branch (mainline "NAND gate") is the one not taken.
* **The U-Boot environment lives on the boot card** (`mmc 1` = SD2 = TF1, byte offsets `0x5000` and `0x25000`, 128 KiB each). It is zero in the image, so the default environment applies. A future tool that writes a U-Boot environment would write to the boot card; nothing in this project does.
* **New open question C-PREDRAM-PATH.** On the code-2 path, the pre-DRAM routine `0xb4069254` also runs its GPIO `0x55aa55aa` ADFU handshake, which is skipped for code 0 (BOOT-021). The DRAM-stage emulation in PR #6 was run for code 0; it should be re-run for code 2. Storage reads and the AFI are already shown identical.
* **TF2 is SD0** by the same logic (`sd_card` on `b0230000` in Koriki's scripts and the driver's slot naming). Not exercised with a card in TF2.
* **For an independent bootloader or Linux:** boot from TF1 means SD2 must be initialised by the replacement stage; a mainline DT for this board should describe TF1 on `mmc@b0238000`.

## 6. What is still not observed

The ROM's media search, the CMU bit value, the AFI bytes, U-Boot's console (`emmc boot`, mmc messages) and the GPIOC6 level were not observed; they are reproduced or inferred. None of them is needed to use the result. Cheapest confirmations, all optional:

1. A future read-only capture could add `/proc/bootdev` (the kernel's `g_boot_dev`; read-only file, but its write handler exists, so the capture must only read it).
2. An early serial log (separately approved) would show `bootdev= 0x22`, `bootmode = 0`, `emmc boot` and the mmc slot messages.

## 7. Reproduce

```sh
python tools/acquire_firmware.py koriki-v1.0-release INPUTS --expand
python tools/boot_chain.py boot-path INPUTS/koriki-v1.0.img out.json --release koriki-v1.0 \
    --sha256 d5bd300740884d80faee2fd3ae70d91f86e6a316610c56efc0e1f7545539d6ae \
    --observation evidence/observations/OBS-001.json        # ~10 s
ATM_FIRMWARE_DIR=INPUTS python -m unittest tests.test_boot_chain -v    # re-derives and compares
```

Kernel side: decompress the uImage's gzip stream (offset 17588, `evidence/firmware/kernel-payload.json`), recover symbols with `tools/kallsyms.py`, and read `mmc_alloc_host` (`0xc049fb28`), `mmc_add_card` (`0xc049f45c`), `acts_mmc_probe` (`0xc0a43724`) and `boot_dev_process` (`0xc0a1bb9c`); the pinned vendor source lines are cited in STOR-003. No firmware bytes or disassembly listings are committed.
