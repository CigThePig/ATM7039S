# Serial console: offline evidence

Scope: **Koriki v1.0** release bytes plus the pinned vendor kernel and U-Boot source. Findings: UART-001, UART-002, BOOT-006, STOR-001. No board was opened, probed or connected. This page narrows test V7 (UART feasibility review) and does not authorise any physical work.

## How the console is chosen

| Layer | Evidence | Effect |
|---|---|---|
| `uEnv.txt` | `bootargs=earlyprintk clk_ignore_unused selinux=0 init=/init` | **Applied (C-UENV resolved offline; confirmed by OBS-001).** `check_boot_flag` replaces `bootcmd=run ramboot` with `run mmcboot` (AFI 0x20) or `run emmcboot` (AFI 0x22, the observed unit); both import `uEnv.txt` before loading the images (BOOT-015/016/022). |
| Release DTB `/chosen` | `bootargs = "earlyprintk clk_ignore_unused selinux=0"` | No `console=`; this is the base command line U-Boot extends if `uEnv.txt` is not applied |
| U-Boot environment | `console=ttyS2,115200`, `baudrate=115200`, `stdout=serial` | U-Boot's own variable; not referenced by the boot commands found |
| U-Boot FDT fixup | Release binary contains `console=ttyS%d`; source `owl_boot_fdt.c:181–183` prepends `console=ttyS<AFI uart_index>` | **The kernel console index comes from the early loader's AFI record at runtime** |
| AFI producer | Early routine copies `uart_index` from `0xb407082c` (BOOT-004) | Emulating the stock loader on the shipped `bootloader.ini` gives index 3, so the reconstructed kernel console is `ttyS3` (BOOT-013, BOOT-017) |
| Fallback | `owl_afi.c:33–40` returns 5 when the AFI magic is missing | Source behaviour; release equivalence unproven |
| Userspace | `/etc/inittab`: `getty -L console 0 vt100` | A login prompt is offered on whatever `console=` selects |

The release DTB enables **UART0, UART3 and UART5** and disables UART1, 2, 4 and 6. If the runtime index is 0, 3 or 5, the kernel console has a configured controller. If it is 2, which matches U-Boot's environment default, the kernel has no enabled controller for it. Prediction **P-CONSOLE** in `evidence/predictions.json` records these outcomes. The V3 capture's `/proc/cmdline` settles it with no extra procedure.

## UART over the SD slot (lead only)

> PR #8: OBS-001 shows the console is `ttyS3` (UART3, AFI `uart_pad` 0) and that TF2 is the SD0 controller. The pin-sharing lead below concerns **UART5** on SD0's pins, so a breakout in TF2 would most likely not carry the boot console (inference; see [next-hardware-research.md](../reports/next-hardware-research.md)).

The second card controller, `mmc@b0230000`, has a second pinctrl state named `share_uart2_5`. It selects a `uart5` function on pin groups `mfp2_19_17` and `mfp2_16_14` while keeping SD0 command and clock. Release scripts expose this controller as `mmcblk1` (`sd_card`), which is the TF2 slot. The vendor `gl520x_mmc` driver defines `PINCTRL_UART_PIN "share_uart2_5"`, but switches to it only when the node carries `sdio_uart_supported`. **The Koriki v1.0 DTB does not carry that property**, so Linux on this release does not route UART5 to TF2.

This points to a vendor debug pattern where UART signals share pins with a card slot. If it works on this board, a passive microSD breakout in TF2 could reach a console without opening the case. That has **not** been established:

- the early loader and U-Boot may or may not use these pads (the AFI also carries a `uart_pad` byte);
- which SD contacts carry TX/RX has not been mapped from the pin groups;
- the signal voltage was not measured (the slot supply is described as `sd_vcc`);
- enabling it in Linux would need a modified DTB, which is a boot modification and needs separate approval.

## What to do with this

1. Read `console=` and `boot_dev=` from the V3 capture. This needs no new permission beyond V3.
2. If the console is on UART5, map `mfp2_19_17`/`mfp2_16_14` to pads offline using the pinned `pinctrl_data-atm7059.c`, before considering any adapter.
3. Any breakout, adapter, voltage measurement or DTB change remains a separate, explicitly approved procedure under V7. The owner's cards are never used.

`/proc/cmdline` on this firmware is expected to include `androidboot.serialno=<board serial>` (BOOT-006). The capture parser redacts it from summaries. The raw capture keeps it, so review the raw files before sharing them.

## Stock firmware update (UART-003)

The early loader's own configuration settles the AFI `uart_index` statically. Every examined loader carries `uart_index=3`, `uart_pad=0` and `115200` in `bootloader.ini` (+0x0e/+0x0f/+0x10): stock 221203, 221223, 230309, 20231014 and Koriki v1.0 (byte-identical to 230309). Loader routine `0xb4065ff8` copies them into the parameter block from which the AFI is written. Both the stock and Koriki DTBs enable UART3 (`0xb0126000`), so the expected kernel console is **`ttyS3`**. Stock `default.prop` sets `ro.debuggable=1`, which starts a root `console` shell service (USB-002). P-CONSOLE is left as pre-registered; `/proc/cmdline` from the V3 capture still decides it. See the [stock dossier](../reports/anbernic-stock-reverse-engineering.md).

## Loader UART initialization (PR #9, UART-004)

The early loader sets UART3 up itself, before DRAM init, for both boot codes:

* clock gate `0xb01600a4` bit 19;
* reset pulse `0xb01600ac` bit 15;
* `0xb0126000` := `0x8003`;
* divider `0xb01600b0` := 25, which is 24 MHz/(8·26) ≈ 115385 baud if the clock is 24 MHz.

Its table entry for UART3/pad 0 contains **no pin-mux write**, so the loader does not choose the UART3 pins. They come from Boot ROM or reset state (or from the later board MFP write), and which balls carry them remains unknown. TX polling is unbounded. Everything the loader prints before DRAM is listed in `evidence/firmware/sd2-predram.json` (`runs.code2.printed`): `row_col 72`, `ddr_cap 256`, `bootdev= 0x22`, `scan 1`, `g_current_bus = 1`, `--pmu- ok`, the PMIC reg 0x11 echo, `PMU_CTL3 …`, `pmu_status = 0x0`. These are emulation outputs, not observed console text. Nothing here proposes a connection.

## Update from the boot-chain reconstruction (PR #5)

Emulating the whole pre-kernel chain on all four stock images and Koriki v1.0 gives AFI `uart_index` 3 and the final command line `console=ttyS3 …` (UART3, enabled in the DTB: prediction P-CONSOLE's `ttys3` outcome). U-Boot's autoboot uses `bootdelay=0` with the default abort key `s500`: typing it on U-Boot's serial console during the single poll before `run bootcmd` would stop autoboot. That note is for planning only and authorises nothing ([report](../reports/stock-boot-chain-reconstruction.md)).
