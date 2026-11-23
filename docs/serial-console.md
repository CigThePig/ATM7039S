# Serial console: offline evidence

Scope: **Koriki v1.0** release bytes plus the pinned vendor kernel and U-Boot source. Findings: UART-001, UART-002, BOOT-006, STOR-001. No board was opened, probed or connected. This page narrows test V7 (UART feasibility review) and does not authorise any physical work.

## How the console is chosen

| Layer | Evidence | Effect |
|---|---|---|
| `uEnv.txt` | `bootargs=earlyprintk clk_ignore_unused selinux=0 init=/init` | **Disputed (C-UENV).** U-Boot's `bootcmd=run ramboot` never imports it (BOOT-007), yet RetroArch alpha 0.1 depends on its `root=` to boot. P-UENV settles this from `/proc/cmdline`. |
| Release DTB `/chosen` | `bootargs = "earlyprintk clk_ignore_unused selinux=0"` | No `console=`; this is the base command line U-Boot extends if `uEnv.txt` is not applied |
| U-Boot environment | `console=ttyS2,115200`, `baudrate=115200`, `stdout=serial` | U-Boot's own variable; not referenced by the boot commands found |
| U-Boot FDT fixup | Release binary contains `console=ttyS%d`; source `owl_boot_fdt.c:181–183` prepends `console=ttyS<AFI uart_index>` | **The kernel console index comes from the early loader's AFI record at runtime** |
| AFI producer | Early routine copies `uart_index` from `0xb407082c` (BOOT-004) | Value not present in the static window; set at runtime |
| Fallback | `owl_afi.c:33–40` returns 5 when the AFI magic is missing | Source behaviour; release equivalence unproven |
| Userspace | `/etc/inittab`: `getty -L console 0 vt100` | A login prompt is offered on whatever `console=` selects |

The release DTB enables **UART0, UART3 and UART5** and disables UART1, 2, 4 and 6. If the runtime index is 0, 3 or 5, the kernel console has a configured controller. If it is 2, which matches U-Boot's environment default, the kernel has no enabled controller for it. Prediction **P-CONSOLE** in `evidence/predictions.json` records these outcomes. The V3 capture's `/proc/cmdline` settles it with no extra procedure.

## UART over the SD slot (lead only)

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
