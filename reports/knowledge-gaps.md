# Knowledge gaps and limits

## Foundational gaps

1. **Target silicon identity:** no package photograph/revision, MIDR, GPU ID or fuse identification was obtained. The manufacturer differentiates ATM7039S, but software uses several related names.
2. **Early boot:** no authenticated Boot ROM description, early loader disassembly, media-search sequence or DDR-training reconstruction. `bootloader.img` remains a distinct dependency in the source recipe.
3. **Final memory map:** zero-size DT placeholders and dynamic AFI/reservation code do not establish actual physical RAM and reserved ranges at handoff.
4. **Safe clocks and power:** source offsets are available; electrical limits, reset defaults, power sequences and rail relationships on ATM7039S are not verified.
5. **Exact shipped software:** no complete stock/Garlic/Koriki image was analyzed. The documented source kernel is not automatically the kernel in any named release.

## Peripheral gaps

DMA request/descriptor/coherency details, pinmux register meanings, physical package pinout, board test pads, USB PHY/role/VBUS, panel initialization/scanout, codec routing, charger policy, suspend retention and multimedia command interfaces need deeper work. GPU integration has concrete source leads, but full replacement needs much more than a kernel module.

Blocks absent or incomplete in the DT may include boot ROM/SRAM, DRAM PHY/training, chip ID/fuses, interconnect/QoS, security engines, proprietary media MMUs and debug infrastructure. Header names are leads, not proofs of target presence.

## Search limits

No genuine complete ATM7039S TRM was authenticated. Search results advertising a PDF were not accepted as manuals. This is a finite-session search result, not proof of nonexistence. Historic web archives, non-English vendor SDK mirrors, Kaiboer F5 Plus firmware and manufacturer-origin board packages remain worthwhile leads.

The upstream driver comparison is pinned to v6.12 for reproducibility. Current PowerVR scope and KNULLI support pages were checked separately, but later upstream Owl changes were not exhaustively compared. GitHub shallow checkouts do not constitute a full history review.

## What was not completed

No whole-image firmware extraction, Ghidra decompilation, full source cross build, electrical validation, exact ATM7039S bitfield/reset audit, complete mainline port or physical test was completed. Tools and provenance are provided to continue these tasks. No hardware verification is claimed and no vendor binary is redistributed.
