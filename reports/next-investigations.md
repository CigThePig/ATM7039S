# Prioritized continuation roadmap

Every task begins from the pinned sources and unresolved claims, not a presumed ATM7039S/S500 equivalence. No hardware task below is authorized for execution yet.

| Rank | Concrete task | Expected benefit | Dependencies | Difficulty | Required evidence / completion test | Mode |
|---|---|---|---|---|---|---|
| 1 | Acquire a hash-identified public original-RG35XX boot bundle and component manifest | Anchor all boot claims to actual shipped bytes | Lawful source/download, redistribution review | Moderate | Bootloader/U-Boot/kernel/DT/initrd/modules/userspace hashes, format and release provenance; no execution | Offline |
| 2 | Trace early loader DDR/AFI production and U-Boot fixups | Resolve memory handoff and major closed dependency | Task 1; disassembler and load-address evidence | High | Exact binary hash/offset records; trace DDR size, AFI and final DT changes; distinguish pointer spaces | Offline |
| 3 | Compare selected S500 manual sections against vendor and upstream fields | Turn named offsets into supported register semantics | `s500-pdf` hash; exact source paths | Moderate | Per-field matrix, reset/access evidence on S500, target applicability kept inferred; record differences | Offline |
| 4 | Audit source recipe to complete reproducible old-kernel build | Establish which dependencies can actually build from source | Source/toolchain pins; investigate missing 2600 DTB and boot image names | Moderate–high | Build log/config/toolchain hash, component hashes, no board execution claim | Offline |
| 5 | Resolve CPU masks and final RAM from an existing trustworthy log | Narrow CPU count and actual memory layout | Existing saved log or separately approved diagnostics | Low for log analysis; hardware route pending | Image/board identity, cmdline, SCU count, possible/present/online, final memory resources | Offline first; hardware only with approval |
| 6 | Build a CMU/reset/power-domain compatibility matrix | Unblock most Linux drivers | Manual/source comparison, Task 2/3 | High | Compare masks/parents/gates/acks and silicon-specific branches; no guessed safe rates | Offline |
| 7 | Reconcile MMC DMA routing, slot detect and timing controls | Improve core OS support | CMU/pinctrl/DMA source audit | Moderate | Offset/field/request-ID diff; source unit fixtures; later read-only spare-card transfers under approval | Offline, future hardware |
| 8 | Reconstruct display initialization and framebuffer ownership | Usable modern-kernel route | Memory/power/clock handoff | High | Panel control trace, format/stride/pixel clock units, reserved-memory lifetime, source/binary agreement | Offline, future hardware |
| 9 | Match PowerVR module/userspace ABI and renderer provenance | Preserve achievable acceleration without false open-driver promise | Exact firmware pair; selected DDK 1.14 paths | High | Module/version/IOCTL/allocation/display bridge matrix, licensing; renderer log later | Offline, future hardware |
| 10 | Review reMESA SGX544 compiler/command evidence for transferable knowledge | Avoid duplicating prior reverse engineering | Exact core/DDK/platform comparisons | High | Source-referenced applicability report, no SGX535 command assumptions; identify missing firmware/compiler components | Offline |
| 11 | Recover audio and USB wrapper/PHY dependencies | Complete handheld functionality | PMIC/DMA/display/clock baseline | High | SoC versus external-device boundary, GPIO/polarity/routing, IRQ/clock matrix | Offline, future hardware |
| 12 | Assess safe spare-card validation environment | Enable target observations with rollback | Reviewed images, spare card, explicit permission | Moderate | Concrete artifacts/test script/recovery assessment approved before use; owner's cards excluded | Hardware approval required |

## Additional evidence or equipment worth obtaining

Prefer public boot-only bundles and vendor-origin manuals before more hardware. Exact board-revision photographs already publicly available may resolve fitted parts, but must not be treated as the owner's board. An existing runtime log may answer CPU/RAM questions without firmware changes. A later spare microSD would isolate experiments from the working system. UART equipment should be selected only after pin function and voltage are established; neither opening nor soldering is requested by this roadmap.

The project does not need a firmware rewrite to improve immediately: a reliable image/component manifest, DDR/AFI handoff analysis and a field-by-field S500/ATM7039S compatibility study would remove more uncertainty than speculative driver code.
