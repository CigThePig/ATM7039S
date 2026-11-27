# What else OBS-001 tells us (PR #8)

The 16 preregistered predictions (kept unchanged as historical evidence: 11 expected, 3 alternative, 2 unexpected) cover only part of the redacted summary. This report reads the rest of it against the pinned Koriki v1.0 binaries. Everything here is about **one unit, one boot, one firmware**. Findings: CPU-003, CLK-006, MEM-011, MAP-002, FW-021 (plus the boot-path findings in [sd2-boot-path-reconciliation.md](sd2-boot-path-reconciliation.md)).

## CPU and SMP (CPU-003)

| Observation | Explanation | Status |
|---|---|---|
| DT has `cpu@0` and `cpu@1` only, yet four CPUs run | The vendor `owl_smp_init_cpus` takes the count from the Cortex-A9 SCU (`scu_get_core_count`), not the DT. It clips to `nr_cpu_ids` (CONFIG_NR_CPUS=4, CPU-001) and forces 2 only with `powersave` (CPU-002). The DT cpu nodes are used by cpufreq (`cpu@0` carries `cpuvdd-supply` and `transition-latency`). | verified (binary + source + observation) |
| `ncores 4`, MPIDR `0x80000000–3`, possible/present/online `0-3`, kernel_max 3 | Four Cortex-A9 r4p1 cores (implementer `0x41`, part `0xc09`, variant `0x4`, revision 1; NEON, VFPv3), single cluster | observed |
| PRODUCE/charger paths | U-Boot appends `powersave` on PRODUCE (BOOT-017); then only two cores would be possible | static, not observed |

**Did offline research underestimate the CPU?** No: CPU-001/002 already allowed four. What was missing was the runtime fact, now observed. For **mainline Linux** the DT matters: mainline enumerates CPUs from `/cpus`, so a future DT must list four `cpu` nodes (and the S500 SMP enable method). The vendor kernel's two-node DT would give a mainline kernel two CPUs.

## Clock and DVFS (CLK-006)

* The ten exposed frequencies are one table, `cpu0_table` at `0xc0ad5b70` in the Koriki kernel: **240–1488 MHz with requested voltages 975–1375 mV**. The pinned vendor source has different per-`dvfslevel` tables that stop at 1104 MHz, so the Koriki build is modified.
* **The 1008 MHz cap is userspace.** `/etc/init.d/S02overclock` writes `scaling_max_freq` for cpu0–3 from `batocera-boot.conf` `overclocking` (unset → 1008000). The ramdisk `/init` sets the `performance` governor. Neither the bootloader nor the kernel imposes 1008 MHz.
* **`androidboot.dvfslevel=0x705x`** is a constant string U-Boot appends; no consumer of that argument was found in this kernel. The kernel's `asoc_get_dvfslevel` is a separate (chip-ID based) mechanism; whether it affects this build's single table was not traced.
* **Not established:** PLL configuration at each step, actual rail voltages, thermal behaviour, stability or safe limits. **No overclocking was performed or is authorized.** Future work, if ever approved separately: measure temperature and stability at the existing 1008 MHz first; treat table entries above it as untested software settings, not capabilities.

## Memory (MEM-011)

| Quantity | Value | Meaning |
|---|---|---|
| DT `/memory`, iomem System RAM | 256 MiB `0x0–0x0fffffff` | what U-Boot handed over (AFI `ddr_size`) |
| Kernel `Memory: 256MB` | 256 MiB | same bank |
| `150452k available, 111692k reserved` | early boot | free pages after kernel image, initrd, vendor 32 MB, 48 MiB CMA, page tables |
| `MemTotal` | 237548 kB | later: initrd (3728 kB) and init memory freed, CMA pages returned to the allocator (still counted; `CmaFree` 37572 kB) |
| `Reserved memory 32MB` | vendor reservation | inside the 256 MiB |
| CMA 48 MiB at `0x0a400000` | contiguous pool for display/video | inside the 256 MiB |
| `SwapTotal` 524284 kB | the 512 MiB card partition | not RAM |

The early-vs-runtime difference (87,096 kB) is CMA (49,152 kB) + initrd (3,728 kB) + ~34 MiB of reservations later released or counted differently; the exact split was not traced. For a **future minimal OS** the relevant number is the 256 MiB handed over; the 32 MB vendor block and the CMA size are vendor-kernel choices, not hardware facts, and the physical DRAM size and training remain unobservable after boot (MEM-006).

## GPU and multimedia

* `pvrsrvkm` 1.14.3625561 loaded; user/kernel DDK 3625561 match; `SGX revision = 115`; the DDK string says `omap_linux` (the vendor built from TI's OMAP DDK flavour). DT: `gpu@b0300000`, 64 KiB, `actions,atm7039c-gpu`, SPI 3.
* No GPU entry appears in `/proc/iomem` (the module maps its region without claiming it), so the absence of an iomem line is not evidence of anything.
* Display: `owlfb` fb0 and fb1, mode `U:640x480p-56`, virtual 640×960 (double-buffered), 32 bpp, stride 2560. DE at `0xb02e0000`; VDE `0xb0280000`, VCE `0xb0288000`, DMA `0xb0260000` (four interrupts), HDMI `0xb02c0000` — all claimed by drivers.
* **Not established:** the exact GPU model, its clock, or whether "revision 115" maps to an SGX544 core revision. These need the GPU dossier's open items (GPU-008).

## Hardware resource map (MAP-002)

All 16 MMIO resources Linux claimed lie inside blocks already in the canonical model; 14 match a block's base and size exactly (owl-serial.0 claims 4 KiB of its 8 KiB block; dwc3.0 sits inside the USB block). **No new or conflicting ranges.** Only `serial@b0120000` is claimed although the console is ttyS3 (`b0126000`); that is a driver-registration detail, not evidence about UART hardware. No register definitions were added: a claimed range says what a driver asked for, not which registers exist.

## Kernel and firmware facts

* Linux 3.10.37 #75, GCC 4.9.4 (Linaro 2017.01), built 2023-07-17 by `ctalon@endymion` (the Koriki build host; public, in the firmware). No `/proc/config.gz` and no `/sys/firmware/fdt` (FW-018/019 predicted this).
* Buildroot 2023.05.1 userspace; `koriki-version.txt` says **1.2** although the release is tagged v1.0 (the file is catalogued; the label difference is the release's own).
* Root filesystem mounted twice read-write (FW-021): see the rootfs section of [the retrospective](v3-session-retrospective.md).

## Privacy review of the committed summary

Checked: no serial number (cpuinfo `Serial` is redacted, no `androidboot.serialno`), no card CID or serial (only the SD manufacturer ID `0x0000c4` and OEM ID `0x4254`, which identify a card *brand*, not a card), no MAC or IP address, no hostname beyond the firmware's own `buildroot`, no user paths. One cosmetic issue: catalogue paths in `release_link` were written with Windows backslashes; the parser now writes POSIX paths (the committed OBS-001 summary is left as recorded).
