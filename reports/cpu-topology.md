# CPU topology discrepancy

## Established evidence

- Manufacturer product entry: ATM7039S is advertised as quad-core (ID-001).
- Original examined board artifacts and this release's selected DTB declare two Cortex-A9 nodes (DT-002; release DTB hash in the firmware catalogue).
- The pinned vendor defconfig enables SMP, hotplug and `CONFIG_NR_CPUS=4` (`rg35xx_atm7039_defconfig:386–403`). This is a compiled maximum, not a detected count.
- `platsmp-owl.c:202–248` defaults `powersave` false, queries the SCU count, caps it at `nr_cpu_ids`, optionally substitutes two when the early parameter is supplied, and populates the possible mask. Its secondary startup path powers a core and uses a holding-pen handshake. Source availability does not prove successful startup of four cores on the handheld.
- The acquired release's `/uEnv.txt` has no `powersave` parameter. That does not exclude bootloader-added arguments, hotplug policy, other command-line sources or differences in the shipped kernel.
- Bounded decompression identifies the release kernel as 3.10.37 SMP. Embedded IKCONFIG extraction was attempted with the pinned kernel script and failed; do not substitute the source defconfig for the release's missing configuration.

## Competing explanations

| Explanation | Supporting evidence | What remains missing |
|---|---|---|
| DT intentionally describes only two CPUs | Repeated two-node artifacts | Whether this legacy kernel discovers CPUs from SCU independently of those nodes |
| Early power-save argument limits possible mask | Explicit source mechanism | Final release cmdline and a source/binary match for this routine |
| Runtime hotplug/policy limits online CPUs | Source has hotplug support | Runtime possible/present/online masks and policy settings |
| SCU reports fewer cores on the fitted variant | Compatible with limited observations | Actual SCU-derived boot log and silicon revision evidence |
| Board/firmware variant differences | V6C-specific artifacts exist | Controlled comparison of identified boards and firmware |

None is selected as the established explanation. No four-usable-core claim is made.

## Minimal future validation

First seek an existing log tied to a board/release hash. Capture the kernel cmdline, `owl_smp_init_cpus(): ncores ...`, `possible/present/online/offline` sysfs CPU masks, `/proc/cpuinfo`, and any hotplug-policy state. A separately authorized runtime test should only read those normal files; it needs no arbitrary MMIO, clock writes, core-online writes or firmware replacement. Obtain final boot DT/config if already exported. Absence of an exported file is a missing observation, not permission to probe memory.

The three masks distinguish discovery, presence and policy. A four-core SCU count with only two possible CPUs suggests a software cap; four possible/present with two online points toward policy or startup failures; a two-core count needs revision/SCU interpretation research. Each outcome would narrow the ledger without presuming it in advance.

These outcomes are now machine-readable as prediction **P-CPU** in [predictions.json](../evidence/predictions.json) and are evaluated by `tools/runtime_capture.py`. **P-KCONFIG** reads `/proc/config.gz` if the release kernel exports it, which would replace the failed IKCONFIG extraction.
