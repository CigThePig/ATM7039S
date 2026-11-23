# Validation results

Executed locally on 2026-11-22. These are software/data checks; no target hardware test ran.

| Check | Result | Interpretation |
|---|---|---|
| Unit tests | 40 passed | Parsers, masks, malformed inputs, CRCs, bounds, source auditing, confidence and real extracted artifact comparisons |
| Canonical schema/evidence validation | Pass, zero errors | Model shape, source identities and scope checks |
| Generated reference freshness | Pass | Markdown/CSV/C constants derive from canonical JSON |
| Source-file audit | 65 files / 2,198 references; zero errors | Exact SHA-256/byte size and cited path/line bounds |
| Independent DTB decoding | Pass, zero normalized property differences | Vendor DTC versus custom decoder on the published GPU DTB |
| Gist versus GPU DTB comparison | Nine changed nodes | Repeatable artifact differences, not independent hardware validation |
| S500 numeric-resource comparison | 26 matching base pairs retained | Includes auxiliary resources and differing IRQs/sizes; no blanket compatibility claim |
| Register catalogue | 51 DT tuples + 72 candidate base groups, 1,760 register symbols | Source coverage only; 260 S500-scoped bit-mask observations added where register offsets match |
| HTML generation | Local edition builds | No website deployment; Mermaid source preserved in standalone HTML |

The independent DTC was compiled from the vendor kernel's shipped parser/lexer with host GCC, not from newly invented DTS interpretation rules. Exact commands are in `tools/README.md`. The mainline S500 comparison FDT was synthesized from the pinned upstream DTSI and is not a bootable RG35XX board description.

## Expected warnings retained

The consistency checker reports one register alias at GPIO block offset `0x7c` (`PWM_CTL5` / `SPEED_SENSOR_CTL`) and six overlapping DT resource pairs. They involve shared CMU/GPIO/DMA resources referenced by NAND/watchdog/ISP and shared HDMI/CEC resources. Overlap is not automatically an error: several drivers may reference portions of one block. These warnings remain visible rather than being suppressed or resolved by guessing.

No reset values or target electrical limits were filled from convention. Related-chip registers retain inferred applicability even when exact source extraction is verified. Passing tests cannot establish physical ATM7039S behavior, a valid boot sequence or safe arbitrary MMIO access.

## Reproducibility checks

The pinned-source downloader, independent source audit and source-derived dataset builder are included. The maintained source manifest records exact byte hashes so changed or substituted inputs fail verification. Repository clones are checked against pinned HEADs; file-only retrievals are checked against the manifest. No untrusted input is executed by these tools.

GitHub Actions runs the offline checks and produces an HTML artifact. Its live status is available in the repository Actions page; a local pass is not presented as a remote CI pass until the corresponding run completes.
