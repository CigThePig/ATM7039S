# Review of the owner-supplied GPU research dossier

Source: "Original RG35XX GPU Enablement and ATM7039S Reverse Engineering", prepared 22 November 2026 and supplied by the device owner (`gpu-dossier` in [sources.json](../evidence/sources.json)). The dossier is a documentary review. It does not contain the Ko-fi article text. This page records what it added and where the repository's release-byte evidence agrees with it or corrects it. The dossier itself is not committed.

## Leads it supplied, and what they produced

| Lead | Result |
|---|---|
| [MiaUI-GPU-RG35XX](https://github.com/miaui-cfw/MiaUI-GPU-RG35XX) | Its `src/kernel-rg35xx/` rebuilds the kernel from the same pinned `s500_kernel@81cc77b5` with nine patches recovered from the running vendor kernel. Built here, it recovers 29 of the 96 vendor functions found in no public tree (FW-012). It is a reconstruction, not the vendor tree. |
| MiaUI boot notes | "The pre-loader reads p1:/uImage directly (U-Boot's bootcmd is ramboot, and it does not read uEnv.txt)". Refuted offline in PR #5: the pre-loader performs only raw-sector reads, and U-Boot `mmcboot` imports `uEnv.txt` and loads the images (BOOT-015/016, C-UENV resolved). |
| Koriki December 2023 "stock-like kernel" | Koriki 1.0.3.1 ships ctalon build #40. It comes from the **same vendor product tree** as v1.0's build #75 (99.8% identical function sizes, all 122 vendor functions present) with a different configuration (FW-011). |
| Early Batocera releases on `rg35xx-cfw.github.io` (March–April 2023) | Catalogued. Only RetroArch alpha 0.1 and Batocera Lite alpha 0.2 (12–16 March 2023, Buildroot GCC 7.3.0) ran public-source kernels. From alpha 0.3 on 24 March, every release ships ctalon vendor-tree builds (FW-013). Even alpha 0.1 used a vendor U-Boot (BOOT-008). |

## Corrections from release bytes

| Dossier statement | Scope in the dossier | Release evidence |
|---|---|---|
| GPU node has `gpuvdd-supply = &vdd_gpu_dcdc`; the `vdd-gpu-dcdc` regulator is 0.9–1.25 V, always-on, PWM-controlled (§7.2–7.3) | Source DTS | **Not in the shipped DTB.** Koriki v1.0 and 1.0.3.1 `kernel.dtb` (byte-identical) have neither `gpuvdd-supply` nor the `vdd-core-dcdc`/`vdd-gpu-dcdc` nodes (DT-003). The regulator description applies to the public source only. |
| LCD `pixclock` 47000 ps (§7.5) | Source DTS | Shipped DTB: **50000 ps** (`0xc350`). The source's 47000 is `0xb798`. |
| Later Koriki moved from an S500-derived kernel to a stock-like one (§12) | Release notes and Tinyhack | Release notes stand. At the binary level, the S500-public-source phase lasted only for alpha 0.1–0.2 (March 2023). Every kernel from alpha 0.3 onward, including Koriki 1.0 and 1.0.3.1, is the same vendor tree, so the December change is configuration and init, not a change of source tree (FW-009–FW-013). |
| `SGX_CORE_REV=115`, `SGX_FEATURE_MP_CORE_COUNT=1`, 300 MHz constants (§8.3–8.4) | Source config | Consistent with the repository's GPU findings. They remain compile-time values; no runtime read was done. |
| 256 MB RAM (§3.1) | Retail/community | Still open as contradiction C-RAM. Prediction P-RAM reads it from the V3 capture. |

## Not adopted

The dossier's emulator-performance and history sections are project-reported and are not recorded as findings. Its proposed on-device tests overlap with V3 and the existing predictions. GPU-specific checks (EGL vendor strings, `/proc/pvr/version`) are covered by P-GPU, and anything that runs GPU workloads would be a separate, approved test.
