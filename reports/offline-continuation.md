# Offline reconstruction: edition 0.2 engineering report

## Result

This continuation anchors the technical reference to a complete public original-RG35XX Koriki release and recovers a concrete AFI producer/consumer interface. It adds reusable binary-analysis tools, a released graphics-stack evidence set, selected S500 field semantics and actual historical-build failure records. No hardware was accessed and no firmware binaries are redistributed.

The verified starting point was main commit `fdec966`: three commits, only the main branch, 40 passing tests, 35 findings, nine contradictions, 17 sources, 65 hashed files, 1,760 register candidates and 51 DT resource tuples. Existing work was retained. A continuation branch `research/offline-boot-evidence` contains the new work; main is not changed or merged by this assignment.

## Significant discoveries

1. **Actual boot media evidence.** The 935 MB compressed Koriki v1.0 image expands to 4,303,355,904 bytes. Its MBR and raw components confirm the recipe offsets `0x200200` and `0x300000` for this release. U-Boot declares load/entry `0x05000000/0x05000040`; that differs from the source configuration and must not be silently equated with it.
2. **AFI writer recovered.** A routine at early-window offset `0x6500` populates 16 bytes at firmware address `0xb4060300`. A helper at `0x9180` converts two parameter bytes into a size shifted by 20, and released U-Boot getters match the source structure. This narrows the early-memory handoff; it does not reconstruct DDR training or prove physical mappings/capacity.
3. **Release identity narrowed.** uImage metadata plus bounded internal decompression identifies Linux 3.10.37, with a GCC 4.9.4/build #75 version string. The V6C bootfix kernel exactly matches this release kernel while its DTB differs. A 2600mAh DTB exists in the release despite its absence from the previously inspected recipe checkout.
4. **Graphics artifacts connected.** A nested ext4 filesystem supplies a hash-identified 3.10.37 PowerVR module and selected 1.14.3625561 libraries. Source bridge packaging/dispatch was mapped; GNU readelf independently confirmed module metadata and library dependencies. No GPU execution or open-renderer success is claimed.
5. **Register semantics made more precise.** Ten S500 GPIO/UART gate/reset positions agree with mainline source and are added as explicitly related-chip observations. The manual's 9-bit special UART divisor versus mainline's 8-bit generic divider is retained as a new contradiction, not filled into the target map.

The underlying materials and earlier discoveries remain credited to Actions, Imagination, macromorgan, rg35xx-cfw contributors, Yohanes Nugroho/Tinyhack, KNULLI, upstream Linux and reMESA. New contributions here are the reproducible analyses and connections between those materials, not claims of having originated their hardware knowledge.

## Implementation and verification

- Added streaming pinned acquisition, primary-MBR/component cataloguing, partition-bounded FAT reads, nested-ext4/ELF inspection, bounded internal gzip analysis and A32 branch/literal inventories.
- Added binary-finding hash/range checks and regression protection for preserving curated provenance during regeneration.
- Expanded the manual through focused AFI, firmware, CPU, CMU, graphics and build reports. Preserved existing register exports and MIT licensing.
- Local result: **66 unit tests pass** with optional firmware dependencies installed, including a real synthetic FAT roundtrip and malformed bounds/CRC/gzip/path/hash tests. Canonical validation and generated freshness pass. Source audit: **76 files, 2,244 references, zero errors**. Seven expected alias/overlap warnings remain.
- Dataset rebuild preserves 123 blocks, 1,760 register candidates and nine original DT comparison changes. New totals: **46 findings, ten contradictions, 20 sources, 270 related-chip field observations**. They measure evidence products, not silicon coverage.
- Independent vendor DTC and the custom parser agree exactly on the release DTB. GNU readelf agrees with pyelftools metadata. Selected A32 PC-relative references were checked using Capstone 5.0.6 and independent instruction-field decoding.

See [validation results](validation-results.md) and [firmware reproduction](firmware-analysis.md). Remote Actions results are reported with the delivered PR after completion; local checks alone do not imply remote CI success.

## Build and research limits

The kernel config and U-Boot recipe config were generated, but image builds failed. Host DTC needed `-fcommon`; both target trees then required compiler compatibility beyond the unmodified GCC-version headers. Exact toolchain hashes, normalized logs and commands are retained. Neither a complete historical build nor source-to-release binary identity was achieved.

A stock/Garlic full image, Boot ROM implementation, full DDR training, final DT/memory reservations, complete GPU protocol and a modern-kernel board port remain unfinished. Wider non-English/archive/other-device discovery produced leads, not authenticated new manuals. Newer upstream history was not systematically audited; v6.12 remains the reproducible comparison. No Ghidra headless workflow was run. This is a completed, testable research phase within a larger assignment, not a claim of comprehensive silicon reconstruction.

## Development implications and next priorities

Developers can now reproduce release-component identities before changing software, compare a concrete handoff ABI, and distinguish source configuration from shipped bytes. The clock-field matrix supplies auditable comparison candidates while recording where apparent agreement breaks down. The graphics set provides a stable starting point for ABI matching instead of mixing arbitrary DDK binaries.

Next: acquire stock/Garlic components; trace the early parameter-block producer and DDR paths; recover final memory fixups; establish a compatible historical build; then expand clocks/power/DMA/display and graphics synchronization. Existing public runtime logs could settle CPU/RAM questions before any physical testing. Future owner-authorized tests should first read normal exported topology, memory and driver metadata; arbitrary MMIO or clock/PMIC changes are not initial diagnostics.
