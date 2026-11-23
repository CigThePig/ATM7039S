# First-edition results (historical baseline)

This report records edition 0.1. For current continuation results, including a full acquired image and release-specific AFI evidence, see [edition 0.2 engineering report](offline-continuation.md). Counts and uncompleted work below describe the earlier baseline.

# Session results and technical conclusions

This is a coherent research foundation, not completion of a silicon reference manual. No hardware access occurred. The owner's working/failing cards were excluded. The original repository was already public; visibility was preserved, and only original research artifacts/tools were prepared for commits.

## Answers to the ten project questions

1. **How much reliable information already existed?** Substantial fragmented software knowledge: a public board DT, related vendor kernel/U-Boot, a source-build route, mainline S500 blocks and prior stock-firmware research. A detailed related S500 manual is also publicly mirrored. No complete ATM7039S TRM was authenticated.
2. **What did this investigation establish?** Reproducible extraction of 51 DT resource tuples and 1,760 explicit related-header register symbols; nine changed DT nodes; 26 numeric resource pairs against mainline S500; a selected Linux PowerVR DDK path distinct from its sibling Android tree; and a concrete two-core software-limit mechanism. These are new organized analyses of existing evidence, not newly measured silicon facts.
3. **Which subsystems are adequately documented?** Address/source lookup and candidate-driver selection are useful now for ARM core resources, UART/I2C/MMC/DMA, GPIO and CMU. No entire subsystem has a complete hardware-validated ATM7039S programming specification.
4. **What remains poorly understood?** Boot ROM/early DDR, final RAM reservations, target-specific bitfields/reset values, power/charging/suspend, USB PHY/roles, panel scanout, codec routing and media/GPU command interfaces.
5. **Largest obstacles to fully open firmware?** Exact early-loader/DDR dependency, inability to equate source candidates with shipped binaries, board-specific clock/power/display work and separate PowerVR userspace/compiler/firmware dependencies. Kernel-side PowerVR source exists in inspected paths; calling the entire GPU stack closed source obscures this distinction.
6. **How much Owl support could be reused?** Standard ARM blocks and several S500 peripherals are credible candidates, supported by matching resources and selected CMU offsets. Matching addresses do not prove compatible semantics. S700/S900 have distinct CPUs and variant-specific implementations; no reuse percentage is responsible.
7. **Highest-value work for developers?** Link a lawful boot bundle to exact hashes, trace DDR/AFI/final-DT handoff, finish source-build reproducibility, then compare S500 manual fields and CMU/power dependencies before peripheral porting.
8. **Verified versus hypotheses?** Source properties, source-config/DDK version, parsed component metadata and numerical comparisons are verified in their stated scopes. Silicon aliases, actual active cores, compatible drivers, electrical safety and working target acceleration remain inferred or unknown. No hardware validation was performed.
9. **What additional material is needed?** Known-provenance stock/Garlic boot bundles, final runtime DT/logs, actual module/userspace pairs, exact-board identification and preferably an authenticated target manual. A separately approved spare card could support later validation; physical debugging equipment must wait for pin/voltage evidence.
10. **What next?** Follow the ranked [continuation roadmap](next-investigations.md), beginning with offline image provenance and DDR handoff. Reuse existing SGX544 research rather than assuming a new renderer already exists.

## Delivered artifacts

The maintained manual has 30 scoped sections. JSON/CSV/Markdown/C header outputs share a canonical source. The ledger contains 35 findings, nine contradictions, 17 sources and 65 file provenance records. Tools cover numeric DTS/FDT decoding, constants/masks, MBR/uImage/FDT/ELF inspection, property and resource comparison, source auditing, schema/evidence checks and documentation generation. CI runs offline integrity checks and renders a local HTML edition.

## Validation and limits

The source hashes and all 2,198 cited file/line references were checked locally. Independent vendor DTC decoding of the public DTB produced zero property differences against the custom parser. Unit tests cover malformed inputs, geometry, bitmasks, CRCs, MBR bounds, confidence handling and known real-artifact differences. See [validation results](validation-results.md) for the executed checks and recognized warnings.

No complete firmware release image, cross-built kernel, Ghidra routine reconstruction, electrical test or full target driver was delivered. Source and binary licensing remain file-specific; no firmware, library, PDF or disassembly was redistributed.
